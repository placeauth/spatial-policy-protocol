"""Focused coverage for the experimental RFC 8785 admission-envelope profile."""
from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
import sys

import pytest
from cryptography.hazmat.primitives import serialization

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference" / "admission" / "src"))

from spp_admission.admission_envelope import sign_admission_profile  # noqa: E402
from spp_admission.jcs_admission_envelope import (  # noqa: E402
    JCS_PROFILE,
    PYTHON_JSON_PROFILE,
    JCSProfileError,
    canonicalize_jcs,
    jcs_digest,
    jcs_restriction_identifier,
    jcs_restriction_profile_identifier,
    parse_jcs_json,
    sign_jcs_admission_profile,
    verify_jcs_admission_envelope,
    verify_profiled_admission_envelope,
)
from spp_admission.trust import TrustedIssuer, TrustedIssuerRegistry  # noqa: E402


INTEROP = ROOT / "interop" / "experimental" / "admission-trust-jcs"


def _generator():
    spec = importlib.util.spec_from_file_location("jcs_vectors", INTEROP / "generate_vectors.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def setup():
    module = _generator()
    key = module._key()
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    issuer = TrustedIssuer(module.ISSUER_ID, public, frozenset({"spp:admission-envelope"}), frozenset({module.SCOPE}))
    return module, key, TrustedIssuerRegistry([issuer])


def test_jcs_vectors_are_reproducible_and_profile_comparison_is_stable():
    module = _generator()
    expected_vectors = json.dumps(module.build_vectors(), indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    assert (INTEROP / "vectors.json").read_text(encoding="utf-8") == expected_vectors
    comparison = json.loads((INTEROP / "profile-comparison.json").read_text(encoding="utf-8"))
    assert comparison["expected"] == {"canonical_bytes_equal": False, "digest_equal": False, "signature_equal": False}


@pytest.mark.parametrize("status", ["ADMITTED", "DEGRADED"])
def test_jcs_valid_envelopes_verify(setup, status):
    module, key, trusted = setup
    envelope = sign_jcs_admission_profile(module._profile(status), issuer_id=module.ISSUER_ID, private_key=key, issued_at=module.NOW, expires_at=module.NOW + timedelta(minutes=5))
    result = verify_jcs_admission_envelope(envelope, trusted, expected_subject_id="robot:jcs:1", expected_place="clinic", expected_space="clinic/lobby", now=module.NOW)
    assert result.verified


def test_jcs_profile_identifier_is_cryptographically_covered(setup):
    module, key, trusted = setup
    envelope = sign_jcs_admission_profile(module._profile(), issuer_id=module.ISSUER_ID, private_key=key, issued_at=module.NOW, expires_at=module.NOW + timedelta(minutes=5))
    changed = replace(envelope, canonicalization_profile=PYTHON_JSON_PROFILE)
    result = verify_jcs_admission_envelope(changed, trusted, expected_subject_id="robot:jcs:1", expected_place="clinic", expected_space="clinic/lobby", now=module.NOW)
    assert result.reason == "invalid_envelope_signature"


def test_unknown_profile_and_cross_profile_dispatch_fail_closed(setup):
    module, key, trusted = setup
    jcs = sign_jcs_admission_profile(module._profile(), issuer_id=module.ISSUER_ID, private_key=key, issued_at=module.NOW, expires_at=module.NOW + timedelta(minutes=5))
    python = sign_admission_profile(module._profile(), issuer_id=module.ISSUER_ID, private_key=key, issued_at=module.NOW, expires_at=module.NOW + timedelta(minutes=5))
    kwargs = {"expected_subject_id": "robot:jcs:1", "expected_place": "clinic", "expected_space": "clinic/lobby", "now": module.NOW}
    assert verify_profiled_admission_envelope(jcs, "unknown-profile", trusted, **kwargs).reason == "unsupported_canonicalization_profile"
    assert verify_profiled_admission_envelope(python, JCS_PROFILE, trusted, **kwargs).reason == "canonicalization_profile_mismatch"
    assert verify_profiled_admission_envelope(jcs, PYTHON_JSON_PROFILE, trusted, **kwargs).reason == "canonicalization_profile_mismatch"


def test_unicode_numbers_and_negative_zero_are_profile_safe_or_rejected():
    assert canonicalize_jcs({"label": "café 🚀"}) == '{"label":"café 🚀"}'.encode("utf-8")
    assert canonicalize_jcs({"value": 1e-7}) == b'{"value":1e-7}'
    with pytest.raises(JCSProfileError, match="safe range"):
        canonicalize_jcs({"value": 2**53})
    with pytest.raises(JCSProfileError, match="non-finite"):
        canonicalize_jcs({"value": float("nan")})
    with pytest.raises(JCSProfileError, match="negative zero"):
        canonicalize_jcs({"value": -0.0})
    with pytest.raises(JCSProfileError, match="safe range"):
        canonicalize_jcs({"value": 1e20})


@pytest.mark.parametrize(
    ("source", "accepted"),
    [
        ('{"value": -0}', False),
        ('{"value": -0.0}', False),
        ('{"value": 0}', True),
        ('{"value": 0.0}', True),
        ('{"value": 9007199254740991}', True),
        ('{"value": 9007199254740992}', False),
        ('{"value": -9007199254740991}', True),
        ('{"value": -9007199254740992}', False),
        ('{"value": 1e20}', False),
        ('{"value": 1e3}', True),
        ('{"value": 1.25e-1}', True),
    ],
)
def test_raw_jcs_numeric_contract_is_language_neutral(source, accepted):
    if accepted:
        assert canonicalize_jcs(parse_jcs_json(source))
    else:
        with pytest.raises(JCSProfileError):
            parse_jcs_json(source)


def test_timestamp_form_and_raw_json_parsing_fail_closed(setup):
    module, key, trusted = setup
    with pytest.raises(JCSProfileError, match="fractional seconds"):
        sign_jcs_admission_profile(module._profile(), issuer_id=module.ISSUER_ID, private_key=key, issued_at=module.NOW.replace(microsecond=1), expires_at=module.NOW + timedelta(minutes=5))
    envelope = sign_jcs_admission_profile(module._profile(), issuer_id=module.ISSUER_ID, private_key=key, issued_at=module.NOW, expires_at=module.NOW + timedelta(minutes=5))
    result = verify_jcs_admission_envelope(replace(envelope, issued_at="2030-01-01T07:00:00-05:00"), trusted, expected_subject_id="robot:jcs:1", expected_place="clinic", expected_space="clinic/lobby", now=module.NOW)
    assert result.reason == "jcs_profile_value_invalid"
    with pytest.raises(JCSProfileError, match="duplicate JSON key"):
        parse_jcs_json('{"a":1,"\\u0061":2}')
    with pytest.raises(JCSProfileError, match="non-finite"):
        parse_jcs_json('{"value":NaN}')
    with pytest.raises(JCSProfileError, match="malformed Unicode"):
        parse_jcs_json('{"value":"\\ud800"}')


def test_optional_values_and_restriction_bindings_remain_deterministic(setup):
    module, _, _ = setup
    assert len({jcs_digest({}), jcs_digest({"value": None}), jcs_digest({"value": ""}), jcs_digest({"value": []})}) == 4
    first = module._profile("DEGRADED")
    second = deepcopy(first)
    second.restrictions = list(reversed(first.restrictions)) + [first.restrictions[0]]
    second.operating_profile["restrictions"] = list(reversed(first.operating_profile["restrictions"]))
    assert jcs_restriction_profile_identifier(first) == jcs_restriction_profile_identifier(second)
    assert jcs_restriction_identifier(module.RECORDING) == "sha256:168846719908c226f40ac93b8917f6f3d6f94a16ba348ef3b267958f4a7e36e0"
    changed_ordered_content = deepcopy(first)
    changed_ordered_content.operating_profile["guarantees"] = [{"id": "other", "value": 1}, *first.operating_profile["guarantees"]]
    assert jcs_restriction_profile_identifier(first) != jcs_restriction_profile_identifier(changed_ordered_content)
