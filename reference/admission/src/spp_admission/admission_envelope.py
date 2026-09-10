"""Experimental signed, time-bound wrappers for AdmissionProfiles.

This module is deliberately separate from normative SPP 0.1 policy decisions.
It reuses the reference layer's local Ed25519 and TrustedIssuerRegistry model.
"""
from __future__ import annotations

import base64
import math
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .engine import _canonical, digest
from .lifecycle import ProfileRevocationRegistry
from .models import AdmissionProfile, EvidenceBinding
from .trust import ED25519, TrustedIssuer, TrustedIssuerRegistry


ADMISSION_ENVELOPE_TYPE = "spp:admission-envelope"
ADMISSION_ENVELOPE_VERSION = "0.1-experimental"


@dataclass(frozen=True)
class SignedAdmissionEnvelope:
    """A complete experimental AdmissionProfile and its local issuer assertion."""

    profile: AdmissionProfile
    issuer_id: str
    algorithm: str
    envelope_type: str
    envelope_version: str
    subject_id: str
    place: str
    space: str
    scope: str
    issued_at: str
    expires_at: str
    signed_payload_digest: str
    signature: str


@dataclass(frozen=True)
class AdmissionEnvelopeVerification:
    """Structured verification result; expected failures are not exceptions."""

    verified: bool
    reason: str | None = None
    issuer: TrustedIssuer | None = None


def admission_scope(profile: AdmissionProfile) -> str:
    """Return the local governed scope for a profile without new identity rules."""
    return f"{profile.place}::{profile.space}"


