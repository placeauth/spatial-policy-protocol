"""Local Ed25519 evidence signing and trusted-issuer verification.

This reference layer deliberately has no network discovery, certificates, or
key lifecycle service. A deployment provisions trusted public keys locally.
"""
from __future__ import annotations

import base64
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .engine import _canonical, digest


ED25519 = "Ed25519"
EVIDENCE_BUNDLE_TYPE = "spp:evidence-bundle"
PLACE_REQUIREMENTS_TYPE = "spp:place-requirement-set"


@dataclass(frozen=True)
class TrustedIssuer:
    """A locally provisioned reference trust anchor for signed evidence."""

    issuer_id: str
    public_key: bytes
    allowed_evidence_types: frozenset[str]
    allowed_scopes: frozenset[str]
    enabled: bool = True

    def allows_scope(self, scope: str) -> bool:
        return any(
            allowed == "*" or allowed == scope
            or (allowed.endswith("/*") and scope.startswith(allowed[:-1]))
            for allowed in self.allowed_scopes
        )


class TrustedIssuerRegistry:
    """Small in-memory registry for the reference admission service."""

    def __init__(self, issuers: Iterable[TrustedIssuer] = ()) -> None:
        self._issuers = {issuer.issuer_id: issuer for issuer in issuers}

    def get(self, issuer_id: str) -> TrustedIssuer | None:
        return self._issuers.get(issuer_id)

    def add(self, issuer: TrustedIssuer) -> None:
        self._issuers[issuer.issuer_id] = issuer


def _allows(allowed_values: frozenset[str], value: str) -> bool:
    return any(
        allowed == "*" or allowed == value
        or (allowed.endswith("/*") and value.startswith(allowed[:-1]))
        for allowed in allowed_values
    )


@dataclass(frozen=True)
class TrustedPolicyAuthority:
    """A locally provisioned trust anchor authorized to define place policy."""

    authority_id: str
    public_key: bytes
    allowed_places: frozenset[str]
    allowed_scopes: frozenset[str]
    enabled: bool = True

    def allows_place(self, place: str) -> bool:
        return _allows(self.allowed_places, place)

    def allows_scope(self, scope: str) -> bool:
        return _allows(self.allowed_scopes, scope)


class TrustedPolicyAuthorityRegistry:
    """Small in-memory registry for reference signed place requirements."""

    def __init__(self, authorities: Iterable[TrustedPolicyAuthority] = ()) -> None:
        self._authorities = {authority.authority_id: authority for authority in authorities}

    def get(self, authority_id: str) -> TrustedPolicyAuthority | None:
        return self._authorities.get(authority_id)

    def add(self, authority: TrustedPolicyAuthority) -> None:
        self._authorities[authority.authority_id] = authority


@dataclass(frozen=True)
class SignedEvidence:
    """A complete EvidenceBundle with its issuer assertion and signature."""

    evidence: dict[str, Any]
    issuer_id: str
    algorithm: str
    evidence_type: str
    scope: str
    signed_payload_digest: str
    signature: str


@dataclass(frozen=True)
class SignedEvidenceRecord:
    """Historical source evidence that remains signed for requalification."""

    requirements: dict[str, Any]
    plan: dict[str, Any]
    signed_evidence: SignedEvidence


@dataclass(frozen=True)
class SignedPlaceRequirements:
    """A complete PlaceRequirementSet signed by a policy authority."""

    requirements: dict[str, Any]
    authority_id: str
    algorithm: str
    policy_type: str
    scope: str
    signed_payload_digest: str
    signature: str


@dataclass(frozen=True)
class SignatureVerification:
    verified: bool
    reason: str | None = None
    issuer: TrustedIssuer | None = None


@dataclass(frozen=True)
class PolicySignatureVerification:
    verified: bool
    reason: str | None = None
    authority: TrustedPolicyAuthority | None = None


