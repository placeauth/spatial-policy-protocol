"""Adversarial admission tests independent of whether the planner was invoked."""
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import runpy
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/admission/src"))
from spp_admission import EvidenceRecord, ReplayRegistry, admit_evidence_backed, derive_requalification_plan
from spp_admission.engine import admit, build_evidence, derive_plan, digest, execute_plan, load_requirement_set
from spp_admission.models import RobotState
from spp.evaluator import validate_document

NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)


def rehash(document, field):
    document[field] = digest({k: v for k, v in document.items() if k != field})


@pytest.fixture
def setup():
    req = load_requirement_set(ROOT / "demo/admission/lobby.yaml")
    robot = RobotState("robot:1", "build:1", "controller:1", "demo_mobile_base",
                       req["environment_digest"], {"movement.max_speed": .6})
    source_plan = derive_plan(req, robot, challenge="source")
    source = build_evidence(req, source_plan, robot, execute_plan(source_plan, robot, req), now=NOW)
    record = EvidenceRecord(deepcopy(req), source_plan, source)
    plan, decisions = derive_requalification_plan(req, robot, [record], now=NOW, challenge="destination")
    assert decisions[0].sufficient
    evidence = build_evidence(req, plan, robot, [], now=NOW)
    return req, robot, record, plan, evidence


def evaluate(setup, *, now=NOW, records=None, registry=None):
    req, robot, record, plan, evidence = setup
    return admit_evidence_backed(req, plan, evidence, robot,
                                 [record] if records is None else records,
                                 registry or ReplayRegistry(), now=now)


def test_valid_reuse_has_schema_valid_profile(setup):
    profile = evaluate(setup)
    assert profile.status == "ADMITTED"
    validate_document(asdict(profile), "admission-profile.schema.json")


def test_expired_between_planning_and_admission(setup):
    req, robot, _, plan, _ = setup
    later = NOW + timedelta(minutes=15)
    # Fresh destination evidence is valid; ONLY the historical source expired.
    setup = (*setup[:4], build_evidence(req, plan, robot, [], now=later))
    assert evaluate(setup, now=later).reason_codes == ["stale_evidence"]


@pytest.mark.parametrize("field", ["actor_id", "build_fingerprint", "controller_fingerprint", "environment_digest", "embodiment"])
def test_changed_state_rejects_reused_source_with_fresh_current_bundle(setup, field):
    req, robot, record, _, _ = setup
    robot = replace(robot, **{field: "changed"})
    if field == "environment_digest":
        req["environment_digest"] = robot.environment_digest
    # Bypass the planner by constructing a plan claiming reuse anyway.
    plan = derive_plan(req, robot, challenge="current")
    plan.update(selected_tests=[], unresolved_guarantees=[], reused_guarantees=["movement.max_speed"])
    rehash(plan, "plan_digest")
    evidence = build_evidence(req, plan, robot, [], now=NOW)
    profile = evaluate((req, robot, record, plan, evidence))
    assert profile.reason_codes == ["evidence_binding_mismatch"]
    assert profile.operating_profile == {}


@pytest.mark.parametrize("value", [.7, 1.0])
def test_changed_destination_requires_current_plan_even_when_looser(setup, value):
    req, *_ = setup
    req["requirements"][0]["value"] = value
    assert evaluate(setup).reason_codes == ["policy_digest_mismatch"]


@pytest.mark.parametrize("value,expected", [(.7, "DENIED"), (1.0, "ADMITTED")])
def test_current_destination_bound_independently_checked(setup, value, expected):
    req, robot, record, _, _ = setup
    req["requirements"][0]["value"] = value
    plan = derive_plan(req, robot, challenge="changed-policy")
    plan.update(selected_tests=[], unresolved_guarantees=[], reused_guarantees=["movement.max_speed"])
    rehash(plan, "plan_digest")
    evidence = build_evidence(req, plan, robot, [], now=NOW)
    profile = evaluate((req, robot, record, plan, evidence))
    assert profile.status == expected
    if expected == "DENIED":
        assert profile.reason_codes == ["insufficient_proven_bound"]


