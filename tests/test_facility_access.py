from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/admission/src"))

from spp_admission import (  # noqa: E402
    FacilityAccessDecision, ProfileLifecycleAssessment, ReferenceDoorController,
    map_profile_to_access,
)
from spp_admission.models import AdmissionProfile, EvidenceBinding  # noqa: E402


TARGET = "clinic/patient-wing"


def profile(status="ADMITTED", *, space=TARGET, restrictions=()):
    return AdmissionProfile(
        status, "robot:clinic:1", "clinic", space, 1, "sha256:evidence",
        EvidenceBinding("robot:clinic:1", "build:1", "controller:1", "sha256:policy", "sha256:environment", "sha256:plan"),
        restrictions=list(restrictions), reason_codes=["profile_reason"],
    )


def lifecycle(status):
    return ProfileLifecycleAssessment(status, ["lifecycle_reason"], [], [], "continue", [])


def test_admitted_matching_place_grants_access():
    result = map_profile_to_access(profile(), TARGET)
    assert result.allowed and result.target_place == TARGET and result.outcome == "ADMITTED"


def test_wrong_place_and_missing_profile_fail_closed():
    assert map_profile_to_access(profile(), "clinic/restricted-room").reasons == ("facility_profile_wrong_place",)
    assert map_profile_to_access(None, TARGET).reasons == ("facility_profile_missing",)


def test_degraded_requires_all_exact_restrictions_and_preserves_them_deterministically():
    degraded = profile("DEGRADED", restrictions=("video_disabled", "staff_assistance"))
    denied = map_profile_to_access(degraded, TARGET, accepted_restrictions=frozenset({"video_disabled"}))
    assert not denied.allowed
    assert denied.accepted_restrictions == ("video_disabled",)
    assert denied.rejected_restrictions == ("staff_assistance",)
    assert denied.reasons == ("facility_restriction_not_accepted",)
    allowed = map_profile_to_access(degraded, TARGET, accepted_restrictions=frozenset({"staff_assistance", "video_disabled"}))
    assert allowed.allowed and allowed.accepted_restrictions == ("staff_assistance", "video_disabled")


def test_operating_profile_restrictions_are_preserved_too():
    degraded = profile("DEGRADED", restrictions=("video_disabled",))
    degraded.operating_profile["restrictions"] = ["staff_assistance"]
    result = map_profile_to_access(degraded, TARGET, accepted_restrictions=frozenset({"video_disabled"}))
    assert not result.allowed and result.rejected_restrictions == ("staff_assistance",)


def test_denied_and_non_admitted_profiles_cannot_access():
    assert map_profile_to_access(profile("DENIED"), TARGET).reasons == ("facility_profile_denied",)
    assert map_profile_to_access(profile("UNKNOWN"), TARGET).reasons == ("facility_profile_not_current",)


@pytest.mark.parametrize("status", ["REVALIDATE", "REQUALIFY", "INVALID"])
def test_non_valid_lifecycle_denies_pending_current_profile(status):
    result = map_profile_to_access(profile(), TARGET, lifecycle=lifecycle(status))
    assert not result.allowed and result.reasons == ("facility_profile_not_current",)


def test_malformed_lifecycle_or_profile_fails_closed():
    malformed = profile()
    malformed.restrictions = None
    assert map_profile_to_access(malformed, TARGET).reasons == ("facility_profile_not_current",)
    assert map_profile_to_access(profile(), TARGET, lifecycle="invalid").reasons == ("facility_profile_not_current",)


def test_valid_lifecycle_allows_normal_evaluation_and_reference_controller_wraps_adapter():
    controller = ReferenceDoorController(frozenset({"video_disabled"}))
    result = controller.authorize(profile("DEGRADED", restrictions=("video_disabled",)), TARGET, lifecycle=lifecycle("VALID"))
    assert isinstance(result, FacilityAccessDecision)
    assert result.allowed and result.accepted_restrictions == ("video_disabled",)


def test_decisions_are_deterministic_and_do_not_mutate_profile():
    issued = profile("DEGRADED", restrictions=("video_disabled",))
    before = list(issued.restrictions)
    first = map_profile_to_access(issued, TARGET, accepted_restrictions=frozenset({"video_disabled"}))
    assert first == map_profile_to_access(issued, TARGET, accepted_restrictions=frozenset({"video_disabled"}))
    assert issued.restrictions == before
