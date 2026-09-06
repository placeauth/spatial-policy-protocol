from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference" / "admission" / "src"))

from spp_admission import (  # noqa: E402
    DEFAULT_REQUIREMENT_MAPPING_REGISTRY,
    ConformanceProvider,
    ReplayRegistry,
    RequirementMappingRegistry,
    admit,
    build_evidence,
    derive_plan,
    execute_plan,
)
from spp_admission.models import RobotState  # noqa: E402


REQUIREMENTS = {
    "spp_version": "0.1", "admission_version": "0.1-experimental",
    "requirement_set_id": "urn:spp:requirements:embodiment-test",
    "place": "place:clinic", "space": "clinic/lobby", "policy_version": 1,
    "environment_digest": "sha256:clinic-layout-v1",
    "requirements": [
        {"id": "movement.max_speed", "action": "movement", "operator": "<=", "value": 0.5, "unit": "m/s", "essential": True},
        {"id": "human_separation", "action": "human_interaction", "operator": ">=", "value": 1.0, "unit": "m", "essential": True},
        {"id": "sensing.facial_recognition", "action": "sensing", "operator": "prohibited", "value": True, "essential": True},
    ],
}


def robot(embodiment: str) -> RobotState:
    capabilities = {
        "demo_mobile_base": {
            "movement.max_speed": .5, "human_separation": 1.2,
            "sensing.facial_recognition": False,
        },
        "demo_humanoid": {
            "gait.maximum_speed_mps": .5, "body.minimum_human_clearance_m": 1.2,
            "vision_pipeline.facial_recognition_enabled": False,
        },
    }[embodiment]
    return RobotState(f"robot:{embodiment}", "build:1", "controller:1", embodiment,
                      REQUIREMENTS["environment_digest"], capabilities)


def test_same_requirements_select_distinct_mobile_and_humanoid_mechanisms():
    mobile = robot("demo_mobile_base")
    humanoid = robot("demo_humanoid")
    mobile_plan = derive_plan(REQUIREMENTS, mobile, challenge="nonce:mobile")
    humanoid_plan = derive_plan(REQUIREMENTS, humanoid, challenge="nonce:humanoid")

    assert [test["adapter"] for test in mobile_plan["selected_tests"]] == [
        "speed-bound", "separation-bound", "facial-recognition",
    ]
    assert [test["adapter"] for test in humanoid_plan["selected_tests"]] == [
        "gait-speed-bound", "body-proximity-bound", "vision-pipeline-privacy",
    ]


def test_both_embodiments_execute_selected_tests_and_produce_admitted_profiles():
    for embodiment in ("demo_mobile_base", "demo_humanoid"):
        state = robot(embodiment)
        plan = derive_plan(REQUIREMENTS, state, challenge=f"nonce:{embodiment}")
        results = execute_plan(plan, state, REQUIREMENTS)
        evidence = build_evidence(REQUIREMENTS, plan, state, results, now=datetime.now(timezone.utc))
        profile = admit(REQUIREMENTS, plan, evidence, state, ReplayRegistry())

        assert all(result["passed"] for result in results)
        assert profile.status == "ADMITTED"


def test_registry_prefers_higher_priority_then_provider_id_deterministically():
    factory = lambda requirement: {"test_id": "test:custom", "requirement_id": requirement["id"]}
    registry = RequirementMappingRegistry((
        ConformanceProvider("zeta", "movement.max_speed", "demo", "E2", 10, factory),
        ConformanceProvider("alpha", "movement.max_speed", "demo", "E2", 10, factory),
        ConformanceProvider("highest", "movement.max_speed", "demo", "E2", 20, factory),
    ))
    selection = registry.select(REQUIREMENTS["requirements"][0], "demo")
    assert selection.provider and selection.provider.provider_id == "highest"

    tied = RequirementMappingRegistry((
        ConformanceProvider("zeta", "movement.max_speed", "demo", "E2", 10, factory),
        ConformanceProvider("alpha", "movement.max_speed", "demo", "E2", 10, factory),
    ))
    assert tied.select(REQUIREMENTS["requirements"][0], "demo").provider.provider_id == "alpha"


def test_registry_registers_providers_and_reports_unsupported_or_underassured_matches():
    factory = lambda requirement: {"test_id": "test:custom", "requirement_id": requirement["id"]}
    registry = RequirementMappingRegistry()
    registry.register(ConformanceProvider("limited", "movement.max_speed", "demo", "E1", 1, factory))

    assert not registry.select(REQUIREMENTS["requirements"][0], "demo", "E2").resolved
    assert not registry.select(REQUIREMENTS["requirements"][0], "different").resolved
    assert registry.select(REQUIREMENTS["requirements"][0], "demo", "E1").resolved


def test_unsupported_embodiment_stays_explicitly_unresolved_without_synthetic_test():
    state = RobotState("robot:unknown", "build:1", "controller:1", "unsupported",
                       REQUIREMENTS["environment_digest"], {})
    plan = derive_plan(REQUIREMENTS, state, challenge="nonce:unsupported")
    assert plan["selected_tests"] == []
    assert plan["unresolved_guarantees"] == [r["id"] for r in REQUIREMENTS["requirements"]]


def test_mobile_registry_preserves_the_preexisting_mapping_and_provider_is_resolved():
    requirement = REQUIREMENTS["requirements"][0]
    selection = DEFAULT_REQUIREMENT_MAPPING_REGISTRY.select(requirement, "demo_mobile_base")
    assert selection.provider and selection.provider.provider_id == "mobile_speed_bound"
    assert derive_plan(REQUIREMENTS, robot("demo_mobile_base"), challenge="nonce:legacy")["selected_tests"][0]["test_id"] == "test:speed-bound"