@pytest.mark.parametrize("target", ["source", "fresh"])
def test_tampered_evidence_rejected(setup, target):
    evidence = setup[2].evidence if target == "source" else setup[4]
    evidence["embodiment"] = "tampered"
    assert evaluate(setup).reason_codes == ["evidence_digest_mismatch"]


@pytest.mark.parametrize("mutation,reason", [
    ("source_plan", "plan_digest_mismatch"), ("source_policy", "policy_digest_mismatch"),
    ("assurance", "insufficient_assurance"), ("expiry_missing", "malformed_source_record"),
    ("failed", "failed_source_test"), ("missing_result", "result_coverage_mismatch"),
    ("action", "scope_mismatch"), ("unit", "scope_mismatch"),
])
def test_source_record_adversaries(setup, mutation, reason):
    req, robot, record, plan, evidence = setup
    if mutation == "source_plan": record.plan["challenge"] = "other"
    elif mutation == "source_policy": record.requirements["policy_version"] += 1
    elif mutation == "assurance": record.evidence["evidence_assurance_level"] = "E1"
    elif mutation == "expiry_missing": record.evidence.pop("valid_until")
    elif mutation == "failed": record.evidence["test_results"][0]["passed"] = False
    elif mutation == "missing_result": record.evidence["test_results"] = []
    elif mutation in ("action", "unit"):
        req["requirements"][0][mutation] = "different"
        plan["policy_digest"] = digest(req)
        rehash(plan, "plan_digest")
        evidence = build_evidence(req, plan, robot, [], now=NOW)
    rehash(record.evidence, "evidence_digest")
    assert evaluate((req, robot, record, plan, evidence)).reason_codes == [reason]


def test_destination_assurance_applies_to_reused_proof(setup):
    req, robot, record, plan, _ = setup
    plan["required_assurance_level"] = "E3"
    rehash(plan, "plan_digest")
    evidence = build_evidence(req, plan, robot, [], now=NOW)
    evidence["evidence_assurance_level"] = "E3"
    rehash(evidence, "evidence_digest")
    assert evaluate((req, robot, record, plan, evidence)).reason_codes == ["insufficient_assurance"]


@pytest.mark.parametrize("records", [[], [{}], [{"id": "movement.max_speed", "capabilities": {"movement.max_speed": .1}}]])
def test_guarantee_dictionaries_cannot_bypass_provenance(setup, records):
    assert evaluate(setup, records=records).status == "DENIED"


def test_legacy_path_is_explicitly_distinct(setup):
    req, robot, _, plan, evidence = setup
    assert admit(req, plan, evidence, robot, ReplayRegistry(), now=NOW).status == "ADMITTED"
    assert evaluate(setup, records=[]).reason_codes == ["missing_evidence"]


@pytest.mark.parametrize("mutation", ["omit", "duplicate", "unknown", "overlap"])
def test_forged_coverage_cannot_bypass(setup, mutation):
    req, robot, record, plan, _ = setup
    if mutation == "omit": plan["reused_guarantees"] = []
    elif mutation == "duplicate": plan["reused_guarantees"] *= 2
    elif mutation == "unknown": plan["reused_guarantees"].append("unknown")
    else: plan["unresolved_guarantees"] = ["movement.max_speed"]
    rehash(plan, "plan_digest")
    evidence = build_evidence(req, plan, robot, [], now=NOW)
    assert evaluate((req, robot, record, plan, evidence)).reason_codes == ["result_coverage_mismatch"]


def test_replay_claim_after_validation_and_shared_with_legacy(setup):
    registry = ReplayRegistry()
    assert evaluate(setup, records=[], registry=registry).status == "DENIED"
    assert evaluate(setup, registry=registry).status == "ADMITTED"
    assert evaluate(setup, registry=registry).reason_codes == ["replayed_challenge"]
    req, robot, _, plan, evidence = setup
    assert admit(req, plan, evidence, robot, registry, now=NOW).reason_codes == ["replayed_challenge"]


def test_repeatability_and_no_mutation(setup):
    before = deepcopy(setup)
    assert evaluate(setup) == evaluate(setup)
    assert setup == before


def test_cannot_repackage_reused_only_bundle_as_fresh_proof(setup):
    req, robot, _, plan, evidence = setup
    assert evaluate(setup, records=[EvidenceRecord(req, plan, evidence)]).reason_codes == ["no_direct_test"]


