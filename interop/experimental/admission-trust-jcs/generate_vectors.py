"""Generate deterministic public RFC 8785 JCS admission-trust test vectors."""
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

from spp_admission.admission_envelope import _signature_payload as python_signature_payload, sign_admission_profile  # noqa: E402
from spp_admission.engine import _canonical, digest  # noqa: E402
from spp_admission.jcs_admission_envelope import (  # noqa: E402
    JCS_PROFILE,
    _effective_restrictions,
    _signature_payload as jcs_signature_payload,
    canonicalize_jcs,
    jcs_digest,
    jcs_restriction_identifier,
    jcs_restriction_profile_identifier,
    sign_jcs_admission_profile,
)
from spp_admission.models import AdmissionProfile, EvidenceBinding  # noqa: E402


NOW = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)
ISSUER_ID = "test-jcs-admission-issuer"
SCOPE = "clinic::clinic/lobby"
RECORDING = "recording_disabled@restricted_zone"
SPEED = "movement.max_speed<=0.5@corridor"


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(bytes(range(33, 65)))


def _issuer() -> dict[str, object]:
    public = _key().public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return {
        "issuer_id": ISSUER_ID,
        "public_key_base64": _b64(public),
        "allowed_envelope_types": ["spp:admission-envelope"],
        "allowed_scopes": [SCOPE],
        "enabled": True,
    }


def _profile(status: str = "ADMITTED", *, number: float = 0.5, label: str = "café 🚀") -> AdmissionProfile:
    restrictions = [RECORDING, SPEED] if status == "DEGRADED" else []
    return AdmissionProfile(
        status, "robot:jcs:1", "clinic", "clinic/lobby", 7,
        "sha256:jcs-evidence", EvidenceBinding(
            "robot:jcs:1", "build:jcs:1", "controller:jcs:1",
            "sha256:policy-jcs", "sha256:environment-jcs", "sha256:plan-jcs",
        ),
        {"guarantees": [{"id": "movement.max_speed", "value": number}], "restrictions": list(reversed(restrictions)), "label": label},
        restrictions, [], ["jcs_reference"],
    )


def _wire(envelope) -> dict[str, object]:
    return {
        "profile": asdict(envelope.profile), "issuer_id": envelope.issuer_id,
        "algorithm": envelope.algorithm, "envelope_type": envelope.envelope_type,
        "envelope_version": envelope.envelope_version,
        "canonicalization_profile": envelope.canonicalization_profile,
        "subject_id": envelope.subject_id, "place": envelope.place, "space": envelope.space,
        "scope": envelope.scope, "issued_at": envelope.issued_at, "expires_at": envelope.expires_at,
        "signed_payload_digest": envelope.signed_payload_digest, "signature": envelope.signature,
    }


