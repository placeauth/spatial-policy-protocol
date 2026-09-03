from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from .models import AdmissionProfile, EvidenceBinding, RobotState


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode()).hexdigest()


def load_requirement_set(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as stream:
        requirements = yaml.safe_load(stream)
    if not isinstance(requirements, dict) or requirements.get("spp_version") != "0.1":
        raise ValueError("requirement set must be an SPP 0.1 object")
    if requirements.get("admission_version") != "0.1-experimental":
        raise ValueError("unsupported admission version")
    if not requirements.get("requirements"):
        raise ValueError("requirement set must contain requirements")
    return requirements


def _capability_key(requirement: dict[str, Any]) -> str:
    return requirement["id"]


def _test_for(requirement: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "movement.max_speed": ("speed-bound", "movement.max_speed"),
        "human_separation": ("separation-bound", "human_separation"),
        "sensing.facial_recognition": ("facial-recognition", "facial_recognition"),
        "data.video_retention": ("video-retention", "video_retention"),
    }
    adapter, capability = mapping[requirement["id"]]
    return {
        "test_id": f"test:{adapter}",
        "requirement_id": requirement["id"],
        "adapter": adapter,
        "capability": capability,
        "expected": f"{requirement['operator']} {requirement['value']}",
    }


def _satisfies(requirement: dict[str, Any], capabilities: dict[str, Any]) -> bool:
    actual = capabilities.get(_capability_key(requirement))
    if actual is None:
        return False
    operator = requirement["operator"]
    expected = requirement["value"]
    if operator == "<=":
        return actual <= expected
    if operator == ">=":
        return actual >= expected
    if operator == "=":
        return actual == expected
    if operator == "prohibited":
        return actual is False or actual == "prohibited"
    raise ValueError(f"unsupported operator: {operator}")


def derive_plan(
    requirement_set: dict[str, Any],
    robot: RobotState,
    proven_guarantees: list[dict[str, Any]] | None = None,
    challenge: str | None = None,
) -> dict[str, Any]:
    proven = {item["id"]: item for item in (proven_guarantees or [])}
    selected: list[dict[str, Any]] = []
    reused: list[str] = []
    unresolved: list[str] = []
    for requirement in requirement_set["requirements"]:
        prior = proven.get(requirement["id"])
        if prior and prior.get("environment_digest") == robot.environment_digest and _satisfies(requirement, prior.get("capabilities", {})):
            reused.append(requirement["id"])
            continue
        selected.append(_test_for(requirement))
        unresolved.append(requirement["id"])
    policy_digest = requirement_set.get("policy_digest") or digest(requirement_set)
    plan = {
        "admission_version": "0.1-experimental",
        "plan_id": "urn:spp:plan:" + uuid4().hex,
        "place": requirement_set["place"],
        "space": requirement_set["space"],
        "policy_version": requirement_set["policy_version"],
        "policy_digest": policy_digest,
        "environment_digest": requirement_set["environment_digest"],
        "challenge": challenge or "nonce:" + uuid4().hex,
        "selected_tests": selected,
        "reused_guarantees": reused,
        "unresolved_guarantees": unresolved,
        "required_assurance_level": "E2",
    }
    plan["plan_digest"] = digest(plan)
    return plan


def execute_plan(plan: dict[str, Any], robot: RobotState, requirement_set: dict[str, Any]) -> list[dict[str, Any]]:
    results = []
    for test in plan["selected_tests"]:
        requirement_id = test["requirement_id"]
        requirement = next(r for r in requirement_set["requirements"] if r["id"] == requirement_id)
        passed = _satisfies(requirement, robot.capabilities)
        results.append({"test_id": test["test_id"], "requirement_id": requirement_id, "passed": passed})
    return results


def build_evidence(
    requirement_set: dict[str, Any], plan: dict[str, Any], robot: RobotState, results: list[dict[str, Any]]
) -> dict[str, Any]:
    evidence = {
        "admission_version": "0.1-experimental",
        "evidence_id": "urn:spp:evidence:" + uuid4().hex,
        "actor_id": robot.actor_id,
        "robot_build_fingerprint": robot.build_fingerprint,
        "controller_configuration_fingerprint": robot.controller_fingerprint,
        "embodiment": robot.embodiment,
        "policy_version": requirement_set["policy_version"],
        "policy_digest": plan["policy_digest"],
        "environment_digest": robot.environment_digest,
        "conformance_plan_digest": plan["plan_digest"],
        "challenge": plan["challenge"],
        "test_results": results,
        "evidence_assurance_level": "E2",
        "issued_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    evidence["binding"] = {
        "actor_id": robot.actor_id,
        "build_fingerprint": robot.build_fingerprint,
        "controller_fingerprint": robot.controller_fingerprint,
        "policy_digest": plan["policy_digest"],
        "environment_digest": robot.environment_digest,
        "plan_digest": plan["plan_digest"],
    }
    evidence["valid_until"] = (
        datetime.now(timezone.utc) + timedelta(minutes=15)
    ).isoformat().replace("+00:00", "Z")
    evidence["evidence_digest"] = digest(evidence)
    return evidence


def admit(
    requirement_set: dict[str, Any], plan: dict[str, Any], evidence: dict[str, Any], robot: RobotState
) -> AdmissionProfile:
    binding = evidence.get("binding", {})
    binding_ok = (
        binding.get("actor_id") == robot.actor_id
        and binding.get("build_fingerprint") == robot.build_fingerprint
        and binding.get("controller_fingerprint") == robot.controller_fingerprint
        and binding.get("policy_digest") == plan["policy_digest"]
        and binding.get("environment_digest") == robot.environment_digest
        and binding.get("plan_digest") == plan["plan_digest"]
        and evidence.get("challenge") == plan["challenge"]
        and evidence.get("policy_version") == requirement_set["policy_version"]
    )
    try:
        valid_until = evidence.get("valid_until")
        if valid_until and datetime.fromisoformat(valid_until.replace("Z", "+00:00")) <= datetime.now(timezone.utc):
            return AdmissionProfile("DENIED", robot.actor_id, requirement_set["place"], requirement_set["space"], requirement_set["policy_version"], evidence.get("evidence_digest", ""), _binding(evidence), {}, [], [], ["stale_evidence"])
    except ValueError:
        return AdmissionProfile("DENIED", robot.actor_id, requirement_set["place"], requirement_set["space"], requirement_set["policy_version"], evidence.get("evidence_digest", ""), _binding(evidence), {}, [], [], ["malformed_evidence"])
    failures = {r["requirement_id"] for r in evidence.get("test_results", []) if not r["passed"]}
    unresolved = set(plan.get("unresolved_guarantees", [])) - {
        r["requirement_id"] for r in evidence.get("test_results", [])
    }
    restrictions: list[str] = []
    reasons: list[str] = []
    essential_failure = False
    guarantees: list[dict[str, Any]] = []
    for requirement in requirement_set["requirements"]:
        rid = requirement["id"]
        if rid in failures or rid in unresolved:
            if requirement.get("degraded_restriction") and rid not in {"human_separation"}:
                restrictions.append(requirement["degraded_restriction"])
                reasons.append(f"degraded:{rid}")
            else:
                essential_failure = True
                reasons.append(f"failed:{rid}")
        else:
            guarantees.append({"id": rid, "operator": requirement["operator"], "value": requirement["value"], "environment_digest": robot.environment_digest, "capabilities": robot.capabilities})
    if not binding_ok:
        return AdmissionProfile("DENIED", robot.actor_id, requirement_set["place"], requirement_set["space"], requirement_set["policy_version"], evidence.get("evidence_digest", ""), _binding(evidence), {}, [], [], ["evidence_binding_mismatch"])
    status = "DENIED" if essential_failure else ("DEGRADED" if restrictions else "ADMITTED")
    profile = {"guarantees": guarantees, "restrictions": restrictions}
    return AdmissionProfile(status, robot.actor_id, requirement_set["place"], requirement_set["space"], requirement_set["policy_version"], evidence["evidence_digest"], _binding(evidence), profile, restrictions, sorted(unresolved | failures), reasons)


def _binding(evidence: dict[str, Any]) -> EvidenceBinding:
    b = evidence.get("binding", {})
    return EvidenceBinding(b.get("actor_id", ""), b.get("build_fingerprint", ""), b.get("controller_fingerprint", ""), b.get("policy_digest", ""), b.get("environment_digest", ""), b.get("plan_digest", ""))


def compute_requirement_delta(previous_profile: dict[str, Any], new_requirement_set: dict[str, Any]) -> list[dict[str, Any]]:
    previous = {g["id"]: g for g in previous_profile.get("operating_profile", {}).get("guarantees", [])}
    current_ids = {r["id"] for r in new_requirement_set["requirements"]}
    delta = []
    for requirement in new_requirement_set["requirements"]:
        old = previous.get(requirement["id"])
        if not old:
            classification = "NEW"
        elif old.get("operator") == requirement["operator"] and old.get("value") == requirement["value"]:
            classification = "REUSED"
        elif old.get("operator") == requirement["operator"] and isinstance(old.get("value"), (int, float)) and isinstance(requirement.get("value"), (int, float)):
            if requirement["operator"] == "<=":
                classification = "STRICTER" if requirement["value"] < old["value"] else "RELAXED"
            elif requirement["operator"] == ">=":
                classification = "STRICTER" if requirement["value"] > old["value"] else "RELAXED"
            else:
                classification = "STRICTER"
        else:
            classification = "STRICTER"
        delta.append({"requirement_id": requirement["id"], "classification": classification})
    for old_id in previous:
        if old_id not in current_ids:
            delta.append({"requirement_id": old_id, "classification": "NO_LONGER_APPLICABLE"})
    return delta
