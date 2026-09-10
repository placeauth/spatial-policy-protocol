"""Deterministic SPP evidence-based admission scenarios A-D."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference" / "admission" / "src"))
sys.path.insert(0, str(ROOT / "reference" / "policy-server" / "src"))

from spp_admission.engine import (  # noqa: E402
    admit, build_evidence, compute_requirement_delta, derive_plan,
    execute_plan, load_requirement_set,
)
from spp_admission.models import RobotState  # noqa: E402
from spp.evaluator import evaluate, load_policy  # noqa: E402

REQ = Path(__file__).with_name("patient-wing.yaml")
LOBBY = Path(__file__).with_name("lobby.yaml")


def robot(**overrides: object) -> RobotState:
    capabilities = {
        "movement.max_speed": 0.6,
        "human_separation": 1.5,
        "sensing.facial_recognition": False,
        "data.video_retention": 0,
    }
    capabilities.update(overrides)
    return RobotState("robot:demo:admission-01", "sha256:robot-build-v1",
                      "sha256:controller-config-v1", "demo_mobile_base",
                      "sha256:site-model-clinic-v1", capabilities)


def run_admission(requirement_set: dict, state: RobotState, proven=None, challenge="nonce:demo-fixed") -> tuple[dict, dict]:
    plan = derive_plan(requirement_set, state, proven_guarantees=proven, challenge=challenge)
    results = execute_plan(plan, state, requirement_set)
    evidence = build_evidence(requirement_set, plan, state, results)
    profile = admit(requirement_set, plan, evidence, state)
    print(f"requirements: {', '.join(r['id'] for r in requirement_set['requirements'])}")
    print(f"reused:       {plan['reused_guarantees'] or '-'}")
    print(f"tests:        {[t['requirement_id'] for t in plan['selected_tests']] or '-'}")
    print(f"results:      {[(r['requirement_id'], 'PASS' if r['passed'] else 'FAIL') for r in results] or '-'}")
    print(f"evidence:     {evidence['evidence_digest']}")
    print(f"admission:    {profile.status}")
    print(f"profile:      {json.dumps(profile.operating_profile, sort_keys=True)}")
    if profile.restrictions:
        print(f"restrictions: {profile.restrictions}")
    if profile.reason_codes:
        print(f"reasons:      {profile.reason_codes}")
    return asdict(profile), plan


def admission_result(requirement_set: dict, state: RobotState, *, proven=None,
                     challenge: str) -> tuple[dict, dict, list[dict]]:
    """Run the same reference path as the detailed scenarios without printing JSON."""
    plan = derive_plan(requirement_set, state, proven_guarantees=proven, challenge=challenge)
    results = execute_plan(plan, state, requirement_set)
    evidence = build_evidence(requirement_set, plan, state, results)
    return asdict(admit(requirement_set, plan, evidence, state)), plan, results


def canonical_demo() -> None:
    """A compact, deterministic proof of place-driven SPP decisions and admission."""
    policy = load_policy(ROOT / "examples" / "hospital.yaml")
    scenarios = json.loads((ROOT / "demo" / "clinic" / "scenarios.json").read_text())
    selected = {"lobby", "staff-corridor", "pharmacy"}

    print("SPP 5-MINUTE PROOF")
    print("Same machine: robot:demo:admission-01")
    print("\nLAYER A - PLACE POLICY CHANGES WHAT THE MACHINE MAY DO")
    for scenario_data in scenarios:
        if scenario_data["id"] not in selected:
            continue
        decision = evaluate(policy, scenario_data["request"])
        action = scenario_data["request"]["action"]
        behavior = {
            "permit": "movement permitted",
            "conditional": "movement waits for required authorization",
            "deny": "movement is not permitted",
        }[decision["decision"]]
        print(f"PLACE: {scenario_data['request']['space']}")
        print(f"REQUEST: {action['family']}.{action['name']}")
        print(f"DECISION: {decision['decision'].upper()}")
        print(f"BEHAVIOR: {behavior}")
        if decision.get("requires"):
            print(f"REQUIRES: {', '.join(decision['requires'])}")
        print(f"WHY: {decision['reason']}")

    lobby = load_requirement_set(LOBBY)
    patient_wing = load_requirement_set(REQ)
    print("\nLAYER B - EVIDENCE-BASED ADMISSION")
    print("FLOW: PlaceRequirementSet -> ConformancePlan -> EvidenceBundle / EvidenceBinding -> AdmissionProfile")

    lobby_profile, _, _ = admission_result(lobby, robot(), challenge="nonce:canonical-lobby")
    print("\nPLACE: clinic/lobby")
    print("REQUIREMENTS: movement.max_speed <= 0.8 m/s")
    print(f"ADMISSION: {lobby_profile['status']}")
    print("PERMITTED BEHAVIOR: movement at the place speed limit")

    wing_profile, wing_plan, wing_results = admission_result(
        patient_wing,
        robot(),
        proven=lobby_profile["operating_profile"]["guarantees"],
        challenge="nonce:canonical-patient-wing",
    )
    print("\nMOVE: same machine -> clinic/patient-wing")
    print(f"REUSED EVIDENCE: {', '.join(wing_plan['reused_guarantees'])}")
    print("NEW REQUIREMENTS TESTED: " + ", ".join(result["requirement_id"] for result in wing_results))
    print(f"ADMISSION: {wing_profile['status']}")
    print("PERMITTED BEHAVIOR: movement admitted under the patient-wing requirements")

    degraded_profile, _, _ = admission_result(
        patient_wing, robot(**{"data.video_retention": 15}), challenge="nonce:canonical-degraded"
    )
    print("\nPLACE: clinic/patient-wing")
    print("UNSATISFIED: data.video_retention (nonessential)")
    print(f"ADMISSION: {degraded_profile['status']}")
    print(f"RESTRICTIONS: {', '.join(degraded_profile['restrictions'])}")
    print("PERMITTED BEHAVIOR: movement admitted; video capture disabled")

    denied_profile, _, _ = admission_result(
        patient_wing, robot(human_separation=0.8), challenge="nonce:canonical-denied"
    )
    print("\nPLACE: clinic/patient-wing")
    print("UNSATISFIED: human_separation (essential)")
    print(f"ADMISSION: {denied_profile['status']}")
    print(f"WHY: {', '.join(denied_profile['reason_codes'])}")
    print("PERMITTED BEHAVIOR: no admission profile is issued")
    print("\nThis demo is deterministic reference logic; no physical robot or runtime is connected.")


def scenario(name: str) -> None:
    requirements = load_requirement_set(REQ)
    if name == "a":
        print("SCENARIO A — FULL ADMISSION")
        run_admission(requirements, robot())
    elif name == "b":
        print("SCENARIO B — DEGRADED ADMISSION")
        run_admission(requirements, robot(**{"data.video_retention": 15}))
    elif name == "c":
        print("SCENARIO C — SAFETY FAILURE")
        run_admission(requirements, robot(human_separation=0.8))
    elif name == "d":
        print("SCENARIO D — SPATIAL TRANSITION / DELTA REQUALIFICATION")
        lobby = load_requirement_set(LOBBY)
        prior, _ = run_admission(lobby, robot())
        print(f"delta:        {compute_requirement_delta(prior, requirements)}")
        print("patient wing:")
        run_admission(requirements, robot(), proven=prior["operating_profile"]["guarantees"], challenge="nonce:demo-patient-wing")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", nargs="?", choices=["a", "b", "c", "d"])
    parser.add_argument("--canonical", action="store_true", help="Run the concise five-minute proof.")
    args = parser.parse_args()
    if args.canonical:
        canonical_demo()
        return
    if args.scenario is None:
        parser.error("choose a scenario (a-d) or pass --canonical")
    scenario(args.scenario)


if __name__ == "__main__":
    main()
