import builtins
import copy
import importlib
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference" / "admission" / "src"))
sys.path.insert(0, str(ROOT / "reference" / "ros2-enforcer"))

from spp_admission.models import AdmissionProfile, EvidenceBinding
from spp_enforcer.mapping import map_profile
from spp_enforcer.node import Nav2Enforcer


def profile(status="ADMITTED", speeds=(1.0,), restrictions=None):
    return AdmissionProfile(
        status, "robot:test", "clinic", "clinic/lobby", 1, "digest",
        EvidenceBinding("robot:test", "build", "controller", "policy", "env", "plan"),
        {"guarantees": [{"id": "movement.max_speed", "operator": "<=", "value": speed}
                        for speed in speeds]}, restrictions or [],
    )


def test_admitted_speed():
    plan = map_profile(profile())
    assert plan.navigation_allowed and plan.max_speed_mps == 1.0


def test_degraded_restriction_and_multiple_bounds():
    p = profile("DEGRADED", (1.0, 0.8), ["movement.max_speed<=0.5"])
    p.operating_profile["restrictions"] = ["movement.max_speed<=0.6"]
    plan = map_profile(p)
    assert plan.navigation_allowed and plan.max_speed_mps == 0.5
    p.operating_profile["guarantees"].reverse()
    assert map_profile(p) == plan


def test_denied_never_enables_even_with_speed():
    plan = map_profile(profile("DENIED"))
    assert not plan.navigation_allowed and plan.max_speed_mps is None


def test_no_speed_override_ignores_unrelated_guarantees():
    p = profile(speeds=())
    p.operating_profile["guarantees"] = [{"id": "human_separation", "value": 1.5}]
    plan = map_profile(p)
    assert plan.navigation_allowed and plan.max_speed_mps is None


@pytest.mark.parametrize("value", ["0.5", -0.5, float("nan"), float("inf"), True])
def test_invalid_speed_fails_closed(value):
    plan = map_profile(profile(speeds=(value,)))
    assert not plan.navigation_allowed and plan.reasons == ("invalid_speed_bound",)


def test_zero_is_not_nav2_stop():
    assert map_profile(profile(speeds=(0,))).reasons == ("zero_speed_requires_stop",)


def test_unsupported_restrictions_and_bounds_fail_closed():
    p = profile("DEGRADED", restrictions=["sensing.video.capture=disabled"])
    assert not map_profile(p).navigation_allowed
    p.restrictions = ["movement.max_speed<=bad"]
    assert map_profile(p).reasons == ("invalid_speed_bound",)
    p.restrictions = []
    p.operating_profile["guarantees"][0]["operator"] = ">="
    assert not map_profile(p).navigation_allowed
    p.operating_profile["guarantees"][0].update(operator="<=", unit="km/h")
    assert not map_profile(p).navigation_allowed
    assert not map_profile({}).navigation_allowed


def test_deterministic_and_profile_unchanged():
    p = profile()
    before = copy.deepcopy(p)
    assert map_profile(p) == map_profile(p)
    assert p == before


def test_imports_without_ros_and_clear_runtime_error(monkeypatch):
    original = builtins.__import__
    def no_ros(name, *args, **kwargs):
        if name.split(".")[0] in {"rclpy", "nav2_msgs"}:
            raise ImportError("ROS deliberately unavailable")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", no_ros)
    import spp
    import spp_admission
    import spp_enforcer.node as runtime
    importlib.reload(runtime)
    with pytest.raises(RuntimeError, match="sourced ROS 2 environment"):
        runtime.Nav2Enforcer(None)


def test_runtime_wiring_with_test_doubles(monkeypatch):
    # Contract test only: not a ROS runtime or transport validation.
    sent = []
    publisher = SimpleNamespace(get_subscription_count=lambda: 1, publish=sent.append)
    class Node:
        def create_publisher(self, message, topic, depth):
            assert message is SpeedLimit and topic == "robot/speed_limit" and depth == 10
            return publisher
        def get_clock(self):
            return SimpleNamespace(now=lambda: SimpleNamespace(to_msg=lambda: "stamp"))
    class SpeedLimit:
        def __init__(self):
            self.header = SimpleNamespace(stamp=None)
    monkeypatch.setitem(sys.modules, "rclpy.node", SimpleNamespace(Node=Node))
    monkeypatch.setitem(sys.modules, "nav2_msgs.msg", SimpleNamespace(SpeedLimit=SpeedLimit))
    adapter = Nav2Enforcer(Node(), "robot/speed_limit")
    assert adapter.apply(profile()).navigation_allowed
    assert sent[0].speed_limit == 1.0 and sent[0].percentage is False
    assert sent[0].header.stamp == "stamp"
    assert not adapter.apply(profile("DENIED")).navigation_allowed
    assert adapter.apply(profile(speeds=())).max_speed_mps is None
    assert len(sent) == 1
    publisher.get_subscription_count = lambda: 0
    assert not adapter.apply(profile()).navigation_allowed
    publisher.get_subscription_count = lambda: 1
    def broken(message):
        raise RuntimeError("transport failure")
    publisher.publish = broken
    assert adapter.apply(profile()).reasons == ("nav2_publish_failed",)
