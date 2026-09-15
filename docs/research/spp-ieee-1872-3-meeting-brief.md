# SPP and IEEE 1872.3 — Initial Interoperability Questions

## 1. What SPP is

Spatial Policy Protocol (SPP) is an experimental open protocol for
place-originated machine-operational requirements. It lets a governed physical
environment express requirements applicable to an actor attempting an action
within a named spatial scope and context. The current SPP 0.1 specification
defines a deliberately small place-policy decision: whether an actor may
perform an action in a space under context.

The repository also contains explicitly experimental reference work for
conformance evidence, admission profiles, restrictions, lifecycle and
revalidation, and planner-aware constraints. Those layers explore how a place
requirement might be evaluated against a particular subject, its evidence, and
its operating context. They do not alter SPP 0.1, define a universal robot
model, or prove physical enforcement.

SPP intentionally keeps place-originated requirements separate from robot,
fleet, planner, and facility-control implementation details. This note is not
an IEEE standard, does not claim IEEE endorsement, and does not propose that
IEEE P1872.3 adopt any SPP concept.

## 2. Why ontology alignment matters

An isolated vocabulary would make it harder for robotic systems, planners, and
place authorities to exchange meaning without accidental equivalences. SPP
therefore seeks to reuse established concepts where their semantics actually
fit, while retaining a distinct term where SPP carries additional policy,
scope, evidence, or lifecycle meaning.

IEEE 1872 / CORA, IEEE 1872.2 autonomous-robotics work, and upper-ontology
grounding such as DUL/DOLCE are useful points of comparison. This is a
candidate alignment exercise, not a claim of formal mapping or conformance.
The public material reviewed so far is insufficient to infer exact class or
property equivalences for most SPP concepts.

## 3. Concepts SPP currently needs to distinguish

| Concern | Distinction SPP is preserving |
| --- | --- |
| Autonomous subject / robot | An SPP actor can be broader than a physical robot; a physical-robot case may reuse established robot terminology. |
| Physical place | A physical site, facility, or local authority context; it is not automatically identical to an SPP identifier. |
| Spatial / governed scope | A hierarchical policy space and applicability context; SPP 0.1 does not define geometry. |
| Requirement | A place-originated condition; not a capability, observation, or affordance. |
| Capability | What a subject may be able to do; not proof that it currently satisfies a requirement. |
| Evidence and conformance result | Information supporting a conclusion and the result of evaluating it; neither is the capability itself. |
| Admission / operating profile | An experimental, scoped operating conclusion; not policy permission, safety certification, or task allocation. |
| Restriction | An explicit condition associated with a degraded operating result; its enforcement remains deployment-specific. |
| Task or candidate-plan feasibility | A planner/deployment conclusion involving route, order, state, and resources; it is not an SPP Core decision. |
| Enforcement | The responsibility of a runtime, fleet adapter, or facility control; it is not proved by an admission result. |
| Affordance | A possible subject-environment-state relation, not an SPP requirement or restriction. |

These separations are practical as well as ontological: policy is not
capability; capability is not evidence; evidence is not conformance;
conformance is not admission; admission is not task feasibility; and task
feasibility is not enforcement.

## 4. Affordance question

SPP currently models requirements imposed by a place and evidence or
capabilities relevant to satisfying them. Those requirements are not
affordances. For example, a “no recording” condition in a zone is a
place-originated operational constraint; it does not state that the place
affords recording or that a subject can record.

Admission or candidate-task feasibility may nevertheless depend on facts that
could be represented with affordance-related concepts: a subject, a place or
environment, current state/context, and an available action or capability. It
remains an open interoperability question whether an established P1872.3
pattern could model that relationship without conflating physical possibility,
policy permission, and operational enforcement. This note does not assume a
finalized or publicly stable P1872.3 definition of affordance.

## 5. Questions for the P1872.3 group

1. Is there an existing 1872-family concept suitable for a physically bounded
   governed environment, or should it remain separate from existing
   environment/place concepts?
2. How should place-originated operational constraints relate to robot
   capabilities and affordances without conflating permission with physical
   possibility?
3. How should a scoped admission decision be represented ontologically so that
   it remains distinct from capability, permission, certification, and task
   feasibility?
4. How should evidence supporting a machine/environment compatibility assertion
   be modeled relative to capabilities, observations, and conformance results?
5. How should candidate-task or candidate-route feasibility be modeled when it
   depends jointly on subject state, place-originated constraints, and planned
   actions?
6. Are there established 1872/1872.2 relations that could express the
   applicability of a requirement to a subject within a spatial scope?
7. Which concepts would be inappropriate for SPP to define independently
   because an established IEEE or upper-ontology term should instead be reused?

## 6. Current position

SPP should preferentially reuse established concepts where semantics align.
New SPP-specific ontology terms should exist only where there is a genuine
semantic gap, including possible gaps around governed-scope applicability,
evidence binding, and scoped operating conclusions. The immediate goal is
interoperability and conceptual clarity, not a change to SPP 0.1. Feedback
from the P1872.3 effort may inform a future, separately reviewed ontology
module after experimental admission, trust, and lifecycle semantics stabilize.
