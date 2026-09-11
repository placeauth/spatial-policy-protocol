"""Generate deterministic, non-production vectors for admission-trust interop.

The vectors describe the current Python reference encoding.  They do not add a
normative SPP serialization rule or include a production private key.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "reference" / "admission" / "src"))

from spp_admission.admission_envelope import (  # noqa: E402
    ADMISSION_ENVELOPE_TYPE,
    ADMISSION_ENVELOPE_VERSION,
    _signature_payload,
    sign_admission_profile,
)
from spp_admission.engine import _canonical, digest  # noqa: E402
from spp_admission.models import AdmissionProfile, EvidenceBinding  # noqa: E402
from spp_admission.restriction_acknowledgement import (  # noqa: E402
    _profile_payload,
    acknowledge_restriction,
    map_restriction_to_handler,
    restriction_identifier,
    restriction_profile_identifier,
)


NOW = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)
ISSUER_ID = "test-admission-issuer"
SCOPE = "clinic::clinic/lobby"
RECORDING = "recording_disabled@restricted_zone"
SPEED = "movement.max_speed<=0.5@corridor"


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _key() -> Ed25519PrivateKey:
    """A published, deterministic TEST key seed; never use outside vectors."""
    return Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33)))


def _issuer() -> dict[str, object]:
    public = _key().public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return {
        "issuer_id": ISSUER_ID,
        "public_key_base64": _b64(public),
        "allowed_envelope_types": [ADMISSION_ENVELOPE_TYPE],
        "allowed_scopes": [SCOPE],
        "enabled": True,
    }


def _profile(status: str = "ADMITTED") -> AdmissionProfile:
    restrictions = [RECORDING, SPEED] if status == "DEGRADED" else []
    return AdmissionProfile(
        status=status,
        actor_id="robot:interop:1",
        place="clinic",
        space="clinic/lobby",
        policy_version=7,
        evidence_digest="sha256:interop-evidence",
        binding=EvidenceBinding(
            "robot:interop:1", "build:interop:1", "controller:interop:1",
            "sha256:policy-interop", "sha256:environment-interop", "sha256:plan-interop",
        ),
        operating_profile={
            "guarantees": [{"id": "movement.max_speed", "value": 0.5}],
            "restrictions": list(reversed(restrictions)),
            "label": "caf\u00e9 \U0001f680",
        },
        restrictions=restrictions,
        unresolved=[],
        reason_codes=["interop_reference"],
    )


def _wire(envelope) -> dict[str, object]:
    return {
        "profile": asdict(envelope.profile),
        "issuer_id": envelope.issuer_id,
        "algorithm": envelope.algorithm,
        "envelope_type": envelope.envelope_type,
        "envelope_version": envelope.envelope_version,
        "subject_id": envelope.subject_id,
        "place": envelope.place,
        "space": envelope.space,
        "scope": envelope.scope,
        "issued_at": envelope.issued_at,
        "expires_at": envelope.expires_at,
        "signed_payload_digest": envelope.signed_payload_digest,
        "signature": envelope.signature,
    }


def _envelope_vector(identifier: str, envelope, *, expected_subject: str = "robot:interop:1",
                     expected_place: str = "clinic", expected_space: str = "clinic/lobby",
                     now: datetime = NOW, expected_verified: bool = True,
                     expected_reason: str | None = None) -> dict[str, object]:
    profile = asdict(envelope.profile)
    canonical_profile = _canonical(profile)
    signature_input = _signature_payload(
        issuer_id=envelope.issuer_id,
        algorithm=envelope.algorithm,
        envelope_type=envelope.envelope_type,
        envelope_version=envelope.envelope_version,
        subject_id=envelope.subject_id,
        place=envelope.place,
        space=envelope.space,
        scope=envelope.scope,
        issued_at=envelope.issued_at,
        expires_at=envelope.expires_at,
        signed_payload_digest=envelope.signed_payload_digest,
    )
    return {
        "id": identifier,
        "kind": "admission_envelope",
        "canonicalization_profile": "spp-python-json-v1-experimental",
        "trusted_issuer": _issuer(),
        "envelope": _wire(envelope),
        "verification": {
            "expected_subject_id": expected_subject,
            "expected_place": expected_place,
            "expected_space": expected_space,
            "now": now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
        "canonical_profile_json": canonical_profile,
        "canonical_profile_utf8_base64": _b64(canonical_profile.encode("utf-8")),
        "computed_profile_digest": digest(profile),
        "signature_input_json": signature_input.decode("utf-8"),
        "signature_input_utf8_base64": _b64(signature_input),
        "expected": {"verified": expected_verified, "reason": expected_reason},
    }


def _restriction_vector() -> dict[str, object]:
    profile = _profile("DEGRADED")
    restrictions = tuple(sorted(set(profile.restrictions) | set(profile.operating_profile["restrictions"])))
    acknowledgements = [
        acknowledge_restriction(profile, RECORDING, "camera_suppression", "test-adapter"),
        acknowledge_restriction(profile, SPEED, "speed_limiter", "test-adapter"),
    ]
    mappings = [
        map_restriction_to_handler(RECORDING, "camera_suppression"),
        map_restriction_to_handler(SPEED, "speed_limiter"),
    ]
    binding_payload = _profile_payload(profile, restrictions)
    return {
        "id": "restriction_acknowledgement_valid",
        "kind": "restriction_acknowledgement",
        "canonicalization_profile": "spp-python-json-v1-experimental",
        "profile": asdict(profile),
        "effective_restrictions": list(restrictions),
        "restriction_digests": {item: restriction_identifier(item) for item in restrictions},
        "profile_binding_payload_json": _canonical(binding_payload),
        "profile_binding_payload_utf8_base64": _b64(_canonical(binding_payload).encode("utf-8")),
        "profile_binding": restriction_profile_identifier(profile),
        "acknowledgements": [asdict(item) for item in acknowledgements],
        "enforcement_mappings": [asdict(item) for item in mappings],
        "expected": {"outcome": "ACKNOWLEDGED", "may_rely": True},
    }


def build_vectors() -> dict[str, object]:
    key = _key()
    admitted = sign_admission_profile(
        _profile(), issuer_id=ISSUER_ID, private_key=key,
        issued_at=NOW, expires_at=NOW + timedelta(minutes=5),
    )
    degraded = sign_admission_profile(
        _profile("DEGRADED"), issuer_id=ISSUER_ID, private_key=key,
        issued_at=NOW, expires_at=NOW + timedelta(minutes=5),
    )
    tampered_profile = asdict(admitted.profile)
    tampered_profile["operating_profile"]["label"] = "modified after signing"
    tampered = replace(admitted, profile=AdmissionProfile(
        binding=EvidenceBinding(**tampered_profile.pop("binding")), **tampered_profile,
    ))
    unsupported = replace(admitted, envelope_version="0.2-experimental")
    return {
        "vector_set": "spp-admission-trust-interop",
        "vector_version": "0.1-experimental",
        "canonicalization_profile": "spp-python-json-v1-experimental",
        "status": "experimental",
        "test_key_notice": "The public key is derived from a deterministic test-only seed. No private key is included.",
        "vectors": [
            _envelope_vector("admitted_valid", admitted),
            _envelope_vector("degraded_valid", degraded),
            _envelope_vector("tampered_profile", tampered, expected_verified=False, expected_reason="signed_payload_digest_mismatch"),
            _envelope_vector("wrong_subject", admitted, expected_subject="robot:interop:other", expected_verified=False, expected_reason="envelope_subject_mismatch"),
            _envelope_vector("wrong_place_space", admitted, expected_place="other-clinic", expected_space="other-space", expected_verified=False, expected_reason="envelope_place_mismatch"),
            _envelope_vector("expired", admitted, now=NOW + timedelta(minutes=5), expected_verified=False, expected_reason="envelope_expired"),
            _restriction_vector(),
            _envelope_vector("unsupported_version", unsupported, expected_verified=False, expected_reason="unsupported_envelope_version"),
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    target = Path(__file__).with_name("vectors.json")
    rendered = json.dumps(build_vectors(), indent=2, ensure_ascii=True, sort_keys=True) + "\n"
    if args.check:
        if target.read_text(encoding="utf-8") != rendered:
            raise SystemExit("vectors.json is not reproducible; run generate_vectors.py")
        print("vectors.json: reproducible")
        return
    target.write_text(rendered, encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
