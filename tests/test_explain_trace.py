from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference" / "admission" / "src"))

from spp_admission.explain import build_trace, render_trace  # noqa: E402


def test_human_trace_is_deterministic_and_uses_real_patient_wing_outputs():
    first = render_trace(build_trace())
    second = render_trace(build_trace())
    assert first == second
    assert "PLACE: clinic/patient-wing" in first
    assert "movement.max_speed: REJECTED (insufficient_proven_bound)" in first
    assert "test: movement.max_speed (speed-bound)" in first
    assert "Admission:\n  ADMITTED" in first


def test_json_trace_is_deterministic_and_has_only_trace_fields():
    first = json.dumps(build_trace().as_dict(), sort_keys=True)
    second = json.dumps(build_trace().as_dict(), sort_keys=True)
    assert first == second
    assert set(json.loads(first)) == {
        "place", "space", "embodiment", "requirements", "provider_selection",
        "evidence_assessment", "requirement_delta", "tests_selected",
        "reused_guarantees", "admission_result",
    }


def test_reused_evidence_and_provider_selection_are_projected_from_existing_outputs():
    trace = build_trace("reused")
    movement = next(item for item in trace.evidence_assessment if item["requirement_id"] == "movement.max_speed")
    provider = next(item for item in trace.provider_selection if item["requirement_id"] == "movement.max_speed")
    assert movement == {
        "requirement_id": "movement.max_speed", "status": "REUSED",
        "reason": "sufficient", "evidence_id": "urn:spp:evidence:trace-source",
    }
    assert provider["provider_id"] == "mobile_speed_bound"
    assert "movement.max_speed" in trace.reused_guarantees


def test_tampered_source_evidence_shows_its_existing_rejection_reason():
    trace = build_trace("tampered")
    assert {item["reason"] for item in trace.evidence_assessment} == {"evidence_digest_mismatch"}
    assert all(item["status"] == "REJECTED" for item in trace.evidence_assessment)


def test_denied_trace_carries_actual_admission_reason_codes():
    trace = build_trace("denied")
    assert trace.admission_result["status"] == "DENIED"
    assert trace.admission_result["reason_codes"] == ["failed:human_separation"]
    assert "reason: failed:human_separation" in render_trace(trace)


def test_module_command_renders_text_and_json():
    environment = dict(os.environ, PYTHONPATH=str(ROOT / "reference" / "admission" / "src"))
    text = subprocess.run(
        [sys.executable, "-m", "spp_admission.explain", "--scenario", "patient-wing"],
        cwd=ROOT, env=environment, check=True, text=True, capture_output=True,
    ).stdout
    data = subprocess.run(
        [sys.executable, "-m", "spp_admission.explain", "--scenario", "reused", "--json"],
        cwd=ROOT, env=environment, check=True, text=True, capture_output=True,
    ).stdout
    assert "PLACE: clinic/patient-wing" in text
    assert json.loads(data)["reused_guarantees"] == ["movement.max_speed"]
