"""Bounded Python/Node/Rust raw-JCS differential runner (experimental)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "reference" / "admission" / "src"))
from spp_admission.jcs_admission_envelope import canonicalize_jcs, parse_jcs_json  # noqa: E402

HERE = Path(__file__).resolve().parent
CORPUS = HERE / "adversarial-corpus.json"


def python_results(corpus: dict) -> dict:
    results = []
    for case in corpus["cases"]:
        try:
            parsed = parse_jcs_json(case["source"])
            results.append({"id": case["id"], "category": "accepted", "canonical": canonicalize_jcs(parsed).decode()})
        except Exception as error:  # Experimental runner records an implementation's failure shape.
            results.append({"id": case["id"], "category": "malformed", "detail": str(error)})
    return {"implementation": "python", "results": results}


def invoke(command: list[str]) -> dict:
    return json.loads(subprocess.check_output(command, cwd=ROOT, text=True, encoding="utf-8"))


def main() -> None:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    outputs = [python_results(corpus), invoke(["node", str(HERE / "verify_adversarial.mjs"), str(CORPUS)]), invoke(["cargo", "run", "--quiet", "--manifest-path", str(HERE / "rust-verifier" / "Cargo.toml"), "--", "--raw", str(CORPUS)])]
    by_id = [{item["id"]: item["result"] if "result" in item else item for item in output["results"]} for output in outputs]
    disagreements = []
    unexpected = []
    for case in corpus["cases"]:
        categories = [implementation[case["id"]]["category"] for implementation in by_id]
        if len(set(categories)) != 1:
            disagreements.append({"id": case["id"], "categories": categories})
        elif categories[0] != case["expected"]:
            unexpected.append({"id": case["id"], "expected": case["expected"], "actual": categories[0]})
    print(json.dumps({
        "case_count": len(corpus["cases"]),
        "implementations": [output["implementation"] for output in outputs],
        "disagreements": disagreements,
        "unexpected": unexpected,
    }, indent=2))
    if disagreements or unexpected:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
