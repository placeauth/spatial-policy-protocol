"""Deterministic SPP evidence-based admission scenarios A-D."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference" / "admission" / "src"))

from spp_admission.engine import (  # noqa: E402
    admit, build_evidence, compute_requirement_delta, derive_plan,
    execute_plan, load_requirement_set,
)
from spp_admission.models import RobotState  # noqa: E402

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
    parser.add_argument("scenario", choices=["a", "b", "c", "d"])
    scenario(parser.parse_args().scenario)


if __name__ == "__main__":
    main()
