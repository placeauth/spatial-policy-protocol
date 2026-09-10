from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "demo" / "planner_constraints"))

from model import (  # noqa: E402
    FEASIBLE,
    FEASIBLE_WITH_RESTRICTION,
    INFEASIBLE,
    BehaviorSuppression,
    CandidatePlan,
    ScopeRule,
    SpatialPolicy,
    evaluate_candidate_plan,
)


POLICY = SpatialPolicy({
    "west": ScopeRule("west"),
    "south": ScopeRule("south"),
    "restricted_zone": ScopeRule("restricted_zone", frozenset({"recording"})),
    "destination_b": ScopeRule("destination_b"),
})


def plan(robot: str, start: str, route: tuple[str, ...] | None, *, suppressions=()):
    return CandidatePlan("navigate_to_B_while_recording", robot, start, route,
                         frozenset({"recording"}), tuple(suppressions))


def test_same_task_and_different_candidate_routes_produce_different_results():
    unrestricted = plan("robot:a", "west", ("west", "destination_b"))
    restricted = plan("robot:b", "south", ("south", "restricted_zone", "destination_b"))

    assert evaluate_candidate_plan(POLICY, unrestricted).status == FEASIBLE
    assert evaluate_candidate_plan(POLICY, restricted).status == INFEASIBLE


def test_restricted_route_with_active_prohibited_behavior_is_infeasible():
    result = evaluate_candidate_plan(POLICY, plan("robot:b", "south", ("south", "restricted_zone", "destination_b")))

    assert result.status == INFEASIBLE
    assert result.restricted_scopes == ("restricted_zone",)
    assert result.reasons == ("prohibited_behavior:recording@restricted_zone",)


def test_explicit_enforceable_behavior_suppression_allows_restricted_feasibility():
    suppression = BehaviorSuppression("restricted_zone", "recording", "camera_recording_suppression")
    result = evaluate_candidate_plan(
        POLICY, plan("robot:b", "south", ("south", "restricted_zone", "destination_b"), suppressions=(suppression,)),
        enforceable_mappings=frozenset({"camera_recording_suppression"}),
    )

    assert result.status == FEASIBLE_WITH_RESTRICTION
    assert result.restrictions == ("recording=disabled@restricted_zone",)


def test_missing_spatial_context_fails_closed():
    assert evaluate_candidate_plan(POLICY, plan("robot:b", "south", None)).reasons == ("missing_route_context",)
    unknown = plan("robot:b", "south", ("south", "unmapped_scope", "destination_b"))
    assert evaluate_candidate_plan(POLICY, unknown).reasons == ("unknown_route_scope",)


def test_initial_state_must_match_the_candidate_route():
    result = evaluate_candidate_plan(POLICY, plan("robot:b", "south", ("west", "destination_b")))

    assert result.status == INFEASIBLE
    assert result.reasons == ("initial_scope_route_mismatch",)


def test_declared_suppression_without_enforcement_mapping_fails_closed():
    suppression = BehaviorSuppression("restricted_zone", "recording", "missing_mapping")
    result = evaluate_candidate_plan(
        POLICY, plan("robot:b", "south", ("south", "restricted_zone", "destination_b"), suppressions=(suppression,)),
    )

    assert result.status == INFEASIBLE
    assert result.reasons == ("restriction_not_enforceable:recording@restricted_zone",)
