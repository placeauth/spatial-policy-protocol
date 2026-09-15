from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest


EXPERIMENT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT / "native"))

from evaluator import evaluate_fixture  # noqa: E402


@pytest.mark.parametrize("path", sorted((EXPERIMENT / "fixtures").glob("*.json")), ids=lambda path: path.stem)
def test_native_evaluator_matches_shared_fixture(path: Path) -> None:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    assert evaluate_fixture(fixture) == fixture["expected"]
