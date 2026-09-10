"""Deterministic portable subject-bound revalidation demonstration."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference/admission/src"))
from spp_admission import CurrentEvaluationContext, ReplayRegistry, assess_subject_bound_revalidation, admit, build_evidence, derive_plan, execute_plan, load_requirement_set  # noqa: E402
from spp_admission.models import RobotState  # noqa: E402

NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)

def main():
    req = load_requirement_set(ROOT / "demo/admission/lobby.yaml")
    subject = RobotState("robot-A", "build-A", "controller-A", "demo_mobile_base", req["environment_digest"], {"movement.max_speed": .6})
    plan = derive_plan(req, subject, challenge="nonce:demo-revalidation")
    evidence = build_evidence(req, plan, subject, execute_plan(plan, subject, req), now=NOW)
    profile = admit(req, plan, evidence, subject, ReplayRegistry(), now=NOW)
    def show(label, context, now=NOW):
        result = assess_subject_bound_revalidation(profile, context, now=now)
        print(f"{label}: {result.status} ({', '.join(result.reasons) or 'reuse_valid'})")
        if result.invalidated_guarantees: print("  Refresh: " + ", ".join(result.invalidated_guarantees))
    show("A unchanged", CurrentEvaluationContext(subject, req, evidence))
    show("B evidence expired", CurrentEvaluationContext(subject, req, evidence), NOW + timedelta(minutes=16))
    other = RobotState("robot-B", "build-B", "controller-B", "demo_mobile_base", req["environment_digest"], {"movement.max_speed": .6})
    show("C subject changed", CurrentEvaluationContext(other, req, evidence))
    changed = deepcopy(req); changed["requirements"][0]["value"] = .5
    show("D requirement changed", CurrentEvaluationContext(subject, changed, evidence))

if __name__ == "__main__": main()
