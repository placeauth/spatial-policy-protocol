"""Provenance-enforced admission for locally trusted evidence issuers."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from jsonschema import ValidationError

from .engine import ReplayRegistry, admit
from .models import AdmissionProfile, EvidenceBinding, RobotState
from .sufficiency import EvidenceRecord, _record_error, assess_sufficiency
from .trust import (
    SignedEvidence,
    SignedEvidenceRecord,
    TrustedIssuerRegistry,
    evidence_scope,
    verify_signed_evidence,
)


def _deny(requirements: dict, evidence: dict, robot: RobotState,
          reasons: list[str], unresolved: list[str] | None = None) -> AdmissionProfile:
    """Validation failures must never carry partially accepted guarantees."""
    return AdmissionProfile(
        "DENIED", robot.actor_id, requirements.get("place", "unknown"),
        requirements.get("space", "unknown"), requirements.get("policy_version", 1),
        evidence.get("evidence_digest", ""), EvidenceBinding("", "", "", "", "", ""),
        {}, [], unresolved or [], reasons,
    )


def admit_evidence_backed(
    requirement_set: dict[str, Any], plan: dict[str, Any], evidence: dict[str, Any],
    robot: RobotState, source_records: list[EvidenceRecord] | None = None,
    replay_registry: ReplayRegistry | None = None, *, now: datetime | None = None,
) -> AdmissionProfile:
    """Revalidate ALL relied-on evidence against admission-time inputs.

    The destination, RobotState, time and evidence issuers must be supplied by
    the trusted admission service, not authenticated merely by this function.
    Planner-provided guarantees or sufficiency verdicts are never accepted.
    Existing wire objects and the legacy admit API remain compatible.
    """
    # Snapshot mutable caller data for this synchronous evaluation. This is not
    # a lock on an external runtime; deployments must serialize state updates.
    requirement_set, plan, evidence, robot, source_records = deepcopy(
        (requirement_set, plan, evidence, robot, source_records)
    )
    denial_req = requirement_set if isinstance(requirement_set, dict) else {}
    denial_evidence = evidence if isinstance(evidence, dict) else {}
    try:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise ValueError("admission time must be timezone-aware")
        current = EvidenceRecord(requirement_set, plan, evidence)
        error = _record_error(current, robot, now)
        if error:
            return _deny(denial_req, denial_evidence, robot, [error])

        requirements = {r["id"]: r for r in requirement_set["requirements"]}
        tested = {t["requirement_id"] for t in plan["selected_tests"]}
        reused_list = plan.get("reused_guarantees", [])
        unresolved_list = plan["unresolved_guarantees"]
        reused, unresolved = set(reused_list), set(unresolved_list)
        # Prevent both the omission attack (neither test nor reuse nor unresolved)
        # and double-counting a failed fresh test as a successful reused proof.
        if (len(reused) != len(reused_list) or len(unresolved) != len(unresolved_list)
                or tested & reused or reused & unresolved
                or reused | unresolved != set(requirements) or not tested <= unresolved):
            return _deny(requirement_set, evidence, robot, ["result_coverage_mismatch"])

        decisions = assess_sufficiency(
            requirement_set, robot, source_records or [], now=now,
            required_assurance_level=plan["required_assurance_level"],
        )
        rejected = [d for d in decisions if d.requirement_id in reused and not d.sufficient]
        if rejected:
            return _deny(requirement_set, evidence, robot,
                         list(dict.fromkeys(d.reason for d in rejected)),
                         [d.requirement_id for d in rejected])

        failed = {r["requirement_id"] for r in evidence["test_results"] if not r["passed"]}
        incomplete = unresolved - tested
        essential = [rid for rid in requirements if rid in failed | incomplete
                     and requirements[rid].get("essential", True)]
        if essential:
            return _deny(requirement_set, evidence, robot,
                         [f"failed:{rid}" for rid in essential], essential)
        # Replay is claimed only after provenance/coverage validation succeeds.
        # Historical records are reusable proofs, not replays of old admission.
        return admit(requirement_set, plan, evidence, robot, replay_registry, now=now)
    except (ValidationError, KeyError, TypeError, ValueError, AttributeError, OverflowError, OSError):
        return _deny(denial_req, denial_evidence, robot, ["malformed_source_record"])


def admit_verified_evidence_backed(
    requirement_set: dict[str, Any], plan: dict[str, Any], signed_evidence: SignedEvidence,
    robot: RobotState, trusted_issuers: TrustedIssuerRegistry,
    source_records: list[SignedEvidenceRecord] | None = None,
    replay_registry: ReplayRegistry | None = None, *, now: datetime | None = None,
) -> AdmissionProfile:
    """Fail-closed admission for signed evidence from local trusted issuers.

    This is distinct from ``admit_evidence_backed``, whose existing inputs are
    trusted legacy local records. Every current or historical record accepted
    here must retain its SignedEvidence wrapper and pass issuer verification.
    """
    try:
        # Verify and admit the same synchronous snapshot so a caller cannot
        # replace a signed bundle between signature verification and admission.
        requirement_set, plan, signed_evidence, robot, source_records = deepcopy(
            (requirement_set, plan, signed_evidence, robot, source_records)
        )
        denial_req = requirement_set if isinstance(requirement_set, dict) else {}
        denial_evidence = signed_evidence.evidence if isinstance(signed_evidence, SignedEvidence) else {}
        current_check = verify_signed_evidence(
            signed_evidence, trusted_issuers,
            expected_scope=evidence_scope(requirement_set),
        )
        if not current_check.verified:
            return _deny(denial_req, denial_evidence, robot, [current_check.reason or "invalid_evidence_signature"])

        verified_records: list[EvidenceRecord] = []
        for source in source_records or []:
            if not isinstance(source, SignedEvidenceRecord):
                return _deny(denial_req, denial_evidence, robot, ["unsigned_source_evidence"])
            source_check = verify_signed_evidence(
                source.signed_evidence, trusted_issuers,
                expected_scope=evidence_scope(source.requirements),
            )
            if not source_check.verified:
                return _deny(denial_req, denial_evidence, robot,
                             [source_check.reason or "invalid_evidence_signature"])
            verified_records.append(EvidenceRecord(
                source.requirements, source.plan, source.signed_evidence.evidence,
            ))
        return admit_evidence_backed(
            requirement_set, plan, signed_evidence.evidence, robot,
            source_records=verified_records, replay_registry=replay_registry, now=now,
        )
    except (KeyError, TypeError, ValueError, AttributeError):
        return _deny(
            requirement_set if isinstance(requirement_set, dict) else {},
            signed_evidence.evidence if isinstance(signed_evidence, SignedEvidence) else {},
            robot, ["malformed_signed_evidence"],
        )
