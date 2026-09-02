from __future__ import annotations

import copy
from pathlib import Path

import pytest

from spp.evaluator import PolicyError, evaluate, load_policy


ROOT = Path(__file__).resolve().parents[1]
POLICY = load_policy(ROOT / "examples" / "hospital.yaml")


def request(space: str, family: str, name: str, **context) -> dict:
    return {
        "spp_version": "0.1",
        "request_id": f"test-{space}-{name}",
        "actor": {"id": "robot:test:1", "type": "delivery_robot"},
        "space": space,
        "action": {"family": family, "name": name},
        "context": context,
    }


def test_lobby_inherits_root_permit() -> None:
    result = evaluate(POLICY, request("clinic/lobby", "movement", "enter"))
    assert result["decision"] == "permit"
    assert result["matched_space"] == "clinic"


def test_child_deny_overrides_root_permit() -> None:
    result = evaluate(POLICY, request("clinic/pharmacy", "movement", "enter"))
    assert result["decision"] == "deny"
    assert result["matched_space"] == "clinic/pharmacy"


def test_condition_is_not_a_permit() -> None:
    result = evaluate(POLICY, request("clinic/staff-corridor", "movement", "enter"))
    assert result["decision"] == "conditional"
    assert result["requires"] == ["clinic.staff_escort"]


def test_verified_authorization_satisfies_condition() -> None:
    result = evaluate(
        POLICY,
        request(
            "clinic/staff-corridor",
            "movement",
            "enter",
            authorizations=["clinic.staff_escort"],
        ),
    )
    assert result["decision"] == "permit"
    assert result["requires"] == []


def test_obligation_inherits_separately_from_data_deny() -> None:
    capture = evaluate(
        POLICY,
        request("clinic/patient-wing/room-312", "sensing", "video_capture"),
    )
    storage = evaluate(
        POLICY,
        request("clinic/patient-wing/room-312", "data", "video_store"),
    )
    assert capture["decision"] == "permit"
    assert capture["obligations"] == [{"type": "data.no_retention", "value": True}]
    assert storage["decision"] == "deny"


def test_unmatched_action_denies_by_default() -> None:
    result = evaluate(POLICY, request("clinic/lobby", "sensing", "thermal"))
    assert result["decision"] == "deny"
    assert result["matched_space"] is None


def test_exact_action_precedes_wildcard() -> None:
    policy = copy.deepcopy(POLICY)
    policy["spaces"][0]["rules"].insert(
        0,
        {
            "action": {"family": "movement", "name": "*"},
            "decision": "deny",
            "reason": "Generic movement deny.",
        },
    )
    result = evaluate(policy, request("clinic/lobby", "movement", "enter"))
    assert result["decision"] == "permit"


def test_unknown_space_fails_closed() -> None:
    with pytest.raises(PolicyError, match="unknown space"):
        evaluate(POLICY, request("clinic/unknown", "movement", "enter"))

