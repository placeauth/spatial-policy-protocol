from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from spp.evaluator import evaluate, load_policy, opa_input


ROOT = Path(__file__).resolve().parents[1]
OPA_BIN = os.getenv("SPP_OPA_BIN") or shutil.which("opa")


@pytest.mark.skipif(OPA_BIN is None, reason="OPA binary is optional")
def test_opa_matches_reference_for_pharmacy_deny() -> None:
    policy = load_policy(ROOT / "examples" / "hospital.yaml")
    request = {
        "spp_version": "0.1",
        "request_id": "opa-parity-1",
        "actor": {"id": "robot:test:1", "type": "delivery_robot"},
        "space": "clinic/pharmacy",
        "action": {"family": "movement", "name": "enter"},
        "context": {},
    }
    completed = subprocess.run(
        [
            OPA_BIN,
            "eval",
            "--data",
            str(ROOT / "reference" / "policy-server" / "policy" / "spp.rego"),
            "--stdin-input",
            "--format",
            "json",
            "data.spp.core",
        ],
        input=json.dumps(opa_input(policy, request)),
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(completed.stdout)
    core = payload["result"][0]["expressions"][0]["value"]
    assert core["decision"] == evaluate(policy, request)["decision"] == "deny"
