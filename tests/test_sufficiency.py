from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/admission/src"))
from spp_admission import EvidenceRecord, ReplayRegistry, assess_sufficiency, derive_requalification_plan
from spp_admission.engine import admit, build_evidence, derive_plan, digest, execute_plan, load_requirement_set
from spp_admission.models import RobotState
from spp.evaluator import validate_document

NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)


def resign(document, field):
    document[field] = digest({k: v for k, v in document.items() if k != field})


@pytest.fixture
def sample():
    req = load_requirement_set(ROOT / "demo/admission/lobby.yaml")
    robot = RobotState("robot:1", "build:1", "config:1", "demo_mobile_base",
                       req["environment_digest"], {"movement.max_speed": 0.6})
    plan = derive_plan(req, robot, challenge="nonce:source")
    evidence = build_evidence(req, plan, robot, execute_plan(plan, robot, req))
    evidence.update(issued_at=NOW.isoformat(), valid_until=(NOW + timedelta(minutes=15)).isoformat())
    resign(evidence, "evidence_digest")
    return req, robot, EvidenceRecord(deepcopy(req), plan, evidence)


def test_equal_bound_reused_and_schema_compatible(sample):
    req, robot, record = sample
    plan, decisions = derive_requalification_plan(req, robot, [record], now=NOW)
    assert decisions[0].sufficient
    assert plan["selected_tests"] == []
    assert plan["reused_guarantees"] == ["movement.max_speed"]
    validate_document(plan, "conformance-plan.schema.json")


@pytest.mark.parametrize("operator,source,target,expected", [
    ("<=", .8, .9, True), ("<=", .8, .7, False), ("<=", .8, .8, True),
    (">=", 1.2, 1.1, True), (">=", 1.2, 1.3, False), (">=", 1.2, 1.2, True),
    ("=", 0, 0, True), ("=", 0, False, False), ("=", 0, 1, False),
    ("prohibited", True, True, True), ("prohibited", True, False, False),
    ("<=", .8, True, False), ("<=", .8, float("nan"), False),
])
def test_proven_bounds(sample, operator, source, target, expected):
    req, robot, _ = sample
    req["requirements"][0].update(operator=operator, value=source)
    plan = derive_plan(req, robot)
    evidence = build_evidence(req, plan, robot, [{"test_id": "test:speed-bound", "requirement_id": "movement.max_speed", "passed": True}])
    destination = deepcopy(req)
    destination["requirements"][0]["value"] = target
    assert assess_sufficiency(destination, robot, [EvidenceRecord(req, plan, evidence)])[0].sufficient is expected


@pytest.mark.parametrize("field", ["actor_id", "build_fingerprint", "controller_fingerprint", "environment_digest", "embodiment"])
def test_state_change_invalidates(sample, field):
    req, robot, record = sample
    decision = assess_sufficiency(req, replace(robot, **{field: "changed"}), [record], now=NOW)[0]
    assert not decision.sufficient
    assert decision.reason == "evidence_binding_mismatch"


@pytest.mark.parametrize("mutation,reason", [
    ("tamper", "evidence_digest_mismatch"), ("policy", "policy_digest_mismatch"),
    ("plan", "plan_digest_mismatch"), ("missing", "result_coverage_mismatch"),
    ("duplicate", "duplicate_requirement_or_result"), ("failed", "failed_source_test"),
    ("test_id", "test_mapping_mismatch"), ("assurance", "insufficient_assurance"),
    ("naive_time", "malformed_source_record"), ("no_expiry", "malformed_source_record"),
    ("future", "invalid_validity_window"), ("top_actor", "evidence_binding_mismatch"),
])
def test_invalid_source_never_reused(sample, mutation, reason):
    req, robot, record = sample
    e = record.evidence
    if mutation == "tamper": e["test_results"][0]["passed"] = False
    elif mutation == "policy": record.requirements["policy_version"] += 1
    elif mutation == "plan": record.plan["challenge"] = "changed"
    elif mutation == "missing": e["test_results"] = []
    elif mutation == "duplicate": e["test_results"].append(deepcopy(e["test_results"][0]))
    elif mutation == "failed": e["test_results"][0]["passed"] = False
    elif mutation == "test_id": e["test_results"][0]["test_id"] = "other"
    elif mutation == "assurance": e["evidence_assurance_level"] = "E1"
    elif mutation == "naive_time": e["issued_at"] = "2030-01-01T00:00:00"
    elif mutation == "no_expiry": e.pop("valid_until")
    elif mutation == "future": e["issued_at"] = (NOW + timedelta(seconds=1)).isoformat()
    elif mutation == "top_actor": e["actor_id"] = "other"
    if mutation != "tamper": resign(e, "evidence_digest")
    decision = assess_sufficiency(req, robot, [record], now=NOW)[0]
    assert (decision.sufficient, decision.reason) == (False, reason)


