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
class SignatureVerification:
    verified: bool
    reason: str | None = None
    issuer: TrustedIssuer | None = None


def evidence_scope(requirement_set: dict[str, Any]) -> str:
    """Return the local scope identifier that an issuer is authorized for."""
    return f"{requirement_set['place']}::{requirement_set['space']}"


def _signature_payload(*, issuer_id: str, algorithm: str, evidence_type: str,
                       scope: str, signed_payload_digest: str) -> bytes:
    return _canonical({
        "issuer_id": issuer_id,
        "algorithm": algorithm,
        "evidence_type": evidence_type,
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
