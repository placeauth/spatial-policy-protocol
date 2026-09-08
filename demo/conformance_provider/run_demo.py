"""Run an external provider through current SPP evidence and admission."""
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference/admission/src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gait_speed_provider import GaitSpeedProvider  # noqa: E402
from spp_admission import (  # noqa: E402
    ConformanceProviderDescriptor, ConformanceProviderRegistry,
    ConformanceProviderResult, ReplayRegistry, admit, build_evidence,
    derive_plan,
)
from spp_admission.models import RobotState  # noqa: E402


class NavSpeedProvider:
    descriptor = ConformanceProviderDescriptor(
        "nav-speed-provider", "1.0", frozenset({"movement.max_speed"}),
        frozenset({"demo_mobile_base"}), frozenset({"E2"}), "behavioral_test", 100,
        supported_requirement_versions={"movement.max_speed": frozenset({"1.0"})},
    )

    def evaluate(self, requirement, subject):
        measured = subject.capabilities.get("movement.max_speed")
        return ConformanceProviderResult(
            "nav-speed-provider", "1.0", requirement["id"], measured <= requirement["value"],
            measured, "E2", "behavioral_test", requirement_version="1.0", unit="m/s",
        )


def main():
    requirements = {
        "spp_version": "0.1", "admission_version": "0.1-experimental",
        "requirement_set_id": "urn:spp:provider-demo", "place": "clinic",
        "space": "clinic/patient-wing", "policy_version": 1,
        "environment_digest": "sha256:clinic-provider-demo",
        "requirements": [{"id": "movement.max_speed", "requirement_version": "1.0", "action": "movement.enter", "operator": "<=", "value": .8, "unit": "m/s", "essential": True}],
    }
    humanoid = RobotState("robot:humanoid", "build:1", "controller:1", "demo_humanoid",
                          requirements["environment_digest"], {"gait.maximum_speed_mps": .6})
    registry = ConformanceProviderRegistry([NavSpeedProvider(), GaitSpeedProvider()])
    requirement = requirements["requirements"][0]
    selection, result = registry.evaluate(requirement, humanoid)
    plan = derive_plan(requirements, humanoid, challenge="nonce:provider-demo")
    evidence = build_evidence(requirements, plan, humanoid,
                              [result.to_evidence_result(plan["selected_tests"][0]["test_id"])],
                              now=datetime.now(timezone.utc))
    profile = admit(requirements, plan, evidence, humanoid, ReplayRegistry())
    unsupported, missing = registry.evaluate({"id": "movement.max_speed", "requirement_version": "2.0"}, humanoid)

    print("PLACE REQUIREMENT: movement.max_speed v1.0 <= 0.8 m/s")
    print("SUBJECT: humanoid")
    print("AVAILABLE PROVIDERS: nav-speed-provider [mobile_robot], gait-speed-provider [humanoid]")
    print(f"SELECTED: {selection.provider.descriptor.provider_id}")
    print(f"RESULT: {'PASS' if result.passed else 'FAIL'}")
    print("EVIDENCE: generated")
    print(f"ADMISSION: {profile.status}")
    print("\nRequirement: movement.max_speed v2.0")
    print(f"Result: {'UNRESOLVED' if missing is None else 'RESOLVED'} ({unsupported.reason})")


if __name__ == "__main__":
    main()
