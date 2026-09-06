from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/admission/src"))

from spp_admission import (  # noqa: E402
    EVIDENCE_BUNDLE_TYPE,
    EvidenceRecord,
    ReplayRegistry,
    SignedEvidenceRecord,
    TrustedIssuer,
    TrustedIssuerRegistry,
    admit_verified_evidence_backed,
    evidence_scope,
    sign_evidence,
    verify_signed_evidence,
)
from spp_admission.engine import (  # noqa: E402
    build_evidence,
    derive_plan,
    execute_plan,
    load_requirement_set,
)
from spp_admission.models import RobotState  # noqa: E402


NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def signed_setup():
    requirements = load_requirement_set(ROOT / "demo/admission/lobby.yaml")
    robot = RobotState(
        "robot:signed:1", "build:signed:1", "controller:signed:1",
        "demo_mobile_base", requirements["environment_digest"],
        {"movement.max_speed": 0.6},
    )
    plan = derive_plan(requirements, robot, challenge="nonce:signed-evidence")
    evidence = build_evidence(requirements, plan, robot, execute_plan(plan, robot, requirements), now=NOW)
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    )
    issuer = TrustedIssuer(
        "clinic-validator-1", public_key,
        frozenset({EVIDENCE_BUNDLE_TYPE}), frozenset({evidence_scope(requirements)}),
    )
    registry = TrustedIssuerRegistry([issuer])
    signed = sign_evidence(
        evidence, issuer_id=issuer.issuer_id, private_key=private_key,
        scope=evidence_scope(requirements),
    )
    return requirements, robot, plan, evidence, private_key, issuer, registry, signed


def admit_signed(setup, signed=None, registry=None, source_records=None):
    requirements, robot, plan, _, _, _, trusted, original = setup
    return admit_verified_evidence_backed(
        requirements, plan, signed or original, robot, registry or trusted,
        source_records=source_records, replay_registry=ReplayRegistry(), now=NOW,
    )


def test_valid_trusted_issuer_is_admitted(signed_setup):
    assert verify_signed_evidence(
        signed_setup[-1], signed_setup[-2], expected_scope=evidence_scope(signed_setup[0]),
    ).verified
    assert admit_signed(signed_setup).status == "ADMITTED"


def test_unknown_issuer_fails_closed(signed_setup):
    requirements, _, _, evidence, private_key, _, _, _ = signed_setup
    unknown = sign_evidence(evidence, issuer_id="unknown-validator", private_key=private_key,
                            scope=evidence_scope(requirements))
    profile = admit_signed(signed_setup, signed=unknown)
    assert profile.reason_codes == ["unknown_issuer"]


def test_invalid_signature_fails_closed(signed_setup):
    signed = replace(signed_setup[-1], signature="not-a-valid-ed25519-signature")
    assert admit_signed(signed_setup, signed=signed).reason_codes == ["invalid_evidence_signature"]


@pytest.mark.parametrize("mutation", ["result", "binding", "expiry"])
def test_tampering_after_signing_fails_closed(signed_setup, mutation):
    signed = signed_setup[-1]
    tampered = deepcopy(signed.evidence)
    if mutation == "result":
        tampered["test_results"][0]["passed"] = False
    elif mutation == "binding":
        tampered["binding"]["controller_fingerprint"] = "controller:tampered"
    else:
        tampered["valid_until"] = "2030-01-01T00:00:01Z"
    profile = admit_signed(signed_setup, signed=replace(signed, evidence=tampered))
    assert profile.reason_codes == ["signed_payload_digest_mismatch"]


@pytest.mark.parametrize("kind,reason", [
    ("scope", "issuer_unauthorized_scope"),
    ("type", "issuer_unauthorized_evidence_type"),
])
def test_issuer_authorization_is_enforced(signed_setup, kind, reason):
    _, _, _, _, _, issuer, _, signed = signed_setup
    restricted = TrustedIssuer(
        issuer.issuer_id, issuer.public_key,
        frozenset({"other"}) if kind == "type" else issuer.allowed_evidence_types,
        frozenset({"other::scope"}) if kind == "scope" else issuer.allowed_scopes,
    )
    assert admit_signed(signed_setup, signed=signed,
                        registry=TrustedIssuerRegistry([restricted])).reason_codes == [reason]


def test_disabled_issuer_fails_closed(signed_setup):
    _, _, _, _, _, issuer, _, signed = signed_setup
    disabled = replace(issuer, enabled=False)
    assert admit_signed(signed_setup, signed=signed,
                        registry=TrustedIssuerRegistry([disabled])).reason_codes == ["issuer_disabled"]


def test_wrong_public_key_fails_closed(signed_setup):
    _, _, _, _, _, issuer, _, signed = signed_setup
    wrong_public_key = Ed25519PrivateKey.generate().public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    )
    wrong_key_issuer = replace(issuer, public_key=wrong_public_key)
    assert admit_signed(signed_setup, signed=signed,
                        registry=TrustedIssuerRegistry([wrong_key_issuer])).reason_codes == ["invalid_evidence_signature"]


def test_ed25519_signing_is_deterministic_for_the_same_evidence(signed_setup):
    requirements, _, _, evidence, private_key, issuer, _, first = signed_setup
    second = sign_evidence(evidence, issuer_id=issuer.issuer_id, private_key=private_key,
                           scope=evidence_scope(requirements))
    assert (first.signed_payload_digest, first.signature) == (second.signed_payload_digest, second.signature)


def test_unsigned_historical_record_is_rejected(signed_setup):
    requirements, _, plan, evidence, *_ = signed_setup
    profile = admit_signed(signed_setup, source_records=[EvidenceRecord(requirements, plan, evidence)])
    assert profile.reason_codes == ["unsigned_source_evidence"]


def test_signed_historical_record_is_accepted_without_weakening_admission(signed_setup):
    requirements, _, plan, _, _, _, _, signed = signed_setup
    source = SignedEvidenceRecord(requirements, plan, signed)
    assert admit_signed(signed_setup, source_records=[source]).status == "ADMITTED"
