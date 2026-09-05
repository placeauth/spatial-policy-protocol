"""Inspect real selective requalification without robot hardware or a server."""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "reference/admission/src"), str(ROOT / "reference/policy-server/src")]

from spp_admission import EvidenceRecord, ReplayRegistry, derive_requalification_plan, admit_evidence_backed
from spp_admission.engine import build_evidence, compute_requirement_delta, execute_plan, load_requirement_set
from spp_admission.models import RobotState


def run(scenario: str = "normal") -> list[dict]:
    lobby = load_requirement_set(ROOT / "demo/admission/lobby.yaml")
    wing = load_requirement_set(ROOT / "demo/admission/patient-wing.yaml")
    corridor = deepcopy(lobby)
    corridor.update(space="clinic/corridor", policy_version=3)
    corridor["requirements"][0]["value"] = 1.0
    # The source proves <= 0.8, so the wing's <= 0.7 needs a direct test.
    wing["requirements"][0]["value"] = .7
    room = deepcopy(wing)
    room.update(space="clinic/restricted-room", policy_version=4)
    room["requirements"][1]["value"] = 2.0
    robot = RobotState("robot:demo:1", "build:1", "controller:1", "demo_mobile_base",
                       lobby["environment_digest"], {
                           "movement.max_speed": .6, "human_separation": 1.5,
                           "sensing.facial_recognition": False, "data.video_retention": 0,
                       })
    history: list[EvidenceRecord] = []
    registry = ReplayRegistry()
    previous = {}
    trace = []
    for index, destination in enumerate([lobby, corridor, wing, room]):
        now = datetime.now(timezone.utc)
        if scenario == "stale" and index >= 1:
            now += timedelta(minutes=16)
        if index == 1:
            if scenario == "tamper":
                history[0].evidence["test_results"][0]["passed"] = False
            elif scenario == "controller-change":
                robot = replace(robot, controller_fingerprint="controller:2")
        plan, decisions = derive_requalification_plan(destination, robot, history,
                                                      challenge=f"nonce:boundary:{index}", now=now)
        planning_controller = robot.controller_fingerprint
        if scenario == "toctou" and index == 1:
            # The planner already chose reuse. New evidence uses current state,
            # isolating the stale source-record binding at the admission boundary.
            robot = replace(robot, controller_fingerprint="controller:2")
        results = execute_plan(plan, robot, destination)
        evidence = build_evidence(destination, plan, robot, results, now=now)
        profile = admit_evidence_backed(destination, plan, evidence, robot, history, registry, now=now)
        trace.append({
            "space": destination["space"],
            "delta": compute_requirement_delta(previous, destination),
            "assessment": [asdict(d) for d in decisions],
            "reused": plan["reused_guarantees"],
            "tests": [r["requirement_id"] for r in results],
            "results": results, "status": profile.status,
            "restrictions": profile.restrictions, "reasons": profile.reason_codes,
            "planning_controller": planning_controller,
            "admission_controller": robot.controller_fingerprint,
        })
        # Records stay original. No copied guarantee gains a new test timestamp.
        history.append(EvidenceRecord(deepcopy(destination), plan, evidence))
        previous = asdict(profile)
        if profile.status == "DENIED":
            break
    return trace


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=["normal", "tamper", "stale", "controller-change", "toctou"], default="normal")
    parser.add_argument("--json", action="store_true", help="Emit the actual trace for inspection")
    args = parser.parse_args()
    trace = run(args.scenario)
    if args.json:
        print(json.dumps(trace, indent=2))
        return
    for step in trace:
        print(f"\nENTERING: {step['space']}")
        for decision in step["assessment"]:
            action = "REUSE" if decision["sufficient"] else "TEST"
            print(f"  {action:5} {decision['requirement_id']:28} {decision['reason']}")
        print(f"  Tests executed: {len(step['tests'])}; planned reuse: {len(step['reused'])}")
        if step["planning_controller"] != step["admission_controller"]:
            print(f"  Controller changed after planning: {step['planning_controller']} -> {step['admission_controller']}")
        if step["reasons"]:
            print(f"  Admission reasons: {', '.join(step['reasons'])}")
        print(f"  RESULT: {step['status']}")
    print(f"\nMission stopped at {trace[-1]['space']}. No physical runtime is connected.")


if __name__ == "__main__":
    main()
