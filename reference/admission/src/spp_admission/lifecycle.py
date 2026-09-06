"""Deterministic, local lifecycle assessment for issued AdmissionProfiles."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from .engine import compute_requirement_delta, digest
from .models import AdmissionProfile, RobotState
from .trust import (
    SignedEvidence,
    SignedPlaceRequirements,
    TrustedIssuerRegistry,
    TrustedPolicyAuthorityRegistry,
    evidence_scope,
    verify_signed_evidence,
    verify_signed_place_requirements,
)


@dataclass(frozen=True)
class ProfileLifecycleAssessment:
    """A read-only decision about whether an issued profile may still operate."""

    status: str
    reasons: list[str]
    reusable_guarantees: list[str]
    invalidated_guarantees: list[str]
    required_action: str
    requirement_delta: list[dict[str, Any]]


class ProfileRevocationRegistry:
    """Small in-memory reference registry; not a distributed revocation service."""

    def __init__(self, profile_ids: set[str] | None = None) -> None:
        self._revoked = set(profile_ids or ())

    def revoke(self, profile: AdmissionProfile | str) -> str:
        identifier = profile if isinstance(profile, str) else profile_identifier(profile)
        self._revoked.add(identifier)
        return identifier

    def is_revoked(self, profile: AdmissionProfile | str) -> bool:
        identifier = profile if isinstance(profile, str) else profile_identifier(profile)
        return identifier in self._revoked


def profile_identifier(profile: AdmissionProfile) -> str:
    """Derive a stable local identity without changing the profile wire shape."""
    return "urn:spp:profile:" + digest(asdict(profile)).removeprefix("sha256:")


def _assessment(status: str, reasons: list[str], reusable: list[str] = (),
                invalidated: list[str] = (), delta: list[dict[str, Any]] = ()) -> ProfileLifecycleAssessment:
    actions = {
        "VALID": "continue",
        "REVALIDATE": "revalidate_existing_evidence",
        "REQUALIFY": "selective_requalification",
        "INVALID": "new_admission_required",
    }
    return ProfileLifecycleAssessment(status, reasons, list(reusable), list(invalidated), actions[status], list(delta))


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed


def _trust_assessment(
    requirements: dict[str, Any], evidence: dict[str, Any],
    signed_evidence: SignedEvidence | None, issuers: TrustedIssuerRegistry | None,
    signed_requirements: SignedPlaceRequirements | None,
    authorities: TrustedPolicyAuthorityRegistry | None,
) -> ProfileLifecycleAssessment | None:
    if signed_evidence is not None:
        if issuers is None:
            return _assessment("INVALID", ["profile_evidence_trust_invalid"])
        check = verify_signed_evidence(signed_evidence, issuers, expected_scope=evidence_scope(requirements))
        if not check.verified:
            reason = "profile_evidence_issuer_disabled" if check.reason == "issuer_disabled" else "profile_evidence_trust_invalid"
            return _assessment("INVALID", [reason])
        if signed_evidence.evidence != evidence:
            return _assessment("INVALID", ["profile_evidence_trust_invalid"])
    if signed_requirements is not None:
        if authorities is None:
            return _assessment("INVALID", ["profile_policy_trust_invalid"])
        check = verify_signed_place_requirements(
            signed_requirements, authorities,
            expected_place=requirements.get("place"), expected_scope=requirements.get("space"),
        )
        if not check.verified:
            reason = "profile_policy_authority_disabled" if check.reason == "policy_authority_disabled" else "profile_policy_trust_invalid"
            return _assessment("INVALID", [reason])
        if signed_requirements.requirements != requirements:
            return _assessment("INVALID", ["profile_policy_trust_invalid"])
    return None


def assess_profile_lifecycle(
    profile: AdmissionProfile, current_requirements: dict[str, Any], robot: RobotState,
    evidence: dict[str, Any] | None, *, now: datetime | None = None,
    revocations: ProfileRevocationRegistry | None = None,
    signed_evidence: SignedEvidence | None = None,
    trusted_issuers: TrustedIssuerRegistry | None = None,
    signed_requirements: SignedPlaceRequirements | None = None,
    trusted_authorities: TrustedPolicyAuthorityRegistry | None = None,
) -> ProfileLifecycleAssessment:
    """Assess an already-issued profile without mutating it.

    A caller must provide current policy, runtime state, and the original
    supporting evidence. Missing or malformed context cannot return ``VALID``.
    Signed wrappers are optional to preserve explicit legacy compatibility; if
    supplied, their current local trust anchors are rechecked.
    """
    if not isinstance(profile, AdmissionProfile) or not isinstance(current_requirements, dict) or not isinstance(robot, RobotState):
        return _assessment("INVALID", ["profile_lifecycle_unresolvable"])
    if revocations is not None and revocations.is_revoked(profile):
        return _assessment("INVALID", ["profile_revoked"])
    if profile.status not in {"ADMITTED", "DEGRADED"}:
        return _assessment("INVALID", ["profile_not_admitted"])
    if evidence is None or not isinstance(evidence, dict):
        return _assessment("REVALIDATE", ["profile_evidence_unavailable"])
    try:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise ValueError("timezone required")
        trust = _trust_assessment(
            current_requirements, evidence, signed_evidence, trusted_issuers,
            signed_requirements, trusted_authorities,
        )
        if trust:
            return trust
        if (digest({key: value for key, value in evidence.items() if key != "evidence_digest"})
                != evidence.get("evidence_digest")
                or evidence.get("evidence_digest") != profile.evidence_digest):
            return _assessment("INVALID", ["profile_evidence_mismatch"])
        if _time(evidence["valid_until"]) <= now:
            return _assessment("REVALIDATE", ["profile_evidence_expired"])
        if profile.actor_id != robot.actor_id or profile.binding.actor_id != robot.actor_id:
            return _assessment("INVALID", ["profile_actor_changed"])
        if profile.binding.build_fingerprint != robot.build_fingerprint:
            return _assessment("INVALID", ["profile_build_changed"])
        if profile.binding.controller_fingerprint != robot.controller_fingerprint:
            return _assessment("REVALIDATE", ["profile_controller_changed"])
        if profile.binding.environment_digest != robot.environment_digest:
            return _assessment("REQUALIFY", ["profile_environment_changed"])
        delta = compute_requirement_delta(asdict(profile), current_requirements)
        reusable = [item["requirement_id"] for item in delta if item["classification"] == "REUSED"]
        changed = [item["requirement_id"] for item in delta if item["classification"] != "REUSED"]
        if profile.place != current_requirements.get("place"):
            return _assessment(
                "REQUALIFY", ["profile_destination_changed"], [],
                [item["requirement_id"] for item in delta], delta,
            )
        policy_digest = digest(current_requirements)
        policy_changed = profile.binding.policy_digest != policy_digest
        if changed:
            return _assessment("REQUALIFY", ["profile_policy_changed"], reusable, changed, delta)
        if policy_changed:
            # A version/metadata change with equivalent existing guarantees has
            # no demonstrated requirement impact under the current delta rules.
            return _assessment("VALID", [], reusable, [], delta)
        return _assessment("VALID", [], reusable, [], delta)
    except (KeyError, TypeError, ValueError, OverflowError):
        return _assessment("REVALIDATE", ["profile_lifecycle_unresolvable"])
