"""Verify the portable clinic Place Package and show tamper detection."""
from __future__ import annotations

import base64
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference/admission/src"))

from spp_admission import TrustedPolicyAuthority, TrustedPolicyAuthorityRegistry, load_place_package, verify_place_package  # noqa: E402


def main() -> None:
    package = load_place_package(ROOT / "examples/place-packages/clinic-patient-wing.json")
    authority = TrustedPolicyAuthority(
        "hospital-policy-authority",
        base64.b64decode("4ShcmAmXdpkh5uAlCQ9ZvSQBAleOpxYXYh7zzttH4Ko=", validate=True),
        frozenset({"clinic"}), frozenset({"clinic/patient-wing"}),
    )
    registry = TrustedPolicyAuthorityRegistry([authority])
    valid = verify_place_package(package, registry)
    print(f"Package: {'VALID' if valid.valid else 'INVALID'}")
    print(f"Authority: {valid.authority_id}")
    speed = next(item for item in package["requirements"]["requirements"] if item["id"] == "movement.max_speed")
    print(f"Requirement: movement.max_speed v{speed['requirement_version']}")
    print(f"Value: {speed['value']} {speed['unit']}")
    print("Requirements: ACCEPTED" if valid.valid else f"Reason: {', '.join(valid.reasons)}")

    tampered = deepcopy(package)
    tampered["requirements"]["requirements"][0]["requirement_version"] = "2.0"
    invalid = verify_place_package(tampered, registry)
    print("\nRequirement version modified after signing: 1.0 -> 2.0")
    print(f"Package: {'VALID' if invalid.valid else 'INVALID'}")
    print(f"Reason: {', '.join(invalid.reasons)}")

    unknown = deepcopy(package)
    unknown["requirements"]["requirements"][0].update(id="x-example.foo", requirement_version="1.0")
    unresolved = verify_place_package(unknown, registry)
    print("\nUnknown extension: x-example.foo v1.0")
    print(f"Package: {'VALID' if unresolved.valid else 'INVALID'}")
    print(f"Reason: {', '.join(unresolved.reasons)}")


if __name__ == "__main__":
    main()
