from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import replace
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


REQUIREMENT = {"id": "movement.max_speed", "requirement_version": "1.0", "action": "movement.enter", "operator": "<=", "value": .8, "unit": "m/s"}
ROBOT = RobotState("robot:humanoid", "build:1", "controller:1", "demo_humanoid", "sha256:env",
                   {"gait.maximum_speed_mps": .6})


class Provider:
    def __init__(self, provider_id="provider", embodiment="demo_humanoid", assurance="E2", priority=10):
        self.descriptor = ConformanceProviderDescriptor(
            provider_id, "1.0", frozenset({"movement.max_speed"}), frozenset({embodiment}),
            frozenset({assurance}), "behavioral_test", priority,
            supported_requirement_versions={"movement.max_speed": frozenset({"1.0"})},
        )

    def evaluate(self, requirement, subject):
        return ConformanceProviderResult(self.descriptor.provider_id, "1.0", requirement["id"], True,
                                         .6, next(iter(self.descriptor.supported_assurance_levels)), "behavioral_test",
                                         requirement_version="1.0", unit="m/s")


class InvalidResultProvider(Provider):
    def __init__(self, **changes):
        super().__init__()
        self._changes = changes

    def evaluate(self, requirement, subject):
        return replace(super().evaluate(requirement, subject), **self._changes)


def test_registration_duplicate_and_compatibility_filtering():
    provider = Provider()
    registry = ConformanceProviderRegistry([provider])
    with pytest.raises(ValueError, match="already registered"):
        registry.register(provider)
    assert registry.select(REQUIREMENT, "other").reason == "unsupported_embodiment"
    assert registry.select({"id": "unsupported.example"}, ROBOT.embodiment).reason == "unsupported_requirement"
    assert registry.select(REQUIREMENT, ROBOT.embodiment, "E3").reason == "insufficient_assurance"


def test_descriptor_requires_explicit_versions_for_every_supported_requirement():
    descriptor = ConformanceProviderDescriptor(
        "incomplete", "1.0", frozenset({"movement.max_speed"}), frozenset({ROBOT.embodiment}),
        frozenset({"E2"}), "behavioral_test",
    )
    provider = type("IncompleteProvider", (), {"descriptor": descriptor})()
    with pytest.raises(ValueError, match="invalid provider descriptor"):
        ConformanceProviderRegistry([provider])


def test_exact_requirement_version_and_assurance_filtering_are_required():
    registry = ConformanceProviderRegistry([Provider()])
    assert registry.select(REQUIREMENT, ROBOT.embodiment, "E2").resolved
    assert registry.select(dict(REQUIREMENT, requirement_version="2.0"), ROBOT.embodiment).reason == "incompatible_requirement_version"
    assert registry.select(REQUIREMENT, "mobile_robot").reason == "unsupported_embodiment"
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


@pytest.mark.parametrize(("changes", "reason"), [
    ({"provider_id": "other"}, "provider_result_provider_id_mismatch"),
    ({"provider_version": "2.0"}, "provider_result_provider_version_mismatch"),
    ({"requirement_id": "data.video_retention"}, "provider_result_requirement_id_mismatch"),
    ({"requirement_version": "2.0"}, "provider_result_requirement_version_mismatch"),
    ({"assurance_level": "E1"}, "provider_result_assurance_mismatch"),
    ({"evidence_type": "external_observation"}, "provider_result_evidence_type_mismatch"),
    ({"unit": "km/h"}, "provider_result_unit_mismatch"),
])
def test_invalid_provider_result_fails_closed_before_evidence_conversion(changes, reason):
    registry = ConformanceProviderRegistry([InvalidResultProvider(**changes)])
    with pytest.raises(ValueError, match=reason):
        registry.evaluate(REQUIREMENT, ROBOT)
