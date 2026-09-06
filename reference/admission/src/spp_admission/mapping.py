"""Deterministic local requirement-to-conformance mapping.

This reference registry selects an explicitly registered test mechanism from a
place requirement and robot embodiment.  It is intentionally in-process: it
does not discover plugins, contact middleware, or define a protocol surface.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable


_ASSURANCE_LEVELS = ("E0", "E1", "E2", "E3", "E4")
TestFactory = Callable[[dict[str, Any]], dict[str, Any]]


def _legacy_test(adapter: str, capability: str) -> TestFactory:
    def build(requirement: dict[str, Any]) -> dict[str, Any]:
        return {
            "test_id": f"test:{adapter}",
            "requirement_id": requirement["id"],
            "adapter": adapter,
            "capability": capability,
            "expected": f"{requirement['operator']} {requirement['value']}",
        }
    return build


@dataclass(frozen=True)
class ConformanceProvider:
    """One local mechanism that can prove a requirement for an embodiment."""

    provider_id: str
    requirement_id: str
    embodiment: str
    assurance_level: str
    priority: int
    test_factory: TestFactory

    def build_test(self, requirement: dict[str, Any]) -> dict[str, Any]:
        return self.test_factory(requirement)


@dataclass(frozen=True)
class MappingSelection:
    """The deterministic outcome of one requirement/embodiment lookup."""

    requirement_id: str
    embodiment: str
    provider: ConformanceProvider | None
    reason: str | None = None

    @property
    def resolved(self) -> bool:
        return self.provider is not None


class RequirementMappingRegistry:
    """Small, configured registry for the reference implementation.

    Higher assurance is required to meet a requested level.  Among compatible
    providers, greater priority wins; provider ID is the deterministic tie
    breaker.  Callers configure registrations deliberately at process startup.
    """

    def __init__(self, providers: Iterable[ConformanceProvider] = ()) -> None:
        self._providers: dict[str, ConformanceProvider] = {}
        for provider in providers:
            self.register(provider)

    def register(self, provider: ConformanceProvider) -> None:
        if provider.assurance_level not in _ASSURANCE_LEVELS:
            raise ValueError("unknown provider assurance level")
        if provider.provider_id in self._providers:
            raise ValueError(f"provider already registered: {provider.provider_id}")
        self._providers[provider.provider_id] = provider

    def select(
        self,
        requirement: dict[str, Any],
        embodiment: str,
        required_assurance_level: str = "E2",
    ) -> MappingSelection:
        if required_assurance_level not in _ASSURANCE_LEVELS:
            raise ValueError("unknown required assurance level")
        required_index = _ASSURANCE_LEVELS.index(required_assurance_level)
        candidates = [
            provider for provider in self._providers.values()
            if provider.requirement_id == requirement.get("id")
            and provider.embodiment == embodiment
            and _ASSURANCE_LEVELS.index(provider.assurance_level) >= required_index
        ]
        if not candidates:
            return MappingSelection(
                str(requirement.get("id", "")), embodiment, None,
                "unsupported_requirement_or_embodiment",
            )
        provider = sorted(candidates, key=lambda item: (-item.priority, item.provider_id))[0]
        return MappingSelection(requirement["id"], embodiment, provider)


# Mobile-base factories intentionally retain the original test IDs and
# capability keys so existing reference evidence remains compatible.
DEFAULT_REQUIREMENT_MAPPING_REGISTRY = RequirementMappingRegistry((
    ConformanceProvider("mobile_speed_bound", "movement.max_speed", "demo_mobile_base", "E2", 100,
                        _legacy_test("speed-bound", "movement.max_speed")),
    ConformanceProvider("mobile_lidar_separation", "human_separation", "demo_mobile_base", "E2", 100,
                        _legacy_test("separation-bound", "human_separation")),
    ConformanceProvider("mobile_camera_privacy", "sensing.facial_recognition", "demo_mobile_base", "E2", 100,
                        _legacy_test("facial-recognition", "sensing.facial_recognition")),
    ConformanceProvider("mobile_video_retention", "data.video_retention", "demo_mobile_base", "E2", 100,
                        _legacy_test("video-retention", "data.video_retention")),
    ConformanceProvider("humanoid_gait_speed_bound", "movement.max_speed", "demo_humanoid", "E2", 100,
                        _legacy_test("gait-speed-bound", "gait.maximum_speed_mps")),
    ConformanceProvider("humanoid_body_proximity", "human_separation", "demo_humanoid", "E2", 100,
                        _legacy_test("body-proximity-bound", "body.minimum_human_clearance_m")),
    ConformanceProvider("humanoid_vision_privacy", "sensing.facial_recognition", "demo_humanoid", "E2", 100,
                        _legacy_test("vision-pipeline-privacy", "vision_pipeline.facial_recognition_enabled")),
))
