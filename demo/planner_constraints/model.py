"""Tiny, deterministic candidate-plan constraint spike; not SPP protocol code."""
from __future__ import annotations

from dataclasses import dataclass


FEASIBLE = "FEASIBLE"
FEASIBLE_WITH_RESTRICTION = "FEASIBLE_WITH_RESTRICTION"
INFEASIBLE = "INFEASIBLE"


@dataclass(frozen=True)
class ScopeRule:
    """A declarative rule for one named spatial scope in this synthetic model."""

    scope: str
    prohibited_behaviors: frozenset[str] = frozenset()


@dataclass(frozen=True)
class SpatialPolicy:
    """Named scopes stand in for geometry; SPP 0.1 does not define geometry."""

    scopes: dict[str, ScopeRule]


@dataclass(frozen=True)
class BehaviorSuppression:
    """A deployment-declared behavior suppression for one route scope."""

    scope: str
    behavior: str
    enforcement_id: str


@dataclass(frozen=True)
class CandidatePlan:
    task_id: str
    robot_id: str
    initial_scope: str
    route: tuple[str, ...] | None
    active_behaviors: frozenset[str]
    suppressions: tuple[BehaviorSuppression, ...] = ()


@dataclass(frozen=True)
class PlanConstraintResult:
    status: str
    restricted_scopes: tuple[str, ...] = ()
    restrictions: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()


def evaluate_candidate_plan(
    policy: SpatialPolicy,
    plan: CandidatePlan,
    *,
    enforceable_mappings: frozenset[str] = frozenset(),
) -> PlanConstraintResult:
    """Evaluate a supplied candidate plan without generating a route or task order.

    This intentionally fails closed when route/scope data cannot establish policy
    applicability. ``enforceable_mappings`` is deployment configuration, not
    task input: a declared suppression is insufficient without a matching local
    enforcement mapping.
    """
    if not plan.route:
        return PlanConstraintResult(INFEASIBLE, reasons=("missing_route_context",))
    if plan.initial_scope not in policy.scopes:
        return PlanConstraintResult(INFEASIBLE, reasons=("unknown_initial_scope",))
    if plan.route[0] != plan.initial_scope:
        return PlanConstraintResult(INFEASIBLE, reasons=("initial_scope_route_mismatch",))
    unknown_scopes = tuple(scope for scope in plan.route if scope not in policy.scopes)
    if unknown_scopes:
        return PlanConstraintResult(INFEASIBLE, reasons=("unknown_route_scope",))

    declared = {(item.scope, item.behavior): item for item in plan.suppressions}
    restricted: list[str] = []
    restrictions: list[str] = []
    reasons: list[str] = []

    for scope in plan.route:
        rule = policy.scopes[scope]
        for behavior in sorted(plan.active_behaviors & rule.prohibited_behaviors):
            if scope not in restricted:
                restricted.append(scope)
            suppression = declared.get((scope, behavior))
            if suppression is None:
                reasons.append(f"prohibited_behavior:{behavior}@{scope}")
                continue
            if suppression.enforcement_id not in enforceable_mappings:
                reasons.append(f"restriction_not_enforceable:{behavior}@{scope}")
                continue
            restrictions.append(f"{behavior}=disabled@{scope}")

    if reasons:
        return PlanConstraintResult(INFEASIBLE, tuple(restricted), tuple(restrictions), tuple(reasons))
    if restrictions:
        return PlanConstraintResult(FEASIBLE_WITH_RESTRICTION, tuple(restricted), tuple(restrictions))
    return PlanConstraintResult(FEASIBLE, tuple(restricted))