def _vector(identifier: str, envelope, *, expected_subject="robot:jcs:1", expected_place="clinic",
            expected_space="clinic/lobby", now=NOW, verified=True, reason=None) -> dict[str, object]:
    profile = asdict(envelope.profile)
    profile_bytes = canonicalize_jcs(profile)
    signature_bytes = jcs_signature_payload(
        issuer_id=envelope.issuer_id, algorithm=envelope.algorithm,
        envelope_type=envelope.envelope_type, envelope_version=envelope.envelope_version,
        canonicalization_profile=envelope.canonicalization_profile,
        subject_id=envelope.subject_id, place=envelope.place, space=envelope.space,
        scope=envelope.scope, issued_at=envelope.issued_at, expires_at=envelope.expires_at,
        signed_payload_digest=envelope.signed_payload_digest,
    )
    return {
        "id": identifier, "kind": "jcs_admission_envelope", "canonicalization_profile": JCS_PROFILE,
        "trusted_issuer": _issuer(), "envelope": _wire(envelope),
        "verification": {
            "expected_subject_id": expected_subject, "expected_place": expected_place,
            "expected_space": expected_space, "now": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "canonical_profile_jcs": profile_bytes.decode("utf-8"),
        "canonical_profile_utf8_base64": _b64(profile_bytes),
        "computed_profile_digest": jcs_digest(profile),
        "signature_input_jcs": signature_bytes.decode("utf-8"),
        "signature_input_utf8_base64": _b64(signature_bytes),
        "expected": {"verified": verified, "reason": reason},
    }


def _acknowledgement_vector() -> dict[str, object]:
    profile = _profile("DEGRADED")
    restrictions = _effective_restrictions(profile)
    return {
        "id": "jcs_restriction_acknowledgement", "kind": "jcs_restriction_acknowledgement",
        "canonicalization_profile": JCS_PROFILE, "profile": asdict(profile),
        "effective_restrictions": list(restrictions),
        "restriction_digests": {item: jcs_restriction_identifier(item) for item in restrictions},
        "profile_binding": jcs_restriction_profile_identifier(profile),
        "acknowledgements": [
            {"profile_id": jcs_restriction_profile_identifier(profile), "restriction": RECORDING,
             "restriction_digest": jcs_restriction_identifier(RECORDING), "enforcement_handler": "camera_suppression", "consumer_id": "test-jcs-adapter"},
            {"profile_id": jcs_restriction_profile_identifier(profile), "restriction": SPEED,
             "restriction_digest": jcs_restriction_identifier(SPEED), "enforcement_handler": "speed_limiter", "consumer_id": "test-jcs-adapter"},
        ],
        "enforcement_mappings": [
            {"restriction": RECORDING, "restriction_digest": jcs_restriction_identifier(RECORDING), "enforcement_handler": "camera_suppression"},
            {"restriction": SPEED, "restriction_digest": jcs_restriction_identifier(SPEED), "enforcement_handler": "speed_limiter"},
        ],
        "expected": {"outcome": "ACKNOWLEDGED", "may_rely": True},
    }


def _comparison(profile: AdmissionProfile) -> dict[str, object]:
    key = _key()
    legacy = sign_admission_profile(profile, issuer_id=ISSUER_ID, private_key=key, issued_at=NOW, expires_at=NOW + timedelta(minutes=5))
    jcs = sign_jcs_admission_profile(profile, issuer_id=ISSUER_ID, private_key=key, issued_at=NOW, expires_at=NOW + timedelta(minutes=5))
    source = asdict(profile)
    return {
        "logical_profile": source,
        "python_profile": {
            "canonical_json": _canonical(source), "digest": digest(source), "signature": legacy.signature,
            "signature_input": python_signature_payload(
                issuer_id=legacy.issuer_id, algorithm=legacy.algorithm, envelope_type=legacy.envelope_type,
                envelope_version=legacy.envelope_version, subject_id=legacy.subject_id, place=legacy.place,
                space=legacy.space, scope=legacy.scope, issued_at=legacy.issued_at,
                expires_at=legacy.expires_at, signed_payload_digest=legacy.signed_payload_digest,
            ).decode("utf-8"),
        },
        "jcs_profile": {
            "canonical_json": canonicalize_jcs(source).decode("utf-8"), "digest": jcs_digest(source),
            "signature": jcs.signature,
            "signature_input": jcs_signature_payload(
                issuer_id=jcs.issuer_id, algorithm=jcs.algorithm, envelope_type=jcs.envelope_type,
                envelope_version=jcs.envelope_version, canonicalization_profile=jcs.canonicalization_profile,
                subject_id=jcs.subject_id, place=jcs.place, space=jcs.space, scope=jcs.scope,
                issued_at=jcs.issued_at, expires_at=jcs.expires_at, signed_payload_digest=jcs.signed_payload_digest,
            ).decode("utf-8"),
        },
        "expected": {"canonical_bytes_equal": False, "digest_equal": False, "signature_equal": False},
    }


def build_vectors() -> dict[str, object]:
    key = _key()
    admitted = sign_jcs_admission_profile(_profile(), issuer_id=ISSUER_ID, private_key=key, issued_at=NOW, expires_at=NOW + timedelta(minutes=5))
    degraded = sign_jcs_admission_profile(_profile("DEGRADED"), issuer_id=ISSUER_ID, private_key=key, issued_at=NOW, expires_at=NOW + timedelta(minutes=5))
    numeric = sign_jcs_admission_profile(_profile(number=1e-7), issuer_id=ISSUER_ID, private_key=key, issued_at=NOW, expires_at=NOW + timedelta(minutes=5))
    unicode = sign_jcs_admission_profile(_profile(label="Ångström 😀"), issuer_id=ISSUER_ID, private_key=key, issued_at=NOW, expires_at=NOW + timedelta(minutes=5))
    changed = replace(admitted, profile=replace(admitted.profile, operating_profile={**admitted.profile.operating_profile, "label": "tampered"}))
    unsupported = replace(admitted, canonicalization_profile="unknown-profile")
    return {
        "vector_set": "spp-admission-trust-jcs-interop", "vector_version": "0.1-experimental",
        "canonicalization_profile": JCS_PROFILE, "status": "experimental",
        "test_key_notice": "A deterministic test-only key was used to generate signatures. No private key is included.",
        "vectors": [
            _vector("jcs_admitted_valid", admitted),
            _vector("jcs_degraded_valid", degraded),
            _vector("jcs_tampered_profile", changed, verified=False, reason="signed_payload_digest_mismatch"),
            _vector("jcs_wrong_subject", admitted, expected_subject="robot:jcs:other", verified=False, reason="envelope_subject_mismatch"),
            _vector("jcs_wrong_place_space", admitted, expected_place="other-clinic", expected_space="other-space", verified=False, reason="envelope_place_mismatch"),
            _vector("jcs_expired", admitted, now=NOW + timedelta(minutes=5), verified=False, reason="envelope_expired"),
            _acknowledgement_vector(),
            _vector("jcs_unsupported_profile", unsupported, verified=False, reason="unsupported_canonicalization_profile"),
            _vector("jcs_numeric_exponent", numeric),
            _vector("jcs_unicode", unicode),
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    directory = Path(__file__).parent
    vectors = json.dumps(build_vectors(), indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    comparison = json.dumps(_comparison(_profile()), indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    targets = {directory / "vectors.json": vectors, directory / "profile-comparison.json": comparison}
    if args.check:
        if any(path.read_text(encoding="utf-8") != rendered for path, rendered in targets.items()):
            raise SystemExit("JCS vectors are not reproducible; run generate_vectors.py")
        print("JCS vectors: reproducible")
        return
    for path, rendered in targets.items():
        path.write_text(rendered, encoding="utf-8")
        print(path)


if __name__ == "__main__":
    main()
