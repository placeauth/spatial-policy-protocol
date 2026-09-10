from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference" / "admission" / "src"))

from spp_admission.models import AdmissionProfile, EvidenceBinding
from spp_admission.restriction_acknowledgement import (
    RestrictionAcknowledgement,
    RestrictionEnforcementMapping,
    acknowledge_restriction,
    assess_degraded_restriction_acknowledgement,
    map_restriction_to_handler,
    restriction_identifier,
    restriction_profile_identifier,
)


RECORDING = "recording_disabled@operating_room_3"
SPEED = "movement.max_speed<=0.5@corridor_7"


def profile(
    status="DEGRADED", restrictions=(RECORDING, SPEED), *, evidence="sha256:evidence",
    place="clinic", actor="robot:1", reason_codes=("reference_reason",), operating_profile=None,
):
    operating_profile = operating_profile if operating_profile is not None else {
        "restrictions": list(reversed(restrictions)),
    }
    return AdmissionProfile(
        status, actor, place, "clinic/corridor_7", 1, evidence,
        EvidenceBinding(actor, "build:1", "controller:1", "policy:1", "environment:1", "plan:1"),
        operating_profile, list(restrictions), [], list(reason_codes),
    )


def mappings(restrictions=(RECORDING, SPEED)):
    return [map_restriction_to_handler(item, f"handler:{index}") for index, item in enumerate(restrictions)]


def acknowledgements(issued, restrictions=(RECORDING, SPEED), consumer="clinic-adapter"):
    return [
        acknowledge_restriction(issued, item, f"handler:{index}", consumer)
        for index, item in enumerate(restrictions)
    ]


def test_admitted_profile_does_not_require_degraded_restriction_acknowledgement():
    result = assess_degraded_restriction_acknowledgement(profile("ADMITTED", ()), None, None)
    assert result.outcome == "NOT_REQUIRED" and result.may_rely
    assert result.reasons == ("profile_admitted_no_restriction_acknowledgement_required",)


def test_admitted_profile_ignores_extraneous_acknowledgements_without_mutation():
    issued = profile("ADMITTED", ())
    before = (issued.status, list(issued.restrictions), dict(issued.operating_profile))
    extraneous = RestrictionAcknowledgement("not-a-profile", RECORDING, restriction_identifier(RECORDING), "handler", "consumer")
    result = assess_degraded_restriction_acknowledgement(issued, [extraneous], [])
    assert result.outcome == "NOT_REQUIRED" and result.may_rely
    assert (issued.status, issued.restrictions, issued.operating_profile) == before


def test_degraded_all_exact_restrictions_and_mappings_are_acknowledged():
    issued = profile()
    result = assess_degraded_restriction_acknowledgement(issued, acknowledgements(issued), mappings())
    assert result.outcome == "ACKNOWLEDGED" and result.may_rely
    assert result.required_restrictions == (SPEED, RECORDING)
    assert result.acknowledged_restrictions == (SPEED, RECORDING)
    assert result.enforcement_mappings == ((SPEED, "handler:1"), (RECORDING, "handler:0"))


def test_missing_required_restriction_fails_closed():
    issued = profile()
    result = assess_degraded_restriction_acknowledgement(issued, acknowledgements(issued, (RECORDING,)), mappings())
    assert not result.may_rely and "restriction_acknowledgement_missing" in result.reasons


def test_acknowledged_but_unsupported_restriction_fails_closed():
    issued = profile()
    result = assess_degraded_restriction_acknowledgement(issued, acknowledgements(issued), mappings((RECORDING,)))
    assert not result.may_rely and "restriction_unsupported" in result.reasons


def test_acknowledgement_bound_to_a_different_profile_fails_closed():
    issued = profile()
    result = assess_degraded_restriction_acknowledgement(
        profile(evidence="sha256:other"), acknowledgements(issued), mappings(),
    )
    assert not result.may_rely and "acknowledgement_profile_mismatch" in result.reasons


