from __future__ import annotations

import base64
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys
import os
import subprocess
import tempfile

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/admission/src"))

from spp_admission import (  # noqa: E402
    TrustedPolicyAuthority, TrustedPolicyAuthorityRegistry, create_place_package,
    load_place_package, serialize_place_package, verify_place_package,
)
from spp_admission.engine import load_requirement_set  # noqa: E402
from spp_admission.place_package import _signature_payload, _unsigned_content, digest  # noqa: E402
from spp_admission.vocabulary import RequirementDefinition, RequirementVocabularyRegistry  # noqa: E402


@pytest.fixture
def package_setup():
    requirements = load_requirement_set(ROOT / "demo/admission/patient-wing.yaml")
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    )
    authority = TrustedPolicyAuthority(
        "hospital-policy-authority", public_key, frozenset({"clinic"}),
        frozenset({"clinic/patient-wing"}),
    )
    package = create_place_package(
        requirements, authority_id=authority.authority_id, private_key=private_key,
        metadata={"name": "Clinic Patient Wing"},
    )
    return requirements, authority, package


def registry(authority):
    return TrustedPolicyAuthorityRegistry([authority])


def test_valid_package_serializes_deterministically_and_verifies(package_setup):
    _, authority, package = package_setup
    first = serialize_place_package(package)
    assert first == serialize_place_package(package)
    with tempfile.TemporaryDirectory(dir=ROOT) as directory:
        path = Path(directory) / "package.json"
        path.write_text(first, encoding="utf-8")
        loaded = load_place_package(path)
        result = verify_place_package(loaded, registry(authority))
    assert result.valid and result.authority_id == authority.authority_id


@pytest.mark.parametrize("mutation", [
    lambda package: package["requirements"]["requirements"][0].update(value=1.2),
    lambda package: package.update(place_id="other-clinic/wing"),
    lambda package: package.update(policy_version=99),
])
def test_semantic_tampering_fails_signature_verification(package_setup, mutation):
    _, authority, package = package_setup
    altered = deepcopy(package)
    mutation(altered)
    result = verify_place_package(altered, registry(authority))
    assert result.reasons in (
        ["place_package_signature_invalid"], ["invalid_place_package"],
        ["requirement_value_type_mismatch"],
    )


def test_unknown_and_disabled_authority_are_rejected(package_setup):
    _, authority, package = package_setup
    assert verify_place_package(package, TrustedPolicyAuthorityRegistry()).reasons == ["unknown_policy_authority"]
    assert verify_place_package(package, registry(replace(authority, enabled=False))).reasons == ["policy_authority_disabled"]


def test_authority_place_and_scope_authorization_are_rejected(package_setup):
    _, authority, package = package_setup
    no_place = replace(authority, allowed_places=frozenset({"other"}))
    no_scope = replace(authority, allowed_scopes=frozenset({"clinic/other"}))
    assert verify_place_package(package, registry(no_place)).reasons == ["policy_authority_unauthorized"]
    assert verify_place_package(package, registry(no_scope)).reasons == ["policy_authority_unauthorized"]


def test_version_and_malformed_packages_are_rejected(package_setup):
    _, authority, package = package_setup
    unsupported = deepcopy(package)
    unsupported["place_package_version"] = "99"
    assert verify_place_package(unsupported, registry(authority)).reasons == ["unsupported_place_package_version"]
    assert verify_place_package({"broken": True}, registry(authority)).reasons == ["invalid_place_package"]


def test_canonical_example_loads_and_verifies_in_a_fresh_process_shape():
    package = load_place_package(ROOT / "examples/place-packages/clinic-patient-wing.json")
    key = base64.b64decode("4ShcmAmXdpkh5uAlCQ9ZvSQBAleOpxYXYh7zzttH4Ko=", validate=True)
    authority = TrustedPolicyAuthority(
        "hospital-policy-authority", key, frozenset({"clinic"}),
        frozenset({"clinic/patient-wing"}),
    )
    assert verify_place_package(package, registry(authority)).valid


def test_example_verifies_from_disk_in_a_fresh_process():
    environment = dict(os.environ, PYTHONPATH=str(ROOT / "reference/admission/src"))
    command = (
        "import base64; from spp_admission import TrustedPolicyAuthority, TrustedPolicyAuthorityRegistry, "
        "load_place_package, verify_place_package; "
        "p=load_place_package(r'examples/place-packages/clinic-patient-wing.json'); "
        "a=TrustedPolicyAuthority('hospital-policy-authority',base64.b64decode('4ShcmAmXdpkh5uAlCQ9ZvSQBAleOpxYXYh7zzttH4Ko='),"
        "frozenset({'clinic'}),frozenset({'clinic/patient-wing'})); "
        "assert verify_place_package(p, TrustedPolicyAuthorityRegistry([a])).valid"
    )
    subprocess.run([sys.executable, "-c", command], cwd=ROOT, env=environment, check=True)