def evidence_scope(requirement_set: dict[str, Any]) -> str:
    """Return the local scope identifier that an issuer is authorized for."""
    return f"{requirement_set['place']}::{requirement_set['space']}"


def policy_scope(requirement_set: dict[str, Any]) -> str:
    """Return the place-local scope controlled by a requirements authority."""
    return str(requirement_set["space"])


def _signature_payload(*, issuer_id: str, algorithm: str, evidence_type: str,
                       scope: str, signed_payload_digest: str) -> bytes:
    return _canonical({
        "issuer_id": issuer_id,
        "algorithm": algorithm,
        "evidence_type": evidence_type,
        "scope": scope,
        "signed_payload_digest": signed_payload_digest,
    }).encode("utf-8")


def _policy_signature_payload(*, authority_id: str, algorithm: str, policy_type: str,
                              scope: str, signed_payload_digest: str) -> bytes:
    return _canonical({
        "authority_id": authority_id,
        "algorithm": algorithm,
        "policy_type": policy_type,
        "scope": scope,
        "signed_payload_digest": signed_payload_digest,
    }).encode("utf-8")


def sign_evidence(evidence: dict[str, Any], *, issuer_id: str,
                  private_key: Ed25519PrivateKey, scope: str,
                  evidence_type: str = EVIDENCE_BUNDLE_TYPE) -> SignedEvidence:
    """Sign the canonical digest of the complete existing EvidenceBundle."""
    if not issuer_id or not scope or not evidence_type:
        raise ValueError("issuer_id, scope, and evidence_type are required")
    signed_payload_digest = digest(evidence)
    payload = _signature_payload(
        issuer_id=issuer_id, algorithm=ED25519, evidence_type=evidence_type,
        scope=scope, signed_payload_digest=signed_payload_digest,
    )
    signature = base64.b64encode(private_key.sign(payload)).decode("ascii")
    return SignedEvidence(
        evidence=deepcopy(evidence), issuer_id=issuer_id, algorithm=ED25519,
        evidence_type=evidence_type, scope=scope,
        signed_payload_digest=signed_payload_digest, signature=signature,
    )


def verify_signed_evidence(signed_evidence: SignedEvidence,
                           trusted_issuers: TrustedIssuerRegistry, *,
                           expected_scope: str) -> SignatureVerification:
    """Verify signature, issuer availability, and issuer type/scope authority."""
    if not isinstance(signed_evidence, SignedEvidence):
        return SignatureVerification(False, "unsigned_evidence")
    if signed_evidence.algorithm != ED25519:
        return SignatureVerification(False, "unsupported_signature_algorithm")
    issuer = trusted_issuers.get(signed_evidence.issuer_id)
    if issuer is None:
        return SignatureVerification(False, "unknown_issuer")
    if not issuer.enabled:
        return SignatureVerification(False, "issuer_disabled")
    if signed_evidence.evidence_type not in issuer.allowed_evidence_types:
        return SignatureVerification(False, "issuer_unauthorized_evidence_type")
    if signed_evidence.scope != expected_scope:
        return SignatureVerification(False, "signed_scope_mismatch")
    if not issuer.allows_scope(signed_evidence.scope):
        return SignatureVerification(False, "issuer_unauthorized_scope")
    if digest(signed_evidence.evidence) != signed_evidence.signed_payload_digest:
        return SignatureVerification(False, "signed_payload_digest_mismatch")
    try:
        signature = base64.b64decode(signed_evidence.signature, validate=True)
        public_key = Ed25519PublicKey.from_public_bytes(issuer.public_key)
        public_key.verify(signature, _signature_payload(
            issuer_id=signed_evidence.issuer_id,
            algorithm=signed_evidence.algorithm,
            evidence_type=signed_evidence.evidence_type,
            scope=signed_evidence.scope,
            signed_payload_digest=signed_evidence.signed_payload_digest,
        ))
    except (ValueError, TypeError, InvalidSignature):
        return SignatureVerification(False, "invalid_evidence_signature")
    return SignatureVerification(True, issuer=issuer)


