"""Experimental RFC 8785 profile for signed AdmissionProfile envelopes.

The existing Python canonicalization profile is intentionally left in
``admission_envelope.py``. This module is a separate, non-normative profile.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import re
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .admission_envelope import (
    ADMISSION_ENVELOPE_TYPE,
    ADMISSION_ENVELOPE_VERSION,
    AdmissionEnvelopeVerification,
    SignedAdmissionEnvelope,
    admission_scope,
    verify_signed_admission_envelope,
)
from .lifecycle import ProfileRevocationRegistry
from .models import AdmissionProfile, EvidenceBinding
from .trust import ED25519, TrustedIssuer, TrustedIssuerRegistry


PYTHON_JSON_PROFILE = "spp-python-json-v1-experimental"
JCS_PROFILE = "rfc8785-jcs-v1-experimental"
SUPPORTED_CANONICALIZATION_PROFILES = frozenset({PYTHON_JSON_PROFILE, JCS_PROFILE})
_UTC_SECONDS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_MAX_SAFE_INTEGER = 2**53 - 1


class JCSProfileError(ValueError):
    """A value cannot be represented by this experimental portable profile."""


@dataclass(frozen=True)
class JCSSignedAdmissionEnvelope:
    """JCS-bound experimental AdmissionProfile envelope.

    ``canonicalization_profile`` is not advisory: it is a required signed
    field and must be exactly ``JCS_PROFILE`` for successful verification.
    """

    profile: AdmissionProfile
    issuer_id: str
    algorithm: str
    envelope_type: str
    envelope_version: str
    canonicalization_profile: str
    subject_id: str
    place: str
    space: str
    scope: str
    issued_at: str
    expires_at: str
    signed_payload_digest: str
    signature: str


def _valid_profile(profile: AdmissionProfile) -> bool:
    return (
        isinstance(profile, AdmissionProfile)
        and isinstance(profile.binding, EvidenceBinding)
        and profile.status in {"ADMITTED", "DEGRADED", "DENIED"}
        and all(isinstance(value, str) and value for value in (profile.actor_id, profile.place, profile.space))
        and isinstance(profile.evidence_digest, str)
        and (profile.status == "DENIED" or profile.binding.actor_id == profile.actor_id)
    )


def _validate_jcs_value(value: Any) -> Any:
    """Reject values outside the explicit portable subset before JCS encoding."""
    if value is None or isinstance(value, (str, bool)):
        if isinstance(value, str) and any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise JCSProfileError("malformed Unicode scalar value")
        return value
    if isinstance(value, int):
        if abs(value) > _MAX_SAFE_INTEGER:
            raise JCSProfileError("integer outside JavaScript safe range")
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise JCSProfileError("non-finite JSON number")
        if value == 0.0 and math.copysign(1.0, value) < 0:
            raise JCSProfileError("negative zero is not permitted")
        if value.is_integer() and abs(value) > _MAX_SAFE_INTEGER:
            raise JCSProfileError("integer outside JavaScript safe range")
        return value
    if isinstance(value, list):
        return [_validate_jcs_value(item) for item in value]
    if isinstance(value, tuple):
        return [_validate_jcs_value(item) for item in value]
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, nested in value.items():
            if not isinstance(key, str):
                raise JCSProfileError("JSON object key must be a string")
            _validate_jcs_value(key)
            normalized[key] = _validate_jcs_value(nested)
        return normalized
    raise JCSProfileError(f"unsupported JCS value type: {type(value).__name__}")


def canonicalize_jcs(value: Any) -> bytes:
    """Return RFC 8785 bytes for the experimental safe JSON subset."""
    try:
        return rfc8785.dumps(_validate_jcs_value(value))
    except (rfc8785.CanonicalizationError, OverflowError, TypeError, ValueError) as error:
        raise JCSProfileError(str(error)) from error


def jcs_digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonicalize_jcs(value)).hexdigest()


def jcs_restriction_identifier(restriction: str) -> str:
    """Return the JCS-profile identity for one exact restriction string."""
    if not isinstance(restriction, str) or not restriction.strip():
        raise JCSProfileError("restriction must be a nonempty string")
    return jcs_digest({"restriction": restriction})


def _effective_restrictions(profile: AdmissionProfile) -> tuple[str, ...]:
    embedded = profile.operating_profile.get("restrictions", []) if isinstance(profile.operating_profile, dict) else []
    if not isinstance(profile.restrictions, list) or not isinstance(embedded, list):
        raise JCSProfileError("profile restrictions malformed")
    values = [*profile.restrictions, *embedded]
    if not all(isinstance(item, str) and item.strip() for item in values):
        raise JCSProfileError("profile restrictions malformed")
    # JCS orders object properties by UTF-16 code units. Use that same explicit
    # ordering for this profile's normalized restriction-set array so a Python
    # implementation does not accidentally rely on Unicode code-point order.
    return tuple(sorted(set(values), key=lambda item: item.encode("utf-16be")))


def jcs_restriction_profile_identifier(profile: AdmissionProfile) -> str:
    """Bind the full profile with the two existing restriction lists as a set."""
    if not isinstance(profile, AdmissionProfile):
        raise JCSProfileError("AdmissionProfile required")
    restrictions = _effective_restrictions(profile)
    operating_profile = dict(profile.operating_profile)
    operating_profile.pop("restrictions", None)
    payload = {
        "status": profile.status,
        "actor_id": profile.actor_id,
        "place": profile.place,
        "space": profile.space,
        "policy_version": profile.policy_version,
        "evidence_digest": profile.evidence_digest,
        "binding": asdict(profile.binding),
        "operating_profile": operating_profile,
        "effective_restrictions": list(restrictions),
        "unresolved": profile.unresolved,
        "reason_codes": profile.reason_codes,
    }
    return "urn:spp:jcs-restriction-profile:" + jcs_digest(payload).removeprefix("sha256:")


def parse_jcs_json(source: str) -> Any:
    """Parse JSON fail-closed for duplicate keys and invalid JCS-profile data.

    This intentionally parses generic JSON only; it does not claim to be a
    complete envelope wire parser.
    """
    if not isinstance(source, str):
        raise JCSProfileError("JSON source must be text")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in pairs:
            if key in output:
                raise JCSProfileError(f"duplicate JSON key: {key}")
            output[key] = value
        return output

    def reject_constant(value: str) -> Any:
        raise JCSProfileError(f"non-finite JSON number: {value}")

    def parse_integer(token: str) -> int:
        # json.loads otherwise turns the lexeme -0 into integer 0 and erases
        # the profile-significant invalid representation before validation.
        if token == "-0":
            raise JCSProfileError("negative zero is not permitted")
        value = int(token)
        if abs(value) > _MAX_SAFE_INTEGER:
            raise JCSProfileError("integer outside JavaScript safe range")
        return value

    def parse_float(token: str) -> float:
        value = float(token)
        if not math.isfinite(value):
            raise JCSProfileError("non-finite JSON number")
        if value == 0.0 and math.copysign(1.0, value) < 0:
            raise JCSProfileError("negative zero is not permitted")
        if value.is_integer() and abs(value) > _MAX_SAFE_INTEGER:
            raise JCSProfileError("integer outside JavaScript safe range")
        return value

    try:
        return _validate_jcs_value(json.loads(
            source,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_constant,
            parse_int=parse_integer,
            parse_float=parse_float,
        ))
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError) as error:
        if isinstance(error, JCSProfileError):
            raise
        raise JCSProfileError("malformed JSON") from error


def _timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not _UTC_SECONDS.fullmatch(value):
        raise JCSProfileError("noncanonical_timestamp")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise JCSProfileError("noncanonical_timestamp") from error


def _timestamp_text(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise JCSProfileError("timezone-aware timestamp required")
    utc = value.astimezone(timezone.utc)
    if utc.microsecond:
        raise JCSProfileError("fractional seconds are not permitted")
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def _profile_digest(profile: AdmissionProfile) -> str:
    return jcs_digest(asdict(profile))


def _signature_payload(*, issuer_id: str, algorithm: str, envelope_type: str,
                       envelope_version: str, canonicalization_profile: str,
                       subject_id: str, place: str, space: str, scope: str,
                       issued_at: str, expires_at: str, signed_payload_digest: str) -> bytes:
    return canonicalize_jcs({
        "issuer_id": issuer_id,
        "algorithm": algorithm,
        "envelope_type": envelope_type,
        "envelope_version": envelope_version,
        "canonicalization_profile": canonicalization_profile,
        "subject_id": subject_id,
        "place": place,
        "space": space,
        "scope": scope,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "signed_payload_digest": signed_payload_digest,
    })


def sign_jcs_admission_profile(profile: AdmissionProfile, *, issuer_id: str,
                               private_key: Ed25519PrivateKey, issued_at: datetime,
                               expires_at: datetime) -> JCSSignedAdmissionEnvelope:
    """Create a JCS-profile envelope without changing the legacy profile."""
    if not _valid_profile(profile) or not isinstance(issuer_id, str) or not issuer_id:
        raise JCSProfileError("valid profile and issuer_id are required")
    issued, expires = _timestamp_text(issued_at), _timestamp_text(expires_at)
    if _timestamp(expires) <= _timestamp(issued):
        raise JCSProfileError("invalid envelope time range")
    subject_id, place, space = profile.actor_id, profile.place, profile.space
    scope = admission_scope(profile)
    signed_payload_digest = _profile_digest(profile)
    payload = _signature_payload(
        issuer_id=issuer_id, algorithm=ED25519, envelope_type=ADMISSION_ENVELOPE_TYPE,
        envelope_version=ADMISSION_ENVELOPE_VERSION, canonicalization_profile=JCS_PROFILE,
        subject_id=subject_id, place=place, space=space, scope=scope,
        issued_at=issued, expires_at=expires, signed_payload_digest=signed_payload_digest,
    )
    return JCSSignedAdmissionEnvelope(
        deepcopy(profile), issuer_id, ED25519, ADMISSION_ENVELOPE_TYPE,
        ADMISSION_ENVELOPE_VERSION, JCS_PROFILE, subject_id, place, space, scope,
        issued, expires, signed_payload_digest,
        base64.b64encode(private_key.sign(payload)).decode("ascii"),
    )


def verify_jcs_admission_envelope(envelope: JCSSignedAdmissionEnvelope,
                                  trusted_issuers: TrustedIssuerRegistry, *,
                                  expected_subject_id: str, expected_place: str,
                                  expected_space: str, now: datetime | None = None,
                                  revocations: ProfileRevocationRegistry | None = None) -> AdmissionEnvelopeVerification:
    """Verify a JCS envelope with exact profile dispatch and timestamp rules."""
    if not isinstance(envelope, JCSSignedAdmissionEnvelope) or not isinstance(trusted_issuers, TrustedIssuerRegistry):
        return AdmissionEnvelopeVerification(False, "malformed_envelope")
    if envelope.canonicalization_profile not in SUPPORTED_CANONICALIZATION_PROFILES:
        return AdmissionEnvelopeVerification(False, "unsupported_canonicalization_profile")
    if not all(isinstance(value, str) and value for value in (
        expected_subject_id, expected_place, expected_space, envelope.issuer_id,
        envelope.subject_id, envelope.place, envelope.space, envelope.scope,
        envelope.signed_payload_digest, envelope.signature,
    )) or not _valid_profile(envelope.profile):
        return AdmissionEnvelopeVerification(False, "malformed_envelope")
    if envelope.envelope_version != ADMISSION_ENVELOPE_VERSION:
        return AdmissionEnvelopeVerification(False, "unsupported_envelope_version")
    if envelope.envelope_type != ADMISSION_ENVELOPE_TYPE or envelope.algorithm != ED25519:
        return AdmissionEnvelopeVerification(False, "unsupported_signature_algorithm")
    if (envelope.subject_id != envelope.profile.actor_id or envelope.place != envelope.profile.place
            or envelope.space != envelope.profile.space or envelope.scope != admission_scope(envelope.profile)):
        return AdmissionEnvelopeVerification(False, "malformed_envelope")
    try:
        issued, expires = _timestamp(envelope.issued_at), _timestamp(envelope.expires_at)
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            return AdmissionEnvelopeVerification(False, "malformed_verification_time")
        current = current.astimezone(timezone.utc)
        if expires <= issued:
            return AdmissionEnvelopeVerification(False, "invalid_envelope_time_range")
        if issued > current:
            return AdmissionEnvelopeVerification(False, "envelope_issued_in_future")
        if expires <= current:
            return AdmissionEnvelopeVerification(False, "envelope_expired")
        profile_digest = _profile_digest(envelope.profile)
    except JCSProfileError:
        return AdmissionEnvelopeVerification(False, "jcs_profile_value_invalid")
    if profile_digest != envelope.signed_payload_digest:
        return AdmissionEnvelopeVerification(False, "signed_payload_digest_mismatch")
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
        signature = base64.b64decode(envelope.signature, validate=True)
        Ed25519PublicKey.from_public_bytes(issuer.public_key).verify(signature, _signature_payload(
            issuer_id=envelope.issuer_id, algorithm=envelope.algorithm,
            envelope_type=envelope.envelope_type, envelope_version=envelope.envelope_version,
            canonicalization_profile=envelope.canonicalization_profile,
            subject_id=envelope.subject_id, place=envelope.place, space=envelope.space,
            scope=envelope.scope, issued_at=envelope.issued_at, expires_at=envelope.expires_at,
            signed_payload_digest=envelope.signed_payload_digest,
        ))
    except (JCSProfileError, ValueError, TypeError, InvalidSignature):
        return AdmissionEnvelopeVerification(False, "invalid_envelope_signature")
    if envelope.canonicalization_profile != JCS_PROFILE:
        return AdmissionEnvelopeVerification(False, "canonicalization_profile_mismatch", issuer)
    if envelope.subject_id != expected_subject_id:
        return AdmissionEnvelopeVerification(False, "envelope_subject_mismatch", issuer)
    if envelope.place != expected_place or envelope.space != expected_space:
        return AdmissionEnvelopeVerification(False, "envelope_place_mismatch", issuer)
    if revocations is not None and revocations.is_revoked(envelope.profile):
        return AdmissionEnvelopeVerification(False, "envelope_revoked", issuer)
    return AdmissionEnvelopeVerification(True, issuer=issuer)


def verify_profiled_admission_envelope(envelope: SignedAdmissionEnvelope | JCSSignedAdmissionEnvelope,
                                       canonicalization_profile: str, trusted_issuers: TrustedIssuerRegistry,
                                       **kwargs: Any) -> AdmissionEnvelopeVerification:
    """Dispatch only when the caller supplies an explicit supported profile."""
    if canonicalization_profile not in SUPPORTED_CANONICALIZATION_PROFILES:
        return AdmissionEnvelopeVerification(False, "unsupported_canonicalization_profile")
    if canonicalization_profile == PYTHON_JSON_PROFILE:
        if not isinstance(envelope, SignedAdmissionEnvelope):
            return AdmissionEnvelopeVerification(False, "canonicalization_profile_mismatch")
        return verify_signed_admission_envelope(envelope, trusted_issuers, **kwargs)
    if not isinstance(envelope, JCSSignedAdmissionEnvelope):
        return AdmissionEnvelopeVerification(False, "canonicalization_profile_mismatch")
    return verify_jcs_admission_envelope(envelope, trusted_issuers, **kwargs)
