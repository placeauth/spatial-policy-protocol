"""Native adapter for the non-normative SPP Core Profile fixtures.

It deliberately delegates rule selection to the existing SPP 0.1 reference
evaluator after adapting the engine-neutral resolved scope chain.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "reference" / "policy-server" / "src"))

from spp.evaluator import PolicyError, evaluate  # noqa: E402


def _scope_is_applicable(fixture: dict[str, Any]) -> bool:
    profile, request = fixture["profile"], fixture["request"]
    chain = fixture.get("scope_chain", [])
    return bool(chain and chain[0]["id"] == request["governed_scope"]
                and chain[-1]["id"] == profile["governed_scope"])


def _spp_inputs(fixture: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Translate the shared resolved chain into valid existing SPP 0.1 input."""
    profile, request = fixture["profile"], fixture["request"]
    chain = fixture["scope_chain"]
    spaces: list[dict[str, Any]] = []
    for index in range(len(chain) - 1, -1, -1):
        item = deepcopy(chain[index])
        item["parent"] = chain[index + 1]["id"] if index + 1 < len(chain) else None
        spaces.append(item)
    policy = {
        "spp_version": "0.1",
        "policy_id": profile["policy_id"],
        "policy_version": profile["policy_version"],
        "authority": {"id": profile["authority"]["id"]},
        "root_space": chain[-1]["id"],
        "default_decision": "deny",
        "spaces": spaces,
    }
    spp_request = {
        "spp_version": "0.1",
        "request_id": request["request_id"],
        "actor": deepcopy(request["subject"]),
        "space": request["governed_scope"],
        "action": deepcopy(request["action"]),
        "context": deepcopy(request.get("context", {})),
    }
    return policy, spp_request


def _unsupported_obligation(result: dict[str, Any], supported: set[str]) -> bool:
    return any(item["type"] not in supported for item in result.get("obligations", []))


def evaluate_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    """Return the compact engine-neutral profile result for one fixture."""
    if not _scope_is_applicable(fixture):
        return {"decision": "DENY", "obligations": [], "reason_codes": ["scope_mismatch"]}
    try:
        policy, request = _spp_inputs(fixture)
        result = evaluate(policy, request)
    except (KeyError, TypeError, PolicyError):
        return {"decision": "DENY", "obligations": [], "reason_codes": ["malformed_profile"]}
    obligations = result.get("obligations", [])
    supported = set(fixture.get("deployment", {}).get("supported_obligations", []))
    if _unsupported_obligation(result, supported):
        return {"decision": "DENY", "obligations": [], "reason_codes": ["required_obligation_unsupported"]}
    if result["decision"] == "conditional":
        reason_codes = ["required_authorization_missing"]
    elif result["decision"] == "deny" and result.get("matched_space") is None:
        reason_codes = ["no_applicable_rule"]
    else:
        reason_codes = ["matched_rule"]
    return {"decision": result["decision"].upper(), "obligations": obligations, "reason_codes": reason_codes}
