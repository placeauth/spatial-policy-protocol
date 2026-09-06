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


_ROOT = Path(__file__).resolve().parents[4]
_NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)


@dataclass(frozen=True)
class ExplainTrace:
    """A read-only projection of existing conformance and admission outputs."""

    place: str
    space: str
    embodiment: str
    requirements: list[dict[str, Any]]
    provider_selection: list[dict[str, Any]]
    evidence_assessment: list[dict[str, Any]]
    requirement_delta: list[dict[str, Any]]
    tests_selected: list[dict[str, Any]]
    reused_guarantees: list[str]
    admission_result: dict[str, Any]

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
            "resolved": selection.resolved,
            "provider_id": selection.provider.provider_id if selection.provider else None,
            "assurance_level": selection.provider.assurance_level if selection.provider else None,
            "reason": selection.reason,
        })
    return ExplainTrace(
        destination["place"], destination["space"], robot.embodiment,
        [
            {key: requirement[key] for key in ("id", "action", "operator", "value", "unit") if key in requirement}
            for requirement in destination["requirements"]
        ],
        providers,
        [
            {
                "requirement_id": decision.requirement_id,
                "status": "REUSED" if decision.sufficient else "REJECTED",
                "reason": decision.reason,
                "evidence_id": decision.evidence_id,
            }
            for decision in assessment
        ],
        compute_requirement_delta(asdict(source_profile), destination),
        plan["selected_tests"], plan["reused_guarantees"],
        {
            "status": profile.status,
            "restrictions": profile.restrictions,
            "reason_codes": profile.reason_codes,
            "unresolved": profile.unresolved,
        },
    )


def render_trace(trace: ExplainTrace) -> str:
    """Render only fields supplied by ``ExplainTrace`` in stable order."""
    lines = [f"PLACE: {trace.space}", f"EMBODIMENT: {trace.embodiment}", "", "Requirements:"]
    for requirement in trace.requirements:
        unit = f" {requirement['unit']}" if requirement.get("unit") else ""
        lines.append(f"  {requirement['id']} {requirement['operator']} {requirement['value']}{unit}")
    lines.extend(["", "Provider selection:"])
    for selection in trace.provider_selection:
        provider = selection["provider_id"] or selection["reason"]
        lines.append(f"  {selection['requirement_id']}: {provider}")
    lines.extend(["", "Existing evidence:"])
    for assessment in trace.evidence_assessment:
        lines.append(f"  {assessment['requirement_id']}: {assessment['status']} ({assessment['reason']})")
    lines.extend(["", "Requirement delta:"])
    for item in trace.requirement_delta:
        lines.append(f"  {item['requirement_id']}: {item['classification']}")
    lines.extend(["", "Requalification:"])
    for requirement_id in trace.reused_guarantees:
        lines.append(f"  reuse: {requirement_id}")
    for test in trace.tests_selected:
        lines.append(f"  test: {test['requirement_id']} ({test['adapter']})")
    lines.extend(["", "Admission:", f"  {trace.admission_result['status']}"])
    for restriction in trace.admission_result["restrictions"]:
        lines.append(f"  restriction: {restriction}")
    for reason in trace.admission_result["reason_codes"]:
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
