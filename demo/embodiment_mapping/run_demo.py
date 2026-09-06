"""Run identical place requirements through mobile-base and humanoid mappings."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference" / "admission" / "src"))

from spp_admission import DEFAULT_REQUIREMENT_MAPPING_REGISTRY, ReplayRegistry, admit, build_evidence, derive_plan, execute_plan
from spp_admission.models import RobotState


REQUIREMENTS = {
    "spp_version": "0.1", "admission_version": "0.1-experimental",
    "requirement_set_id": "urn:spp:requirements:embodiment-demo",
    "place": "place:clinic", "space": "clinic/lobby", "policy_version": 1,
    "environment_digest": "sha256:clinic-layout-v1",
    "requirements": [
        {"id": "movement.max_speed", "action": "movement", "operator": "<=", "value": 0.5, "unit": "m/s", "essential": True},
        {"id": "human_separation", "action": "human_interaction", "operator": ">=", "value": 1.0, "unit": "m", "essential": True},
        {"id": "sensing.facial_recognition", "action": "sensing", "operator": "prohibited", "value": True, "essential": True},
    ],
}


def _robot(embodiment: str) -> RobotState:
    capabilities = {
        "demo_mobile_base": {
            "movement.max_speed": 0.5, "human_separation": 1.2,
            "sensing.facial_recognition": False,
        },
        "demo_humanoid": {
            "gait.maximum_speed_mps": 0.5, "body.minimum_human_clearance_m": 1.2,
            "vision_pipeline.facial_recognition_enabled": False,
        },
    }[embodiment]
    return RobotState(f"robot:{embodiment}", "build:demo", "controller:demo", embodiment,
                      REQUIREMENTS["environment_digest"], capabilities)


def run() -> list[dict[str, object]]:
    """Select, execute, bind, and admit both embodiment-specific test paths."""
    output = []
    for embodiment in ("demo_mobile_base", "demo_humanoid"):
        robot = _robot(embodiment)
        selections = [DEFAULT_REQUIREMENT_MAPPING_REGISTRY.select(r, embodiment) for r in REQUIREMENTS["requirements"]]
        plan = derive_plan(REQUIREMENTS, robot, challenge=f"nonce:{embodiment}")
        results = execute_plan(plan, robot, REQUIREMENTS)
        evidence = build_evidence(REQUIREMENTS, plan, robot, results, now=datetime.now(timezone.utc))
        profile = admit(REQUIREMENTS, plan, evidence, robot, ReplayRegistry())
        output.append({
            "embodiment": embodiment,
            "providers": [selection.provider.provider_id for selection in selections if selection.provider],
            "tests": [test["adapter"] for test in plan["selected_tests"]],
            "results": results,
            "admission": profile.status,
        })
    return output


def main() -> None:
    for trace in run():
        print(f"\nEmbodiment: {trace['embodiment']}")
        for provider, test in zip(trace["providers"], trace["tests"]):
            print(f"  {provider} -> {test}")
        print(f"  Tests executed: {len(trace['results'])}")
        print(f"  Admission: {trace['admission']}")


if __name__ == "__main__":
    main()
