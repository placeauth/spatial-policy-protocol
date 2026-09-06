"""Minimal deterministic AdmissionProfile lifecycle demonstration."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference/admission/src"))

from spp_admission import (  # noqa: E402
    ProfileRevocationRegistry, TrustedPolicyAuthority, TrustedPolicyAuthorityRegistry,
    assess_profile_lifecycle, policy_scope, sign_place_requirements,
)
from spp_admission.engine import ReplayRegistry, admit, build_evidence, derive_plan, execute_plan, load_requirement_set  # noqa: E402
from spp_admission.models import RobotState  # noqa: E402


NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)


def issue():
    requirements = load_requirement_set(ROOT / "demo/admission/lobby.yaml")
    robot = RobotState(
        "robot:lifecycle-demo", "build:lifecycle-demo", "controller:lifecycle-demo",
        "demo_mobile_base", requirements["environment_digest"], {"movement.max_speed": .6},
    )
    plan = derive_plan(requirements, robot, challenge="nonce:lifecycle-demo")
    evidence = build_evidence(requirements, plan, robot, execute_plan(plan, robot, requirements), now=NOW)
    profile = admit(requirements, plan, evidence, robot, ReplayRegistry(), now=NOW)
    return requirements, robot, evidence, profile


def show(label, assessment):
    print(f"{label}: {assessment.status}")
    if assessment.reasons:
        print(f"  Reason: {', '.join(assessment.reasons)}")
    if assessment.reusable_guarantees:
        print(f"  Reuse: {', '.join(assessment.reusable_guarantees)}")
    if assessment.invalidated_guarantees:
        print(f"  Retest: {', '.join(assessment.invalidated_guarantees)}")


def main() -> None:
    requirements, robot, evidence, profile = issue()
    show("SCENARIO A — unchanged profile", assess_profile_lifecycle(profile, requirements, robot, evidence, now=NOW))
    show("SCENARIO B — evidence expires", assess_profile_lifecycle(
        profile, requirements, robot, evidence, now=NOW + timedelta(minutes=16),
    ))

    stricter = deepcopy(requirements)
    stricter["requirements"][0]["value"] = .7
    show("SCENARIO C — stricter destination policy", assess_profile_lifecycle(
        profile, stricter, robot, evidence, now=NOW,
    ))

    authority_key = Ed25519PrivateKey.generate()
    authority = TrustedPolicyAuthority(
        "hospital-policy-authority",
        authority_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw),
        frozenset({requirements["place"]}), frozenset({policy_scope(requirements)}), enabled=False,
    )
    signed = sign_place_requirements(requirements, authority_id=authority.authority_id, private_key=authority_key)
    show("SCENARIO D — policy authority disabled", assess_profile_lifecycle(
        profile, requirements, robot, evidence, now=NOW, signed_requirements=signed,
        trusted_authorities=TrustedPolicyAuthorityRegistry([authority]),
    ))

    revocations = ProfileRevocationRegistry()
    revocations.revoke(profile)
    show("SCENARIO E — explicit revocation", assess_profile_lifecycle(
        profile, requirements, robot, evidence, now=NOW, revocations=revocations,
    ))


if __name__ == "__main__":
    main()
