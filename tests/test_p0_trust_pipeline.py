"""Focused integration coverage for the experimental P0 trust pipeline."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference" / "admission" / "src"))

from spp_admission import (  # noqa: E402
    ADMISSION_ENVELOPE_TYPE,
    CurrentEvaluationContext,
    EvidenceRevocationRegistry,
    ProfileRevocationRegistry,
    ReplayRegistry,
    TrustedIssuer,
    TrustedIssuerRegistry,
    acknowledge_restriction,
    assess_admission_reliance,
    admit,
    build_evidence,
    derive_plan,
    execute_plan,
    load_requirement_set,
    map_restriction_to_handler,
    sign_admission_profile,
)
from spp_admission.models import RobotState  # noqa: E402


NOW = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)
RECORDING = "recording_disabled@restricted_zone"
SPEED = "movement.max_speed<=0.5@corridor"


def _public_bytes(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


@pytest.fixture
def issued():
    requirements = load_requirement_set(ROOT / "demo" / "admission" / "lobby.yaml")
    subject = RobotState(
        "robot:p0", "build:p0", "controller:p0", "demo_mobile_base",
        requirements["environment_digest"], {"movement.max_speed": 0.6},
    )
    plan = derive_plan(requirements, subject, challenge="nonce:p0-trust-pipeline")
    evidence = build_evidence(requirements, plan, subject, execute_plan(plan, subject, requirements), now=NOW)
    profile = admit(requirements, plan, evidence, subject, ReplayRegistry(), now=NOW)
    key = Ed25519PrivateKey.generate()
    issuer = TrustedIssuer(
        "clinic-admission-service", _public_bytes(key),
        frozenset({ADMISSION_ENVELOPE_TYPE}),
        frozenset({f"{requirements['place']}::{requirements['space']}"}),
    )
    return requirements, subject, evidence, profile, key, TrustedIssuerRegistry([issuer]), issuer


def _envelope(issued, profile=None, *, expires_at=NOW + timedelta(minutes=5)):
    requirements, _, _, original, key, _, issuer = issued
    return sign_admission_profile(
        profile or original, issuer_id=issuer.issuer_id, private_key=key,
        issued_at=NOW, expires_at=expires_at,
    )


def _context(issued, **changes):
    requirements, subject, evidence, *_ = issued
    return CurrentEvaluationContext(
        changes.get("subject", subject),
        changes.get("requirements", requirements),
        changes.get("evidence", evidence),
    )


def _degraded(profile):
    return replace(
        profile, status="DEGRADED", restrictions=[RECORDING, SPEED],
        operating_profile={**profile.operating_profile, "restrictions": [SPEED, RECORDING]},
    )


def _acknowledgements(profile):
    return [
        acknowledge_restriction(profile, RECORDING, "camera_suppression", "clinic-adapter"),
        acknowledge_restriction(profile, SPEED, "speed_limiter", "clinic-adapter"),
    ]


def _mappings():
    return [
        map_restriction_to_handler(RECORDING, "camera_suppression"),
        map_restriction_to_handler(SPEED, "speed_limiter"),
    ]


def _assess(issued, envelope, *, context=None, acknowledgements=None, mappings=None, **kwargs):
    return assess_admission_reliance(
        envelope, context or _context(issued), issued[5], now=NOW,
        acknowledgements=acknowledgements, enforcement_mappings=mappings,
        **kwargs,
    )


def test_admitted_reliance_requires_valid_envelope_and_valid_lifecycle(issued):
    result = _assess(issued, _envelope(issued))
    assert (result.outcome, result.may_rely, result.profile_status) == ("RELIABLE_ADMITTED", True, "ADMITTED")
    assert result.acknowledgement is None
    assert result.lifecycle.status == "VALID"


def test_degraded_reliance_retains_exact_restrictions_after_full_acknowledgement(issued):
    profile = _degraded(issued[3])
    result = _assess(issued, _envelope(issued, profile), acknowledgements=_acknowledgements(profile), mappings=_mappings())
    assert (result.outcome, result.may_rely) == ("RELIABLE_DEGRADED", True)
    assert result.restrictions == (SPEED, RECORDING)
    assert result.acknowledgement.outcome == "ACKNOWLEDGED"


@pytest.mark.parametrize("kind,reason", [
    ("unknown", "unknown_issuer"),
    ("wrong_key", "invalid_envelope_signature"),
    ("expired", "envelope_expired"),
    ("tampered_profile", "signed_payload_digest_mismatch"),
])
def test_envelope_failures_block_before_lifecycle(issued, kind, reason):
    envelope = _envelope(issued)
    registry = issued[5]
    verification_time = NOW
    if kind == "unknown":
        registry = TrustedIssuerRegistry()
    elif kind == "wrong_key":
        issuer = replace(issued[6], public_key=_public_bytes(Ed25519PrivateKey.generate()))
        registry = TrustedIssuerRegistry([issuer])
    elif kind == "expired":
        envelope = _envelope(issued, expires_at=NOW + timedelta(seconds=1))
        verification_time = NOW + timedelta(seconds=2)
    else:
        altered = deepcopy(envelope.profile)
        altered.operating_profile["movement.max_speed"] = 0.1
        envelope = replace(envelope, profile=altered)
    result = assess_admission_reliance(envelope, _context(issued), registry, now=verification_time)
    assert (result.outcome, result.blocking_stage, result.reasons) == ("BLOCKED", "envelope", (reason,))
    assert result.lifecycle is None


def test_subject_and_place_context_mismatches_block_at_envelope_boundary(issued):
    different_subject = replace(issued[1], actor_id="robot:other")
    result = _assess(issued, _envelope(issued), context=_context(issued, subject=different_subject))
    assert result.blocking_stage == "envelope" and result.reasons == ("envelope_subject_mismatch",)
    changed_requirements = deepcopy(issued[0]); changed_requirements["space"] = "clinic/other"
    result = _assess(issued, _envelope(issued), context=_context(issued, requirements=changed_requirements))
    assert result.blocking_stage == "envelope" and result.reasons == ("envelope_place_mismatch",)


@pytest.mark.parametrize("change,expected", [
    ("capability", "profile_capability_changed"),
    ("evidence_expired", "profile_evidence_expired"),
    ("evidence_revoked", "profile_evidence_revoked"),
    ("profile_revoked", "envelope_revoked"),
])
def test_material_lifecycle_changes_block_reliance(issued, change, expected):
    kwargs = {}
    context = _context(issued)
    if change == "capability":
        context = _context(issued, subject=replace(issued[1], capabilities={"movement.max_speed": 0.7}))
    elif change == "evidence_expired":
        kwargs["now"] = NOW + timedelta(minutes=16)
    elif change == "evidence_revoked":
        registry = EvidenceRevocationRegistry(); registry.revoke(issued[2])
        kwargs["evidence_revocations"] = registry
    else:
        registry = ProfileRevocationRegistry(); registry.revoke(issued[3])
        kwargs["profile_revocations"] = registry
    if "now" in kwargs:
        result = assess_admission_reliance(
            _envelope(issued, expires_at=NOW + timedelta(minutes=30)), context,
            issued[5], **kwargs,
        )
    else:
        result = _assess(issued, _envelope(issued), context=context, **kwargs)
    assert result.outcome == "BLOCKED"
    assert expected in result.reasons
    assert result.blocking_stage in {"envelope", "lifecycle"}


def test_denied_profile_never_becomes_reliable(issued):
    profile = replace(issued[3], status="DENIED", restrictions=[], operating_profile={})
    result = _assess(issued, _envelope(issued, profile), acknowledgements=[], mappings=[])
    assert (result.outcome, result.may_rely, result.blocking_stage, result.reasons) == (
        "BLOCKED", False, "admission_status", ("profile_denied",),
    )


@pytest.mark.parametrize("kind,reason", [
    ("missing", "restriction_acknowledgement_missing"),
    ("unsupported", "restriction_unsupported"),
    ("wrong_profile", "acknowledgement_profile_mismatch"),
    ("altered", "acknowledgement_restriction_not_required"),
    ("handler_mismatch", "enforcement_handler_mismatch"),
])
def test_degraded_acknowledgement_failures_block_after_valid_envelope_and_lifecycle(issued, kind, reason):
    profile = _degraded(issued[3])
    acknowledgements, mappings = _acknowledgements(profile), _mappings()
    if kind == "missing":
        acknowledgements = acknowledgements[:1]
    elif kind == "unsupported":
        mappings = mappings[:1]
    elif kind == "wrong_profile":
        other = _degraded(replace(issued[3], evidence_digest="sha256:other"))
        acknowledgements = _acknowledgements(other)
    elif kind == "altered":
        acknowledgements[1] = acknowledge_restriction(profile, "movement.max_speed<=0.5", "speed_limiter", "clinic-adapter")
    else:
        acknowledgements[1] = acknowledge_restriction(profile, SPEED, "other-handler", "clinic-adapter")
    result = _assess(issued, _envelope(issued, profile), acknowledgements=acknowledgements, mappings=mappings)
    assert result.outcome == "BLOCKED"
    assert result.blocking_stage == "restriction_acknowledgement"
    assert reason in result.reasons
    assert result.envelope.verified and result.lifecycle.status == "VALID"


def test_profile_tampering_after_signing_cannot_reach_acknowledgement(issued):
    profile = _degraded(issued[3])
    envelope = _envelope(issued, profile)
    changed = deepcopy(envelope.profile)
    changed.restrictions[1] = "movement.max_speed<=0.2@corridor"
    result = _assess(issued, replace(envelope, profile=changed), acknowledgements=_acknowledgements(profile), mappings=_mappings())
    assert result.blocking_stage == "envelope"
    assert result.reasons == ("signed_payload_digest_mismatch",)


def test_legacy_unenveloped_profile_has_no_reliance_path(issued):
    result = assess_admission_reliance(issued[3], _context(issued), issued[5], now=NOW)
    assert (result.outcome, result.may_rely, result.blocking_stage) == ("BLOCKED", False, "envelope")
    assert result.reasons == ("malformed_envelope",)


def test_missing_or_malformed_current_context_fails_closed(issued):
    result = assess_admission_reliance(_envelope(issued), None, issued[5], now=NOW)
    assert (result.blocking_stage, result.reasons) == ("lifecycle", ("current_context_missing",))
    requirements = deepcopy(issued[0]); requirements.pop("space")
    result = _assess(issued, _envelope(issued), context=_context(issued, requirements=requirements))
    assert (result.blocking_stage, result.reasons) == ("envelope", ("envelope_context_unresolvable",))


def test_component_outcomes_and_profile_are_not_mutated(issued):
    profile = _degraded(issued[3])
    before = (profile.status, list(profile.restrictions), deepcopy(profile.operating_profile))
    result = _assess(issued, _envelope(issued, profile), acknowledgements=_acknowledgements(profile), mappings=_mappings())
    assert result.may_rely
    assert (profile.status, profile.restrictions, profile.operating_profile) == before
    assert result.envelope.verified and result.lifecycle.may_rely_without_additional_work
