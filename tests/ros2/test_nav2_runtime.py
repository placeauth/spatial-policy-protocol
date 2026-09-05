"""Real ROS 2 pub/sub tests, separate from transport-double unit tests."""
import importlib.util
import os
from pathlib import Path
import sys
import time
import uuid

import pytest

missing = [name for name in ("rclpy", "nav2_msgs") if importlib.util.find_spec(name) is None]
if missing:
    if os.environ.get("SPP_REQUIRE_ROS") == "1":
        raise RuntimeError(f"Required ROS runtime packages missing: {missing}")
    pytest.skip("ROS 2/Nav2 unavailable: real runtime tests require ROS", allow_module_level=True)

# When packages exist, import/runtime failures are errors, never hidden skips.
import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from nav2_msgs.msg import SpeedLimit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference" / "admission" / "src"))
sys.path.insert(0, str(ROOT / "reference" / "ros2-enforcer"))
from spp_admission.models import AdmissionProfile, EvidenceBinding
from spp_enforcer.mapping import map_profile
from spp_enforcer.node import Nav2Enforcer


def spin_until(executor, condition, seconds=5.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        executor.spin_once(timeout_sec=0.05)
        if condition():
            return True
    return condition()


@pytest.mark.parametrize("status,expected", [("ADMITTED", 1.0), ("DEGRADED", 0.5), ("DENIED", None)])
def test_real_speed_limit_publication(status, expected):
    context = Context()
    rclpy.init(context=context)
    executor = SingleThreadedExecutor(context=context)
    sender = rclpy.create_node("spp_runtime_sender", context=context)
    receiver = rclpy.create_node("spp_runtime_receiver", context=context)
    topic = f"/spp_runtime_test_{uuid.uuid4().hex}/speed_limit"
    messages = []
    subscription = receiver.create_subscription(SpeedLimit, topic, messages.append, 10)
    executor.add_node(sender)
    executor.add_node(receiver)
    try:
        adapter = Nav2Enforcer(sender, topic)
        assert spin_until(executor, lambda: sender.count_subscribers(topic) == 1), "DDS discovery timed out"
        profile = AdmissionProfile(
            status, "robot:runtime", "clinic", "clinic/corridor", 1, "test-evidence",
            EvidenceBinding("robot:runtime", "build", "controller", "policy", "env", "plan"),
            {"guarantees": [{"id": "movement.max_speed", "operator": "<=", "value": 1.0}]},
            ["movement.max_speed<=0.5"] if status == "DEGRADED" else [],
        )
        mapped = map_profile(profile)
        applied = adapter.apply(profile)
        assert applied == mapped
        assert applied.navigation_allowed is (expected is not None)
        if expected is None:
            # First prove the observer is live, then drain that separate control
            # publication before checking DENIED on the SAME transport path.
            profile.status = "ADMITTED"
            assert adapter.apply(profile).navigation_allowed
            assert spin_until(executor, lambda: len(messages) == 1)
            messages.clear()
            profile.status = "DENIED"
            assert not adapter.apply(profile).navigation_allowed
            assert not spin_until(executor, lambda: bool(messages), seconds=0.75)
            print("DENIED: no SpeedLimit observed during 0.75 s; navigation_allowed=False")
        else:
            assert spin_until(executor, lambda: bool(messages)), "SpeedLimit was not received"
            assert len(messages) == 1
            assert isinstance(messages[0], SpeedLimit)
            assert messages[0].percentage is False
            assert messages[0].speed_limit == expected
            print(f"{status}: actual nav2_msgs/SpeedLimit observed: {messages[0].speed_limit} m/s, percentage=False")
    finally:
        receiver.destroy_subscription(subscription)
        executor.shutdown()
        sender.destroy_node()
        receiver.destroy_node()
        context.shutdown()
