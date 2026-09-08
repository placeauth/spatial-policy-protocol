"""Pure facility-side access-control boundary for AdmissionProfiles."""
from __future__ import annotations

from dataclasses import dataclass

from .lifecycle import ProfileLifecycleAssessment, profile_identifier
from .models import AdmissionProfile


@dataclass(frozen=True)
class FacilityAccessDecision:
    """Deterministic answer for a facility endpoint; not a hardware command."""

    allowed: bool
    target_place: str
    profile_id: str | None
    outcome: str | None
    accepted_restrictions: tuple[str, ...] = ()
    rejected_restrictions: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()


def _decision(
    allowed: bool, target_place: str, profile: AdmissionProfile | None, *,
    accepted: tuple[str, ...] = (), rejected: tuple[str, ...] = (), reasons: tuple[str, ...] = (),
) -> FacilityAccessDecision:
    return FacilityAccessDecision(
        allowed, target_place, profile_identifier(profile) if isinstance(profile, AdmissionProfile) else None,
        profile.status if isinstance(profile, AdmissionProfile) else None, accepted, rejected, reasons,
    )


def map_profile_to_access(
    profile: AdmissionProfile | None, target_place: str, *,
    accepted_restrictions: frozenset[str] = frozenset(),
    lifecycle: ProfileLifecycleAssessment | None = None,
) -> FacilityAccessDecision:
    """Map one profile to a deterministic facility access decision.

    ``accepted_restrictions`` is facility configuration. Every exact profile
    restriction must be present before a DEGRADED profile can grant access.
    A lifecycle assessment is read-only input; callers must revalidate or
    requalify before presenting a current profile again.
    """
    if not isinstance(target_place, str) or not target_place:
        return _decision(False, target_place if isinstance(target_place, str) else "", None,
                         reasons=("facility_target_place_invalid",))
    if profile is None:
        return _decision(False, target_place, None, reasons=("facility_profile_missing",))
    if not isinstance(profile, AdmissionProfile):
        return _decision(False, target_place, None, reasons=("facility_profile_missing",))
    if lifecycle is not None and not isinstance(lifecycle, ProfileLifecycleAssessment):
        return _decision(False, target_place, profile, reasons=("facility_profile_not_current",))
    if lifecycle is not None and lifecycle.status != "VALID":
        return _decision(False, target_place, profile, reasons=("facility_profile_not_current",))
    if (not isinstance(profile.space, str) or not profile.space
            or not isinstance(profile.restrictions, list)
            or not isinstance(profile.operating_profile, dict)
            or not isinstance(profile.reason_codes, list)
            or not all(isinstance(item, str) and item for item in profile.reason_codes)):
        return _decision(False, target_place, profile, reasons=("facility_profile_not_current",))
    if profile.space != target_place:
        return _decision(False, target_place, profile, reasons=("facility_profile_wrong_place",))
    if profile.status == "DENIED":
        return _decision(False, target_place, profile, reasons=("facility_profile_denied",))
    if profile.status not in {"ADMITTED", "DEGRADED"}:
        return _decision(False, target_place, profile, reasons=("facility_profile_not_current",))
    profile_restrictions = profile.operating_profile.get("restrictions", [])
    if (not isinstance(profile_restrictions, list)
            or not all(isinstance(item, str) and item for item in profile.restrictions)
            or not all(isinstance(item, str) and item for item in profile_restrictions)):
        return _decision(False, target_place, profile, reasons=("facility_profile_not_current",))
    restrictions = tuple(sorted(set(profile.restrictions) | set(profile_restrictions)))
    accepted_policy = frozenset(accepted_restrictions)
    accepted = tuple(item for item in restrictions if item in accepted_policy)
    rejected = tuple(item for item in restrictions if item not in accepted_policy)
    if rejected:
        return _decision(
            False, target_place, profile, accepted=accepted, rejected=rejected,
            reasons=("facility_restriction_not_accepted",),
        )
    if profile.status == "DEGRADED" and not restrictions:
        return _decision(False, target_place, profile, reasons=("facility_profile_not_current",))
    return _decision(True, target_place, profile, accepted=accepted, reasons=tuple(profile.reason_codes))


class ReferenceDoorController:
    """Reference place endpoint that answers access only; it drives no door hardware."""

    def __init__(self, accepted_restrictions: frozenset[str] = frozenset()) -> None:
        self._accepted_restrictions = frozenset(accepted_restrictions)

    def authorize(
        self, profile: AdmissionProfile | None, target_place: str, *,
        lifecycle: ProfileLifecycleAssessment | None = None,
    ) -> FacilityAccessDecision:
        return map_profile_to_access(
            profile, target_place, accepted_restrictions=self._accepted_restrictions, lifecycle=lifecycle,
        )
