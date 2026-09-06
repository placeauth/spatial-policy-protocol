"""Minimal signed-place-requirements reference demonstration."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference/admission/src"))

from spp_admission import (  # noqa: E402
    EVIDENCE_BUNDLE_TYPE, ReplayRegistry, TrustedIssuer, TrustedIssuerRegistry,
    TrustedPolicyAuthority, TrustedPolicyAuthorityRegistry,
    admit_verified_policy_evidence_backed, derive_verified_plan, evidence_scope, policy_scope,
    sign_evidence, sign_place_requirements, verify_signed_place_requirements,
)
from spp_admission.engine import build_evidence, derive_plan, execute_plan, load_requirement_set  # noqa: E402
from spp_admission.models import RobotState  # noqa: E402


def raw_public_key(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    )


def main() -> None:
    requirements = load_requirement_set(ROOT / "demo/admission/lobby.yaml")
    robot = RobotState(
        "robot:policy-demo", "build:policy-demo", "controller:policy-demo",
        "demo_mobile_base", requirements["environment_digest"], {"movement.max_speed": 0.6},
    )
    policy_key = Ed25519PrivateKey.generate()
    authority = TrustedPolicyAuthority(
        "hospital-policy-authority", raw_public_key(policy_key),
        frozenset({"clinic"}), frozenset({policy_scope(requirements)}),
    )
    authorities = TrustedPolicyAuthorityRegistry([authority])
    signed_requirements = sign_place_requirements(
        requirements, authority_id=authority.authority_id, private_key=policy_key,
    )

    evidence_key = Ed25519PrivateKey.generate()
    issuer = TrustedIssuer(
        "clinic-validator-1", raw_public_key(evidence_key),
        frozenset({EVIDENCE_BUNDLE_TYPE}), frozenset({evidence_scope(requirements)}),
    )
    plan = derive_verified_plan(
        signed_requirements, robot, authorities, challenge="nonce:policy-demo",
    )
    evidence = build_evidence(
        requirements, plan, robot, execute_plan(plan, robot, requirements),
        now=datetime(2030, 1, 1, tzinfo=timezone.utc),
    )
    signed_evidence = sign_evidence(
        evidence, issuer_id=issuer.issuer_id, private_key=evidence_key,
        scope=evidence_scope(requirements),
    )
    profile = admit_verified_policy_evidence_backed(
        signed_requirements, plan, signed_evidence, robot, authorities,
        TrustedIssuerRegistry([issuer]), replay_registry=ReplayRegistry(),
        now=datetime(2030, 1, 1, tzinfo=timezone.utc),
    )
    verification = verify_signed_place_requirements(
        signed_requirements, authorities,
        expected_place=requirements["place"], expected_scope=requirements["space"],
    )
    print(f"Authority: {authority.authority_id}")
    print(f"Place: {requirements['space']}")
    print(f"Policy signature: {'VALID' if verification.verified else 'INVALID'}")
    print("Requirements: ACCEPTED" if verification.verified else "Requirements: REJECTED")
    print(f"Admission: {profile.status}")

    tampered = deepcopy(signed_requirements.requirements)
    tampered["requirements"][0]["value"] = 1.2
    invalid = verify_signed_place_requirements(
        type(signed_requirements)(
            tampered, signed_requirements.authority_id, signed_requirements.algorithm,
            signed_requirements.policy_type, signed_requirements.scope,
            signed_requirements.signed_payload_digest, signed_requirements.signature,
        ), authorities, expected_place=requirements["place"], expected_scope=requirements["space"],
    )
    print("\nPolicy modified after signing (movement.max_speed: 0.8 -> 1.2)")
    print(f"Policy signature: {'VALID' if invalid.verified else 'INVALID'}")
    print("Requirements: ACCEPTED" if invalid.verified else "Requirements: REJECTED")


if __name__ == "__main__":
    main()
