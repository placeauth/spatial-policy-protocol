"""Tier 2a: real ControllerServer -> pluginlib-loaded TEST observation plugin."""
import importlib.util
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
        raise RuntimeError("Tier 2a requires ROS 2/Nav2")
    pytest.skip("ROS 2 unavailable: controller-boundary test", allow_module_level=True)

import rclpy
from ament_index_python.packages import get_package_prefix
from lifecycle_msgs.msg import Transition
from lifecycle_msgs.srv import ChangeState
from nav2_msgs.msg import SpeedLimit
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import QoSProfile, DurabilityPolicy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference" / "admission" / "src"))
sys.path.insert(0, str(ROOT / "reference" / "ros2-enforcer"))
from spp_admission.models import AdmissionProfile, EvidenceBinding
from spp_enforcer.mapping import map_profile
from spp_enforcer.node import Nav2Enforcer


def test_degraded_reaches_controller_plugin(tmp_path):
    # Missing binary/plugin is a failure when ROS is present, not a hidden skip.
    prefix = get_package_prefix("nav2_controller")
    get_package_prefix("spp_boundary_observer")
    executable = str(Path(prefix) / "lib/nav2_controller/controller_server")
    namespace = f"/spp_boundary_{uuid.uuid4().hex}"
    context = Context()
    rclpy.init(context=context)
    node = rclpy.create_node("observer_client", namespace=namespace, context=context)
    executor = SingleThreadedExecutor(context=context)
    executor.add_node(node)
    observations = []
    node.create_subscription(
        SpeedLimit, "spp_boundary_observed", observations.append,
        QoSProfile(depth=10, durability=DurabilityPolicy.TRANSIENT_LOCAL),
    )
    log_path = tmp_path / "controller.log"
    process = None
    def until(condition, seconds=10):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if process.poll() is not None:
                pytest.fail(log_path.read_text())
            executor.spin_once(timeout_sec=0.05)
            if condition():
                return True
        return condition()
    try:
        with log_path.open("w") as log:
            process = subprocess.Popen(
                [executable, "--ros-args", "-r", f"__ns:={namespace}", "--params-file",
                 str(Path(__file__).parent / "plugins/controller.yaml")],
                stdout=log, stderr=subprocess.STDOUT,
            )
        client = node.create_client(ChangeState, "controller_server/change_state")
        assert client.wait_for_service(timeout_sec=10), log_path.read_text()
        request = ChangeState.Request()
        request.transition.id = Transition.TRANSITION_CONFIGURE
        future = client.call_async(request)
        assert until(future.done), log_path.read_text()
        assert future.result().success, log_path.read_text()
        # Configure is sufficient: official ControllerServer creates its real
        # SpeedLimit subscription here. Never activate or submit a path.
        adapter = Nav2Enforcer(node, "speed_limit")
        assert until(lambda: node.count_subscribers(f"{namespace}/speed_limit") == 1)
        assert until(lambda: node.count_publishers(f"{namespace}/spp_boundary_observed") == 1)
        assert not observations
        profile = AdmissionProfile(
            "DEGRADED", "robot:boundary", "clinic", "clinic/corridor", 1, "test-evidence",
            EvidenceBinding("robot:boundary", "build", "controller", "policy", "env", "plan"),
            {"guarantees": [{"id": "movement.max_speed", "operator": "<=", "value": 1.0}]},
            ["movement.max_speed<=0.5"],
        )
        plan = map_profile(profile)
        assert plan.navigation_allowed and plan.max_speed_mps == 0.5
        assert adapter.apply(profile) == plan
        assert until(lambda: bool(observations)), log_path.read_text()
        assert len(observations) == 1
        assert observations[0].speed_limit == 0.5
        assert observations[0].percentage is False
        print("Real ControllerServer -> plugin setSpeedLimit: 0.5 m/s, percentage=False")
    finally:
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
