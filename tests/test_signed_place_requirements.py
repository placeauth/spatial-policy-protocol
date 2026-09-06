from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/admission/src"))

from spp_admission import (  # noqa: E402
    EVIDENCE_BUNDLE_TYPE,
    PLACE_REQUIREMENTS_TYPE,
    ReplayRegistry,
    SignedPlaceRequirements,
    TrustedIssuer,
    TrustedIssuerRegistry,
    TrustedPolicyAuthority,
    TrustedPolicyAuthorityRegistry,
    admit_verified_policy_evidence_backed,
    derive_verified_plan,
    evidence_scope,
    policy_scope,
    sign_evidence,
    sign_place_requirements,
    verify_signed_place_requirements,
)
from spp_admission.engine import build_evidence, derive_plan, execute_plan, load_requirement_set  # noqa: E402
from spp_admission.models import RobotState  # noqa: E402


NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def policy_setup():
    requirements = load_requirement_set(ROOT / "demo/admission/lobby.yaml")
    robot = RobotState(
        "robot:policy:1", "build:policy:1", "controller:policy:1",
        "demo_mobile_base", requirements["environment_digest"],
        {"movement.max_speed": 0.6},
    )
    policy_private_key = Ed25519PrivateKey.generate()
    policy_public_key = policy_private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    )
    authority = TrustedPolicyAuthority(
        "clinic-policy-authority", policy_public_key,
        frozenset({requirements["place"]}), frozenset({policy_scope(requirements)}),
    )
    policy_registry = TrustedPolicyAuthorityRegistry([authority])
    signed_requirements = sign_place_requirements(
        requirements, authority_id=authority.authority_id, private_key=policy_private_key,
    )

    evidence_private_key = Ed25519PrivateKey.generate()
    evidence_public_key = evidence_private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    )
    issuer = TrustedIssuer(
        "clinic-validator-1", evidence_public_key,
        frozenset({EVIDENCE_BUNDLE_TYPE}), frozenset({evidence_scope(requirements)}),
    )
    issuer_registry = TrustedIssuerRegistry([issuer])
    plan = derive_plan(requirements, robot, challenge="nonce:policy-trust")
    evidence = build_evidence(
        requirements, plan, robot, execute_plan(plan, robot, requirements), now=NOW,
    )
    signed_evidence = sign_evidence(
        evidence, issuer_id=issuer.issuer_id, private_key=evidence_private_key,
        scope=evidence_scope(requirements),
    )
    return (requirements, robot, authority, policy_registry, signed_requirements,
            plan, issuer_registry, signed_evidence)


def admit_signed_policy(setup, signed_requirements=None, registry=None):
    requirements, robot, _, trusted, original, plan, issuers, signed_evidence = setup
    return admit_verified_policy_evidence_backed(
        signed_requirements or original, plan, signed_evidence, robot,
        registry or trusted, issuers, replay_registry=ReplayRegistry(), now=NOW,
    )


def test_trusted_authority_and_valid_signed_requirements_are_admitted(policy_setup):
    requirements, _, _, registry, signed, *_ = policy_setup
    assert verify_signed_place_requirements(
        signed, registry, expected_place=requirements["place"], expected_scope=requirements["space"],
    ).verified
    assert admit_signed_policy(policy_setup).status == "ADMITTED"


@pytest.mark.parametrize("mutate", [
    lambda signed: replace(signed, authority_id="unknown-policy-authority"),
    lambda signed: replace(signed, signature="not-a-valid-ed25519-signature"),
])
def test_unknown_authority_and_invalid_signature_fail_closed(policy_setup, mutate):
    profile = admit_signed_policy(policy_setup, signed_requirements=mutate(policy_setup[4]))
    assert profile.status == "DENIED"
    assert profile.reason_codes[0] in {"unknown_policy_authority", "policy_signature_invalid"}


def test_disabled_authority_fails_closed(policy_setup):
    _, _, authority, _, signed, *_ = policy_setup
    registry = TrustedPolicyAuthorityRegistry([replace(authority, enabled=False)])
    assert admit_signed_policy(policy_setup, registry=registry).reason_codes == ["policy_authority_disabled"]


