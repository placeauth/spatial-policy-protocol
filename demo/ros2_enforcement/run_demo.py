"""ROS-free demonstration using real AdmissionProfile objects and mapping."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference" / "admission" / "src"))
sys.path.insert(0, str(ROOT / "reference" / "ros2-enforcer"))

from spp_admission.models import AdmissionProfile, EvidenceBinding
from spp_enforcer.mapping import map_profile


def profiles():
    # Illustrative trusted profiles, not a claim of newly measured evidence.
    for status in ("ADMITTED", "DEGRADED", "DENIED"):
        restrictions = ["movement.max_speed<=0.5"] if status == "DEGRADED" else []
        yield AdmissionProfile(
            status, "robot:demo", "clinic", "clinic/corridor", 1, "demo-evidence",
            EvidenceBinding("robot:demo", "build", "controller", "policy", "env", "plan"),
            {"guarantees": [{"id": "movement.max_speed", "operator": "<=", "value": 1.0}]},
            restrictions,
        )


def main():
    for profile in profiles():
        plan = map_profile(profile)
        print(profile.status)
        action = "none"
        if plan.navigation_allowed and plan.max_speed_mps is not None:
            print(f"  SPP max speed: {plan.max_speed_mps} m/s")
            action = f"set speed limit to {plan.max_speed_mps} m/s"
        print(f"  Nav2 action: {action}")
        print(f"  navigation_allowed: {str(plan.navigation_allowed).lower()}")


if __name__ == "__main__":
    main()
