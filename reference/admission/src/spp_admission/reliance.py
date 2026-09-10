"""Experimental end-to-end reliance assessment for signed AdmissionProfiles.

This is deliberately an orchestration boundary rather than a new SPP policy
or decision type.  It composes the three experimental reference mechanisms in
their required fail-closed order.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from .admission_envelope import (
    AdmissionEnvelopeVerification,
    SignedAdmissionEnvelope,
    verify_signed_admission_envelope,
)
from .lifecycle import ProfileLifecycleAssessment, ProfileRevocationRegistry
from .revalidation import (
    CurrentEvaluationContext,
    EvidenceRevocationRegistry,
    assess_subject_bound_revalidation,
)
from .restriction_acknowledgement import (
    RestrictionAcknowledgement,
    RestrictionAcknowledgementAssessment,
    RestrictionEnforcementMapping,
    assess_degraded_restriction_acknowledgement,
)
from .trust import (
    SignedEvidence,
    SignedPlaceRequirements,
    TrustedIssuerRegistry,
    TrustedPolicyAuthorityRegistry,
)


@dataclass(frozen=True)
class AdmissionRelianceAssessment:
    """The only operational conclusion of the experimental P0 composition.

    ``may_rely`` is false unless every prerequisite for the enclosed profile
    was valid at this assessment boundary.  The original profile and exact
    restriction strings are never rewritten or widened by this object.
    """

    outcome: str
    may_rely: bool
    profile_status: str | None
    blocking_stage: str | None = None
    reasons: tuple[str, ...] = ()
    restrictions: tuple[str, ...] = ()
    envelope: AdmissionEnvelopeVerification | None = None
    lifecycle: ProfileLifecycleAssessment | None = None
    acknowledgement: RestrictionAcknowledgementAssessment | None = None


def _blocked(
    stage: str,
    reasons: Iterable[str],
    *,
    profile_status: str | None = None,
    restrictions: Iterable[str] = (),
    envelope: AdmissionEnvelopeVerification | None = None,
    lifecycle: ProfileLifecycleAssessment | None = None,
    acknowledgement: RestrictionAcknowledgementAssessment | None = None,
) -> AdmissionRelianceAssessment:
    reason_values = (reasons,) if isinstance(reasons, str) else tuple(reasons)
    return AdmissionRelianceAssessment(
        "BLOCKED", False, profile_status, stage,
        tuple(sorted(set(reason_values))), tuple(restrictions), envelope, lifecycle,
        acknowledgement,
    )


def assess_admission_reliance(
    envelope: SignedAdmissionEnvelope,
    context: CurrentEvaluationContext,
    trusted_issuers: TrustedIssuerRegistry,
    *,
    acknowledgements: Iterable[RestrictionAcknowledgement] | None = None,
    enforcement_mappings: Iterable[RestrictionEnforcementMapping] | None = None,
    now: datetime | None = None,
    profile_revocations: ProfileRevocationRegistry | None = None,
    evidence_revocations: EvidenceRevocationRegistry | None = None,
    signed_evidence: SignedEvidence | None = None,
    evidence_issuers: TrustedIssuerRegistry | None = None,
    signed_requirements: SignedPlaceRequirements | None = None,
    trusted_authorities: TrustedPolicyAuthorityRegistry | None = None,
) -> AdmissionRelianceAssessment:
    """Assess whether a consumer may rely on one signed profile *now*.

    The fixed order is: envelope authenticity/trust/time/scope, current
    subject-bound lifecycle, profile status, and, only for ``DEGRADED``, exact
    acknowledgement plus a local enforcement-handler mapping.  Missing or
    malformed inputs never become operational permission.
    """
    if not isinstance(context, CurrentEvaluationContext) or not isinstance(context.requirements, dict):
        return _blocked("lifecycle", ("current_context_missing",))

    expected_place = context.requirements.get("place")
    expected_space = context.requirements.get("space")
    expected_subject = getattr(context.subject, "actor_id", None)
    if not all(isinstance(value, str) and value for value in (expected_subject, expected_place, expected_space)):
        return _blocked("envelope", ("envelope_context_unresolvable",))

    envelope_result = verify_signed_admission_envelope(
        envelope, trusted_issuers,
        expected_subject_id=expected_subject,
        expected_place=expected_place,
        expected_space=expected_space,
        now=now,
        revocations=profile_revocations,
    )
    if not envelope_result.verified:
        return _blocked(
            "envelope", (envelope_result.reason or "envelope_verification_failed"),
            envelope=envelope_result,
        )

    # Only a profile authenticated by the verified envelope reaches later
    # stages.  A caller cannot substitute an adjacent, unsigned profile.
    profile = envelope.profile
    # Denial is terminal.  It is recognized before lifecycle reuse logic so a
    # caller receives the explicit admission-status reason rather than a more
    # general "profile_not_admitted" lifecycle result.
    if profile.status == "DENIED":
        return _blocked(
            "admission_status", ("profile_denied",),
            profile_status=profile.status, envelope=envelope_result,
        )
    lifecycle_result = assess_subject_bound_revalidation(
        profile, context, now=now,
        profile_revocations=profile_revocations,
        evidence_revocations=evidence_revocations,
        signed_evidence=signed_evidence,
        trusted_issuers=evidence_issuers,
        signed_requirements=signed_requirements,
        trusted_authorities=trusted_authorities,
    )
    if not lifecycle_result.may_rely_without_additional_work:
        return _blocked(
            "lifecycle", lifecycle_result.reasons,
            profile_status=profile.status,
            envelope=envelope_result, lifecycle=lifecycle_result,
        )

    if profile.status == "ADMITTED":
        return AdmissionRelianceAssessment(
            "RELIABLE_ADMITTED", True, profile.status,
            envelope=envelope_result, lifecycle=lifecycle_result,
        )
    if profile.status != "DEGRADED":
        return _blocked(
            "admission_status", ("profile_status_unusable",),
            profile_status=profile.status,
            envelope=envelope_result, lifecycle=lifecycle_result,
        )

    acknowledgement_result = assess_degraded_restriction_acknowledgement(
        profile, acknowledgements, enforcement_mappings,
    )
    if not acknowledgement_result.may_rely:
        return _blocked(
            "restriction_acknowledgement", acknowledgement_result.reasons,
            profile_status=profile.status,
            restrictions=acknowledgement_result.required_restrictions,
            envelope=envelope_result, lifecycle=lifecycle_result,
            acknowledgement=acknowledgement_result,
        )
    return AdmissionRelianceAssessment(
        "RELIABLE_DEGRADED", True, profile.status,
        restrictions=acknowledgement_result.required_restrictions,
        envelope=envelope_result, lifecycle=lifecycle_result,
        acknowledgement=acknowledgement_result,
    )
