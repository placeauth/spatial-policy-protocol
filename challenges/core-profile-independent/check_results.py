"""Compare participant-provided normalized Core Profile outputs to expected JSON."""
from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
EXPECTED = ROOT / "expected"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python check_results.py PATH_TO_RESULTS")
        return 2

    results = Path(sys.argv[1])
    matched = 0
    expected_paths = sorted(EXPECTED.glob("*.json"))
    for expected_path in expected_paths:
        result_path = results / expected_path.name
        if not result_path.is_file():
            print(f"{expected_path.stem}: missing")
            continue
        try:
            expected = json.loads(expected_path.read_text(encoding="utf-8"))
            actual = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            print(f"{expected_path.stem}: invalid JSON ({error.msg})")
            continue
        if actual == expected:
            matched += 1
            print(f"{expected_path.stem}: match")
        else:
            print(f"{expected_path.stem}: mismatch")
    total = len(expected_paths)
    print(f"summary: {matched}/{total} fixtures matched")
    return 0 if matched == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
