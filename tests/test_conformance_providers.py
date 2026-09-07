from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/admission/src"))
sys.path.insert(0, str(ROOT / "demo/conformance_provider"))

from gait_speed_provider import GaitSpeedProvider  # noqa: E402
from spp_admission import (  # noqa: E402
    ConformanceProviderDescriptor, ConformanceProviderRegistry,
    ConformanceProviderResult, ReplayRegistry, admit, build_evidence, derive_plan,
)
from spp_admission.models import RobotState  # noqa: E402


REQUIREMENT = {"id": "movement.max_speed", "action": "movement.enter", "operator": "<=", "value": .8}
ROBOT = RobotState("robot:humanoid", "build:1", "controller:1", "demo_humanoid", "sha256:env",
                   {"gait.maximum_speed_mps": .6})


class Provider:
    def __init__(self, provider_id="provider", embodiment="demo_humanoid", assurance="E2", priority=10):
        self.descriptor = ConformanceProviderDescriptor(
            provider_id, "1.0", frozenset({"movement.max_speed"}), frozenset({embodiment}),
            frozenset({assurance}), "behavioral_test", priority,
        )

    def evaluate(self, requirement, subject):
        return ConformanceProviderResult(self.descriptor.provider_id, "1.0", requirement["id"], True,
                                         .6, self.descriptor.supported_assurance_levels.copy().pop(), "behavioral_test")


def test_registration_duplicate_and_compatibility_filtering():
    provider = Provider()
    registry = ConformanceProviderRegistry([provider])
    with pytest.raises(ValueError, match="already registered"):
        registry.register(provider)
    assert registry.select(REQUIREMENT, "other").reason == "unsupported_embodiment"
    assert registry.select({"id": "unsupported.example"}, ROBOT.embodiment).reason == "unsupported_requirement"
    assert registry.select(REQUIREMENT, ROBOT.embodiment, "E3").reason == "insufficient_assurance"


def test_selection_uses_priority_then_stable_provider_id():
    high = Provider("high", priority=20)
    zeta = Provider("zeta", priority=10)
    alpha = Provider("alpha", priority=10)
    assert ConformanceProviderRegistry([zeta, alpha, high]).select(REQUIREMENT, ROBOT.embodiment).provider.descriptor.provider_id == "high"
    assert ConformanceProviderRegistry([zeta, alpha]).select(REQUIREMENT, ROBOT.embodiment).provider.descriptor.provider_id == "alpha"


def test_external_provider_executes_and_feeds_existing_evidence_and_admission():
    provider = GaitSpeedProvider()
    registry = ConformanceProviderRegistry([provider])
    selection, result = registry.evaluate(REQUIREMENT, ROBOT)
    assert selection.provider is provider and result and result.passed
    requirements = {
        "spp_version": "0.1", "admission_version": "0.1-experimental", "requirement_set_id": "urn:spp:provider-test",
        "place": "clinic", "space": "clinic/patient-wing", "policy_version": 1, "environment_digest": ROBOT.environment_digest,
        "requirements": [dict(REQUIREMENT, essential=True)],
    }
    plan = derive_plan(requirements, ROBOT, challenge="nonce:provider-test")
    evidence = build_evidence(requirements, plan, ROBOT,
                              [result.to_evidence_result(plan["selected_tests"][0]["test_id"])], now=datetime.now(timezone.utc))
    assert admit(requirements, plan, evidence, ROBOT, ReplayRegistry()).status == "ADMITTED"
