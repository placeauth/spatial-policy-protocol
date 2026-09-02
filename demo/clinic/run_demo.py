from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference" / "policy-server" / "src"))

from spp.evaluator import evaluate, load_policy  # noqa: E402


def main() -> None:
    policy = load_policy(ROOT / "examples" / "hospital.yaml")
    scenarios = json.loads((Path(__file__).parent / "scenarios.json").read_text())
    for scenario in scenarios:
        decision = evaluate(policy, scenario["request"])
        obligations = decision.get("obligations") or []
        suffix = f" | obligations={json.dumps(obligations)}" if obligations else ""
        print(
            f"{decision['decision'].upper():11} "
            f"{scenario['label']}: {decision['reason']}{suffix}"
        )


if __name__ == "__main__":
    main()
