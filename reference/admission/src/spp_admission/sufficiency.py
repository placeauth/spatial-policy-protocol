"""Conservative evidence reuse for trusted, local reference orchestration.

Digests establish internal consistency, not issuer authenticity. Callers must
obtain source records from a trusted test runner and authenticate RobotState.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, ValidationError

from .engine import _test_for, derive_plan, digest
from .models import RobotState


def _validate(document: dict[str, Any], name: str) -> None:
    schema = Path(__file__).resolve().parents[4] / "schema" / name
    Draft202012Validator(json.loads(schema.read_text(encoding="utf-8"))).validate(document)


@dataclass(frozen=True)
class EvidenceRecord:
    """Original policy, plan and bundle; retain originals across transitions."""

    requirements: dict[str, Any]
    plan: dict[str, Any]
    evidence: dict[str, Any]


@dataclass(frozen=True)
class Sufficiency:
    requirement_id: str
    sufficient: bool
    reason: str
    evidence_id: str | None = None


def _time(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timezone required")
    return result


def _number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _entails(source: dict, target: dict) -> bool:
    """A passing bound proves that bound, not an unrecorded measured value."""
    op, old, new = source["operator"], source["value"], target["value"]
    if op != target["operator"]:
        return False
    if op in ("<=", ">="):
        return (_number(old) and _number(new)
                and (old <= new if op == "<=" else old >= new))
    if op == "prohibited":
        return old is True and new is True
    return type(old) is type(new) and old == new


def _record_error(record: EvidenceRecord, robot: RobotState, now: datetime,
                  required_assurance_level: str = "E2") -> str | None:
    req, plan, evidence = record.requirements, record.plan, record.evidence
    try:
        for document, schema in ((req, "place-requirement-set"),
                                 (plan, "conformance-plan"), (evidence, "evidence-bundle")):
            _validate(document, schema + ".schema.json")
        if digest({k: v for k, v in evidence.items() if k != "evidence_digest"}) != evidence.get("evidence_digest"):
            return "evidence_digest_mismatch"
        if digest({k: v for k, v in plan.items() if k != "plan_digest"}) != plan.get("plan_digest"):
            return "plan_digest_mismatch"
        # An explicitly supplied policy digest remains a local opaque identifier.
        # Do not accept it as a substitute for hashing the actual source contents.
        if req.get("policy_digest"):
            return "opaque_policy_digest"
        if digest(req) != plan["policy_digest"]:
            return "policy_digest_mismatch"
        for field in ("place", "space", "policy_version", "environment_digest"):
            if plan[field] != req[field]:
                return "source_scope_mismatch"
        expected = {
            "actor_id": robot.actor_id, "build_fingerprint": robot.build_fingerprint,
            "controller_fingerprint": robot.controller_fingerprint,
            "policy_digest": plan["policy_digest"],
            "environment_digest": robot.environment_digest, "plan_digest": plan["plan_digest"],
        }
        if evidence["binding"] != expected:
            return "evidence_binding_mismatch"
        top = {
            "actor_id": robot.actor_id, "robot_build_fingerprint": robot.build_fingerprint,
            "controller_configuration_fingerprint": robot.controller_fingerprint,
            "embodiment": robot.embodiment, "environment_digest": robot.environment_digest,
            "policy_digest": plan["policy_digest"], "policy_version": req["policy_version"],
            "conformance_plan_digest": plan["plan_digest"], "challenge": plan["challenge"],
        }
        if any(evidence[k] != v for k, v in top.items()) or plan["environment_digest"] != robot.environment_digest:
            return "evidence_binding_mismatch"
        issued, expires = _time(evidence["issued_at"]), _time(evidence["valid_until"])
        if issued > now or expires <= issued:
            return "invalid_validity_window"
        if expires <= now:
            return "stale_evidence"
        levels = ["E0", "E1", "E2", "E3", "E4"]
        if levels.index(evidence["evidence_assurance_level"]) < max(2, levels.index(plan["required_assurance_level"]), levels.index(required_assurance_level)):
            return "insufficient_assurance"
        requirements = {r["id"]: r for r in req["requirements"]}
        tests = {t["requirement_id"]: t for t in plan["selected_tests"]}
        results = {r["requirement_id"]: r for r in evidence["test_results"]}
        if len(requirements) != len(req["requirements"]) or len(tests) != len(plan["selected_tests"]) or len(results) != len(evidence["test_results"]):
            return "duplicate_requirement_or_result"
        if set(results) != set(tests):
            return "result_coverage_mismatch"
        for rid, test in tests.items():
            if test != _test_for(requirements[rid]) or results[rid]["test_id"] != test["test_id"]:
                return "test_mapping_mismatch"
    except (ValidationError, KeyError, ValueError, TypeError, OverflowError):
        return "malformed_source_record"
    return None


def assess_sufficiency(destination: dict[str, Any], robot: RobotState,
                       records: list[EvidenceRecord], *, now: datetime | None = None,
                       required_assurance_level: str = "E2") -> list[Sufficiency]:
    """Return one ordered reuse/retest explanation per destination requirement.

    Invalid source evidence causes retesting, never a reused guarantee. An
    invalid destination raises ValueError; callers must stop admission on error.
    """
    _validate(destination, "place-requirement-set.schema.json")
    ids = [r["id"] for r in destination["requirements"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate destination requirement")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if required_assurance_level not in ("E0", "E1", "E2", "E3", "E4"):
        raise ValueError("unknown assurance level")
    checked = [(record, _record_error(record, robot, now, required_assurance_level)) for record in records]
    decisions = []
    for target in destination["requirements"]:
        rid = target["id"]
        try:
            _test_for(target)
        except KeyError:
            decisions.append(Sufficiency(rid, False, "unsupported_requirement"))
            continue
        reason, chosen = "missing_evidence", None
        for record, error in checked:
            if error:
                reason = error
                continue
            source = next((r for r in record.requirements["requirements"] if r["id"] == rid), None)
            if source is None:
                continue
            if (record.requirements["place"] != destination["place"] or
                    destination["environment_digest"] != robot.environment_digest or
                    source["action"] != target["action"] or source.get("unit") != target.get("unit")):
                reason = "scope_mismatch"
                continue
            result = next((r for r in record.evidence["test_results"] if r["requirement_id"] == rid), None)
            if result is None:
                if reason == "missing_evidence":
                    reason = "no_direct_test"
            elif result["passed"] is not True:
                reason = "failed_source_test"
            elif not _entails(source, target):
                reason = "insufficient_proven_bound"
            else:
                chosen, reason = record.evidence["evidence_id"], "sufficient"
                break
        decisions.append(Sufficiency(rid, chosen is not None, reason, chosen))
    return decisions


def derive_requalification_plan(destination: dict[str, Any], robot: RobotState,
                                records: list[EvidenceRecord], *, challenge: str | None = None,
                                now: datetime | None = None) -> tuple[dict[str, Any], list[Sufficiency]]:
    """Build an existing ConformancePlan from validated source evidence.

    Unsupported requirements stay unresolved without manufacturing a test.
    Use original records again at the next boundary; do not promote a reused
    guarantee to fresh evidence. This helper does not consume replay challenges.
    """
    decisions = assess_sufficiency(destination, robot, records, now=now)
    if destination["environment_digest"] != robot.environment_digest:
        raise ValueError("destination environment does not match current robot state")
    supported = {d.requirement_id for d in decisions if d.reason != "unsupported_requirement"}
    subset = dict(destination, requirements=[r for r in destination["requirements"] if r["id"] in supported])
    plan = derive_plan(subset, robot, challenge=challenge)
    reused = [d.requirement_id for d in decisions if d.sufficient]
    plan["selected_tests"] = [t for t in plan["selected_tests"] if t["requirement_id"] not in reused]
    plan["reused_guarantees"] = reused
    plan["unresolved_guarantees"] = [d.requirement_id for d in decisions if not d.sufficient]
    plan["policy_digest"] = destination.get("policy_digest") or digest(destination)
    plan.pop("plan_digest")
    plan["plan_digest"] = digest(plan)
    return plan, decisions
