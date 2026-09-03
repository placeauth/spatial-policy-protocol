from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PlaceRequirement:
    id: str
    action: str
    operator: str
    value: Any
    unit: str | None = None
    essential: bool = True
    degraded_restriction: str | None = None


@dataclass(frozen=True)
class RobotState:
    actor_id: str
    build_fingerprint: str
    controller_fingerprint: str
    embodiment: str
    environment_digest: str
    capabilities: dict[str, Any]


@dataclass(frozen=True)
class ConformanceTest:
    test_id: str
    requirement_id: str
    adapter: str
    expected: str


@dataclass(frozen=True)
class EvidenceBinding:
    actor_id: str
    build_fingerprint: str
    controller_fingerprint: str
    policy_digest: str
    environment_digest: str
    plan_digest: str


@dataclass
class AdmissionProfile:
    status: str
    actor_id: str
    place: str
    space: str
    policy_version: int
    evidence_digest: str
    binding: EvidenceBinding
    operating_profile: dict[str, Any] = field(default_factory=dict)
    restrictions: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