def test_wrong_public_key_fails_closed(policy_setup):
    requirements, _, authority, _, signed, *_ = policy_setup
    wrong_key = Ed25519PrivateKey.generate().public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    )
    registry = TrustedPolicyAuthorityRegistry([replace(authority, public_key=wrong_key)])
    assert verify_signed_place_requirements(
        signed, registry, expected_place=requirements["place"], expected_scope=requirements["space"],
    ).reason == "policy_signature_invalid"


@pytest.mark.parametrize("field,value", [
    ("requirement", 1.2), ("place", "other-clinic"), ("scope", "clinic/other-wing"),
])
def test_semantic_policy_tampering_invalidates_signature(policy_setup, field, value):
    signed = policy_setup[4]
    requirements = deepcopy(signed.requirements)
    if field == "requirement":
        requirements["requirements"][0]["value"] = value
    elif field == "place":
        requirements["place"] = value
    else:
        requirements["space"] = value
    tampered = replace(signed, requirements=requirements)
    profile = admit_signed_policy(policy_setup, signed_requirements=tampered)
    assert profile.status == "DENIED"
    # The verified boundary intentionally authorizes place/scope before
    # signature work; every semantic mutation remains fail-closed.
    assert profile.reason_codes[0] in {
        "policy_signature_invalid", "policy_authority_unauthorized", "policy_scope_mismatch",
    }


def test_authority_place_and_scope_authorization_are_enforced(policy_setup):
    _, _, authority, _, _, *_ = policy_setup
    no_place = TrustedPolicyAuthorityRegistry([
        replace(authority, allowed_places=frozenset({"other-place"})),
    ])
    no_scope = TrustedPolicyAuthorityRegistry([
        replace(authority, allowed_scopes=frozenset({"clinic/other-wing"})),
    ])
    assert admit_signed_policy(policy_setup, registry=no_place).reason_codes == ["policy_authority_unauthorized"]
    assert admit_signed_policy(policy_setup, registry=no_scope).reason_codes == ["policy_authority_unauthorized"]


def test_unsigned_policy_is_rejected_in_verified_mode(policy_setup):
    assert admit_verified_policy_evidence_backed(
        {}, policy_setup[5], policy_setup[7], policy_setup[1], policy_setup[3], policy_setup[6],
        replay_registry=ReplayRegistry(), now=NOW,
    ).reason_codes == ["unsigned_policy_not_allowed"]


def test_verified_planning_rejects_unsigned_or_tampered_policy(policy_setup):
    requirements, robot, _, registry, signed, *_ = policy_setup
    assert derive_verified_plan(signed, robot, registry, challenge="nonce:verified")["place"] == requirements["place"]
    with pytest.raises(ValueError, match="unsigned_policy_not_allowed"):
        derive_verified_plan({}, robot, registry)
    tampered = replace(signed, requirements=dict(signed.requirements, place="tampered"))
    with pytest.raises(ValueError):
        derive_verified_plan(tampered, robot, registry)


def test_signing_is_deterministic_and_existing_signed_evidence_stays_valid(policy_setup):
    requirements, _, authority, registry, first, _, issuers, signed_evidence = policy_setup
    private_key = Ed25519PrivateKey.generate()
    # A deterministic Ed25519 assertion must be checked using the matching trust anchor.
    public_key = private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    deterministic_authority = replace(authority, public_key=public_key)
    second = sign_place_requirements(requirements, authority_id=authority.authority_id, private_key=private_key)
    third = sign_place_requirements(requirements, authority_id=authority.authority_id, private_key=private_key)
    assert (second.signed_payload_digest, second.signature) == (third.signed_payload_digest, third.signature)
    assert verify_signed_place_requirements(second, TrustedPolicyAuthorityRegistry([deterministic_authority]),
                                            expected_place=requirements["place"], expected_scope=requirements["space"]).verified
    # Existing signed evidence remains independently verifiable through its registry.
    from spp_admission import verify_signed_evidence
    assert verify_signed_evidence(signed_evidence, issuers, expected_scope=evidence_scope(requirements)).verified
