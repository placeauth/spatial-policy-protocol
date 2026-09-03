from __future__ import annotations

import copy
import json
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference" / "admission" / "src"))

from spp_admission.engine import (  # noqa: E402
    admit, build_evidence, compute_requirement_delta, derive_plan,
    execute_plan, load_requirement_set,
)
from spp_admission.models import RobotState  # noqa: E402
from spp.evaluator import validate_document  # noqa: E402


REQ = load_requirement_set(ROOT / "demo" / "admission" / "patient-wing.yaml")


def state(**changes: object) -> RobotState:
    capabilities = {
        "movement.max_speed": 0.6,
        "human_separation": 1.5,
        "sensing.facial_recognition": False,
        "data.video_retention": 0,
    }
    capabilities.update({k: v for k, v in changes.items() if k in capabilities})
    return RobotState(
        "robot:test:1",
        str(changes.get("build_fingerprint", "build:v1")),
        str(changes.get("controller_fingerprint", "controller:v1")),
        "demo_mobile_base",
        str(changes.get("environment_digest", "sha256:site-model-clinic-v1")),
        capabilities,
    )


def issue(robot: RobotState, requirements=REQ, proven=None):
    plan = derive_plan(requirements, robot, proven_guarantees=proven, challenge="nonce:test")
    results = execute_plan(plan, robot, requirements)
    evidence = build_evidence(requirements, plan, robot, results)
    return plan, evidence, admit(requirements, plan, evidence, robot)


def test_full_admission() -> None:
    assert issue(state())[2].status == "ADMITTED"


def test_degraded_video_restriction() -> None:
    profile = issue(state(**{"data.video_retention": 5}))[2]
    assert profile.status == "DEGRADED"
    assert "sensing.video.capture=disabled" in profile.restrictions


def test_essential_safety_failure_denies() -> None:
    assert issue(state(human_separation=0.7))[2].status == "DENIED"


@pytest.mark.parametrize("change", [
    {"build_fingerprint": "build:v2"},
    {"controller_fingerprint": "controller:v2"},
    {"environment_digest": "sha256:other-site"},
])
def test_wrong_binding_denies(change: dict[str, str]) -> None:
    plan, evidence, _ = issue(state())
    altered = state(**change)
    assert admit(REQ, plan, evidence, altered).status == "DENIED"


def test_wrong_policy_version_denies() -> None:
    plan, evidence, _ = issue(state())
    altered = copy.deepcopy(REQ)
    altered["policy_version"] = 99
    assert admit(altered, plan, evidence, state()).status == "DENIED"


def test_malformed_and_stale_evidence_deny() -> None:
    plan, evidence, _ = issue(state())
    malformed = copy.deepcopy(evidence)
    malformed.pop("binding")
    assert admit(REQ, plan, malformed, state()).status == "DENIED"
    stale = copy.deepcopy(evidence)
    stale["valid_until"] = "2000-01-01T00:00:00Z"
    assert admit(REQ, plan, stale, state()).status == "DENIED"


def test_replayed_challenge_denies() -> None:
    plan, evidence, _ = issue(state())
    plan["challenge"] = "nonce:other"
    assert admit(REQ, plan, evidence, state()).status == "DENIED"


def test_delta_reuses_proven_and_selects_only_new_tests() -> None:
    lobby = load_requirement_set(ROOT / "demo" / "admission" / "lobby.yaml")
    prior, _, profile = issue(state(), lobby)
    profile_dict = asdict(profile)
    delta = compute_requirement_delta(profile_dict, REQ)
    assert {item["classification"] for item in delta if item["requirement_id"] == "movement.max_speed"} == {"REUSED"}
    plan = derive_plan(REQ, state(), proven_guarantees=profile_dict["operating_profile"]["guarantees"], challenge="nonce:test")
    assert plan["reused_guarantees"] == ["movement.max_speed"]
    assert "movement.max_speed" not in [test["requirement_id"] for test in plan["selected_tests"]]


def test_admission_objects_match_schemas() -> None:
    robot_state = state()
    plan, evidence, profile = issue(robot_state)
    validate_document(REQ, "place-requirement-set.schema.json")
    validate_document(plan, "conformance-plan.schema.json")
    validate_document(evidence, "evidence-bundle.schema.json")
    validate_document(asdict(profile), "admission-profile.schema.json")


def test_admission_fixtures_cover_valid_and_invalid_shapes() -> None:
    valid = json.loads((ROOT / "tests" / "fixtures" / "admission" / "valid-requirement-set.json").read_text())
    validate_document(valid, "place-requirement-set.schema.json")
    invalid = json.loads((ROOT / "tests" / "fixtures" / "admission" / "invalid-evidence.json").read_text())
    with pytest.raises(Exception):
        validate_document(invalid, "evidence-bundle.schema.json")
