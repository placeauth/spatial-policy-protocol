from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/admission/src"))

from spp_admission import CurrentEvaluationContext, EvidenceRevocationRegistry, ReplayRegistry, assess_subject_bound_revalidation, admit, build_evidence, derive_plan, execute_plan, load_requirement_set  # noqa: E402
from spp_admission.models import RobotState  # noqa: E402

NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def issued():
    requirements = load_requirement_set(ROOT / "demo/admission/lobby.yaml")
    subject = RobotState("subject:A", "build:1", "controller:1", "demo_mobile_base", requirements["environment_digest"], {"movement.max_speed": .6, "unrelated": True})
    plan = derive_plan(requirements, subject, challenge="nonce:subject-revalidation")
    evidence = build_evidence(requirements, plan, subject, execute_plan(plan, subject, requirements), now=NOW)
    profile = admit(requirements, plan, evidence, subject, ReplayRegistry(), now=NOW)
    return requirements, subject, evidence, profile


def assess(issued, **changes):
    requirements, subject, evidence, profile = issued
    context = CurrentEvaluationContext(changes.pop("subject", subject), changes.pop("requirements", requirements), changes.pop("evidence", evidence))
    return assess_subject_bound_revalidation(profile, context, now=changes.pop("now", NOW), **changes)


def test_unchanged_context_reuses_safely(issued):
    assert assess(issued).status == "VALID"


def test_subject_change_is_invalid(issued):
    result = assess(issued, subject=replace(issued[1], actor_id="subject:B"))
    assert (result.status, result.reasons) == ("INVALID", ["profile_actor_changed"])


def test_space_change_requires_requalification(issued):
    requirements = deepcopy(issued[0]); requirements["space"] = "clinic/other"
    result = assess(issued, requirements=requirements)
    assert (result.status, result.reasons) == ("REQUALIFY", ["profile_space_changed"])


def test_expired_and_revoked_evidence_require_revalidation(issued):
    assert assess(issued, now=NOW + timedelta(minutes=16)).reasons == ["profile_evidence_expired"]
    registry = EvidenceRevocationRegistry(); registry.revoke(issued[2])
    assert assess(issued, evidence_revocations=registry).reasons == ["profile_evidence_revoked"]


def test_changed_required_capability_selectively_requalifies(issued):
    subject = replace(issued[1], capabilities={"movement.max_speed": .7, "unrelated": True})
    result = assess(issued, subject=subject)
    assert result.status == "REQUALIFY"
    assert result.reasons == ["profile_capability_changed"]
    assert result.invalidated_guarantees == ["movement.max_speed"]


def test_unrelated_capability_change_remains_valid(issued):
    subject = replace(issued[1], capabilities={"movement.max_speed": .6, "unrelated": False})
    assert assess(issued, subject=subject).status == "VALID"


def test_requirement_change_is_detected_and_selective(issued):
    requirements = deepcopy(issued[0]); requirements["requirements"][0]["value"] = .5
    result = assess(issued, requirements=requirements)
    assert result.status == "REQUALIFY"
    assert result.invalidated_guarantees == ["movement.max_speed"]


def test_equivalent_requirement_set_identity_change_requires_rebinding_with_reused_evidence(issued):
    requirements = deepcopy(issued[0]); requirements["requirement_set_id"] = "urn:spp:clinic:lobby:renamed"
    result = assess(issued, requirements=requirements)
    assert (result.status, result.reasons) == ("REQUALIFY", ["profile_requirement_set_changed_reuse_evidence"])
    assert result.reusable_guarantees == ["movement.max_speed"]


@pytest.mark.parametrize("status,expected", [
    ("VALID", True), ("REVALIDATE", False), ("REQUALIFY", False), ("INVALID", False),
])
def test_only_valid_lifecycle_status_permits_reliance(issued, status, expected):
    if status == "VALID":
        result = assess(issued)
    elif status == "REVALIDATE":
        result = assess(issued, now=NOW + timedelta(minutes=16))
    elif status == "REQUALIFY":
        result = assess(issued, subject=replace(issued[1], capabilities={"movement.max_speed": .7, "unrelated": True}))
    else:
        result = assess(issued, subject=replace(issued[1], actor_id="subject:B"))
    assert result.status == status
    assert result.may_rely_without_additional_work is expected


def test_missing_context_and_denied_profile_fail_closed(issued):
    assert assess_subject_bound_revalidation(issued[3], None).status == "INVALID"
    denied = replace(issued[3], status="DENIED")
    context = CurrentEvaluationContext(issued[1], issued[0], issued[2])
    assert assess_subject_bound_revalidation(denied, context, now=NOW).reasons == ["profile_not_admitted"]


def test_missing_capability_context_fails_closed(issued):
    subject = replace(issued[1], capabilities=None)
    result = assess(issued, subject=subject)
    assert (result.status, result.reasons) == ("REQUALIFY", ["profile_capability_dependency_unresolvable"])
    assert not result.may_rely_without_additional_work


def test_degraded_restrictions_are_not_changed_by_revalidation(issued):
    profile = replace(issued[3], status="DEGRADED", restrictions=["sensing.video.capture=disabled"])
    context = CurrentEvaluationContext(issued[1], issued[0], issued[2])
    result = assess_subject_bound_revalidation(profile, context, now=NOW)
    assert result.status == "VALID"
    assert profile.restrictions == ["sensing.video.capture=disabled"]


def test_revoked_evidence_never_becomes_reusable_without_replacement_context(issued):
    registry = EvidenceRevocationRegistry(); registry.revoke(issued[2])
    first = assess(issued, evidence_revocations=registry)
    second = assess(issued, evidence_revocations=registry)
    assert not first.may_rely_without_additional_work
    assert not second.may_rely_without_additional_work
