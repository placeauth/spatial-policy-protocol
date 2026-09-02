from __future__ import annotations

import json
from pathlib import Path

import pytest

from spp.evaluator import load_policy, validate_document


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("name", ["home", "hospital", "warehouse", "hotel"])
def test_example_policy_is_valid(name: str) -> None:
    load_policy(ROOT / "examples" / f"{name}.yaml")


def test_demo_requests_are_valid() -> None:
    scenarios = json.loads((ROOT / "demo" / "clinic" / "scenarios.json").read_text())
    for scenario in scenarios:
        validate_document(scenario["request"], "request.schema.json")


def test_examples_cover_every_action_family() -> None:
    expected = {
        "movement",
        "sensing",
        "data",
        "manipulation",
        "infrastructure",
        "human_interaction",
    }
    seen = set()
    for path in (ROOT / "examples").glob("*.yaml"):
        policy = load_policy(path)
        for space in policy["spaces"]:
            seen.update(rule["action"]["family"] for rule in space["rules"])
    assert seen == expected

