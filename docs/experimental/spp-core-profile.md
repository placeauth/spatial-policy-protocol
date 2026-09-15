# SPP Core Profile

**Status: EXPERIMENTAL and NON-NORMATIVE.** This document does not change SPP
0.1, its schemas, or its normative evaluator. It is a deliberately reduced
interoperability experiment, not a proposal for a new policy engine.

## Purpose

The profile tests whether a place-authorized policy contract can remain useful
when different policy decision points perform evaluation. It deliberately
resembles ABAC/PDP models: that resemblance is expected, not a novelty claim.
The question is whether a constrained place/robotics profile creates useful
interoperability above a general-purpose evaluator.

## Contract

Each profile input contains only:

| Field | Meaning |
| --- | --- |
| `profile.authority.id` | Issuer identifier supplied by the deployment; no identity scheme is implied. |
| `profile.policy_id`, `policy_version` | Place-policy identifiers. |
| `profile.governed_scope` | Opaque or externally resolved authority scope. |
| `request.subject` | Subject fields selected by a rule; no universal identity model. |
| `request.action` | Machine-readable family and name. |
| `request.context` | Structured policy-relevant attributes and verified authorizations. |
| `request.governed_scope` | Scope in which the requested action is evaluated. |
| `scope_chain` | Resolver-supplied nearest-to-root policy scopes and rules. It contains no geometry. |
| `deployment.supported_obligations` | Obligation types the deployment claims it can interpret and enforce. |

Rules reuse the relevant SPP 0.1 shape: action selector, optional subject and
context selectors, `permit`/`deny`/`conditional`, required authorizations, and
obligations. The scope chain is ordered from the requested scope toward the
policy root. The first matching rule wins; within one scope, an exact action
name wins over `*`, then document order applies. This is the current SPP 0.1
inheritance/precedence behavior represented without a geometry model.

The normalized result is exactly:

```json
{"decision":"PERMIT|DENY|CONDITIONAL","obligations":[],"reason_codes":[]}
```

`CONDITIONAL` is not permission. A deployment must re-evaluate after any
required authorization is present. Any required obligation whose type is not
in `deployment.supported_obligations` produces `DENY` with
`required_obligation_unsupported`. That is a fail-closed reliance rule only;
it neither attests a handler nor proves physical enforcement.

## Deliberate exclusions

This Core Profile does not define robot identity, PKI, transport security,
building geometry, map format, fleet taxonomy, planner semantics, route
feasibility, task allocation, capability ontology, evidence generation,
certification, admission profiles, lifecycle, physical enforcement, or safety
guarantees.

SPP MAY eventually standardize authority identification conventions,
governed-scope references, subject/action/context input conventions,
place-originated requirements, deterministic decisions, conditional
obligations, fail-closed handling, and conformance fixtures. It should not
standardize the excluded systems in this Core Profile.

## ABAC/XACML/OPA position

This experiment does not argue that OPA, XACML, or ABAC are inadequate. They
can perform these evaluations. If SPP has a defensible future role, it is the
shared place-authority contract and fixtures—not ownership of the evaluator.