def test_semantically_meaningful_profile_content_changes_invalidate_the_binding():
    issued = profile()
    issued_acknowledgements = acknowledgements(issued)
    variants = [
        profile(reason_codes=("different_reason",)),
        profile(place="other_clinic"),
        profile(actor="robot:2"),
        profile(operating_profile={"restrictions": [SPEED, RECORDING], "guarantees": [{"id": "changed"}]}),
    ]
    for changed in variants:
        assert restriction_profile_identifier(changed) != restriction_profile_identifier(issued)
        result = assess_degraded_restriction_acknowledgement(changed, issued_acknowledgements, mappings())
        assert not result.may_rely and "acknowledgement_profile_mismatch" in result.reasons


def test_profile_status_change_changes_binding_and_never_uses_old_acknowledgement():
    issued = profile()
    denied = profile("DENIED")
    assert restriction_profile_identifier(issued) != restriction_profile_identifier(denied)
    result = assess_degraded_restriction_acknowledgement(denied, acknowledgements(issued), mappings())
    assert not result.may_rely and result.reasons == ("profile_denied",)


def test_altered_or_wrong_digest_restriction_acknowledgements_fail_closed():
    issued = profile()
    altered = acknowledge_restriction(issued, "movement.max_speed<=0.5", "handler:1", "clinic-adapter")
    bad_digest = RestrictionAcknowledgement(
        restriction_profile_identifier(issued), RECORDING, "sha256:wrong", "handler:0", "clinic-adapter",
    )
    result = assess_degraded_restriction_acknowledgement(issued, [altered, bad_digest], mappings())
    assert not result.may_rely
    assert "acknowledgement_restriction_not_required" in result.reasons
    assert "acknowledgement_restriction_digest_mismatch" in result.reasons


def test_empty_enforcement_mapping_fails_closed():
    issued = profile()
    configured = mappings()
    configured[1] = RestrictionEnforcementMapping(SPEED, restriction_identifier(SPEED), "")
    result = assess_degraded_restriction_acknowledgement(issued, acknowledgements(issued), configured)
    assert not result.may_rely and "enforcement_mapping_malformed" in result.reasons


def test_whitespace_only_handler_or_consumer_identity_fails_closed_without_normalization():
    issued = profile()
    blank_handler = RestrictionAcknowledgement(
        restriction_profile_identifier(issued), RECORDING, restriction_identifier(RECORDING), "  ", "clinic-adapter",
    )
    blank_consumer = RestrictionAcknowledgement(
        restriction_profile_identifier(issued), SPEED, restriction_identifier(SPEED), "handler:1", "\t",
    )
    empty_profile_id = RestrictionAcknowledgement(
        "", SPEED, restriction_identifier(SPEED), "handler:1", "clinic-adapter",
    )
    result = assess_degraded_restriction_acknowledgement(
        issued, [blank_handler, blank_consumer, empty_profile_id], mappings(),
    )
    assert not result.may_rely and "acknowledgement_malformed" in result.reasons


def test_conflicting_duplicate_acknowledgement_and_ambiguous_mapping_fail_closed():
    issued = profile()
    configured = mappings() + [map_restriction_to_handler(RECORDING, "other-handler")]
    duplicate = acknowledge_restriction(issued, RECORDING, "other-handler", "clinic-adapter")
    result = assess_degraded_restriction_acknowledgement(issued, acknowledgements(issued) + [duplicate], configured)
    assert not result.may_rely
    assert "conflicting_restriction_acknowledgement" in result.reasons
    assert "ambiguous_enforcement_mapping" in result.reasons


