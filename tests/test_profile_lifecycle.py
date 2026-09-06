from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/admission/src"))

from spp_admission import (  # noqa: E402
    EVIDENCE_BUNDLE_TYPE, ProfileRevocationRegistry, TrustedIssuer,
    TrustedIssuerRegistry, TrustedPolicyAuthority, TrustedPolicyAuthorityRegistry,
    assess_profile_lifecycle, evidence_scope, policy_scope, sign_evidence,
    sign_place_requirements,
)
from spp_admission.engine import ReplayRegistry, admit, build_evidence, derive_plan, execute_plan, load_requirement_set  # noqa: E402
from spp_admission.models import RobotState  # noqa: E402


NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)


def public_key(private_key):
    return private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


@pytest.fixture
def issued():
    requirements = load_requirement_set(ROOT / "demo/admission/lobby.yaml")
    robot = RobotState(
        "robot:lifecycle:1", "build:lifecycle:1", "controller:lifecycle:1",
        "demo_mobile_base", requirements["environment_digest"], {"movement.max_speed": .6},
    )
    plan = derive_plan(requirements, robot, challenge="nonce:lifecycle")
    evidence = build_evidence(requirements, plan, robot, execute_plan(plan, robot, requirements), now=NOW)
    profile = admit(requirements, plan, evidence, robot, ReplayRegistry(), now=NOW)
    return requirements, robot, evidence, profile


def assess(issued, **changes):
    requirements, robot, evidence, profile = issued
    return assess_profile_lifecycle(profile, requirements, robot, evidence, now=NOW, **changes)


def test_unchanged_profile_is_valid(issued):
    result = assess(issued)
    assert result.status == "VALID"
    assert result.required_action == "continue"


def test_expired_evidence_requires_revalidation(issued):
    result = assess_profile_lifecycle(issued[3], issued[0], issued[1], issued[2], now=NOW + timedelta(minutes=16))
    assert (result.status, result.reasons) == ("REVALIDATE", ["profile_evidence_expired"])


def test_stricter_policy_requires_selective_requalification(issued):
    requirements = deepcopy(issued[0])
    requirements["requirements"][0]["value"] = .7
    result = assess_profile_lifecycle(issued[3], requirements, issued[1], issued[2], now=NOW)
    assert result.status == "REQUALIFY"
    assert result.reasons == ["profile_policy_changed"]
    assert result.invalidated_guarantees == ["movement.max_speed"]


def test_equivalent_policy_version_change_does_not_invalidate(issued):
    requirements = deepcopy(issued[0])
    requirements["policy_version"] += 1
    result = assess_profile_lifecycle(issued[3], requirements, issued[1], issued[2], now=NOW)
    assert result.status == "VALID"


@pytest.mark.parametrize("field,reason,status", [
    ("controller_fingerprint", "profile_controller_changed", "REVALIDATE"),
    ("build_fingerprint", "profile_build_changed", "INVALID"),
    ("actor_id", "profile_actor_changed", "INVALID"),
    ("environment_digest", "profile_environment_changed", "REQUALIFY"),
])
def test_runtime_binding_changes_fail_closed(issued, field, reason, status):
    robot = replace(issued[1], **{field: "changed"})
    result = assess_profile_lifecycle(issued[3], issued[0], robot, issued[2], now=NOW)
    assert (result.status, result.reasons) == (status, [reason])


def test_explicit_profile_revocation_invalidates(issued):
    revocations = ProfileRevocationRegistry()
    revocations.revoke(issued[3])
    assert assess(issued, revocations=revocations).reasons == ["profile_revoked"]
    assert assess(issued, revocations=revocations).status == "INVALID"


def test_destination_transition_triggers_requalification(issued):
    destination = deepcopy(issued[0])
    destination["place"] = "other-clinic"
    destination["space"] = "other-clinic/lobby"
    result = assess_profile_lifecycle(issued[3], destination, issued[1], issued[2], now=NOW)
    assert result.status == "REQUALIFY"
    assert result.reasons == ["profile_destination_changed"]


def test_new_requirement_triggers_selective_requalification(issued):
    requirements = deepcopy(issued[0])
    requirements["requirements"].append({
        "id": "human_separation", "action": "movement.enter", "operator": ">=", "value": 1.2,
    })
    result = assess_profile_lifecycle(issued[3], requirements, issued[1], issued[2], now=NOW)
    assert result.status == "REQUALIFY"
    assert result.invalidated_guarantees == ["human_separation"]


def test_disabled_evidence_issuer_invalidates_signed_profile(issued):
    requirements, _, evidence, profile = issued
    key = Ed25519PrivateKey.generate()
    issuer = TrustedIssuer("issuer", public_key(key), frozenset({EVIDENCE_BUNDLE_TYPE}), frozenset({evidence_scope(requirements)}), enabled=False)
    signed = sign_evidence(evidence, issuer_id="issuer", private_key=key, scope=evidence_scope(requirements))
    result = assess_profile_lifecycle(profile, requirements, issued[1], evidence, now=NOW,
                                      signed_evidence=signed, trusted_issuers=TrustedIssuerRegistry([issuer]))
    assert (result.status, result.reasons) == ("INVALID", ["profile_evidence_issuer_disabled"])


def test_disabled_policy_authority_invalidates_signed_policy(issued):
    requirements, _, evidence, profile = issued
    key = Ed25519PrivateKey.generate()
    authority = TrustedPolicyAuthority("authority", public_key(key), frozenset({requirements["place"]}), frozenset({policy_scope(requirements)}), enabled=False)
    signed = sign_place_requirements(requirements, authority_id="authority", private_key=key)
    result = assess_profile_lifecycle(profile, requirements, issued[1], evidence, now=NOW,
                                      signed_requirements=signed, trusted_authorities=TrustedPolicyAuthorityRegistry([authority]))
    assert (result.status, result.reasons) == ("INVALID", ["profile_policy_authority_disabled"])


def test_missing_evidence_never_returns_valid(issued):
    assert assess_profile_lifecycle(issued[3], issued[0], issued[1], None, now=NOW).status == "REVALIDATE"


def test_tampered_supporting_evidence_invalidates_profile(issued):
    evidence = deepcopy(issued[2])
    evidence["test_results"][0]["passed"] = False
    result = assess_profile_lifecycle(issued[3], issued[0], issued[1], evidence, now=NOW)
    assert (result.status, result.reasons) == ("INVALID", ["profile_evidence_mismatch"])
