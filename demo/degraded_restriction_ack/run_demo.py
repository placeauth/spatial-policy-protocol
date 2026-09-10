"""Deterministic reference demo for exact DEGRADED restriction acknowledgement."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference" / "admission" / "src"))

from spp_admission.models import AdmissionProfile, EvidenceBinding
from spp_admission.restriction_acknowledgement import (
    acknowledge_restriction,
    assess_degraded_restriction_acknowledgement,
    map_restriction_to_handler,
)


def profile() -> AdmissionProfile:
    restrictions = [
        "recording_disabled@restricted_zone",
        "movement.max_speed<=0.5@corridor",
    ]
    return AdmissionProfile(
        "DEGRADED", "robot:clinic-1", "clinic", "clinic/corridor", 1,
        "sha256:demo-evidence", EvidenceBinding(
            "robot:clinic-1", "build:1", "controller:1", "policy:1", "environment:1", "plan:1",
        ), {"restrictions": list(reversed(restrictions))}, restrictions, [], ["video_restricted"],
    )


def report(label, result) -> None:
    print(f"{label}: {result.outcome} (may_rely={str(result.may_rely).lower()})")
    if result.reasons:
        print("  Reasons: " + ", ".join(result.reasons))


def run() -> None:
    issued = profile()
    recording = "recording_disabled@restricted_zone"
    speed = "movement.max_speed<=0.5@corridor"
    mappings = [
        map_restriction_to_handler(recording, "camera_recording_suppression"),
        map_restriction_to_handler(speed, "speed_limiter"),
    ]
    all_acknowledged = [
        acknowledge_restriction(issued, recording, "camera_recording_suppression", "clinic-adapter-1"),
        acknowledge_restriction(issued, speed, "speed_limiter", "clinic-adapter-1"),
    ]
    report("A both exact restrictions", assess_degraded_restriction_acknowledgement(issued, all_acknowledged, mappings))
    report("B speed restriction missing", assess_degraded_restriction_acknowledgement(issued, all_acknowledged[:1], mappings))
    altered = acknowledge_restriction(issued, "movement.max_speed<=0.5", "speed_limiter", "clinic-adapter-1")
    report("C altered restriction", assess_degraded_restriction_acknowledgement(issued, [all_acknowledged[0], altered], mappings))


if __name__ == "__main__":
    run()