def test_duplicate_identical_mapping_is_ambiguous_but_one_handler_may_serve_two_restrictions():
    issued = profile()
    same_handler = [
        map_restriction_to_handler(RECORDING, "shared-handler"),
        map_restriction_to_handler(SPEED, "shared-handler"),
    ]
    shared_acknowledgements = [
        acknowledge_restriction(issued, RECORDING, "shared-handler", "clinic-adapter"),
        acknowledge_restriction(issued, SPEED, "shared-handler", "clinic-adapter"),
    ]
    assert assess_degraded_restriction_acknowledgement(issued, shared_acknowledgements, same_handler).may_rely
    duplicate = same_handler + [map_restriction_to_handler(RECORDING, "shared-handler")]
    result = assess_degraded_restriction_acknowledgement(issued, shared_acknowledgements, duplicate)
    assert not result.may_rely and "ambiguous_enforcement_mapping" in result.reasons


def test_unrelated_local_mapping_is_unused_configuration_not_profile_acceptance():
    issued = profile()
    configured = mappings() + [map_restriction_to_handler("unrelated_restriction", "unused-handler")]
    result = assess_degraded_restriction_acknowledgement(issued, acknowledgements(issued), configured)
    assert result.outcome == "ACKNOWLEDGED" and result.may_rely


def test_extra_unrelated_acknowledgement_does_not_satisfy_missing_required_restriction():
    issued = profile()
    extra = acknowledge_restriction(issued, "recording_disabled", "camera_handler", "clinic-adapter")
    result = assess_degraded_restriction_acknowledgement(issued, [acknowledgements(issued)[0], extra], mappings())
    assert not result.may_rely
    assert "acknowledgement_restriction_not_required" in result.reasons
    assert "restriction_acknowledgement_missing" in result.reasons


def test_malformed_acknowledgement_is_not_ignored_when_valid_acknowledgements_are_complete():
    issued = profile()
    result = assess_degraded_restriction_acknowledgement(issued, acknowledgements(issued) + [object()], mappings())
    assert not result.may_rely and result.reasons == ("acknowledgement_malformed",)


def test_denied_profile_never_becomes_operationally_usable():
    issued = profile("DENIED")
    result = assess_degraded_restriction_acknowledgement(issued, acknowledgements(issued), mappings())
    assert result.outcome == "BLOCKED" and not result.may_rely
    assert result.reasons == ("profile_denied",)


def test_non_admission_profile_status_is_distinguished_and_blocked():
    issued = profile("UNKNOWN")
    result = assess_degraded_restriction_acknowledgement(issued, [], [])
    assert result.outcome == "BLOCKED" and not result.may_rely
    assert result.reasons == ("profile_not_degraded",)


def test_restriction_order_and_duplicate_required_restrictions_are_set_like_and_deterministic():
    first = profile("DEGRADED", (RECORDING, SPEED, RECORDING))
    second = profile("DEGRADED", (SPEED, RECORDING))
    assert restriction_profile_identifier(first) == restriction_profile_identifier(second)
    result = assess_degraded_restriction_acknowledgement(second, acknowledgements(first), mappings())
    assert result.outcome == "ACKNOWLEDGED" and result.required_restrictions == (SPEED, RECORDING)


def test_degraded_profile_without_restrictions_fails_closed():
    result = assess_degraded_restriction_acknowledgement(profile("DEGRADED", ()), [], [])
    assert not result.may_rely and result.reasons == ("degraded_without_restrictions",)


def test_malformed_profile_and_acknowledgement_expose_structured_reasons():
    issued = profile()
    malformed = object()
    result = assess_degraded_restriction_acknowledgement(issued, [malformed], mappings())
    assert result.outcome == "BLOCKED" and "acknowledgement_malformed" in result.reasons
    issued.restrictions = None
    malformed_profile = assess_degraded_restriction_acknowledgement(issued, [], [])
    assert malformed_profile.reasons == ("profile_malformed",)


def test_existing_admission_profile_semantics_are_not_mutated():
    issued = profile()
    before = (list(issued.restrictions), dict(issued.operating_profile), list(issued.reason_codes))
    result = assess_degraded_restriction_acknowledgement(issued, acknowledgements(issued), mappings())
    assert result.may_rely
    assert (issued.restrictions, issued.operating_profile, issued.reason_codes) == before
