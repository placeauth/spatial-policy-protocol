"""Tier 3: measure stock Nav2 command output with a fixed-pose test fixture.

No robot dynamics or motion are simulated. The actual ControllerServer runs
FollowPath and emits Twist commands; only its supplied operating limit changes.
"""
import importlib.util
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

import pytest

if any(importlib.util.find_spec(name) is None for name in ("rclpy", "nav2_msgs")):
    if os.environ.get("SPP_REQUIRE_ROS") == "1":
        raise RuntimeError("Tier 3 requires ROS 2/Nav2")
    pytest.skip("ROS 2 unavailable: motion-limit test", allow_module_level=True)

import rclpy
from ament_index_python.packages import get_package_prefix
from geometry_msgs.msg import PoseStamped, TransformStamped, Twist
from lifecycle_msgs.msg import Transition
from lifecycle_msgs.srv import ChangeState
from nav2_msgs.action import FollowPath
from nav_msgs.msg import Odometry
from rclpy.action import ActionClient
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from tf2_ros import StaticTransformBroadcaster

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference" / "admission" / "src"))
sys.path.insert(0, str(ROOT / "reference" / "ros2-enforcer"))
from spp_admission.models import AdmissionProfile, EvidenceBinding
from spp_enforcer.mapping import map_profile
from spp_enforcer.node import Nav2Enforcer


def test_live_nav2_speed_change(tmp_path):
    prefix = get_package_prefix("nav2_controller")
    get_package_prefix("nav2_regulated_pure_pursuit_controller")
    namespace = f"/spp_motion_{uuid.uuid4().hex}"
    context = Context()
    rclpy.init(context=context)
    node = rclpy.create_node("motion_fixture", namespace=namespace, context=context)
    executor = SingleThreadedExecutor(context=context)
    executor.add_node(node)
    samples = []
    node.create_subscription(
        Twist, "cmd_vel",
        lambda msg: samples.append((time.monotonic(), math.hypot(msg.linear.x, msg.linear.y, msg.linear.z))),
        100,
    )
    broadcaster = StaticTransformBroadcaster(node)
    transform = TransformStamped()
    transform.header.stamp = node.get_clock().now().to_msg()
    transform.header.frame_id = "odom"
    transform.child_frame_id = "base_link"
    transform.transform.rotation.w = 1.0
    broadcaster.sendTransform(transform)
    odom_publisher = node.create_publisher(Odometry, "odom", 10)
    def publish_pose():
        odom = Odometry()
        odom.header.stamp = node.get_clock().now().to_msg()
        odom.header.frame_id = "odom"
        odom.child_frame_id = "base_link"
        odom.pose.pose.orientation.w = 1.0
        odom_publisher.publish(odom)
    node.create_timer(0.025, publish_pose)
    log_path = tmp_path / "controller.log"
    process = None
    goal_handle = None
    def until(condition, seconds=10):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if process.poll() is not None:
                pytest.fail(log_path.read_text())
            executor.spin_once(timeout_sec=0.025)
            if condition():
                return True
        return condition()
    def profile(speed, space):
        # Trusted profile fixtures exercise enforcement, not evidence creation.
        return AdmissionProfile(
            "ADMITTED", "robot:motion", "clinic", space, 1, "test-evidence",
            EvidenceBinding("robot:motion", "build", "controller", "policy", "env", "plan"),
            {"guarantees": [{"id": "movement.max_speed", "operator": "<=", "value": speed}]},
        )
    try:
        with log_path.open("w") as log:
            process = subprocess.Popen(
                [str(Path(prefix) / "lib/nav2_controller/controller_server"), "--ros-args",
                 "-r", f"__ns:={namespace}", "--params-file",
                 str(Path(__file__).with_name("motion_controller.yaml"))],
                stdout=log, stderr=subprocess.STDOUT,
            )
        lifecycle = node.create_client(ChangeState, "controller_server/change_state")
        assert lifecycle.wait_for_service(timeout_sec=10), log_path.read_text()
        for transition in (Transition.TRANSITION_CONFIGURE, Transition.TRANSITION_ACTIVATE):
            request = ChangeState.Request()
            request.transition.id = transition
            future = lifecycle.call_async(request)
            assert until(future.done), log_path.read_text()
            assert future.result().success, log_path.read_text()
        adapter = Nav2Enforcer(node, "speed_limit")
        assert until(lambda: node.count_subscribers(f"{namespace}/speed_limit") == 1)
        initial = profile(1.0, "clinic/lobby")
        assert adapter.apply(initial) == map_profile(initial)
        navigation = ActionClient(node, FollowPath, "follow_path")
        assert navigation.wait_for_server(timeout_sec=5)
        goal = FollowPath.Goal()
        goal.controller_id = "FollowPath"
        goal.goal_checker_id = "goal_checker"
        goal.path.header.frame_id = "odom"
        for index in range(81):
            pose = PoseStamped()
            pose.header.frame_id = "odom"
            pose.pose.position.x = index * 0.1
            pose.pose.orientation.w = 1.0
            goal.path.poses.append(pose)
        future = navigation.send_goal_async(goal)
        assert until(future.done)
        goal_handle = future.result()
        assert goal_handle.accepted, log_path.read_text()
        result = goal_handle.get_result_async()
        assert until(lambda: len(samples) >= 10), log_path.read_text()
        before = [speed for _, speed in samples[-10:]]
        assert all(0.9 <= speed <= 1.0 + 1e-6 for speed in before), before
        assert not result.done(), log_path.read_text()
        updated = profile(0.5, "clinic/patient-wing")
        assert adapter.apply(updated) == map_profile(updated)
        changed_at = time.monotonic()
        # Allow 0.3 s for DDS/callback scheduling, then measure a full second.
        # This explicitly does not assert an instantaneous actuation deadline.
        def post_samples():
            return [speed for stamp, speed in samples if stamp >= changed_at + 0.3]
        assert until(lambda: len(post_samples()) >= 20, seconds=3), log_path.read_text()
        after = post_samples()
        assert all(math.isfinite(speed) and 0.45 <= speed <= 0.5 + 1e-6 for speed in after), after
        assert not result.done(), log_path.read_text()
        print(f"Same active FollowPath goal: pre={min(before):.6f}..{max(before):.6f} m/s ({len(before)} commands); "
              f"post={min(after):.6f}..{max(after):.6f} m/s ({len(after)} commands)")
    finally:
        if goal_handle is not None and process is not None and process.poll() is None:
            cancellation = goal_handle.cancel_goal_async()
            until(cancellation.done, seconds=2)
        if process is not None and process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        executor.shutdown()
        node.destroy_node()
        context.shutdown()
