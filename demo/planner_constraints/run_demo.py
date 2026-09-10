"""Show why a location-sensitive policy can require candidate-plan context."""
from __future__ import annotations

from model import (
    BehaviorSuppression,
    CandidatePlan,
    ScopeRule,
    SpatialPolicy,
    evaluate_candidate_plan,
)


TASK = "navigate_to_B_while_recording"
POLICY = SpatialPolicy({
    "west": ScopeRule("west"),
    "north": ScopeRule("north"),
    "south": ScopeRule("south"),
    "restricted_zone": ScopeRule("restricted_zone", frozenset({"recording"})),
    "destination_b": ScopeRule("destination_b"),
})
RECORDING_SUPPRESSION = "camera_recording_suppression"


def cases() -> tuple[tuple[str, CandidatePlan, frozenset[str]], ...]:
    return (
        ("Robot A", CandidatePlan(TASK, "robot:a", "west", ("west", "north", "destination_b"), frozenset({"recording"})), frozenset()),
        ("Robot B", CandidatePlan(TASK, "robot:b", "south", ("south", "restricted_zone", "destination_b"), frozenset({"recording"})), frozenset()),
        ("Robot B / restricted execution", CandidatePlan(
            TASK, "robot:b", "south", ("south", "restricted_zone", "destination_b"),
            frozenset({"recording"}),
            (BehaviorSuppression("restricted_zone", "recording", RECORDING_SUPPRESSION),),
        ), frozenset({RECORDING_SUPPRESSION})),
    )


def _show(label: str, plan: CandidatePlan, mappings: frozenset[str]) -> None:
    result = evaluate_candidate_plan(POLICY, plan, enforceable_mappings=mappings)
    print(f"\n{label}")
    print(f"Start: {plan.initial_scope}")
    print(f"Route: {' -> '.join(plan.route or ()) or 'unknown'}")
    print("Recording active: yes" if "recording" in plan.active_behaviors else "Recording active: no")
    print("Restricted recording scopes crossed: " + (", ".join(result.restricted_scopes) or "none"))
    if plan.suppressions:
        suppression = plan.suppressions[0]
        mapped = suppression.enforcement_id in mappings
        print(f"Recording disabled in {suppression.scope}: {'yes' if mapped else 'no'}")
        print(f"Enforcement mapping: {suppression.enforcement_id} ({'present' if mapped else 'missing'})")
    if result.restrictions:
        print(f"Restrictions: {', '.join(result.restrictions)}")
    if result.reasons:
        print(f"Why: {', '.join(result.reasons)}")
    print(f"Result: {result.status}")


def main() -> None:
    print(f"Task: {TASK}")
    for label, plan, mappings in cases():
        _show(label, plan, mappings)
    print("\nThis is a deterministic planner-side spike; it does not generate routes, order tasks, or call Open-RMF.")


if __name__ == "__main__":
    main()
