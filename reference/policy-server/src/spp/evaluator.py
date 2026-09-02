from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource


REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_DIR = REPO_ROOT / "schema"


class PolicyError(ValueError):
    """Raised when a policy is structurally invalid."""


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validator(name: str) -> Draft202012Validator:
    schema = _read_json(SCHEMA_DIR / name)
    decision = _read_json(SCHEMA_DIR / "decision.schema.json")
    registry = Registry().with_resources(
        [
            (schema["$id"], Resource.from_contents(schema)),
            (decision["$id"], Resource.from_contents(decision)),
        ]
    )
    return Draft202012Validator(schema, registry=registry)


def validate_document(document: dict[str, Any], schema_name: str) -> None:
    errors = sorted(_validator(schema_name).iter_errors(document), key=lambda e: list(e.path))
    if errors:
        details = "; ".join(
            f"{'/'.join(str(part) for part in error.path) or '$'}: {error.message}"
            for error in errors
        )
        raise PolicyError(details)


def load_policy(path: str | Path) -> dict[str, Any]:
    policy_path = Path(path)
    with policy_path.open("r", encoding="utf-8") as stream:
        policy = yaml.safe_load(stream)
    validate_policy(policy)
    return policy


def validate_policy(policy: dict[str, Any]) -> None:
    validate_document(policy, "policy.schema.json")
    spaces = policy["spaces"]
    by_id = {space["id"]: space for space in spaces}
    if len(by_id) != len(spaces):
        raise PolicyError("space ids must be unique")
    if policy["root_space"] not in by_id:
        raise PolicyError("root_space must identify a declared space")
    root = by_id[policy["root_space"]]
    if root.get("parent") is not None:
        raise PolicyError("root space parent must be null")

    for space in spaces:
        parent = space.get("parent")
        if space["id"] != policy["root_space"] and not parent:
            raise PolicyError(f"{space['id']}: non-root spaces require parent")
        if parent and parent not in by_id:
            raise PolicyError(f"{space['id']}: unknown parent {parent}")

        seen: set[str] = set()
        cursor: str | None = space["id"]
        while cursor is not None:
            if cursor in seen:
                raise PolicyError(f"{space['id']}: cycle in space hierarchy")
            seen.add(cursor)
            cursor = by_id[cursor].get("parent")


def policy_chain(policy: dict[str, Any], space_id: str) -> list[dict[str, Any]]:
    by_id = {space["id"]: space for space in policy["spaces"]}
    if space_id not in by_id:
        raise PolicyError(f"unknown space: {space_id}")
    chain: list[dict[str, Any]] = []
    cursor: str | None = space_id
    while cursor is not None:
        space = by_id[cursor]
        chain.append(space)
        cursor = space.get("parent")
    return chain


def _subset(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    return all(key in actual and actual[key] == value for key, value in expected.items())


def _actor_matches(rule: dict[str, Any], actor: dict[str, Any]) -> bool:
    selector = rule.get("actor", {})
    ids = selector.get("ids", [])
    types = selector.get("types", [])
    return (
        (not ids or actor["id"] in ids)
        and (not types or actor["type"] in types)
        and _subset(selector.get("attributes", {}), actor.get("attributes", {}))
    )


def _context_matches(rule: dict[str, Any], context: dict[str, Any]) -> bool:
    when = rule.get("when", {})
    purpose = when.get("purpose")
    if isinstance(purpose, str) and context.get("purpose") != purpose:
        return False
    if isinstance(purpose, list) and context.get("purpose") not in purpose:
        return False
    if "emergency" in when and context.get("emergency", False) != when["emergency"]:
        return False
    return _subset(when.get("attributes", {}), context.get("attributes", {}))


def _matching_rules(
    rules: Iterable[dict[str, Any]], request: dict[str, Any]
) -> Iterable[dict[str, Any]]:
    action = request["action"]
    eligible = [
        rule
        for rule in rules
        if rule["action"]["family"] == action["family"]
        and rule["action"]["name"] in (action["name"], "*")
        and _actor_matches(rule, request["actor"])
        and _context_matches(rule, request["context"])
    ]
    yield from (rule for rule in eligible if rule["action"]["name"] == action["name"])
    yield from (rule for rule in eligible if rule["action"]["name"] == "*")


def _finalize(
    policy: dict[str, Any],
    request: dict[str, Any],
    core: dict[str, Any],
) -> dict[str, Any]:
    return {
        "spp_version": "0.1",
        "request_id": request["request_id"],
        "decision_id": f"urn:uuid:{uuid4()}",
        "decision": core["decision"],
        "policy_id": policy["policy_id"],
        "policy_version": policy["policy_version"],
        "matched_space": core.get("matched_space"),
        "reason": core["reason"],
        "requires": core.get("requires", []),
        "obligations": core.get("obligations", []),
        "expires_in": core.get("expires_in", 30),
        "evaluated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def evaluate(policy: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    validate_document(request, "request.schema.json")
    for space in policy_chain(policy, request["space"]):
        rule = next(iter(_matching_rules(space["rules"], request)), None)
        if rule is None:
            continue

        decision = rule["decision"]
        required = rule.get("requires", [])
        granted = set(request["context"].get("authorizations", []))
        missing = [authorization for authorization in required if authorization not in granted]
        reason = rule.get("reason", f"Matched policy rule at {space['id']}.")
        if decision == "conditional" and not missing:
            decision = "permit"
            reason = f"{reason} Required authorizations are present."

        core = {
            "decision": decision,
            "matched_space": space["id"],
            "reason": reason,
            "requires": missing if decision == "conditional" else [],
            "obligations": rule.get("obligations", []),
            "expires_in": rule.get("expires_in", 30),
        }
        result = _finalize(policy, request, core)
        validate_document(result, "decision.schema.json")
        return result

    result = _finalize(
        policy,
        request,
        {
            "decision": "deny",
            "matched_space": None,
            "reason": "No applicable rule; SPP 0.1 is deny by default.",
            "expires_in": 30,
        },
    )
    validate_document(result, "decision.schema.json")
    return result


def opa_input(policy: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    validate_document(request, "request.schema.json")
    return {
        "request": request,
        "policy_chain": policy_chain(policy, request["space"]),
    }


def finalize_opa(
    policy: dict[str, Any], request: dict[str, Any], core: dict[str, Any]
) -> dict[str, Any]:
    result = _finalize(policy, request, core)
    validate_document(result, "decision.schema.json")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate one SPP 0.1 request")
    parser.add_argument("policy", help="Path to an SPP YAML policy")
    parser.add_argument("request", help="Path to a JSON decision request")
    args = parser.parse_args()
    policy = load_policy(args.policy)
    request = _read_json(Path(args.request))
    print(json.dumps(evaluate(policy, request), indent=2))


if __name__ == "__main__":
    main()
