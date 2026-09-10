"""Experimental exact acknowledgement of DEGRADED profile restrictions.

This local reference boundary verifies consumer-declared configuration. It does
not attest that a handler ran or that physical enforcement occurred.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from .engine import digest
from .models import AdmissionProfile, EvidenceBinding


@dataclass(frozen=True)
class RestrictionAcknowledgement:
    """One consumer acknowledgement bound to one profile and exact restriction."""

    profile_id: str
    restriction: str
    restriction_digest: str
    enforcement_handler: str
    consumer_id: str


@dataclass(frozen=True)
class RestrictionEnforcementMapping:
    """Local deployment configuration for one exact restriction."""

    restriction: str
    restriction_digest: str
    enforcement_handler: str


@dataclass(frozen=True)
class RestrictionAcknowledgementAssessment:
    """Read-only acknowledgement-boundary result for a consumer.

    ``may_rely`` says only that this restriction-acknowledgement condition is
    satisfied. The caller must separately establish profile authenticity and
    currentness before relying on the profile operationally.
    """

    outcome: str
    may_rely: bool
    profile_id: str | None
    required_restrictions: tuple[str, ...] = ()
    acknowledged_restrictions: tuple[str, ...] = ()
    enforcement_mappings: tuple[tuple[str, str], ...] = ()
    reasons: tuple[str, ...] = ()


def restriction_identifier(restriction: str) -> str:
    """Return the deterministic identity of one existing string restriction."""
    if not isinstance(restriction, str) or not restriction.strip():
        raise ValueError("restriction must be a nonempty string")
    return digest({"restriction": restriction})


def _nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _strings(value: Any) -> bool:
    return isinstance(value, list) and all(_nonblank(item) for item in value)


def _effective_restrictions(profile: AdmissionProfile) -> tuple[str, ...]:
    embedded = profile.operating_profile.get("restrictions", [])
    if not _strings(profile.restrictions) or not _strings(embedded):
        raise ValueError("profile restrictions malformed")
    return tuple(sorted(set(profile.restrictions) | set(embedded)))


def _profile_payload(profile: AdmissionProfile, restrictions: tuple[str, ...]) -> dict[str, Any]:
    """Canonicalize the current profile while treating restrictions as a set.

    Existing adapters combine ``profile.restrictions`` and
    ``operating_profile.restrictions`` as one set. The acknowledgement binding
    follows that established behavior, so list ordering, duplication, or which
    of those two equivalent locations carried a restriction does not change its
    identity. All other profile content remains bound.
    """
    operating_profile = dict(profile.operating_profile)
    operating_profile.pop("restrictions", None)
    return {
        "status": profile.status,
        "actor_id": profile.actor_id,
        "place": profile.place,
        "space": profile.space,
        "policy_version": profile.policy_version,
        "evidence_digest": profile.evidence_digest,
        "binding": asdict(profile.binding),
        "operating_profile": operating_profile,
        "effective_restrictions": list(restrictions),
        "unresolved": profile.unresolved,
        "reason_codes": profile.reason_codes,
    }


def restriction_profile_identifier(profile: AdmissionProfile) -> str:
    """Derive a deterministic experimental profile binding for acknowledgements."""
    if not isinstance(profile, AdmissionProfile):
        raise ValueError("AdmissionProfile required")
    restrictions = _effective_restrictions(profile)
    return "urn:spp:restriction-profile:" + digest(
        _profile_payload(profile, restrictions)
    ).removeprefix("sha256:")


def acknowledge_restriction(
    profile: AdmissionProfile, restriction: str, enforcement_handler: str, consumer_id: str,
) -> RestrictionAcknowledgement:
    """Construct a correctly bound reference acknowledgement."""
    return RestrictionAcknowledgement(
        restriction_profile_identifier(profile), restriction, restriction_identifier(restriction),
        enforcement_handler, consumer_id,
    )


def map_restriction_to_handler(restriction: str, enforcement_handler: str) -> RestrictionEnforcementMapping:
    """Construct one local, exact restriction-to-handler mapping."""
    return RestrictionEnforcementMapping(
        restriction, restriction_identifier(restriction), enforcement_handler,
    )


def _profile(profile: AdmissionProfile | None) -> tuple[str | None, tuple[str, ...], str | None]:
    if not isinstance(profile, AdmissionProfile):
        return None, (), "profile_missing"
    if profile.status not in {"ADMITTED", "DEGRADED", "DENIED"}:
        return None, (), "profile_not_degraded"
    if (not isinstance(profile.binding, EvidenceBinding)
            or not isinstance(profile.operating_profile, dict)
            or type(profile.policy_version) is not int or profile.policy_version < 1
            or not _strings(profile.unresolved) or not _strings(profile.reason_codes)
            or not all(_nonblank(value) for value in (
                profile.actor_id, profile.place, profile.space, profile.evidence_digest,
                profile.binding.actor_id, profile.binding.build_fingerprint,
                profile.binding.controller_fingerprint, profile.binding.policy_digest,
                profile.binding.environment_digest, profile.binding.plan_digest,
            ))):
        return None, (), "profile_malformed"
    try:
        restrictions = _effective_restrictions(profile)
        return restriction_profile_identifier(profile), restrictions, None
    except (TypeError, ValueError):
        return None, (), "profile_malformed"


def _assessment(
    outcome: str, may_rely: bool, profile_id: str | None, restrictions: tuple[str, ...], *,
    acknowledged: Iterable[str] = (), mappings: Iterable[tuple[str, str]] = (), reasons: Iterable[str] = (),
) -> RestrictionAcknowledgementAssessment:
    return RestrictionAcknowledgementAssessment(
        outcome, may_rely, profile_id, restrictions, tuple(sorted(set(acknowledged))),
        tuple(sorted(set(mappings))), tuple(sorted(set(reasons))),
    )


def _acknowledgement_error(ack: Any) -> str | None:
    if not isinstance(ack, RestrictionAcknowledgement):
        return "acknowledgement_malformed"
    if not all(_nonblank(value) for value in (
        ack.profile_id, ack.restriction, ack.restriction_digest,
        ack.enforcement_handler, ack.consumer_id,
    )):
        return "acknowledgement_malformed"
    try:
        return None if ack.restriction_digest == restriction_identifier(ack.restriction) else "acknowledgement_restriction_digest_mismatch"
    except ValueError:
        return "acknowledgement_malformed"


def _mapping_error(mapping: Any) -> str | None:
    if not isinstance(mapping, RestrictionEnforcementMapping):
        return "enforcement_mapping_malformed"
    if not all(_nonblank(value) for value in (
        mapping.restriction, mapping.restriction_digest, mapping.enforcement_handler,
    )):
        return "enforcement_mapping_malformed"
    try:
        return None if mapping.restriction_digest == restriction_identifier(mapping.restriction) else "enforcement_mapping_digest_mismatch"
    except ValueError:
        return "enforcement_mapping_malformed"


def assess_degraded_restriction_acknowledgement(
    profile: AdmissionProfile | None,
    acknowledgements: Iterable[RestrictionAcknowledgement] | None,
    enforcement_mappings: Iterable[RestrictionEnforcementMapping] | None,
) -> RestrictionAcknowledgementAssessment:
    """Fail closed unless every DEGRADED restriction has one exact mapping.

    The result establishes only that one local consumer explicitly recognized
    every restriction and named matching handlers in its configuration. It
    never proves a handler executed or that physical enforcement succeeded.
    """
    profile_id, required, profile_error = _profile(profile)
    if profile_error:
        return _assessment("BLOCKED", False, profile_id, required, reasons=(profile_error,))
    assert isinstance(profile, AdmissionProfile)
    if profile.status == "DENIED":
        return _assessment("BLOCKED", False, profile_id, required, reasons=("profile_denied",))
    if profile.status == "ADMITTED":
        return _assessment(
            "NOT_REQUIRED", True, profile_id, required,
            reasons=("profile_admitted_no_restriction_acknowledgement_required",),
        )
    if not required:
        return _assessment("BLOCKED", False, profile_id, required, reasons=("degraded_without_restrictions",))
    if not isinstance(acknowledgements, (list, tuple)):
        return _assessment("BLOCKED", False, profile_id, required, reasons=("acknowledgement_malformed",))
    if not isinstance(enforcement_mappings, (list, tuple)):
        return _assessment("BLOCKED", False, profile_id, required, reasons=("enforcement_mapping_malformed",))

    reasons: list[str] = []
    acknowledgements_by_restriction: dict[str, list[RestrictionAcknowledgement]] = {}
    acknowledged: list[str] = []
    consumer_ids: set[str] = set()
    for acknowledgement in acknowledgements:
        error = _acknowledgement_error(acknowledgement)
        if error:
            reasons.append(error)
            continue
        assert isinstance(acknowledgement, RestrictionAcknowledgement)
        if acknowledgement.profile_id != profile_id:
            reasons.append("acknowledgement_profile_mismatch")
            continue
        if acknowledgement.restriction not in required:
            reasons.append("acknowledgement_restriction_not_required")
            continue
        acknowledged.append(acknowledgement.restriction)
        consumer_ids.add(acknowledgement.consumer_id)
        acknowledgements_by_restriction.setdefault(acknowledgement.restriction, []).append(acknowledgement)
    if len(consumer_ids) > 1:
        reasons.append("acknowledgement_consumer_mismatch")
    for restriction, items in acknowledgements_by_restriction.items():
        if len(items) > 1:
            distinct = {(item.enforcement_handler, item.consumer_id) for item in items}
            reasons.append(
                "conflicting_restriction_acknowledgement" if len(distinct) > 1
                else "duplicate_restriction_acknowledgement"
            )
    for restriction in required:
        if restriction not in acknowledgements_by_restriction:
            reasons.append("restriction_acknowledgement_missing")

    mappings_by_restriction: dict[str, list[RestrictionEnforcementMapping]] = {}
    mapping_values: list[tuple[str, str]] = []
    for mapping in enforcement_mappings:
        error = _mapping_error(mapping)
        if error:
            reasons.append(error)
            continue
        assert isinstance(mapping, RestrictionEnforcementMapping)
        if mapping.restriction in required:
            mappings_by_restriction.setdefault(mapping.restriction, []).append(mapping)
            mapping_values.append((mapping.restriction, mapping.enforcement_handler))
    for restriction in required:
        items = mappings_by_restriction.get(restriction, [])
        if not items:
            if restriction in acknowledgements_by_restriction:
                reasons.append("restriction_unsupported")
            continue
        if len(items) > 1:
            reasons.append("ambiguous_enforcement_mapping")
            continue
        acknowledgements_for_restriction = acknowledgements_by_restriction.get(restriction, [])
        if len(acknowledgements_for_restriction) == 1 and items[0].enforcement_handler != acknowledgements_for_restriction[0].enforcement_handler:
            reasons.append("enforcement_handler_mismatch")

    if reasons:
        return _assessment(
            "BLOCKED", False, profile_id, required, acknowledged=acknowledged,
            mappings=mapping_values, reasons=reasons,
        )
    return _assessment(
        "ACKNOWLEDGED", True, profile_id, required, acknowledged=acknowledged,
        mappings=mapping_values,
    )
