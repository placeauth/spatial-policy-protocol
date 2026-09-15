from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference" / "admission" / "src"))
sys.path.insert(0, str(ROOT / "sandbox" / "app"))

from sandbox_app import app  # noqa: E402


client = TestClient(app)


def verify(name: str) -> dict:
    response = client.post("/verify", json={"scenario": name})
    assert response.status_code == 200, response.text
    return response.json()


def test_health_and_about_keep_the_status_boundary_explicit() -> None:
    assert client.get("/health").json()["spp_version"] == "0.1"
    about = client.get("/about").json()
    assert "non-normative" in about["normative_status"]
    assert "production deployment" in about["non_goals"]


def test_examples_are_discoverable() -> None:
    names = {item["name"] for item in client.get("/examples").json()}
    assert names == {"admitted", "degraded", "denied", "expired", "tampered", "missing-restriction-ack", "changed-subject"}
    assert client.get("/examples/admitted").json()["request"] == {"scenario": "admitted"}


def test_admitted_is_reliable_without_restriction_acknowledgement() -> None:
    result = verify("admitted")
    assert result["profile"]["status"] == "ADMITTED"
    assert result["reliability"] == "RELIABLE_ADMITTED"
    assert result["verification"]["restriction_acknowledgement"]["outcome"] == "NOT_REQUIRED"


def test_lifecycle_current_degraded_fixture_requires_an_exact_local_acknowledgement_and_mapping() -> None:
    result = verify("degraded")
    assert result["profile"]["status"] == "DEGRADED"
    assert result["reliability"] == "RELIABLE_DEGRADED"
    assert result["verification"]["restriction_acknowledgement"]["outcome"] == "ACKNOWLEDGED"
    assert result["verification"]["lifecycle"]["status"] == "VALID"


def test_denied_expired_and_changed_subject_are_blocked() -> None:
    for name in ("denied", "expired", "changed-subject"):
        result = verify(name)
        assert result["reliability"] == "BLOCKED"
        assert result["profile"]["status"] == "DENIED"


def test_tampered_evidence_fails_signature_verification() -> None:
    result = verify("tampered")
    assert result["reliability"] == "BLOCKED"
    assert result["verification"]["evidence_signature"]["verified"] is False
    assert result["verification"]["evidence_signature"]["reason"] == "signed_payload_digest_mismatch"


def test_missing_restriction_acknowledgement_fails_closed() -> None:
    result = verify("missing-restriction-ack")
    acknowledgement = result["verification"]["restriction_acknowledgement"]
    assert result["profile"]["status"] == "DEGRADED"
    assert result["reliability"] == "BLOCKED"
    assert acknowledgement["outcome"] == "BLOCKED"
    assert "restriction_acknowledgement_missing" in acknowledgement["reasons"]


def test_evaluate_exposes_the_existing_admission_profile_only() -> None:
    response = client.post("/evaluate", json={"scenario": "degraded"})
    assert response.status_code == 200
    assert response.json()["admission"] == "DEGRADED"
    assert "verification" not in response.json()
