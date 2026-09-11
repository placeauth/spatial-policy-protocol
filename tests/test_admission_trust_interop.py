"""Python-side reproducibility checks for experimental interop vectors."""
from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import timedelta
from pathlib import Path
import sys

import pytest
from cryptography.hazmat.primitives import serialization

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference" / "admission" / "src"))

from spp_admission.admission_envelope import sign_admission_profile, verify_signed_admission_envelope  # noqa: E402
from spp_admission.engine import _canonical, digest  # noqa: E402
from spp_admission.restriction_acknowledgement import restriction_identifier, restriction_profile_identifier  # noqa: E402
from spp_admission.trust import TrustedIssuer, TrustedIssuerRegistry  # noqa: E402


INTEROP = ROOT / "interop" / "experimental" / "admission-trust"
VECTORS = INTEROP / "vectors.json"


def _generator_module():
    spec = importlib.util.spec_from_file_location("admission_trust_vectors", INTEROP / "generate_vectors.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _vectors():
    return json.loads(VECTORS.read_text(encoding="utf-8"))


def test_checked_vectors_are_deterministically_regenerated():
    generated = _generator_module().build_vectors()
    assert json.dumps(generated, indent=2, ensure_ascii=True, sort_keys=True) + "\n" == VECTORS.read_text(encoding="utf-8")


def test_python_canonical_json_golden_unicode_and_key_order():
    value = {"z": "café 🚀", "a": [True, None, "cafe\u0301"]}
    assert _canonical(value) == '{"a":[true,null,"cafe\\u0301"],"z":"caf\\u00e9 \\ud83d\\ude80"}'
    assert digest(value) == "sha256:f05ceb6524eccbd8a1be2b28831e89af2e66cf036c381c5fe4a8b061579d7760"


def test_optional_null_empty_and_unicode_variants_are_distinct():
    forms = [{}, {"value": None}, {"value": ""}, {"value": []}]
    assert len({digest(item) for item in forms}) == len(forms)
    assert digest({"value": "café"}) != digest({"value": "cafe\u0301"})


def test_number_edge_behavior_is_explicitly_reference_only():
    assert _canonical({"negative_zero": -0.0}) == '{"negative_zero":-0.0}'
    assert _canonical({"nonfinite": float("nan")}) == '{"nonfinite":NaN}'
    module = _generator_module()
    profile = module._profile()
    profile.operating_profile["nonfinite"] = float("inf")
    with pytest.raises(ValueError, match="non-finite JSON number"):
        sign_admission_profile(
            profile, issuer_id=module.ISSUER_ID, private_key=module._key(),
            issued_at=module.NOW, expires_at=module.NOW + timedelta(minutes=5),
        )


def test_admission_profile_digest_and_signature_match_valid_vector():
    module = _generator_module()
    vector = next(item for item in _vectors()["vectors"] if item["id"] == "admitted_valid")
    envelope = sign_admission_profile(
        module._profile(), issuer_id=module.ISSUER_ID, private_key=module._key(),
        issued_at=module.NOW, expires_at=module.NOW + timedelta(minutes=5),
    )
    assert envelope.signed_payload_digest == vector["computed_profile_digest"]
    assert envelope.signature == vector["envelope"]["signature"]
    assert _canonical(asdict(envelope.profile)) == vector["canonical_profile_json"]


def test_restriction_digest_and_profile_binding_are_stable_for_set_like_restrictions():
    module = _generator_module()
    vector = next(item for item in _vectors()["vectors"] if item["kind"] == "restriction_acknowledgement")
    first = module._profile("DEGRADED")
    second = deepcopy(first)
    second.restrictions = list(reversed(first.restrictions)) + [first.restrictions[0]]
    second.operating_profile["restrictions"] = list(reversed(first.operating_profile["restrictions"]))
    assert restriction_profile_identifier(first) == restriction_profile_identifier(second) == vector["profile_binding"]
    for restriction, expected in vector["restriction_digests"].items():
        assert restriction_identifier(restriction) == expected


def test_non_restriction_order_remains_semantic_in_profile_binding():
    module = _generator_module()
    first = module._profile("DEGRADED")
    second = deepcopy(first)
    second.operating_profile["guarantees"] = [
        {"id": "other", "value": 1},
        *second.operating_profile["guarantees"],
    ]
    assert restriction_profile_identifier(first) != restriction_profile_identifier(second)


def test_timestamp_textual_variants_are_not_interchangeable_after_signing():
    module = _generator_module()
    envelope = sign_admission_profile(
        module._profile(), issuer_id=module.ISSUER_ID, private_key=module._key(),
        issued_at=module.NOW, expires_at=module.NOW + timedelta(minutes=5),
    )
    issuer = TrustedIssuer(
        module.ISSUER_ID,
        module._key().public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw),
        frozenset({"spp:admission-envelope"}), frozenset({module.SCOPE}),
    )
    variant = replace(envelope, issued_at="2030-01-01T07:00:00-05:00")
    result = verify_signed_admission_envelope(
        variant, TrustedIssuerRegistry([issuer]), expected_subject_id="robot:interop:1",
        expected_place="clinic", expected_space="clinic/lobby", now=module.NOW,
    )
    assert result.reason == "invalid_envelope_signature"
