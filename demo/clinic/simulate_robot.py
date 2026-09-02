"""Small, deterministic robot behavior demo for the SPP money-shot test.

The robot code is identical for Policy A and Policy B. Only the place policy
path changes; the resulting behavior demonstrates deny versus conditional.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference" / "policy-server" / "src"))

from spp.evaluator import evaluate, load_policy  # noqa: E402


ACTOR = {"id": "robot:demo:01", "type": "delivery_robot"}


def request(space: str, authorizations: list[str] | None = None) -> dict:
    return {
        "spp_version": "0.1",
        "request_id": "money-shot-route-01",
        "actor": ACTOR,
        "space": space,
        "action": {"family": "movement", "name": "enter"},
        "context": {
            "purpose": "delivery",
            "authorizations": authorizations or [],
        },
    }


def run(policy_path: Path) -> None:
    policy = load_policy(policy_path)
    print(f"Policy: {policy['policy_id']}")
    print("Task: deliver package through lobby -> restricted-room")

    lobby = evaluate(policy, request("clinic/lobby"))
    print(f"  lobby:            {lobby['decision'].upper()} — proceed")

    restricted = evaluate(policy, request("clinic/restricted-room"))
    if restricted["decision"] == "deny":
        print("  restricted-room:  DENY — robot refuses entry and replans")
        print("  result:           alternate-route / blocked-action")
        return

    if restricted["decision"] == "conditional":
        required = ", ".join(restricted["requires"])
        print(f"  restricted-room:  CONDITIONAL — pause; request {required}")
        authorized = evaluate(
            policy,
            request("clinic/restricted-room", ["delivery_authorization"]),
        )
        print(f"  authorization:    {authorized['decision'].upper()} — proceed")
        print("  result:           delivery completed after approval")
        return

    print("  restricted-room:  PERMIT — proceed")
    print("  result:           delivery completed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("policy", type=Path, help="Policy A or Policy B YAML")
    run(parser.parse_args().policy)


if __name__ == "__main__":
    main()
