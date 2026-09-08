from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/admission/src"))

from spp_admission import (  # noqa: E402
    ConformanceProviderDescriptor, ConformanceProviderRegistry,
    DEFAULT_REQUIREMENT_VOCABULARY, RequirementDefinition,
    RequirementVocabularyRegistry, TrustedPolicyAuthority,
    TrustedPolicyAuthorityRegistry, compute_requirement_delta,
    create_place_package, verify_place_package,
)


SPEED = {"id": "movement.max_speed", "requirement_version": "1.0", "action": "movement", "operator": "<=", "value": .8, "unit": "m/s"}
SEPARATION = {"id": "human_separation", "action": "movement", "operator": ">=", "value": 1.2, "unit": "m"}
FACE = {"id": "sensing.facial_recognition", "action": "sensing", "operator": "prohibited", "value": True}


def test_builtin_lookup_and_validation_cover_numeric_minimum_and_prohibition():
    assert DEFAULT_REQUIREMENT_VOCABULARY.resolve("movement.max_speed").definition.version == "1.0"
    assert DEFAULT_REQUIREMENT_VOCABULARY.validate(SPEED).definition.comparison == "MAX"
    assert DEFAULT_REQUIREMENT_VOCABULARY.validate(SEPARATION).definition.comparison == "MIN"
    assert DEFAULT_REQUIREMENT_VOCABULARY.validate(FACE).definition.comparison == "PROHIBITED"


def test_duplicate_incompatible_definition_and_invalid_unit_or_value_are_rejected():
    registry = RequirementVocabularyRegistry()
    definition = RequirementDefinition("x-acme.limit", "1.0", "number", "m", "MAX", "Test limit.")
    registry.register(definition)
    with pytest.raises(ValueError, match="incompatible duplicate"):
        registry.register(RequirementDefinition("x-acme.limit", "1.0", "integer", "m", "MAX", "Different."))
    with pytest.raises(ValueError, match="unit"):
        DEFAULT_REQUIREMENT_VOCABULARY.validate(dict(SPEED, unit="km/h"))
    with pytest.raises(ValueError, match="value_type"):
        DEFAULT_REQUIREMENT_VOCABULARY.validate(dict(SPEED, value=True))


def test_unknown_extension_is_unresolved_until_explicitly_registered():
    extension = {"id": "x-acme.visibility", "requirement_version": "1.0", "action": "sensing", "operator": "=", "value": True}
    assert DEFAULT_REQUIREMENT_VOCABULARY.validate(extension).reason == "unknown_requirement"
    registry = RequirementVocabularyRegistry((
        RequirementDefinition("x-acme.visibility", "1.0", "boolean", None, "EXACT", "Visibility test."),
    ))
    assert registry.validate(extension).resolved


def test_provider_requires_compatible_requirement_version():
    class Provider:
        descriptor = ConformanceProviderDescriptor(
            "provider", "1.0", frozenset({"movement.max_speed"}), frozenset({"demo"}),
            frozenset({"E2"}), "test", supported_requirement_versions={"movement.max_speed": frozenset({"1.0"})},
        )

        def evaluate(self, requirement, subject):  # pragma: no cover - selection only
            raise AssertionError

    registry = ConformanceProviderRegistry([Provider()])
    assert registry.select(SPEED, "demo").resolved
    assert registry.select(dict(SPEED, requirement_version="2.0"), "demo").reason == "incompatible_requirement_version"


def test_requirement_delta_only_compares_compatible_versions():
    profile = {"operating_profile": {"guarantees": [dict(SPEED)]}}
    compatible = {"requirements": [dict(SPEED)]}
    incompatible = {"requirements": [dict(SPEED, requirement_version="2.0")]}
    assert compute_requirement_delta(profile, compatible)[0]["classification"] == "REUSED"
    assert compute_requirement_delta(profile, incompatible)[0]["classification"] == "UNRESOLVED"


def test_place_package_accepts_known_default_and_fails_closed_for_unknown_extension():
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    requirement_set = {
        "spp_version": "0.1", "admission_version": "0.1-experimental",
        "requirement_set_id": "urn:spp:vocabulary", "place": "clinic", "space": "clinic/lobby",
        "policy_version": 1, "environment_digest": "sha256:env", "requirements": [dict(SPEED)],
    }
    authority = TrustedPolicyAuthority("authority", public, frozenset({"clinic"}), frozenset({"clinic/lobby"}))
    package = create_place_package(requirement_set, authority_id="authority", private_key=key)
    assert verify_place_package(package, TrustedPolicyAuthorityRegistry([authority])).valid
    unknown = deepcopy(package)
    unknown["requirements"]["requirements"] = [{"id": "x-acme.visibility", "requirement_version": "1.0", "action": "sensing", "operator": "=", "value": True}]
    assert verify_place_package(unknown, TrustedPolicyAuthorityRegistry([authority])).reasons == ["unknown_requirement"]
