"""Local, versioned requirement vocabulary for the SPP reference layer."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


VERSION_PATTERN = r"^[0-9]+\.[0-9]+$"
VALUE_TYPES = frozenset({"number", "integer", "boolean"})
COMPARISONS = frozenset({"MAX", "MIN", "EXACT", "PROHIBITED"})


@dataclass(frozen=True)
class RequirementDefinition:
    requirement_id: str
    version: str
    value_type: str
    unit: str | None
    comparison: str
    description: str


@dataclass(frozen=True)
class RequirementResolution:
    definition: RequirementDefinition | None
    status: str
    reason: str | None = None

    @property
    def resolved(self) -> bool:
        return self.definition is not None


def _value_matches(value: Any, value_type: str) -> bool:
    if value_type == "number":
        return type(value) in (int, float)
    if value_type == "integer":
        return type(value) is int
    if value_type == "boolean":
        return type(value) is bool
    return False


class RequirementVocabularyRegistry:
    """Explicit local definitions; no remote registry or discovery behavior."""

    def __init__(self, definitions: Iterable[RequirementDefinition] = ()) -> None:
        self._definitions: dict[tuple[str, str], RequirementDefinition] = {}
        for definition in definitions:
            self.register(definition)

    def register(self, definition: RequirementDefinition) -> None:
        if (not definition.requirement_id or not definition.version
                or definition.value_type not in VALUE_TYPES
                or definition.comparison not in COMPARISONS):
            raise ValueError("invalid requirement definition")
        key = (definition.requirement_id, definition.version)
        existing = self._definitions.get(key)
        if existing is not None:
            if existing != definition:
                raise ValueError(f"incompatible duplicate requirement definition: {definition.requirement_id}@{definition.version}")
            raise ValueError(f"requirement definition already registered: {definition.requirement_id}@{definition.version}")
        self._definitions[key] = definition

    def resolve(self, requirement_id: str, version: str | None = None) -> RequirementResolution:
        versions = [definition for (identifier, _), definition in self._definitions.items() if identifier == requirement_id]
        if not versions:
            return RequirementResolution(None, "UNKNOWN", "unknown_requirement")
        if version is None:
            if len(versions) == 1:
                return RequirementResolution(versions[0], "RESOLVED")
            return RequirementResolution(None, "INCOMPATIBLE", "requirement_version_required")
        definition = self._definitions.get((requirement_id, version))
        if definition is None:
            return RequirementResolution(None, "INCOMPATIBLE", "incompatible_requirement_version")
        return RequirementResolution(definition, "RESOLVED")

    def validate(self, requirement: dict[str, Any]) -> RequirementResolution:
        resolution = self.resolve(str(requirement.get("id", "")), requirement.get("requirement_version"))
        if not resolution.resolved:
            return resolution
        # Existing SPP 0.1 fixtures predate explicit definition versions and
        # use the conformance layer for generic comparison probes. They resolve
        # safely to the sole built-in 1.0 definition, while strict vocabulary
        # validation begins when a requirement opts into requirement_version.
        if "requirement_version" not in requirement:
            return resolution
        definition = resolution.definition
        assert definition is not None
        if not _value_matches(requirement.get("value"), definition.value_type):
            raise ValueError("requirement_value_type_mismatch")
        if requirement.get("operator") != {
            "MAX": "<=", "MIN": ">=", "EXACT": "=", "PROHIBITED": "prohibited",
        }[definition.comparison]:
            raise ValueError("requirement_comparison_mismatch")
        # Omitted legacy units mean the documented canonical unit. A supplied
        # unit must match exactly because this reference layer has no converter.
        if definition.unit is not None and requirement.get("unit") not in (None, definition.unit):
            raise ValueError("requirement_unit_mismatch")
        return resolution

    def definitions(self) -> list[RequirementDefinition]:
        return sorted(self._definitions.values(), key=lambda item: (item.requirement_id, item.version))


BUILTIN_REQUIREMENTS = (
    RequirementDefinition("movement.max_speed", "1.0", "number", "m/s", "MAX",
                          "Maximum permitted translational speed."),
    RequirementDefinition("human_separation", "1.0", "number", "m", "MIN",
                          "Minimum separation from a human."),
    RequirementDefinition("sensing.facial_recognition", "1.0", "boolean", None, "PROHIBITED",
                          "Facial recognition must be disabled."),
    RequirementDefinition("data.video_retention", "1.0", "integer", "seconds", "EXACT",
                          "Permitted video-retention duration."),
)

DEFAULT_REQUIREMENT_VOCABULARY = RequirementVocabularyRegistry(BUILTIN_REQUIREMENTS)


def requirement_version(requirement: dict[str, Any],
                        registry: RequirementVocabularyRegistry = DEFAULT_REQUIREMENT_VOCABULARY) -> str | None:
    """Return an explicit version or the safe built-in 1.0 compatibility default."""
    resolution = registry.resolve(str(requirement.get("id", "")), requirement.get("requirement_version"))
    return resolution.definition.version if resolution.resolved else None


def requirements_compatible(previous: dict[str, Any], current: dict[str, Any],
                            registry: RequirementVocabularyRegistry = DEFAULT_REQUIREMENT_VOCABULARY) -> bool:
    if previous.get("id") != current.get("id"):
        return False
    old = registry.resolve(str(previous.get("id", "")), previous.get("requirement_version"))
    new = registry.resolve(str(current.get("id", "")), current.get("requirement_version"))
    return old.resolved and new.resolved and old.definition == new.definition
