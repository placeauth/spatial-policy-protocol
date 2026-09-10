# Planner-aware spatial constraints spike

This small, deterministic experiment demonstrates a planner-sensitive case that a task description alone cannot decide:

> Navigate to destination B while recording imagery.

The synthetic place policy says that `recording` is prohibited in the named `restricted_zone`. Robot A's route avoids that scope and is feasible. Robot B's route enters it and is infeasible while recording remains active. The same Robot B route becomes `FEASIBLE_WITH_RESTRICTION` only when recording suppression is explicitly declared and the deployment supplies a matching enforcement mapping.

## Run

From the repository root:

```sh
python demo/planner_constraints/run_demo.py
```

## What this demonstrates

- The same task has different outcomes for different candidate plans.
- Initial robot state, route scopes, active behavior, and an enforceable suppression mapping affect the result.
- Missing route or spatial-scope context fails closed rather than defaulting to feasibility.
- SPP/place policy is represented declaratively. The spike evaluates a supplied route; it does not generate routes, assign robots, sequence tasks, or make an Open-RMF API proposal.

`FEASIBLE_WITH_RESTRICTION` is local spike vocabulary, not an SPP protocol outcome. It is analogous to constrained operation: a deployment must prove and apply the restriction itself. The named scopes are a deterministic stand-in for geometry because SPP 0.1 does not define geometry.

## What this does not demonstrate

This is not an Open-RMF integration, route planner, simulation, geometry engine, safety system, or production enforcement implementation. It does not imply endorsement or adoption by Open-RMF or any maintainer. It is exploratory work motivated by architectural discussion about candidate-plan context.
