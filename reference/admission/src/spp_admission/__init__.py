"""Experimental SPP Conformance and Admission reference implementation."""

from .engine import (
    ReplayRegistry,
    admit,
    build_evidence,
    compute_requirement_delta,
    derive_plan,
    execute_plan,
    load_requirement_set,
    reset_replay_registry,
)

__all__ = [
    "EvidenceRecord",
    "Sufficiency",
    "assess_sufficiency",
    "derive_requalification_plan",
    "admit",
    "admit_evidence_backed",
    "admit_verified_evidence_backed",
    "ReplayRegistry",
    "build_evidence",
    "compute_requirement_delta",
    "derive_plan",
    "execute_plan",
    "load_requirement_set",
    "reset_replay_registry",
    "ConformanceProvider",
    "MappingSelection",
    "RequirementMappingRegistry",
    "DEFAULT_REQUIREMENT_MAPPING_REGISTRY",
    "EVIDENCE_BUNDLE_TYPE",
    "SignedEvidence",
    "SignedEvidenceRecord",
    "SignatureVerification",
    "TrustedIssuer",
    "TrustedIssuerRegistry",
    "evidence_scope",
    "sign_evidence",
    "verify_signed_evidence",
]

from .sufficiency import EvidenceRecord, Sufficiency, assess_sufficiency, derive_requalification_plan
from .boundary import admit_evidence_backed, admit_verified_evidence_backed
from .trust import (
    EVIDENCE_BUNDLE_TYPE,
    SignedEvidence,
    SignedEvidenceRecord,
    SignatureVerification,
    TrustedIssuer,
    TrustedIssuerRegistry,
    evidence_scope,
    sign_evidence,
    verify_signed_evidence,
)
from .mapping import (
    ConformanceProvider,
    DEFAULT_REQUIREMENT_MAPPING_REGISTRY,
    MappingSelection,
    RequirementMappingRegistry,
)
