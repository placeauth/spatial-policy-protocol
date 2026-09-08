"""Run the pure SPP facility access-control boundary demonstration."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference/admission/src"))

from spp_admission import ProfileLifecycleAssessment, ReferenceDoorController  # noqa: E402
from spp_admission.models import AdmissionProfile, EvidenceBinding  # noqa: E402


TARGET = "clinic/patient-wing"


def issued_profile(status, restrictions=()):
    return AdmissionProfile(
        status, "robot:clinic:1", "clinic", TARGET, 1, "sha256:evidence",
        EvidenceBinding("robot:clinic:1", "build:1", "controller:1", "sha256:policy", "sha256:environment", "sha256:plan"),
        restrictions=list(restrictions),
    )


def lifecycle(status):
    return ProfileLifecycleAssessment(status, [], [], [], "continue", [])


def main() -> None:
    accepting = ReferenceDoorController(frozenset({"video_disabled"}))
    rejecting = ReferenceDoorController()
    scenarios = [
        ("A", "ADMITTED", accepting.authorize(issued_profile("ADMITTED"), TARGET)),
        ("B", "DEGRADED / video_disabled accepted", accepting.authorize(issued_profile("DEGRADED", ("video_disabled",)), TARGET)),
        ("C", "DEGRADED / video_disabled rejected", rejecting.authorize(issued_profile("DEGRADED", ("video_disabled",)), TARGET)),
        ("D", "DENIED", accepting.authorize(issued_profile("DENIED"), TARGET)),
        ("E", "INVALID lifecycle", accepting.authorize(issued_profile("ADMITTED"), TARGET, lifecycle=lifecycle("INVALID"))),
    ]
    for label, description, decision in scenarios:
        print(f"\nSCENARIO {label}: {description}")
        print(f"Target: {decision.target_place}")
        print("Door: ACCESS GRANTED" if decision.allowed else "Door: ACCESS DENIED")
        if decision.accepted_restrictions:
            print("Accepted restrictions: " + ", ".join(decision.accepted_restrictions))
        if decision.rejected_restrictions:
            print("Rejected restrictions: " + ", ".join(decision.rejected_restrictions))
        if decision.reasons:
            print("Reasons: " + ", ".join(decision.reasons))


if __name__ == "__main__":
    main()