def test_validation_unavailable_fails_closed(setup, monkeypatch):
    from spp_admission import sufficiency
    def unavailable(*args):
        raise OSError("schema unavailable")
    monkeypatch.setattr(sufficiency, "_validate", unavailable)
    assert evaluate(setup).reason_codes == ["malformed_source_record"]


def test_invalid_time_fails_closed(setup):
    assert evaluate(setup, now=NOW.replace(tzinfo=None)).status == "DENIED"


def test_toctou_demo_denies_after_planner_accepts_reuse():
    demo = runpy.run_path(str(ROOT / "demo/requalification/run_demo.py"))
    trace = demo["run"]("toctou")
    assert len(trace) == 2
    assert trace[-1]["assessment"][0]["sufficient"]
    assert trace[-1]["tests"] == []
    assert trace[-1]["status"] == "DENIED"
    assert trace[-1]["reasons"] == ["evidence_binding_mismatch"]


@pytest.mark.parametrize("mutation,reason", [
    ("expired", "stale_evidence"), ("future", "invalid_validity_window"),
    ("assurance", "insufficient_assurance"), ("challenge", "evidence_binding_mismatch"),
    ("plan", "plan_digest_mismatch"),
])
def test_fresh_evidence_checked_independently(setup, mutation, reason):
    evidence = setup[4]
    if mutation == "expired":
        evidence["issued_at"] = (NOW - timedelta(minutes=16)).isoformat()
        evidence["valid_until"] = NOW.isoformat()
    elif mutation == "future": evidence["issued_at"] = (NOW + timedelta(seconds=1)).isoformat()
    elif mutation == "assurance": evidence["evidence_assurance_level"] = "E1"
    elif mutation == "challenge": evidence["challenge"] = "wrong"
    else: setup[3]["space"] = "tampered"
    rehash(evidence, "evidence_digest")
    assert evaluate(setup).reason_codes == [reason]


def test_historical_accepted_nonce_can_support_new_challenge(setup):
    req, robot, record, _, _ = setup
    registry = ReplayRegistry()
    source_profile = admit_evidence_backed(req, record.plan, record.evidence, robot,
                                           replay_registry=registry, now=NOW)
    assert source_profile.status == "ADMITTED"
    assert evaluate(setup, registry=registry).status == "ADMITTED"


@pytest.mark.parametrize("essential,expected", [(True, "DENIED"), (False, "DEGRADED")])
def test_essential_failures_cannot_use_degraded_escape(essential, expected):
    req = load_requirement_set(ROOT / "demo/admission/patient-wing.yaml")
    req["requirements"] = [req["requirements"][-1]]
    req["requirements"][0]["essential"] = essential
    robot = RobotState("robot:1", "build:1", "controller:1", "demo_mobile_base",
                       req["environment_digest"], {"data.video_retention": 5})
    plan = derive_plan(req, robot)
    evidence = build_evidence(req, plan, robot, execute_plan(plan, robot, req), now=NOW)
    profile = admit_evidence_backed(req, plan, evidence, robot, now=NOW, replay_registry=ReplayRegistry())
    assert profile.status == expected


def test_nonessential_invalid_reuse_still_denies(setup):
    req, robot, record, plan, _ = setup
    req["requirements"][0].update(essential=False, degraded_restriction="movement=disabled")
    plan["policy_digest"] = digest(req)
    rehash(plan, "plan_digest")
    evidence = build_evidence(req, plan, robot, [], now=NOW)
    assert evaluate((req, robot, record, plan, evidence), records=[]).status == "DENIED"


@pytest.mark.parametrize("bad", [None, [], {}, {"policy_version": "invalid"}])
def test_malformed_destination_cannot_issue_permission(setup, bad):
    _, robot, record, plan, evidence = setup
    assert admit_evidence_backed(bad, plan, evidence, robot, [record], now=NOW).status == "DENIED"


def test_source_records_are_not_mutated_during_rejection(setup):
    before = deepcopy(setup)
    assert evaluate(setup, now=NOW + timedelta(minutes=16)).status == "DENIED"
    assert setup == before
