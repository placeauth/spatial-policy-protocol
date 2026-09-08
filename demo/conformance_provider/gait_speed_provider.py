"""Example external provider: it imports only the public provider contract."""
from spp_admission import ConformanceProviderDescriptor, ConformanceProviderResult


class GaitSpeedProvider:
    descriptor = ConformanceProviderDescriptor(
        provider_id="gait-speed-provider",
        provider_version="1.0",
        supported_requirement_types=frozenset({"movement.max_speed"}),
        supported_embodiments=frozenset({"demo_humanoid"}),
        supported_assurance_levels=frozenset({"E2", "E3"}),
        evidence_type="behavioral_test",
        priority=100,
        description="Reference gait-speed conformance provider.",
        supported_requirement_versions={"movement.max_speed": frozenset({"1.0"})},
    )

    def evaluate(self, requirement, subject):
        measured = subject.capabilities.get("gait.maximum_speed_mps")
        passed = measured is not None and measured <= requirement["value"]
        return ConformanceProviderResult(
            self.descriptor.provider_id, self.descriptor.provider_version,
            requirement["id"], passed, measured, "E2", self.descriptor.evidence_type,
            {"capability": "gait.maximum_speed_mps"}, requirement_version="1.0", unit="m/s",
        )
