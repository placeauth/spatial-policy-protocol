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
        base64.b64decode("GzaTa4UD1s7Qz2G0vj5AUl7ptnVMlopTqBf9B4FkbXQ=", validate=True),
        frozenset({"clinic"}), frozenset({"clinic/patient-wing"}),
    )
    registry = TrustedPolicyAuthorityRegistry([authority])
    valid = verify_place_package(package, registry)
    print(f"Package: {'VALID' if valid.valid else 'INVALID'}")
    print(f"Authority: {valid.authority_id}")
    print("Requirements: ACCEPTED" if valid.valid else f"Reason: {', '.join(valid.reasons)}")

    tampered = deepcopy(package)
    tampered["requirements"]["requirements"][0]["value"] = 1.2
    invalid = verify_place_package(tampered, registry)
    print("\nRequirement modified after signing")
    print(f"Package: {'VALID' if invalid.valid else 'INVALID'}")
    print(f"Reason: {', '.join(invalid.reasons)}")


if __name__ == "__main__":
    main()
