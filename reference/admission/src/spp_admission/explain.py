"""Deterministic, developer-facing trace of an SPP admission evaluation."""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .engine import (
    ReplayRegistry,
    build_evidence,
    compute_requirement_delta,
    derive_plan,
    digest,
    execute_plan,
    load_requirement_set,
)
from .mapping import DEFAULT_REQUIREMENT_MAPPING_REGISTRY
from .boundary import admit_evidence_backed
from .models import RobotState
from .sufficiency import EvidenceRecord, assess_sufficiency, derive_requalification_plan
from .lifecycle import assess_profile_lifecycle
from .vocabulary import DEFAULT_REQUIREMENT_VOCABULARY


_ROOT = Path(__file__).resolve().parents[4]
_NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)
TRACE_FORMAT_VERSION = "0.1"


@dataclass(frozen=True)
class ExplainTrace:
    """Stable, read-only machine projection of existing admission outputs."""

    trace_version: str
    decision_id: str
    place: dict[str, Any]
    subject: dict[str, Any]
    requirements: list[dict[str, Any]]
    provider_selection: list[dict[str, Any]]
    evidence_assessment: list[dict[str, Any]]
    requirement_delta: dict[str, Any]
    selected_tests: list[dict[str, Any]]
    reused_guarantees: list[dict[str, Any]]
    admission: dict[str, Any]
    lifecycle: dict[str, Any] | None
    restrictions: list[str]
    reasons: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _rehash(document: dict[str, Any], field: str) -> None:
    document[field] = digest({key: value for key, value in document.items() if key != field})


def _requirements() -> tuple[dict[str, Any], dict[str, Any]]:
    lobby = load_requirement_set(_ROOT / "demo" / "admission" / "lobby.yaml")
    wing = load_requirement_set(_ROOT / "demo" / "admission" / "patient-wing.yaml")
    return lobby, wing


def _robot(environment_digest: str, *, human_separation: float = 1.5) -> RobotState:
    return RobotState(
        "robot:trace:1", "build:trace:1", "controller:trace:1", "demo_mobile_base",
        environment_digest,
        {
            "movement.max_speed": .6,
            "human_separation": human_separation,
            "sensing.facial_recognition": False,
            "data.video_retention": 0,
        },
    )


