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
    ADMISSION_ENVELOPE_TYPE, ADMISSION_ENVELOPE_VERSION, ProfileRevocationRegistry,
    TrustedIssuer, TrustedIssuerRegistry, sign_admission_profile,
    verify_signed_admission_envelope,
)
from spp_admission.models import AdmissionProfile, EvidenceBinding  # noqa: E402


NOW = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)


def raw_public_key(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


@pytest.fixture
def envelope_setup():
    profile = AdmissionProfile(
        "DEGRADED", "robot:envelope:1", "clinic", "patient-wing", 7,
        "sha256:evidence", EvidenceBinding(
            "robot:envelope:1", "build:1", "controller:1", "sha256:policy",
            "sha256:environment", "sha256:plan",
        ), {"movement.max_speed": 0.4}, ["sensing.video.capture=disabled"], [], [],
    )
    key = Ed25519PrivateKey.generate()
    issuer = TrustedIssuer(
        "clinic-admission-service", raw_public_key(key),
        frozenset({ADMISSION_ENVELOPE_TYPE}), frozenset({"clinic::patient-wing"}),
    )
    registry = TrustedIssuerRegistry([issuer])
    envelope = sign_admission_profile(
        profile, issuer_id=issuer.issuer_id, private_key=key,
        issued_at=NOW, expires_at=NOW + timedelta(minutes=5),
    )
    return profile, key, issuer, registry, envelope


def verify(setup, envelope=None, registry=None, *, subject="robot:envelope:1",
           place="clinic", space="patient-wing", now=NOW, revocations=None):
    return verify_signed_admission_envelope(
        envelope or setup[-1], registry or setup[-2], expected_subject_id=subject,
        expected_place=place, expected_space=space, now=now, revocations=revocations,
    )


def test_valid_signed_envelope_verifies(envelope_setup):
    result = verify(envelope_setup)
    assert result.verified and result.issuer.issuer_id == "clinic-admission-service"


@pytest.mark.parametrize("mutation", ["profile", "subject", "place", "expiry"])
def test_tampered_signed_content_fails(envelope_setup, mutation):
    envelope = envelope_setup[-1]
    if mutation == "profile":
        profile = deepcopy(envelope.profile)
        profile.operating_profile["movement.max_speed"] = 1.0
        envelope = replace(envelope, profile=profile)
        expected = "signed_payload_digest_mismatch"
    elif mutation == "subject":
        envelope, expected = replace(envelope, subject_id="robot:tampered"), "malformed_envelope"
    elif mutation == "place":
        envelope, expected = replace(envelope, place="other-clinic"), "malformed_envelope"
    else:
        envelope, expected = replace(envelope, expires_at="2030-01-01T12:10:00Z"), "invalid_envelope_signature"
    assert verify(envelope_setup, envelope).reason == expected


def test_expired_envelope_fails(envelope_setup):
    assert verify(envelope_setup, now=NOW + timedelta(minutes=5)).reason == "envelope_expired"


def test_invalid_time_range_fails_closed(envelope_setup):
    envelope = replace(envelope_setup[-1], expires_at=envelope_setup[-1].issued_at)
    assert verify(envelope_setup, envelope).reason == "invalid_envelope_time_range"


def test_future_issuance_fails_closed(envelope_setup):
    envelope = replace(envelope_setup[-1], issued_at="2030-01-01T12:01:00Z")
    assert verify(envelope_setup, envelope).reason == "envelope_issued_in_future"


@pytest.mark.parametrize("timestamp", ["not-a-time", "2030-01-01T12:00:00", ""])
def test_malformed_timestamps_fail_closed(envelope_setup, timestamp):
    envelope = replace(envelope_setup[-1], issued_at=timestamp)
    assert verify(envelope_setup, envelope).reason == "malformed_envelope_time"


def test_naive_verification_time_fails_closed(envelope_setup):
    assert verify(envelope_setup, now=datetime(2030, 1, 1, 12, 0)).reason == "malformed_verification_time"


def test_untrusted_but_cryptographically_valid_issuer_fails(envelope_setup):
    assert verify(envelope_setup, registry=TrustedIssuerRegistry()).reason == "unknown_issuer"


def test_wrong_public_key_fails(envelope_setup):
    _, _, issuer, _, envelope = envelope_setup
    wrong = replace(issuer, public_key=raw_public_key(Ed25519PrivateKey.generate()))
    assert verify(envelope_setup, envelope, TrustedIssuerRegistry([wrong])).reason == "invalid_envelope_signature"


@pytest.mark.parametrize("mutation,reason", [
    ("scope", "malformed_envelope"),
    ("algorithm", "unsupported_signature_algorithm"),
    ("signature", "invalid_envelope_signature"),
    ("issuer", "malformed_envelope"),
])
def test_inconsistent_or_malformed_signed_metadata_fails(envelope_setup, mutation, reason):
    envelope = envelope_setup[-1]
    if mutation == "scope":
        envelope = replace(envelope, scope="clinic::other")
    elif mutation == "algorithm":
        envelope = replace(envelope, algorithm="RSA")
    elif mutation == "signature":
        envelope = replace(envelope, signature="%%%")
    else:
        envelope = replace(envelope, issuer_id="")
    assert verify(envelope_setup, envelope).reason == reason


def test_missing_subject_or_malformed_nested_profile_fails_closed(envelope_setup):
    assert verify(envelope_setup, replace(envelope_setup[-1], subject_id="")).reason == "malformed_envelope"
    malformed_profile = replace(envelope_setup[-1].profile, binding="not-a-binding")
    assert verify(envelope_setup, replace(envelope_setup[-1], profile=malformed_profile)).reason == "malformed_envelope"


@pytest.mark.parametrize("kind,reason", [
    ("disabled", "issuer_disabled"),
    ("type", "issuer_unauthorized_envelope_type"),
    ("scope", "issuer_unauthorized_scope"),
])
def test_envelope_issuer_trust_state_and_authorization_are_enforced(envelope_setup, kind, reason):
    _, _, issuer, _, envelope = envelope_setup
    if kind == "disabled":
        replacement = replace(issuer, enabled=False)
    elif kind == "type":
        replacement = replace(issuer, allowed_evidence_types=frozenset({"other"}))
    else:
        replacement = replace(issuer, allowed_scopes=frozenset({"other::scope"}))
    assert verify(envelope_setup, envelope, TrustedIssuerRegistry([replacement])).reason == reason


def test_subject_and_place_replay_fail(envelope_setup):
    assert verify(envelope_setup, subject="robot:other").reason == "envelope_subject_mismatch"
    assert verify(envelope_setup, place="other-clinic").reason == "envelope_place_mismatch"


def test_same_context_replay_is_allowed_until_expiry(envelope_setup):
    assert verify(envelope_setup).verified
    assert verify(envelope_setup).verified


def test_unsupported_version_fails_closed(envelope_setup):
    envelope = replace(envelope_setup[-1], envelope_version="0.2-experimental")
    assert verify(envelope_setup, envelope).reason == "unsupported_envelope_version"


def test_degraded_restrictions_are_signed(envelope_setup):
    profile = deepcopy(envelope_setup[-1].profile)
    profile.restrictions.append("human.assistance=required")
    assert verify(envelope_setup, replace(envelope_setup[-1], profile=profile)).reason == "signed_payload_digest_mismatch"


def test_revoked_profile_fails(envelope_setup):
    revocations = ProfileRevocationRegistry()
    revocations.revoke(envelope_setup[-1].profile)
    assert verify(envelope_setup, revocations=revocations).reason == "envelope_revoked"


def test_revoking_one_profile_revokes_each_envelope_for_that_profile(envelope_setup):
    profile, key, issuer, registry, first = envelope_setup
    second = sign_admission_profile(
        profile, issuer_id=issuer.issuer_id, private_key=key,
        issued_at=NOW, expires_at=NOW + timedelta(minutes=4),
    )
    revocations = ProfileRevocationRegistry()
    revocations.revoke(first.profile)
    assert verify(envelope_setup, first, registry, revocations=revocations).reason == "envelope_revoked"
    assert verify(envelope_setup, second, registry, revocations=revocations).reason == "envelope_revoked"


@pytest.mark.parametrize("status", ["ADMITTED", "DEGRADED", "DENIED"])
def test_all_existing_admission_statuses_remain_distinct_and_signable(envelope_setup, status):
    profile, key, issuer, registry, _ = envelope_setup
    if status == "DENIED":
        profile = replace(profile, status=status, evidence_digest="", restrictions=[],
                          binding=EvidenceBinding("", "", "", "", "", ""))
    else:
        profile = replace(profile, status=status)
    envelope = sign_admission_profile(
        profile, issuer_id=issuer.issuer_id, private_key=key,
        issued_at=NOW, expires_at=NOW + timedelta(minutes=5),
    )
    assert verify(envelope_setup, envelope, registry).verified
    assert envelope.profile.status == status


def test_existing_profile_is_not_mutated_by_signing(envelope_setup):
    profile, *_ = envelope_setup
    assert profile.status == "DEGRADED"
    assert profile.restrictions == ["sensing.video.capture=disabled"]
    assert ADMISSION_ENVELOPE_VERSION == "0.1-experimental"


def test_nonfinite_profile_number_is_not_signable(envelope_setup):
    profile = deepcopy(envelope_setup[0])
    profile.operating_profile["movement.max_speed"] = float("nan")
    with pytest.raises(ValueError, match="non-finite JSON number"):
        sign_admission_profile(
            profile, issuer_id=envelope_setup[2].issuer_id, private_key=envelope_setup[1],
            issued_at=NOW, expires_at=NOW + timedelta(minutes=5),
        )


def test_python_reference_golden_signature_vector():
    """Regression vector for the documented Python reference serializer only."""
    profile = AdmissionProfile(
        "ADMITTED", "subject:golden", "place:golden", "space:golden", 1,
        "sha256:evidence", EvidenceBinding(
            "subject:golden", "build:golden", "controller:golden", "sha256:policy",
            "sha256:environment", "sha256:plan",
        ), {"limit": 1}, ["sensing.video.capture=disabled"], [], ["demo"],
    )
    envelope = sign_admission_profile(
        profile, issuer_id="issuer:golden",
        private_key=Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33))),
        issued_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        expires_at=datetime(2030, 1, 1, 0, 5, tzinfo=timezone.utc),
    )
    assert envelope.scope == "place:golden::space:golden"
    assert envelope.signed_payload_digest == "sha256:7a4f0a475b574e86ff1e4901f8cf833ba7dd56e0a28df378bad5c5784fdd442a"
    assert envelope.signature == "ue6D42jRPUQGgBrxfkfK2jc4JHYFABXWuJ37xKIiUhITdfvRf2C5SWLbVQ5Yk0GSzXp01l4DUbWAvgbyK4+ODw=="