def _time(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("timestamp required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)


def _profile_valid(profile: AdmissionProfile) -> bool:
    return (
        isinstance(profile, AdmissionProfile)
        and isinstance(profile.binding, EvidenceBinding)
        and profile.status in {"ADMITTED", "DEGRADED", "DENIED"}
        and all(isinstance(value, str) and value for value in (
            profile.actor_id, profile.place, profile.space,
        ))
        and isinstance(profile.evidence_digest, str)
        and (profile.status == "DENIED" or profile.binding.actor_id == profile.actor_id)
    )


def _reject_nonfinite_numbers(value: object) -> None:
    """Keep the signed profile payload within interoperable JSON value space."""
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite JSON number")
    if isinstance(value, dict):
        for key, nested in value.items():
            if not isinstance(key, str):
                raise ValueError("JSON object key must be a string")
            _reject_nonfinite_numbers(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _reject_nonfinite_numbers(nested)


def _profile_digest(profile: AdmissionProfile) -> str:
    content = asdict(profile)
    _reject_nonfinite_numbers(content)
    return digest(content)


def _signature_payload(*, issuer_id: str, algorithm: str, envelope_type: str,
                       envelope_version: str, subject_id: str, place: str, space: str,
                       scope: str, issued_at: str, expires_at: str,
                       signed_payload_digest: str) -> bytes:
    return _canonical({
        "issuer_id": issuer_id,
        "algorithm": algorithm,
        "envelope_type": envelope_type,
        "envelope_version": envelope_version,
        "subject_id": subject_id,
        "place": place,
        "space": space,
        "scope": scope,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "signed_payload_digest": signed_payload_digest,
    }).encode("utf-8")


def sign_admission_profile(
    profile: AdmissionProfile, *, issuer_id: str, private_key: Ed25519PrivateKey,
    issued_at: datetime, expires_at: datetime,
) -> SignedAdmissionEnvelope:
    """Sign an experimental AdmissionProfile using the existing Ed25519 model.

    The complete dataclass representation is canonicalized and SHA-256 hashed;
    the signature covers that digest and all envelope metadata.
    """
    if not _profile_valid(profile) or not issuer_id:
        raise ValueError("valid profile and issuer_id are required")
    if issued_at.tzinfo is None or expires_at.tzinfo is None:
        raise ValueError("issued_at and expires_at must be timezone-aware")
    subject_id, place, space = profile.actor_id, profile.place, profile.space
    scope = admission_scope(profile)
    issued = issued_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    expires = expires_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    signed_payload_digest = _profile_digest(profile)
    payload = _signature_payload(
        issuer_id=issuer_id, algorithm=ED25519,
        envelope_type=ADMISSION_ENVELOPE_TYPE,
        envelope_version=ADMISSION_ENVELOPE_VERSION,
        subject_id=subject_id, place=place, space=space, scope=scope,
        issued_at=issued, expires_at=expires,
        signed_payload_digest=signed_payload_digest,
    )
    return SignedAdmissionEnvelope(
        profile=deepcopy(profile), issuer_id=issuer_id, algorithm=ED25519,
        envelope_type=ADMISSION_ENVELOPE_TYPE,
        envelope_version=ADMISSION_ENVELOPE_VERSION,
        subject_id=subject_id, place=place, space=space, scope=scope,
        issued_at=issued, expires_at=expires,
        signed_payload_digest=signed_payload_digest,
        signature=base64.b64encode(private_key.sign(payload)).decode("ascii"),
    )


def verify_signed_admission_envelope(
    envelope: SignedAdmissionEnvelope, trusted_issuers: TrustedIssuerRegistry, *,
    expected_subject_id: str, expected_place: str, expected_space: str,
    now: datetime | None = None,
    revocations: ProfileRevocationRegistry | None = None,
) -> AdmissionEnvelopeVerification:
    """Verify an envelope for one subject at one governed place scope.

    This performs no network lookup. A trusted caller supplies locally
    provisioned issuers, current UTC time, and any local revocation registry.
    """
    if not isinstance(envelope, SignedAdmissionEnvelope) or not isinstance(trusted_issuers, TrustedIssuerRegistry):
        return AdmissionEnvelopeVerification(False, "malformed_envelope")
    if not all(isinstance(value, str) and value for value in (
        expected_subject_id, expected_place, expected_space,
        envelope.issuer_id, envelope.subject_id, envelope.place, envelope.space,
        envelope.scope, envelope.signed_payload_digest, envelope.signature,
    )) or not _profile_valid(envelope.profile):
        return AdmissionEnvelopeVerification(False, "malformed_envelope")
    if envelope.envelope_version != ADMISSION_ENVELOPE_VERSION:
        return AdmissionEnvelopeVerification(False, "unsupported_envelope_version")
    if envelope.envelope_type != ADMISSION_ENVELOPE_TYPE or envelope.algorithm != ED25519:
        return AdmissionEnvelopeVerification(False, "unsupported_signature_algorithm")
    if (envelope.subject_id != envelope.profile.actor_id
            or envelope.place != envelope.profile.place
            or envelope.space != envelope.profile.space
            or envelope.scope != admission_scope(envelope.profile)):
        return AdmissionEnvelopeVerification(False, "malformed_envelope")
    try:
        issued, expires = _time(envelope.issued_at), _time(envelope.expires_at)
        current_source = now or datetime.now(timezone.utc)
        if current_source.tzinfo is None:
            return AdmissionEnvelopeVerification(False, "malformed_verification_time")
        current = current_source.astimezone(timezone.utc)
        if expires <= issued:
            return AdmissionEnvelopeVerification(False, "invalid_envelope_time_range")
        if issued > current:
            return AdmissionEnvelopeVerification(False, "envelope_issued_in_future")
        if expires <= current:
            return AdmissionEnvelopeVerification(False, "envelope_expired")
    except (AttributeError, TypeError, ValueError, OverflowError):
        return AdmissionEnvelopeVerification(False, "malformed_envelope_time")
    issuer = trusted_issuers.get(envelope.issuer_id)
    if issuer is None:
        return AdmissionEnvelopeVerification(False, "unknown_issuer")
    if not issuer.enabled:
        return AdmissionEnvelopeVerification(False, "issuer_disabled")
    if envelope.envelope_type not in issuer.allowed_evidence_types:
        return AdmissionEnvelopeVerification(False, "issuer_unauthorized_envelope_type")
    if not issuer.allows_scope(envelope.scope):
        return AdmissionEnvelopeVerification(False, "issuer_unauthorized_scope")
    try:
        profile_digest = _profile_digest(envelope.profile)
    except (TypeError, ValueError, OverflowError):
        return AdmissionEnvelopeVerification(False, "malformed_envelope")
    if profile_digest != envelope.signed_payload_digest:
        return AdmissionEnvelopeVerification(False, "signed_payload_digest_mismatch")
    try:
        signature = base64.b64decode(envelope.signature, validate=True)
        Ed25519PublicKey.from_public_bytes(issuer.public_key).verify(
            signature,
            _signature_payload(
                issuer_id=envelope.issuer_id, algorithm=envelope.algorithm,
                envelope_type=envelope.envelope_type,
                envelope_version=envelope.envelope_version,
                subject_id=envelope.subject_id, place=envelope.place,
                space=envelope.space, scope=envelope.scope,
                issued_at=envelope.issued_at, expires_at=envelope.expires_at,
                signed_payload_digest=envelope.signed_payload_digest,
            ),
        )
    except (ValueError, TypeError, InvalidSignature):
        return AdmissionEnvelopeVerification(False, "invalid_envelope_signature")
    if envelope.subject_id != expected_subject_id:
        return AdmissionEnvelopeVerification(False, "envelope_subject_mismatch", issuer)
    if envelope.place != expected_place or envelope.space != expected_space:
        return AdmissionEnvelopeVerification(False, "envelope_place_mismatch", issuer)
    if revocations is not None and revocations.is_revoked(envelope.profile):
        return AdmissionEnvelopeVerification(False, "envelope_revoked", issuer)
    return AdmissionEnvelopeVerification(True, issuer=issuer)
