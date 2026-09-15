"""Local, non-normative HTTP wrapper around existing SPP reference admission.

This deliberately keeps its fixtures and adapter-side restriction check inside
``sandbox``.  It does not extend the SPP 0.1 wire contract.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI, HTTPException

from spp_admission import (
    EVIDENCE_BUNDLE_TYPE,
    ReplayRegistry,
    TrustedIssuer,
    TrustedIssuerRegistry,
    TrustedPolicyAuthority,
    TrustedPolicyAuthorityRegistry,
    admit_verified_policy_evidence_backed,
    assess_profile_lifecycle,
    evidence_scope,
    policy_scope,
    profile_identifier,
    sign_evidence,
    sign_place_requirements,
    verify_signed_evidence,
    verify_signed_place_requirements,
)
from spp_admission.engine import build_evidence, derive_plan, digest, execute_plan, load_requirement_set
from spp_admission.models import RobotState


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "sandbox" / "examples"
NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)
SCENARIOS = ("admitted", "degraded", "denied", "expired", "tampered", "missing-restriction-ack", "changed-subject")

app = FastAPI(
    title="SPP Reference Sandbox",
    version="0.1-sandbox",
    description="Experimental, non-normative local demonstration of existing SPP reference admission.",
)


def _public_key(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    )


def _requirements() -> dict[str, Any]:
    return load_requirement_set(ROOT / "demo" / "admission" / "patient-wing.yaml")


def _robot(requirements: dict[str, Any], *, actor_id: str = "robot:sandbox:01", **overrides: Any) -> RobotState:
    capabilities = {
        "movement.max_speed": 0.6,
        "human_separation": 1.5,
        "sensing.facial_recognition": False,
        "data.video_retention": 0,
    }
    capabilities.update(overrides)
    return RobotState(
        actor_id, "sha256:sandbox-build-v1", "sha256:sandbox-controller-v1",
        "demo_mobile_base", requirements["environment_digest"], capabilities,
    )


def _restriction_digest(restriction: str) -> str:
    return digest({"restriction": restriction})


def _current_degraded_fixture(profile: Any) -> None:
    """Represent a current, already-issued restricted operating profile.

    The existing admission engine derives its current restriction only from a
    nonessential failed test; lifecycle correctly asks to requalify that
    profile. This sandbox fixture instead starts with complete current
    evidence, preserves its binding, and represents an explicitly restricted
    ``DEGRADED`` profile for adapter-boundary demonstration. It is not a new
    admission rule or SPP 0.1 behavior.
    """
    restriction = "sensing.video.capture=disabled"
    if profile.status != "ADMITTED":
        raise ValueError("sandbox degraded fixture requires a current admitted profile")
    profile.status = "DEGRADED"
    profile.restrictions = [restriction]
    profile.operating_profile["restrictions"] = [restriction]
    profile.reason_codes = ["sandbox_fixture:explicit_operating_restriction"]


def _restriction_acknowledgement(profile: Any, supplied: dict[str, Any] | None) -> dict[str, Any]:
    """A deliberately local exact-string-to-handler configuration check.

    It proves acknowledgement/configuration only, not handler execution or
    physical enforcement.  The experimental restriction-ack branch remains
    separate and is not imported by this sandbox.
    """
    if profile.status == "DENIED":
        return {"outcome": "BLOCKED", "may_rely": False, "reasons": ["profile_denied"]}
    if profile.status == "ADMITTED":
        return {"outcome": "NOT_REQUIRED", "may_rely": True, "reasons": ["profile_admitted_no_restriction_acknowledgement_required"]}

    required = sorted(set(profile.restrictions))
    if not required:
        return {"outcome": "BLOCKED", "may_rely": False, "reasons": ["degraded_without_restrictions"]}
    binding = profile_identifier(profile)
    default_acks = [
        {"profile_id": binding, "restriction": item, "restriction_digest": _restriction_digest(item), "handler": f"sandbox:{index}"}
        for index, item in enumerate(required, start=1)
    ]
    payload = supplied or {}
    acknowledgements = payload.get("acknowledgements", default_acks)
    mappings = payload.get("enforcement_mappings", default_acks)
    if not isinstance(acknowledgements, list) or not isinstance(mappings, list):
        return {"outcome": "BLOCKED", "may_rely": False, "reasons": ["acknowledgement_or_mapping_malformed"]}

    reasons: list[str] = []
    acknowledged: dict[str, dict[str, Any]] = {}
    mapped: dict[str, dict[str, Any]] = {}
    for item in acknowledgements:
        if not isinstance(item, dict) or not all(isinstance(item.get(k), str) and item[k].strip() for k in ("profile_id", "restriction", "restriction_digest", "handler")):
            reasons.append("acknowledgement_malformed")
            continue
        if item["profile_id"] != binding:
            reasons.append("acknowledgement_profile_mismatch")
            continue
        if item["restriction_digest"] != _restriction_digest(item["restriction"]):
            reasons.append("acknowledgement_restriction_digest_mismatch")
            continue
        if item["restriction"] not in required:
            reasons.append("acknowledgement_restriction_not_required")
            continue
        if item["restriction"] in acknowledged:
            reasons.append("duplicate_restriction_acknowledgement")
            continue
        acknowledged[item["restriction"]] = item
    for item in mappings:
        if not isinstance(item, dict) or not all(isinstance(item.get(k), str) and item[k].strip() for k in ("restriction", "restriction_digest", "handler")):
            reasons.append("enforcement_mapping_malformed")
            continue
        if item["restriction_digest"] != _restriction_digest(item["restriction"]):
            reasons.append("enforcement_mapping_digest_mismatch")
            continue
        if item["restriction"] not in required:
            continue
        if item["restriction"] in mapped:
            reasons.append("ambiguous_enforcement_mapping")
            continue
        mapped[item["restriction"]] = item
    for restriction in required:
        acknowledgement = acknowledged.get(restriction)
        mapping = mapped.get(restriction)
        if acknowledgement is None:
            reasons.append("restriction_acknowledgement_missing")
        elif mapping is None:
            reasons.append("restriction_unsupported")
        elif acknowledgement["handler"] != mapping["handler"]:
            reasons.append("enforcement_handler_mismatch")
    return {
        "outcome": "ACKNOWLEDGED" if not reasons else "BLOCKED",
        "may_rely": not reasons,
        "profile_id": binding,
        "required_restrictions": required,
        "reasons": sorted(set(reasons)),
    }


def _pipeline(name: str, acknowledgement: dict[str, Any] | None = None) -> dict[str, Any]:
    if name not in SCENARIOS:
        raise ValueError(f"unknown scenario: {name}")
    requirements = _requirements()
    capability_overrides: dict[str, Any] = {}
    if name == "denied":
        capability_overrides["human_separation"] = 0.8
    evidence_robot = _robot(requirements, **capability_overrides)
    admission_robot = evidence_robot if name != "changed-subject" else _robot(
        requirements, actor_id="robot:sandbox:replacement", **capability_overrides,
    )
    plan = derive_plan(requirements, evidence_robot, challenge=f"nonce:sandbox:{name}")
    plan["plan_id"] = f"urn:spp:sandbox:plan:{name}"
    plan.pop("plan_digest")
    plan["plan_digest"] = digest(plan)
    evidence = build_evidence(
        requirements, plan, evidence_robot, execute_plan(plan, evidence_robot, requirements), now=NOW,
    )
    evidence["evidence_id"] = f"urn:spp:sandbox:evidence:{name}"
    evidence.pop("evidence_digest")
    evidence["evidence_digest"] = digest(evidence)
    policy_key, evidence_key = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    authority = TrustedPolicyAuthority(
        "sandbox-policy-authority", _public_key(policy_key), frozenset({requirements["place"]}),
        frozenset({policy_scope(requirements)}),
    )
    issuer = TrustedIssuer(
        "sandbox-validator", _public_key(evidence_key), frozenset({EVIDENCE_BUNDLE_TYPE}),
        frozenset({evidence_scope(requirements)}),
    )
    signed_requirements = sign_place_requirements(requirements, authority_id=authority.authority_id, private_key=policy_key)
    signed_evidence = sign_evidence(evidence, issuer_id=issuer.issuer_id, private_key=evidence_key, scope=evidence_scope(requirements))
    if name == "tampered":
        signed_evidence.evidence["test_results"][0]["passed"] = False
    authorities = TrustedPolicyAuthorityRegistry([authority])
    issuers = TrustedIssuerRegistry([issuer])
    policy_check = verify_signed_place_requirements(
        signed_requirements, authorities, expected_place=requirements["place"], expected_scope=requirements["space"],
    )
    evidence_check = verify_signed_evidence(signed_evidence, issuers, expected_scope=evidence_scope(requirements))
    now = NOW + timedelta(minutes=16) if name == "expired" else NOW
    profile = admit_verified_policy_evidence_backed(
        signed_requirements, plan, signed_evidence, admission_robot, authorities, issuers,
        replay_registry=ReplayRegistry(), now=now,
    )
    if name in {"degraded", "missing-restriction-ack"}:
        _current_degraded_fixture(profile)
    lifecycle = assess_profile_lifecycle(
        profile, requirements, admission_robot, signed_evidence.evidence, now=now,
        signed_evidence=signed_evidence, trusted_issuers=issuers,
        signed_requirements=signed_requirements, trusted_authorities=authorities,
    )
    acknowledgement_data = acknowledgement
    if name == "missing-restriction-ack":
        acknowledgement_data = {"acknowledgements": [], "enforcement_mappings": []}
    restriction_ack = _restriction_acknowledgement(profile, acknowledgement_data)
    subject_ok = evidence.get("actor_id") == admission_robot.actor_id and profile.binding.actor_id == admission_robot.actor_id
    valid_until = datetime.fromisoformat(evidence["valid_until"].replace("Z", "+00:00"))
    time_ok = valid_until > now
    verified = policy_check.verified and evidence_check.verified and subject_ok and time_ok and lifecycle.status == "VALID"
    if profile.status == "ADMITTED" and verified:
        reliability = "RELIABLE_ADMITTED"
    elif profile.status == "DEGRADED" and verified and restriction_ack["may_rely"]:
        reliability = "RELIABLE_DEGRADED"
    else:
        reliability = "BLOCKED"
    return {
        "scenario": name,
        "profile": asdict(profile),
        "reliability": reliability,
        "verification": {
            "canonicalization": {"profile": "reference-json-sort-keys-v1", "verified": policy_check.verified and evidence_check.verified, "note": "This sandbox does not claim the separate experimental JCS profile."},
            "policy_signature": {"verified": policy_check.verified, "reason": policy_check.reason},
            "evidence_signature": {"verified": evidence_check.verified, "reason": evidence_check.reason},
            "binding": {"subject": subject_ok, "place": profile.place == requirements["place"], "scope": policy_check.verified and evidence_check.verified, "time": time_ok},
            "lifecycle": asdict(lifecycle),
            "restriction_acknowledgement": restriction_ack,
        },
    }


def _scenario_request(payload: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    if not isinstance(payload, dict) or not isinstance(payload.get("scenario"), str):
        raise HTTPException(status_code=422, detail="body must contain a supported scenario")
    acknowledgement = payload.get("restriction_acknowledgement")
    if acknowledgement is not None and not isinstance(acknowledgement, dict):
        raise HTTPException(status_code=422, detail="restriction_acknowledgement must be an object")
    return payload["scenario"], acknowledgement


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "SPP Reference Sandbox", "spp_version": "0.1", "status_boundary": "experimental/non-normative"}


@app.get("/about")
def about() -> dict[str, Any]:
    return {
        "service": "SPP Reference Sandbox",
        "spp_version": "0.1",
        "normative_status": "non-normative sandbox; SPP 0.1 is unchanged",
        "profiles": ["0.1-experimental evidence-based admission", "local Ed25519 issuer/policy trust"],
        "non_goals": ["production deployment", "physical enforcement attestation", "PKI", "network trust discovery"],
    }


@app.get("/examples")
def examples() -> list[dict[str, Any]]:
    return [json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8")) for name in SCENARIOS]


@app.get("/examples/{name}")
def example(name: str) -> dict[str, Any]:
    path = EXAMPLES / f"{name}.json"
    if name not in SCENARIOS or not path.is_file():
        raise HTTPException(status_code=404, detail="example not found")
    return json.loads(path.read_text(encoding="utf-8"))


@app.post("/evaluate")
def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    name, acknowledgement = _scenario_request(payload)
    try:
        result = _pipeline(name, acknowledgement)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"scenario": name, "admission": result["profile"]["status"], "profile": result["profile"]}


@app.post("/verify")
def verify(payload: dict[str, Any]) -> dict[str, Any]:
    name, acknowledgement = _scenario_request(payload)
    try:
        return _pipeline(name, acknowledgement)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