@pytest.mark.parametrize("minutes,expected", [(14, True), (15, False), (16, False)])
def test_expiry_boundary(sample, minutes, expected):
    req, robot, record = sample
    assert assess_sufficiency(req, robot, [record], now=NOW + timedelta(minutes=minutes))[0].sufficient is expected


@pytest.mark.parametrize("field,value", [("action", "movement.exit"), ("unit", "km/h")])
def test_requirement_scope(sample, field, value):
    req, robot, record = sample
    req["requirements"][0][field] = value
    assert assess_sufficiency(req, robot, [record], now=NOW)[0].reason == "scope_mismatch"


def test_cross_place_not_reused(sample):
    req, robot, record = sample
    req["place"] = "another-place"
    assert assess_sufficiency(req, robot, [record], now=NOW)[0].reason == "scope_mismatch"


def test_stricter_bound_does_not_use_unrecorded_capability(sample):
    req, robot, record = sample
    req["requirements"][0]["value"] = .7  # Actual .6 was not recorded in source test.
    plan, decisions = derive_requalification_plan(req, robot, [record], now=NOW)
    assert decisions[0].reason == "insufficient_proven_bound"
    assert len(plan["selected_tests"]) == 1


def test_unsupported_stays_unresolved_and_denies(sample):
    req, robot, _ = sample
    req["requirements"].append(dict(id="unknown.requirement", action="movement.enter", operator="=", value=True))
    plan, decisions = derive_requalification_plan(req, robot, [])
    assert decisions[-1].reason == "unsupported_requirement"
    evidence = build_evidence(req, plan, robot, execute_plan(plan, robot, req))
    assert admit(req, plan, evidence, robot, ReplayRegistry()).status == "DENIED"


def test_deterministic_decisions_and_no_input_mutation(sample):
    req, robot, record = sample
    before = deepcopy(record)
    assert assess_sufficiency(req, robot, [record], now=NOW) == assess_sufficiency(req, robot, [record], now=NOW)
    assert record == before


def test_reused_only_bundle_does_not_renew_proof(sample):
    req, robot, record = sample
    plan, _ = derive_requalification_plan(req, robot, [record], now=NOW)
    evidence = build_evidence(req, plan, robot, [])
    result = assess_sufficiency(req, robot, [EvidenceRecord(req, plan, evidence)])
    assert result[0].reason == "no_direct_test"


def test_destination_environment_mismatch_stops_planning(sample):
    req, robot, _ = sample
    req["environment_digest"] = "changed"
    with pytest.raises(ValueError, match="environment"):
        derive_requalification_plan(req, robot, [])


def test_duplicate_destination_stops_planning(sample):
    req, robot, _ = sample
    req["requirements"].append(deepcopy(req["requirements"][0]))
    with pytest.raises(ValueError, match="duplicate"):
        derive_requalification_plan(req, robot, [])


def test_source_plan_mapping_tampered_with_recomputed_digests(sample):
    req, robot, record = sample
    record.plan["selected_tests"][0]["expected"] = "<= 999"
    resign(record.plan, "plan_digest")
    record.evidence["conformance_plan_digest"] = record.plan["plan_digest"]
    record.evidence["binding"]["plan_digest"] = record.plan["plan_digest"]
    resign(record.evidence, "evidence_digest")
    assert assess_sufficiency(req, robot, [record], now=NOW)[0].reason == "test_mapping_mismatch"


def test_valid_candidate_after_invalid_candidate(sample):
    req, robot, record = sample
    bad = deepcopy(record)
    bad.evidence["actor_id"] = "tampered"
    assert assess_sufficiency(req, robot, [bad, record], now=NOW)[0].sufficient


def test_opaque_digest_cannot_substitute_for_source_hash(sample):
    req, robot, record = sample
    record.requirements["policy_digest"] = "external:opaque"
    assert assess_sufficiency(req, robot, [record], now=NOW)[0].reason == "opaque_policy_digest"


@pytest.mark.parametrize("scenario,reason", [
    ("normal", "sufficient"), ("tamper", "evidence_digest_mismatch"),
    ("stale", "stale_evidence"), ("controller-change", "evidence_binding_mismatch"),
])
def test_transition_demo_exercises_actual_plans(scenario, reason):
    import runpy
    demo = runpy.run_path(str(ROOT / "demo/requalification/run_demo.py"))
    trace = demo["run"](scenario)
    assert [s["status"] for s in trace] == ["ADMITTED", "ADMITTED", "ADMITTED", "DENIED"]
    assert trace[1]["assessment"][0]["reason"] == reason
    assert len(trace[1]["tests"]) == (0 if scenario == "normal" else 1)
    assert len(trace[2]["tests"]) == 4
    assert len(trace[3]["tests"]) == 1
    assert len(trace[3]["reused"]) == 3
