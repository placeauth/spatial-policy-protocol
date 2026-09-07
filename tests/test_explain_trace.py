from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference" / "admission" / "src"))

from spp_admission.explain import build_trace, render_trace  # noqa: E402


def _schema():
    return json.loads((ROOT / "schema" / "explain-trace.schema.json").read_text(encoding="utf-8"))


def test_trace_is_versioned_deterministic_and_schema_valid():
    first = build_trace().as_dict()
    second = build_trace().as_dict()
    assert first == second
    assert first["trace_version"] == "0.1"
    Draft202012Validator(_schema()).validate(first)


def test_provider_evidence_delta_reuse_admission_and_lifecycle_are_projected():
    trace = build_trace("reused").as_dict()
    provider = next(item for item in trace["provider_selection"] if item["requirement_id"] == "movement.max_speed")
    evidence = next(item for item in trace["evidence_assessment"] if item["requirement_id"] == "movement.max_speed")
    assert provider == {
        "requirement_id": "movement.max_speed", "embodiment": "demo_mobile_base",
        "provider_id": "mobile_speed_bound", "provider_version": None,
        "assurance_level": "E2", "status": "SELECTED", "reason": None,
    }
    assert evidence["status"] == "reused"
    assert evidence["reason_codes"] == ["sufficient"]
    assert trace["requirement_delta"]["reusable_requirements"] == ["movement.max_speed"]
    assert trace["reused_guarantees"] == [{
        "requirement_id": "movement.max_speed",
        "source_evidence_id": "urn:spp:evidence:trace-source",
        "status": "reused", "reason": "sufficient", "freshness_status": None,
    }]
    assert trace["admission"]["outcome"] == "ADMITTED"
    assert trace["lifecycle"]["status"] == "VALID"


def test_reason_codes_remain_canonical_and_no_internal_representation_leaks():
    tampered = build_trace("tampered").as_dict()
    denied = build_trace("denied").as_dict()
    assert {item["reason_codes"][0] for item in tampered["evidence_assessment"]} == {"evidence_digest_mismatch"}
    assert denied["admission"]["reasons"] == ["failed:human_separation"]
    encoded = json.dumps(tampered, sort_keys=True)
    assert "object at 0x" not in encoded
    assert "spp_admission." not in encoded


def test_canonical_example_is_schema_valid_and_matches_real_trace():
    example = json.loads((ROOT / "examples" / "traces" / "patient-wing.json").read_text(encoding="utf-8"))
    Draft202012Validator(_schema()).validate(example)
    assert example == build_trace("patient-wing").as_dict()


def test_human_trace_is_unchanged_and_module_cli_emits_schema_valid_json():
    human = render_trace(build_trace())
    assert "PLACE: clinic/patient-wing" in human
    assert "movement.max_speed: REJECTED (insufficient_proven_bound)" in human
    assert "test: movement.max_speed (speed-bound)" in human
    assert "Admission:\n  ADMITTED" in human
    environment = dict(os.environ, PYTHONPATH=str(ROOT / "reference" / "admission" / "src"))
    data = subprocess.run(
        [sys.executable, "-m", "spp_admission.explain", "--scenario", "reused", "--json"],
        cwd=ROOT, env=environment, check=True, text=True, capture_output=True,
    ).stdout
    Draft202012Validator(_schema()).validate(json.loads(data))
