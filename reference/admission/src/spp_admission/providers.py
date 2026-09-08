"""Explicit, local contract for independently implemented conformance providers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Protocol

from .models import RobotState
from .vocabulary import DEFAULT_REQUIREMENT_VOCABULARY, RequirementVocabularyRegistry


ASSURANCE_LEVELS = ("E0", "E1", "E2", "E3", "E4")


@dataclass(frozen=True)
class ConformanceProviderDescriptor:
    """Stable declaration of one external provider's capabilities."""

    provider_id: str
    provider_version: str
    supported_requirement_types: frozenset[str]
    supported_embodiments: frozenset[str]
    supported_assurance_levels: frozenset[str]
    evidence_type: str
    priority: int = 0
    description: str | None = None
    supported_requirement_versions: dict[str, frozenset[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class ConformanceProviderResult:
    """One deterministic provider outcome convertible to an SPP test result."""

    provider_id: str
    provider_version: str
    requirement_id: str
    passed: bool
    measured_value: Any
    assurance_level: str
    evidence_type: str
    metadata: dict[str, Any] = field(default_factory=dict)
    requirement_version: str | None = None
    unit: str | None = None
    reasons: tuple[str, ...] = ()

    def to_evidence_result(self, test_id: str) -> dict[str, Any]:
        """Return the existing EvidenceBundle test-result representation."""
        return {"test_id": test_id, "requirement_id": self.requirement_id, "passed": self.passed}


class ExternalConformanceProvider(Protocol):
    """The deliberately small external-provider execution contract."""

    descriptor: ConformanceProviderDescriptor

    def evaluate(self, requirement: dict[str, Any], subject: RobotState) -> ConformanceProviderResult:
        """Evaluate one requirement against an authenticated subject context."""


@dataclass(frozen=True)
class ProviderSelection:
    requirement_id: str
    embodiment: str
    provider: ExternalConformanceProvider | None
    reason: str | None = None

    @property
    def resolved(self) -> bool:
        return self.provider is not None


def _meets_assurance(provider: ConformanceProviderDescriptor, minimum: str) -> bool:
    return any(ASSURANCE_LEVELS.index(level) >= ASSURANCE_LEVELS.index(minimum)
               for level in provider.supported_assurance_levels)


class ConformanceProviderRegistry:
    """Configured local registry; it does not discover, load, or trust providers."""

    def __init__(
        self, providers: Iterable[ExternalConformanceProvider] = (),
        vocabulary: RequirementVocabularyRegistry = DEFAULT_REQUIREMENT_VOCABULARY,
    ) -> None:
        self._providers: dict[str, ExternalConformanceProvider] = {}
        self._vocabulary = vocabulary
        for provider in providers:
            self.register(provider)

    def register(self, provider: ExternalConformanceProvider) -> None:
        descriptor = provider.descriptor
        if (not descriptor.provider_id or not descriptor.provider_version
                or not descriptor.supported_requirement_types
                or not descriptor.supported_embodiments
                or not descriptor.supported_assurance_levels
                or not descriptor.evidence_type
                or set(descriptor.supported_requirement_versions) != set(descriptor.supported_requirement_types)
                or any(not versions for versions in descriptor.supported_requirement_versions.values())
                or any(not version for versions in descriptor.supported_requirement_versions.values() for version in versions)
                or any(level not in ASSURANCE_LEVELS for level in descriptor.supported_assurance_levels)):
            raise ValueError("invalid provider descriptor")
        if descriptor.provider_id in self._providers:
            raise ValueError(f"provider already registered: {descriptor.provider_id}")
        self._providers[descriptor.provider_id] = provider

    def compatible(
        self, requirement: dict[str, Any], embodiment: str, minimum_assurance_level: str = "E2",
    ) -> list[ExternalConformanceProvider]:
        if minimum_assurance_level not in ASSURANCE_LEVELS:
            raise ValueError("unknown required assurance level")
        resolution = self._vocabulary.validate(requirement)
        if not resolution.resolved:
            return []
        requirement_id = requirement.get("id")
        version = resolution.definition.version
        return sorted(
            [provider for provider in self._providers.values()
             if requirement_id in provider.descriptor.supported_requirement_types
             and self._supports_version(provider.descriptor, requirement_id, version)
             and embodiment in provider.descriptor.supported_embodiments
             and _meets_assurance(provider.descriptor, minimum_assurance_level)],
            key=lambda provider: (-provider.descriptor.priority, provider.descriptor.provider_id),
        )

    def select(
        self, requirement: dict[str, Any], embodiment: str, minimum_assurance_level: str = "E2",
    ) -> ProviderSelection:
        if minimum_assurance_level not in ASSURANCE_LEVELS:
            raise ValueError("unknown required assurance level")
        resolution = self._vocabulary.validate(requirement)
        requirement_id = str(requirement.get("id", ""))
        if not resolution.resolved:
            reason = "unsupported_requirement" if resolution.status == "UNKNOWN" else resolution.reason
            return ProviderSelection(requirement_id, embodiment, None, reason)
        version = resolution.definition.version
        by_requirement = [provider for provider in self._providers.values()
                          if requirement_id in provider.descriptor.supported_requirement_types]
        if not by_requirement:
            return ProviderSelection(requirement_id, embodiment, None, "unsupported_requirement")
        by_embodiment = [provider for provider in by_requirement
                         if embodiment in provider.descriptor.supported_embodiments]
        if not by_embodiment:
            return ProviderSelection(requirement_id, embodiment, None, "unsupported_embodiment")
        by_version = [provider for provider in by_embodiment
                      if self._supports_version(provider.descriptor, requirement_id, version)]
        if not by_version:
            return ProviderSelection(requirement_id, embodiment, None, "unsupported_requirement_version")
        candidates = [provider for provider in by_version
                      if _meets_assurance(provider.descriptor, minimum_assurance_level)]
        if not candidates:
            return ProviderSelection(requirement_id, embodiment, None, "insufficient_assurance")
        provider = sorted(candidates, key=lambda item: (-item.descriptor.priority, item.descriptor.provider_id))[0]
        return ProviderSelection(requirement_id, embodiment, provider)

    @staticmethod
    def _supports_version(descriptor: ConformanceProviderDescriptor, requirement_id: str, version: str) -> bool:
        declared = descriptor.supported_requirement_versions.get(requirement_id)
        # Existing provider descriptors predate vocabulary versions. They retain
        # safe compatibility only for the built-in 1.0 definitions.
        return version in declared if declared is not None else version == "1.0"

    def evaluate(
        self, requirement: dict[str, Any], subject: RobotState, minimum_assurance_level: str = "E2",
    ) -> tuple[ProviderSelection, ConformanceProviderResult | None]:
        selection = self.select(requirement, subject.embodiment, minimum_assurance_level)
        if selection.provider is None:
            return selection, None
        result = selection.provider.evaluate(requirement, subject)
        descriptor = selection.provider.descriptor
        error = self.validate_result(selection, requirement, subject, result, minimum_assurance_level)
        if error:
            raise ValueError(error)
        return selection, result

    def validate_result(
        self, selection: ProviderSelection, requirement: dict[str, Any], subject: RobotState,
        result: ConformanceProviderResult, minimum_assurance_level: str = "E2",
    ) -> str | None:
        """Validate a selected provider result before evidence conversion.

        Provider registration is local configuration, not a trust decision. This
        method only verifies that a result conforms to the selected descriptor.
        """
        if selection.provider is None:
            return "unresolved_provider"
        descriptor = selection.provider.descriptor
        resolution = self._vocabulary.validate(requirement)
        if not resolution.resolved:
            return resolution.reason or "unsupported_requirement"
        definition = resolution.definition
        assert definition is not None
        if result.provider_id != descriptor.provider_id:
            return "provider_result_provider_id_mismatch"
        if result.provider_version != descriptor.provider_version:
            return "provider_result_provider_version_mismatch"
        if result.requirement_id != definition.requirement_id:
            return "provider_result_requirement_id_mismatch"
        if result.requirement_version != definition.version:
            return "provider_result_requirement_version_mismatch"
        if subject.embodiment not in descriptor.supported_embodiments:
            return "provider_result_embodiment_mismatch"
        if result.assurance_level not in descriptor.supported_assurance_levels:
            return "provider_result_assurance_mismatch"
        if ASSURANCE_LEVELS.index(result.assurance_level) < ASSURANCE_LEVELS.index(minimum_assurance_level):
            return "provider_result_insufficient_assurance"
        if result.evidence_type != descriptor.evidence_type:
            return "provider_result_evidence_type_mismatch"
        if result.unit != definition.unit:
            return "provider_result_unit_mismatch"
        if type(result.passed) is not bool or not isinstance(result.metadata, dict):
            return "invalid_provider_result"
        if not isinstance(result.reasons, tuple) or not all(isinstance(reason, str) for reason in result.reasons):
            return "invalid_provider_result"
        return None
