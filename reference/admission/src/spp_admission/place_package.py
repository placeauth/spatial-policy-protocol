"""Portable signed Place Package reference format, version 0.1."""
from __future__ import annotations

import argparse
import base64
import json
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource

from .engine import _canonical, digest
from .trust import ED25519, TrustedPolicyAuthority, TrustedPolicyAuthorityRegistry
from .vocabulary import DEFAULT_REQUIREMENT_VOCABULARY


PLACE_PACKAGE_VERSION = "0.1"


@dataclass(frozen=True)
class PlacePackageVerification:
    valid: bool
    reasons: list[str]
    package_digest: str | None
    authority_id: str | None


def _schema(name: str) -> dict[str, Any]:
    path = Path(__file__).resolve().parents[4] / "schema" / name
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_package(package: dict[str, Any]) -> None:
    """Validate composed schemas using only repository-local resources."""
    package_schema = _schema("place-package.schema.json")
    requirements_schema = _schema("place-requirement-set.schema.json")
    registry = Registry().with_resource(
        requirements_schema["$id"], Resource.from_contents(requirements_schema),
    )
    Draft202012Validator(package_schema, registry=registry).validate(package)


def _unsigned_content(package: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in package.items() if key not in {"signature", "package_digest"}}


def _signature_payload(package: dict[str, Any]) -> bytes:
    return _canonical({
        "authority_id": package["authority_id"],
        "algorithm": package["algorithm"],
        "package_digest": package["package_digest"],
    }).encode("utf-8")


def create_place_package(
    requirements: dict[str, Any], *, authority_id: str, private_key: Ed25519PrivateKey,
    policy_id: str | None = None, scope: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a portable JSON package with one signature over all semantics."""
    if not authority_id:
        raise ValueError("authority_id is required")
    package = {
        "place_package_version": PLACE_PACKAGE_VERSION,
        "place_id": requirements["space"],
        "policy_id": policy_id or requirements["requirement_set_id"],
        "policy_version": requirements["policy_version"],
        "scope": list(scope or [requirements["space"]]),
        "authority_id": authority_id,
        "requirements": deepcopy(requirements),
        "metadata": deepcopy(metadata or {}),
        "algorithm": ED25519,
    }
    package["package_digest"] = digest(_unsigned_content(package))
    package["signature"] = base64.b64encode(private_key.sign(_signature_payload(package))).decode("ascii")
    return package


def serialize_place_package(package: dict[str, Any]) -> str:
    """Return canonical JSON suitable for a single-file portable exchange."""
    return _canonical(package)


def load_place_package(path: str | Path) -> dict[str, Any]:
    """Load a portable JSON package without retaining process-local state."""
    loaded = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("place package must be a JSON object")
    return loaded


def _invalid(reason: str, package: dict[str, Any] | None = None) -> PlacePackageVerification:
    package = package if isinstance(package, dict) else {}
    return PlacePackageVerification(False, [reason], package.get("package_digest"), package.get("authority_id"))


def verify_place_package(
    package: dict[str, Any], trusted_authorities: TrustedPolicyAuthorityRegistry,
) -> PlacePackageVerification:
    """Validate structure, local authority authorization, digest, and signature."""
    if not isinstance(package, dict):
        return _invalid("invalid_place_package")
    if ("place_package_version" in package
            and package["place_package_version"] != PLACE_PACKAGE_VERSION):
        return _invalid("unsupported_place_package_version", package)
    try:
        _validate_package(package)
    except (OSError, ValueError, ValidationError, TypeError):
        return _invalid("invalid_place_package", package)
    authority = trusted_authorities.get(package["authority_id"])
    if authority is None:
        return _invalid("unknown_policy_authority", package)
    if not authority.enabled:
        return _invalid("policy_authority_disabled", package)
    requirements = package["requirements"]
    if (package["place_id"] != requirements["space"]
            or package["policy_id"] != requirements["requirement_set_id"]
            or package["policy_version"] != requirements["policy_version"]
            or requirements["space"] not in package["scope"]):
        return _invalid("invalid_place_package", package)
    try:
        Draft202012Validator(_schema("place-requirement-set.schema.json")).validate(requirements)
        for requirement in requirements["requirements"]:
            resolution = DEFAULT_REQUIREMENT_VOCABULARY.validate(requirement)
            if not resolution.resolved:
                return _invalid("unknown_requirement", package)
    except (OSError, ValueError, ValidationError, TypeError):
        return _invalid("invalid_place_package", package)
    if not authority.allows_place(requirements["place"]) or not all(authority.allows_scope(item) for item in package["scope"]):
        return _invalid("policy_authority_unauthorized", package)
    if digest(_unsigned_content(package)) != package["package_digest"]:
        return _invalid("place_package_signature_invalid", package)
    try:
        signature = base64.b64decode(package["signature"], validate=True)
        Ed25519PublicKey.from_public_bytes(authority.public_key).verify(signature, _signature_payload(package))
    except (ValueError, TypeError, InvalidSignature):
        return _invalid("place_package_signature_invalid", package)
    return PlacePackageVerification(True, [], package["package_digest"], package["authority_id"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["verify", "inspect"])
    parser.add_argument("file")
    parser.add_argument("--authority-key", help="Base64 raw Ed25519 public key for local verification")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON")
    args = parser.parse_args()
    try:
        package = load_place_package(args.file)
        if args.command == "inspect":
            output: Any = package
        elif not args.authority_key:
            output = PlacePackageVerification(False, ["missing_authority_key"], package.get("package_digest"), package.get("authority_id"))
        else:
            key = base64.b64decode(args.authority_key, validate=True)
            authority = TrustedPolicyAuthority(
                package["authority_id"], key, frozenset({package["requirements"]["place"]}),
                frozenset(package["scope"]),
            )
            output = verify_place_package(package, TrustedPolicyAuthorityRegistry([authority]))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        output = PlacePackageVerification(False, ["invalid_place_package"], None, None)
    if args.json:
        print(json.dumps(asdict(output) if isinstance(output, PlacePackageVerification) else output,
                         sort_keys=True, separators=(",", ":")))
    elif isinstance(output, PlacePackageVerification):
        print("VALID" if output.valid else "INVALID")
        for reason in output.reasons:
            print(reason)
    else:
        print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
