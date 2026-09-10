"""Experimental portable subject-bound revalidation over existing lifecycle checks."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .engine import _test_for, digest
from .lifecycle import ProfileLifecycleAssessment, ProfileRevocationRegistry, assess_profile_lifecycle
from .models import AdmissionProfile, RobotState
from .trust import SignedEvidence, SignedPlaceRequirements, TrustedIssuerRegistry, TrustedPolicyAuthorityRegistry


@dataclass(frozen=True)
class CurrentEvaluationContext:
    subject: RobotState
    requirements: dict[str, Any]
    evidence: dict[str, Any] | None


class EvidenceRevocationRegistry:
    """Small local registry keyed by evidence digest; not a distributed service."""
    def __init__(self, evidence_digests: set[str] | None = None) -> None:
        self._revoked = set(evidence_digests or ())

    def revoke(self, evidence: dict[str, Any] | str) -> str:
        identifier = evidence if isinstance(evidence, str) else str(evidence.get("evidence_digest", ""))
        if not identifier:
            raise ValueError("evidence digest required")
        self._revoked.add(identifier)
        return identifier

    def is_revoked(self, evidence: dict[str, Any] | None) -> bool:
        return isinstance(evidence, dict) and evidence.get("evidence_digest") in self._revoked


def _assessment(status: str, reasons: list[str], reusable: list[str] = (), invalidated: list[str] = (), delta: list[dict[str, Any]] = ()) -> ProfileLifecycleAssessment:
    actions = {"VALID": "continue", "REVALIDATE": "revalidate_existing_evidence", "REQUALIFY": "selective_requalification", "INVALID": "new_admission_required"}
    return ProfileLifecycleAssessment(status, reasons, list(reusable), list(invalidated), actions[status], list(delta))


def _guarantee_ids(profile: AdmissionProfile) -> list[str]:
    guarantees = profile.operating_profile.get("guarantees", []) if isinstance(profile.operating_profile, dict) else []
    return [item["id"] for item in guarantees if isinstance(item, dict) and isinstance(item.get("id"), str)]


def _capability_changes(profile: AdmissionProfile, requirements: dict[str, Any], subject: RobotState) -> tuple[list[str], bool]:
    """Compare only the capability keys named by existing test mappings."""
    if not isinstance(subject.capabilities, dict):
        return _guarantee_ids(profile), True
    guarantees = {item.get("id"): item for item in profile.operating_profile.get("guarantees", []) if isinstance(item, dict) and isinstance(item.get("id"), str)} if isinstance(profile.operating_profile, dict) else {}
    changed: list[str] = []
    unresolved = False
    for requirement in requirements.get("requirements", []):
        if not isinstance(requirement, dict) or not isinstance(requirement.get("id"), str):
            return [], True
        guarantee = guarantees.get(requirement["id"])
        if guarantee is None:
            continue
        try:
            capability = _test_for(requirement, subject.embodiment).get("capability")
        except (KeyError, TypeError, ValueError):
            unresolved, capability = True, None
        prior = guarantee.get("capabilities")
        if not isinstance(capability, str) or not isinstance(prior, dict) or capability not in prior or capability not in subject.capabilities:
            unresolved = True
            changed.append(requirement["id"])
        elif type(prior[capability]) is not type(subject.capabilities[capability]) or prior[capability] != subject.capabilities[capability]:
            changed.append(requirement["id"])
    return sorted(set(changed)), unresolved


def assess_subject_bound_revalidation(profile: AdmissionProfile, context: CurrentEvaluationContext, *, now: datetime | None = None, profile_revocations: ProfileRevocationRegistry | None = None, evidence_revocations: EvidenceRevocationRegistry | None = None, signed_evidence: SignedEvidence | None = None, trusted_issuers: TrustedIssuerRegistry | None = None, signed_requirements: SignedPlaceRequirements | None = None, trusted_authorities: TrustedPolicyAuthorityRegistry | None = None) -> ProfileLifecycleAssessment:
    """Assess reuse for a current generic subject without planner or RMF state."""
    if not isinstance(profile, AdmissionProfile) or not isinstance(context, CurrentEvaluationContext) or not isinstance(context.subject, RobotState) or not isinstance(context.requirements, dict):
        return _assessment("INVALID", ["subject_revalidation_context_unresolvable"])
    if evidence_revocations is not None and evidence_revocations.is_revoked(context.evidence):
        return _assessment("REVALIDATE", ["profile_evidence_revoked"], [], _guarantee_ids(profile))
    baseline = assess_profile_lifecycle(profile, context.requirements, context.subject, context.evidence, now=now, revocations=profile_revocations, signed_evidence=signed_evidence, trusted_issuers=trusted_issuers, signed_requirements=signed_requirements, trusted_authorities=trusted_authorities)
    if baseline.status in {"INVALID", "REVALIDATE"}:
        return baseline
    if not isinstance(context.evidence, dict) or context.evidence.get("embodiment") != context.subject.embodiment:
        return _assessment("INVALID", ["profile_embodiment_changed"], [], _guarantee_ids(profile), baseline.requirement_delta)
    changed, unresolved = _capability_changes(profile, context.requirements, context.subject)
    reasons = list(baseline.reasons)
    invalidated = sorted(set(baseline.invalidated_guarantees) | set(changed))
    reusable = [item for item in baseline.reusable_guarantees if item not in invalidated]
    if unresolved:
        reasons.append("profile_capability_dependency_unresolvable")
    elif changed:
        reasons.append("profile_capability_changed")
    if changed or baseline.status == "REQUALIFY":
        return _assessment("REQUALIFY", reasons, reusable, invalidated, baseline.requirement_delta)
    if profile.binding.policy_digest != digest(context.requirements):
        return _assessment("REQUALIFY", ["profile_requirement_set_changed_reuse_evidence"], baseline.reusable_guarantees, [], baseline.requirement_delta)
    return baseline
