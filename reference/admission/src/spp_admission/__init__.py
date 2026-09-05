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
    "ReplayRegistry",
    "build_evidence",
    "compute_requirement_delta",
    "derive_plan",
    "execute_plan",
    "load_requirement_set",
    "reset_replay_registry",
]

from .sufficiency import EvidenceRecord, Sufficiency, assess_sufficiency, derive_requalification_plan