def sign_place_requirements(
    requirements: dict[str, Any], *, authority_id: str, private_key: Ed25519PrivateKey,
    scope: str | None = None, policy_type: str = PLACE_REQUIREMENTS_TYPE,
) -> SignedPlaceRequirements:
    """Sign the complete semantic PlaceRequirementSet with Ed25519.

    The canonical digest covers every currently modeled policy field, including
    place, space, policy identity/version, requirements, and environment data.
    """
    actual_scope = scope or policy_scope(requirements)
    if not authority_id or not actual_scope or not policy_type:
        raise ValueError("authority_id, scope, and policy_type are required")
    signed_payload_digest = digest(requirements)
    signature = base64.b64encode(private_key.sign(_policy_signature_payload(
        authority_id=authority_id, algorithm=ED25519, policy_type=policy_type,
        scope=actual_scope, signed_payload_digest=signed_payload_digest,
    ))).decode("ascii")
    return SignedPlaceRequirements(
        requirements=deepcopy(requirements), authority_id=authority_id,
        algorithm=ED25519, policy_type=policy_type, scope=actual_scope,
        signed_payload_digest=signed_payload_digest, signature=signature,
    )


def verify_signed_place_requirements(
    signed_requirements: SignedPlaceRequirements,
    trusted_authorities: TrustedPolicyAuthorityRegistry,
    *, expected_place: str | None = None, expected_scope: str | None = None,
) -> PolicySignatureVerification:
    """Verify authority, authorization, and a complete signed requirements set."""
    if not isinstance(signed_requirements, SignedPlaceRequirements):
        return PolicySignatureVerification(False, "unsigned_policy_not_allowed")
    if signed_requirements.algorithm != ED25519:
        return PolicySignatureVerification(False, "unsupported_signature_algorithm")
    authority = trusted_authorities.get(signed_requirements.authority_id)
    if authority is None:
        return PolicySignatureVerification(False, "unknown_policy_authority")
    if not authority.enabled:
        return PolicySignatureVerification(False, "policy_authority_disabled")
    requirements = signed_requirements.requirements
    try:
        place = str(requirements["place"])
        scope = policy_scope(requirements)
    except (KeyError, TypeError, ValueError):
        return PolicySignatureVerification(False, "malformed_signed_policy")
    if expected_place is not None and place != expected_place:
        return PolicySignatureVerification(False, "policy_place_mismatch")
    if expected_scope is not None and scope != expected_scope:
        return PolicySignatureVerification(False, "policy_scope_mismatch")
    if signed_requirements.scope != scope:
        return PolicySignatureVerification(False, "policy_scope_mismatch")
    if signed_requirements.policy_type != PLACE_REQUIREMENTS_TYPE:
        return PolicySignatureVerification(False, "policy_authority_unauthorized")
    if not authority.allows_place(place) or not authority.allows_scope(scope):
        return PolicySignatureVerification(False, "policy_authority_unauthorized")
    if digest(requirements) != signed_requirements.signed_payload_digest:
        return PolicySignatureVerification(False, "policy_signature_invalid")
    try:
        signature = base64.b64decode(signed_requirements.signature, validate=True)
        public_key = Ed25519PublicKey.from_public_bytes(authority.public_key)
        public_key.verify(signature, _policy_signature_payload(
            authority_id=signed_requirements.authority_id,
            algorithm=signed_requirements.algorithm,
            policy_type=signed_requirements.policy_type,
            scope=signed_requirements.scope,
            signed_payload_digest=signed_requirements.signed_payload_digest,
        ))
    except (ValueError, TypeError, InvalidSignature):
        return PolicySignatureVerification(False, "policy_signature_invalid")
    return PolicySignatureVerification(True, authority=authority)
