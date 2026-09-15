"""Compare the shared Core Profile fixtures through native and OPA evaluators."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "experiments" / "core-profile"
sys.path.insert(0, str(EXPERIMENT / "native"))

from evaluator import evaluate_fixture  # noqa: E402


OPA_IMAGE = "openpolicyagent/opa:1.17.0-static"
OPA_POLICY = "/work/experiments/core-profile/opa/core_profile.rego"


def opa_evaluate(fixture: dict[str, Any]) -> dict[str, Any]:
    """Run the official OPA CLI image against the exact shared JSON fixture."""
    command = [
        "docker", "run", "--rm", "-i", "-v", f"{ROOT}:/work:ro", OPA_IMAGE,
        "eval", "--format=json", "--stdin-input", "-d", OPA_POLICY,
        "data.spp_core.result",
    ]
    completed = subprocess.run(
        command, input=json.dumps(fixture), text=True, capture_output=True, check=False,
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or "OPA evaluation failed")
    body = json.loads(completed.stdout)
    try:
        return body["result"][0]["expressions"][0]["value"]
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError(f"OPA returned no result: {body}") from error


def fixtures() -> list[Path]:
    return sorted((EXPERIMENT / "fixtures").glob("*.json"))


def main() -> int:
    matched = 0
    for path in fixtures():
        fixture = json.loads(path.read_text(encoding="utf-8"))
        native = evaluate_fixture(fixture)
        opa = opa_evaluate(fixture)
        expected = fixture["expected"]
        match = native == opa == expected
        print(f"fixture: {fixture['name']}")
        print(f"native: {native['decision']}")
        print(f"opa:    {opa['decision']}")
        print(f"match:  {'yes' if match else 'NO'}")
        if not match:
            print(json.dumps({"expected": expected, "native": native, "opa": opa}, indent=2))
        print()
        matched += int(match)
    total = len(fixtures())
    print("summary:")
    print(f"{matched}/{total} fixtures matched")
    return 0 if matched == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