def build_trace(scenario: str = "patient-wing") -> ExplainTrace:
    """Run a representative existing-fixture transition and project its outputs.

    ``patient-wing`` exercises an insufficient prior movement bound. ``reused``
    uses the fixture's original bound to show accepted source evidence.
    ``tampered`` exposes the existing digest rejection; ``denied`` executes the
    same planning path with a failing essential separation result.
    """
    if scenario not in {"patient-wing", "reused", "tampered", "denied"}:
        raise ValueError(f"unknown scenario: {scenario}")
    lobby, destination = _requirements()
    destination = deepcopy(destination)
    if scenario in {"patient-wing", "tampered", "denied"}:
        destination["requirements"][0]["value"] = .7
    robot = _robot(destination["environment_digest"], human_separation=.7 if scenario == "denied" else 1.5)

    source_plan = derive_plan(lobby, robot, challenge="nonce:trace-source")
    source_evidence = build_evidence(
        lobby, source_plan, robot, execute_plan(source_plan, robot, lobby), now=_NOW,
    )
    source_evidence["evidence_id"] = "urn:spp:evidence:trace-source"
    _rehash(source_evidence, "evidence_digest")
    source_profile = admit_evidence_backed(
        lobby, source_plan, source_evidence, robot, replay_registry=ReplayRegistry(), now=_NOW,
    )
    if scenario == "tampered":
        source_evidence["test_results"][0]["passed"] = False
    sources = [EvidenceRecord(lobby, source_plan, source_evidence)]

    assessment = assess_sufficiency(destination, robot, sources, now=_NOW)
    plan, _ = derive_requalification_plan(
        destination, robot, sources, challenge="nonce:trace-destination", now=_NOW,
    )
    results = execute_plan(plan, robot, destination)
    evidence = build_evidence(destination, plan, robot, results, now=_NOW)
    profile = admit_evidence_backed(
        destination, plan, evidence, robot, sources, ReplayRegistry(), now=_NOW,
    )

    providers = []
    for requirement in destination["requirements"]:
        selection = DEFAULT_REQUIREMENT_MAPPING_REGISTRY.select(
            requirement, robot.embodiment, plan["required_assurance_level"],
        )
        providers.append({
            "requirement_id": requirement["id"],
            "embodiment": robot.embodiment,
            "provider_id": selection.provider.provider_id if selection.provider else None,
            "provider_version": None,
            "assurance_level": selection.provider.assurance_level if selection.provider else None,
            "status": "SELECTED" if selection.resolved else "UNRESOLVED",
            "reason": selection.reason,
        })
    requirements = []
    for requirement in destination["requirements"]:
        item = {key: requirement[key] for key in ("id", "requirement_version", "action", "operator", "value", "unit", "scope") if key in requirement}
        resolution = DEFAULT_REQUIREMENT_VOCABULARY.resolve(item["id"], item.get("requirement_version"))
        if resolution.resolved:
            definition = resolution.definition
            item["requirement_version"] = definition.version
            item["canonical_unit"] = definition.unit
            item["comparison"] = definition.comparison
        requirements.append(item)
    evidence_assessment = []
    for decision in assessment:
        status = "reused" if decision.sufficient else (
            "rejected" if decision.reason in {"evidence_digest_mismatch", "evidence_binding_mismatch", "policy_digest_mismatch"}
            else "insufficient"
        )
        evidence_assessment.append({
            "requirement_id": decision.requirement_id,
            "evidence_id": decision.evidence_id,
            "status": status,
            "assurance_level": None,
            "freshness_status": None,
            "reason_codes": [decision.reason],
        })
    delta_items = compute_requirement_delta(asdict(source_profile), destination)
    delta = {
        "items": delta_items,
        "reusable_requirements": [item["requirement_id"] for item in delta_items if item["classification"] == "REUSED"],
        "new_requirements": [item["requirement_id"] for item in delta_items if item["classification"] == "NEW"],
        "stricter_requirements": [item["requirement_id"] for item in delta_items if item["classification"] == "STRICTER"],
        "unresolved_requirements": [item["requirement_id"] for item in delta_items if item["classification"] == "UNRESOLVED"],
        "invalidated_requirements": [],
    }
    selected_tests = []
    for test in plan["selected_tests"]:
        provider = next(item for item in providers if item["requirement_id"] == test["requirement_id"])
        selected_tests.append({
            "test_id": test["test_id"], "provider_id": provider["provider_id"],
            "requirement_id": test["requirement_id"], "embodiment": robot.embodiment,
            "assurance_target": plan["required_assurance_level"],
            "selection_reason": provider["reason"], "adapter": test["adapter"],
        })
    reused = [
        {"requirement_id": item["requirement_id"], "source_evidence_id": item["evidence_id"],
         "status": "reused", "reason": item["reason_codes"][0], "freshness_status": item["freshness_status"]}
        for item in evidence_assessment if item["status"] == "reused"
    ]
    lifecycle_assessment = assess_profile_lifecycle(profile, destination, robot, evidence, now=_NOW)
    lifecycle = {
        "status": lifecycle_assessment.status,
        "reasons": lifecycle_assessment.reasons,
        "reusable_guarantees": lifecycle_assessment.reusable_guarantees,
        "invalidated_guarantees": lifecycle_assessment.invalidated_guarantees,
        "required_action": lifecycle_assessment.required_action,
    }
    admission = {
        "outcome": profile.status, "restrictions": list(profile.restrictions),
        "reasons": list(profile.reason_codes), "unresolved": list(profile.unresolved),
        "place": profile.place, "space": profile.space,
    }
    trace_fields = {
        "trace_version": TRACE_FORMAT_VERSION,
        "place": {"id": destination["place"], "space": destination["space"], "policy_version": destination["policy_version"]},
        "subject": {"actor_id": robot.actor_id, "build_fingerprint": robot.build_fingerprint,
                    "controller_fingerprint": robot.controller_fingerprint, "embodiment": robot.embodiment,
                    "environment_digest": robot.environment_digest},
        "requirements": requirements, "provider_selection": providers,
        "evidence_assessment": evidence_assessment, "requirement_delta": delta,
        "selected_tests": selected_tests, "reused_guarantees": reused,
        "admission": admission, "lifecycle": lifecycle,
        "restrictions": list(profile.restrictions), "reasons": list(profile.reason_codes),
    }
    decision_id = "urn:spp:decision:" + digest(trace_fields).removeprefix("sha256:")
    return ExplainTrace(decision_id=decision_id, **trace_fields)


def render_trace(trace: ExplainTrace) -> str:
    """Render only fields supplied by ``ExplainTrace`` in stable order."""
    lines = [f"PLACE: {trace.place['space']}", f"EMBODIMENT: {trace.subject['embodiment']}", "", "Requirements:"]
    for requirement in trace.requirements:
        unit = f" {requirement['unit']}" if requirement.get("unit") else ""
        lines.append(f"  {requirement['id']} {requirement['operator']} {requirement['value']}{unit}")
    lines.extend(["", "Provider selection:"])
    for selection in trace.provider_selection:
        provider = selection["provider_id"] or selection["reason"]
        lines.append(f"  {selection['requirement_id']}: {provider}")
    lines.extend(["", "Existing evidence:"])
    for assessment in trace.evidence_assessment:
        status = "REUSED" if assessment["status"] == "reused" else "REJECTED"
        lines.append(f"  {assessment['requirement_id']}: {status} ({assessment['reason_codes'][0]})")
    lines.extend(["", "Requirement delta:"])
    for item in trace.requirement_delta["items"]:
        lines.append(f"  {item['requirement_id']}: {item['classification']}")
    lines.extend(["", "Requalification:"])
    for guarantee in trace.reused_guarantees:
        lines.append(f"  reuse: {guarantee['requirement_id']}")
    for test in trace.selected_tests:
        lines.append(f"  test: {test['requirement_id']} ({test['adapter']})")
    lines.extend(["", "Admission:", f"  {trace.admission['outcome']}"])
    for restriction in trace.admission["restrictions"]:
        lines.append(f"  restriction: {restriction}")
    for reason in trace.admission["reasons"]:
        lines.append(f"  reason: {reason}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=["patient-wing", "reused", "tampered", "denied"], default="patient-wing")
    parser.add_argument("--json", action="store_true", help="Emit the trace object as deterministic JSON")
    args = parser.parse_args()
    trace = build_trace(args.scenario)
    if args.json:
        print(json.dumps(trace.as_dict(), indent=2, sort_keys=True))
    else:
        print(render_trace(trace))


if __name__ == "__main__":
    main()
