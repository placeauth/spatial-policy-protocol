"""Pure SPP eligibility demo. No Open-RMF runtime is connected."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference/admission/src"))

from spp_admission import (ReplayRegistry, admit_evidence_backed, build_evidence,
                           derive_plan, execute_plan)
from spp_admission.models import RobotState
from spp_admission.open_rmf import TaskContext, map_profile


def run():
    robot = RobotState("robot:clinic:1", "build:1", "controller:1", "demo_mobile_base",
                       "environment:clinic:1", {"movement.max_speed": 0.6})
    results = []
    for task, space, essential, bound in [
        ("deliver medication to patient-wing", "clinic/patient-wing", True, 0.8),
        ("enter restricted-room", "clinic/restricted-room", True, 0.4),
        ("staff-assisted delivery", "clinic/patient-wing", False, 0.4),
    ]:
        requirement = dict(id="movement.max_speed", action="movement.enter",
                           operator="<=", value=bound, unit="m/s", essential=essential)
        if not essential:
            requirement["degraded_restriction"] = "movement=staff_assisted"
        requirements = dict(spp_version="0.1", admission_version="0.1-experimental",
                            requirement_set_id="urn:spp:rmf-demo:" + space,
                            place="clinic", space=space, policy_version=1,
                            environment_digest=robot.environment_digest,
                            requirements=[requirement])
        plan = derive_plan(requirements, robot)
        evidence = build_evidence(requirements, plan, robot,
                                  execute_plan(plan, robot, requirements))
        # Fresh local evidence-backed admission, not a fabricated status.
        profile = admit_evidence_backed(requirements, plan, evidence, robot,
                                        replay_registry=ReplayRegistry())
        decision = map_profile(profile, TaskContext(robot.actor_id, "clinic", space),
                               accepted_restrictions=frozenset({"movement=staff_assisted"}))
        results.append((task, profile.status, decision))
    return results


if __name__ == "__main__":
    print("Adapter boundary demo only; no Open-RMF runtime connected.")
    print("Staff assistance is explicitly accepted for this demonstration only.")
    for task, status, decision in run():
        print(f"\nTask: {task}\nSPP profile: {status}")
        print("RMF task eligible" if decision.task_allowed else "RMF task rejected")
        if decision.restrictions:
            print("Restrictions: " + ", ".join(decision.restrictions))
        if decision.reasons:
            print("Reasons: " + ", ".join(decision.reasons))
