"""Deterministic demonstration of the experimental P0 reliance pipeline."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference" / "admission" / "src"))

from spp_admission import (  # noqa: E402
    ADMISSION_ENVELOPE_TYPE, CurrentEvaluationContext, ReplayRegistry,
    TrustedIssuer, TrustedIssuerRegistry, acknowledge_restriction,
    assess_admission_reliance, admit, build_evidence, derive_plan, execute_plan,
    load_requirement_set, map_restriction_to_handler, sign_admission_profile,
)
from spp_admission.models import RobotState  # noqa: E402


NOW = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)
RECORDING = "recording_disabled@restricted_zone"
SPEED = "movement.max_speed<=0.5@corridor"


def main() -> None:
    requirements = load_requirement_set(ROOT / "demo" / "admission" / "lobby.yaml")
    subject = RobotState(
        "robot:p0-demo", "build:p0", "controller:p0", "demo_mobile_base",
        requirements["environment_digest"], {"movement.max_speed": 0.6},
    )
    plan = derive_plan(requirements, subject, challenge="nonce:p0-demo")
    evidence = build_evidence(requirements, plan, subject, execute_plan(plan, subject, requirements), now=NOW)
    admitted = admit(requirements, plan, evidence, subject, ReplayRegistry(), now=NOW)
    degraded = replace(
        admitted, status="DEGRADED", restrictions=[RECORDING, SPEED],
        operating_profile={**admitted.operating_profile, "restrictions": [SPEED, RECORDING]},
    )

    key = Ed25519PrivateKey.generate()
    issuer = TrustedIssuer(
        "clinic-admission-service",
        key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw),
        frozenset({ADMISSION_ENVELOPE_TYPE}),
        frozenset({f"{requirements['place']}::{requirements['space']}"}),
    )
    trusted = TrustedIssuerRegistry([issuer])
    admitted_envelope = sign_admission_profile(
        admitted, issuer_id=issuer.issuer_id, private_key=key,
        issued_at=NOW, expires_at=NOW + timedelta(minutes=5),
    )
    envelope = sign_admission_profile(
        degraded, issuer_id=issuer.issuer_id, private_key=key,
        issued_at=NOW, expires_at=NOW + timedelta(minutes=5),
    )
    context = CurrentEvaluationContext(subject, requirements, evidence)
    mappings = [
        map_restriction_to_handler(RECORDING, "camera_suppression"),
        map_restriction_to_handler(SPEED, "speed_limiter"),
    ]
    acknowledgements = [
        acknowledge_restriction(degraded, RECORDING, "camera_suppression", "clinic-adapter"),
        acknowledge_restriction(degraded, SPEED, "speed_limiter", "clinic-adapter"),
    ]

    def show(label, candidate, acks=acknowledgements, handlers=mappings, current=context, now=NOW):
        result = assess_admission_reliance(
            candidate, current, trusted, acknowledgements=acks,
            enforcement_mappings=handlers, now=now,
        )
        details = ", ".join(result.reasons) or "none"
        print(f"{label}: {result.outcome} (may_rely={str(result.may_rely).lower()}, stage={result.blocking_stage or 'complete'}, reasons={details})")
        if result.restrictions:
            print("  Restrictions: " + "; ".join(result.restrictions))

    show("1 valid ADMITTED envelope + VALID lifecycle", admitted_envelope, acks=[], handlers=[])
    show("2 valid DEGRADED envelope + VALID lifecycle + complete acknowledgement", envelope)
    show("3 envelope expiry", envelope, now=NOW + timedelta(minutes=5))
    changed_subject = replace(subject, capabilities={"movement.max_speed": 0.7})
    show("4 material subject capability change", envelope, current=CurrentEvaluationContext(changed_subject, requirements, evidence))
    show("5 missing restriction acknowledgement", envelope, acks=acknowledgements[:1])
    altered = deepcopy(envelope.profile)
    altered.restrictions[1] = "movement.max_speed<=0.2@corridor"
    show("6 tampered profile after signing", replace(envelope, profile=altered))
    denied = replace(admitted, status="DENIED", restrictions=[], operating_profile={})
    denied_envelope = sign_admission_profile(denied, issuer_id=issuer.issuer_id, private_key=key, issued_at=NOW, expires_at=NOW + timedelta(minutes=5))
    show("7 signed DENIED profile", denied_envelope, acks=[], handlers=[])


if __name__ == "__main__":
    main()
