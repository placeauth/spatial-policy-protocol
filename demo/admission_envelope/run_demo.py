"""Concise deterministic demonstration of the experimental admission envelope."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference/admission/src"))

from spp_admission import (  # noqa: E402
    ADMISSION_ENVELOPE_TYPE, TrustedIssuer,
    TrustedIssuerRegistry, sign_admission_profile, verify_signed_admission_envelope,
)
from spp_admission.models import AdmissionProfile, EvidenceBinding  # noqa: E402


NOW = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)


def profile() -> AdmissionProfile:
    return AdmissionProfile(
        "ADMITTED", "robot:envelope-demo", "clinic", "lobby", 1,
        "sha256:demo-evidence",
        EvidenceBinding("robot:envelope-demo", "build:demo", "controller:demo",
                        "sha256:policy", "sha256:environment", "sha256:plan"),
    )


def main() -> None:
    key = Ed25519PrivateKey.generate()
    public_key = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    issuer = TrustedIssuer(
        "clinic-admission-service", public_key,
        frozenset({ADMISSION_ENVELOPE_TYPE}), frozenset({"clinic::lobby"}),
    )
    trusted = TrustedIssuerRegistry([issuer])
    envelope = sign_admission_profile(
        profile(), issuer_id=issuer.issuer_id, private_key=key,
        issued_at=NOW, expires_at=NOW + timedelta(minutes=5),
    )
    valid = verify_signed_admission_envelope(
        envelope, trusted, expected_subject_id="robot:envelope-demo",
        expected_place="clinic", expected_space="lobby", now=NOW,
    )
    print("AdmissionProfile: ADMITTED")
    print(f"Envelope issuer: {issuer.issuer_id}")
    print(f"Result: {'VALID' if valid.verified else valid.reason}")

    tampered_profile = deepcopy(envelope.profile)
    tampered_profile.restrictions.append("movement.max_speed=0.2")
    tampered = replace(envelope, profile=tampered_profile)
    invalid = verify_signed_admission_envelope(
        tampered, trusted, expected_subject_id="robot:envelope-demo",
        expected_place="clinic", expected_space="lobby", now=NOW,
    )
    print(f"Tampered profile: {invalid.reason}")

    replay = verify_signed_admission_envelope(
        envelope, trusted, expected_subject_id="robot:other",
        expected_place="clinic", expected_space="lobby", now=NOW,
    )
    print(f"Different subject: {replay.reason}")


if __name__ == "__main__":
    main()