def _resign(package, private_key):
    package["package_digest"] = digest(_unsigned_content(package))
    package["signature"] = base64.b64encode(private_key.sign(_signature_payload(package))).decode("ascii")


def test_new_packages_emit_sorted_explicit_versioned_requirements(package_setup):
    requirements, authority, _ = package_setup
    private_key = Ed25519PrivateKey.generate()
    package = create_place_package(requirements, authority_id=authority.authority_id, private_key=private_key)
    items = package["requirements"]["requirements"]
    assert [(item["id"], item["requirement_version"]) for item in items] == sorted(
        (item["id"], item["requirement_version"]) for item in items
    )
    assert all("requirement_version" in item for item in items)
    assert next(item for item in items if item["id"] == "movement.max_speed")["unit"] == "m/s"


def test_legacy_known_builtin_without_version_is_accepted_deterministically():
    requirements = load_requirement_set(ROOT / "demo/admission/patient-wing.yaml")
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    authority = TrustedPolicyAuthority("authority", public_key, frozenset({"clinic"}), frozenset({"clinic/patient-wing"}))
    package = create_place_package(requirements, authority_id="authority", private_key=private_key)
    for requirement in package["requirements"]["requirements"]:
        requirement.pop("requirement_version")
    _resign(package, private_key)
    assert verify_place_package(package, registry(authority)).valid


def test_unknown_extension_and_invalid_extension_namespace_fail_closed(package_setup):
    _, authority, package = package_setup
    unknown = deepcopy(package)
    unknown["requirements"]["requirements"][0].update(id="x-example.foo", requirement_version="1.0")
    assert verify_place_package(unknown, registry(authority)).reasons == ["unknown_requirement"]
    malformed = deepcopy(package)
    malformed["requirements"]["requirements"][0].update(id="example.foo", requirement_version="1.0")
    assert verify_place_package(malformed, registry(authority)).reasons == ["invalid_extension_namespace"]


def test_registered_extension_and_strict_requirement_fields_are_supported(package_setup):
    _, authority, package = package_setup
    vocabulary = RequirementVocabularyRegistry((
        RequirementDefinition("x-example.foo", "1.0", "boolean", None, "EXACT", "Extension."),
    ))
    extension_requirements = deepcopy(package["requirements"])
    extension_requirements["requirements"] = [{
        "id": "x-example.foo", "requirement_version": "1.0", "action": "sensing",
        "operator": "=", "value": True,
    }]
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    extension_authority = TrustedPolicyAuthority("extension-authority", public_key, frozenset({"clinic"}), frozenset({"clinic/patient-wing"}))
    extension = create_place_package(extension_requirements, authority_id="extension-authority", private_key=private_key, vocabulary=vocabulary)
    assert verify_place_package(extension, registry(extension_authority), vocabulary).valid
    mismatched_unit = deepcopy(package)
    speed = next(item for item in mismatched_unit["requirements"]["requirements"] if item["id"] == "movement.max_speed")
    speed["unit"] = "km/h"
    assert verify_place_package(mismatched_unit, registry(authority)).reasons == ["requirement_unit_mismatch"]
    mismatched_type = deepcopy(package)
    speed = next(item for item in mismatched_type["requirements"]["requirements"] if item["id"] == "movement.max_speed")
    speed["value"] = True
    assert verify_place_package(mismatched_type, registry(authority)).reasons == ["requirement_value_type_mismatch"]


def test_version_and_unit_tampering_are_invalid_and_creation_is_order_deterministic(package_setup):
    requirements, authority, package = package_setup
    version_tampered = deepcopy(package)
    version_tampered["requirements"]["requirements"][0]["requirement_version"] = "2.0"
    assert digest(_unsigned_content(version_tampered)) != version_tampered["package_digest"]
    assert verify_place_package(version_tampered, registry(authority)).valid is False
    unit_tampered = deepcopy(package)
    speed = next(item for item in unit_tampered["requirements"]["requirements"] if item["id"] == "movement.max_speed")
    speed["unit"] = "km/h"
    assert digest(_unsigned_content(unit_tampered)) != unit_tampered["package_digest"]
    assert verify_place_package(unit_tampered, registry(authority)).valid is False
    private_key = Ed25519PrivateKey.generate()
    reversed_requirements = deepcopy(requirements)
    reversed_requirements["requirements"].reverse()
    first = create_place_package(requirements, authority_id=authority.authority_id, private_key=private_key)
    second = create_place_package(reversed_requirements, authority_id=authority.authority_id, private_key=private_key)
    assert first["package_digest"] == second["package_digest"]
