from __future__ import annotations

import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_canonical_demo_exercises_policy_and_admission(capsys) -> None:
    demo = runpy.run_path(str(ROOT / "demo" / "admission" / "run_demo.py"))
    demo["canonical_demo"]()
    output = capsys.readouterr().out

    assert "DECISION: PERMIT" in output
    assert "DECISION: CONDITIONAL" in output
    assert "DECISION: DENY" in output
    assert "REUSED EVIDENCE: movement.max_speed" in output
    assert "ADMISSION: ADMITTED" in output
    assert "ADMISSION: DEGRADED" in output
    assert "RESTRICTIONS: sensing.video.capture=disabled" in output
    assert "ADMISSION: DENIED" in output
    assert "WHY: failed:human_separation" in output
