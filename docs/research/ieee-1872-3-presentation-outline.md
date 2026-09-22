# Place-Originated Requirements and Robotics Ontology Interoperability

**Purpose:** Non-normative presentation preparation for an IEEE P1872.3 discussion. SPP is experimental and pre-standardization; SPP 0.1 remains the project's normative specification. This is an interoperability and vocabulary-review discussion, not an adoption proposal or a claim of IEEE endorsement, adoption, or conformance.

## Slide 1 — Why I’m here

**On-slide content**

- **Place-Originated Requirements and Robotics Ontology Interoperability**
- PlaceAuth / Spatial Policy Protocol (SPP): an experimental place-policy project
- SPP 0.1 is normative within the project; ontology mapping is non-normative research
- Objective: reuse and critique established concepts, not propose adoption

**Speaker notes:** Thank the group and state the boundary immediately: “I’m not here to propose that P1872.3 adopt SPP. I’m here because SPP has reached a point where ontology alignment matters, and I’d rather reuse established concepts than accidentally create a parallel vocabulary.” PlaceAuth does not claim IEEE endorsement, P1872.3 adoption, or conformance with IEEE 1872, IEEE 1872.2, DUL, DOLCE, SUMO, or P1872.3. Ask the group to correct terminology and point to existing constructs.

**Approximate speaking time:** 0:55

## Slide 2 — The interoperability problem

**On-slide content**

- A physical environment may impose machine-operational requirements
- Those requirements can cross robot vendors, fleets, planners, applications, and infrastructure
- Example concerns: movement, sensing, data handling, access to infrastructure, human interaction
- More than ordinary geofencing or application-local configuration

**Speaker notes:** The problem is not that a map needs another polygon layer. A governed environment may need to state conditions that apply to an action in a named scope and context, independently of a visiting robot vendor or fleet. A local configuration can solve this in a closed deployment. The interoperability question arises when the place authority, robot operator, planner, and enforcement point are separate. SPP is an experiment in making that policy-facing exchange explicit; it does not establish deployment maturity or replace those systems.

**Approximate speaking time:** 1:05

## Slide 3 — The narrow SPP boundary

**On-slide content / diagram**

```text
PLACE AUTHORITY
        ↓
GOVERNED SCOPE + REQUIREMENTS
        ↓
SUBJECT + ACTION + CONTEXT
        ↓
PERMIT / DENY / CONDITIONAL
```

- SPP 0.1 asks whether an actor may perform an action in a space under context
- Core inputs: actor, action, hierarchical space, context
- A policy decision is separate from its enforcement point

**Speaker notes:** This is deliberately a small place-policy boundary, not a universal robotics architecture. In SPP 0.1, a policy authority supplies rules scoped through hierarchical opaque space identifiers. A request supplies actor, action, space, and context; evaluation returns `permit`, `deny`, or `conditional`. The core does not say what a robot is, create a world model, or prove an action occurred. “Governed scope” is useful shorthand for the applicability context, but it is not an asserted IEEE ontology mapping and it is more than a geometric region.

**Approximate speaking time:** 1:00

## Slide 4 — What SPP should not own

**On-slide content**

- Geometry and maps
- Robot identity infrastructure and PKI
- Fleet taxonomy; route, task, and resource planning
- Universal capability ontology
- Physical enforcement and safety certification

**Speaker notes:** These exclusions are as important as the policy model. SPP space IDs are policy keys, not geometry or topology. A deployment must supply identity, trust, and transport mechanisms. A fleet or planner owns candidate generation, assignment, routes, sequences, and final plan feasibility. The robot runtime, fleet adapter, building controller, or another deployment component owns enforcement. Safety systems remain independently authoritative. Keeping this boundary small reduces accidental semantic duplication and lets SPP exchange place-originated conditions without claiming ownership of the surrounding robotics stack.

**Approximate speaking time:** 0:55

## Slide 5 — Semantic distinctions

**On-slide content**

```text
Requirement ≠ Capability ≠ Evidence ≠ Conformance
              ≠ Admission ≠ Task Feasibility ≠ Enforcement
```

- Requirement: a place-originated, scope-bound condition
- Capability: what a subject may be able to do
- Evidence / conformance: support and conclusion about satisfying a requirement
- Admission / feasibility / enforcement: successive, distinct operational questions

**Speaker notes:** A requirement is not a capability. A capability declaration is not evidence. Evidence is information supporting a conclusion; conformance is the relation or conclusion produced by evaluating it. The experimental reference admission layer then produces a scoped `ADMITTED`, `DEGRADED`, or `DENIED` operating conclusion with guarantees, restrictions, unresolved requirements, and reasons. That is not permission under SPP 0.1, safety certification, or task allocation. A planner still decides whether a particular route and task sequence can satisfy all constraints, and an enforcement point must actually block or permit behavior. “I’m more interested in discovering which SPP concepts we should delete or reuse than in defending every term we currently have.”

**Approximate speaking time:** 1:25

## Slide 6 — Requirement versus affordance

**On-slide content**

- Example: **“Recording is prohibited in this zone.”**
- SPP currently treats this as a place-originated requirement / restriction
- It does not assert that the place affords recording or that the robot can record
- Questions: existing representation? independent restriction? reusable relation?

**Speaker notes:** This example is intended to expose a possible modeling seam. The statement is normative: the place says what must not happen in the governed scope. It is not a claim about physical possibility, function, or subject-environment interaction. A robot might have recording capability; it might lack it; the environment might make recording useful or possible. Those facts may matter to a candidate plan, but none changes the meaning of the place restriction. Ask whether IEEE robotics ontology work already models this distinction cleanly, whether a restriction should be represented independently of affordance, and whether there is an existing relation SPP should reuse. Do not assume an answer or describe preliminary P1872.3 concepts as finalized semantics.

**Approximate speaking time:** 1:05

## Slide 7 — Policy versus planning

**On-slide content / diagram**

```text
Robot A: route avoids restricted recording region → candidate may remain feasible
Robot B: route crosses region while recording → candidate is infeasible
Robot B: recording disabled → candidate becomes potentially feasible
```

- **Policy:** “What requirements apply?”
- **Planner:** “Can this candidate satisfy them?”
- “The place declares the constraint. The planner evaluates the candidate.”

**Speaker notes:** The example is conceptual, not a claim about P1872.3 or Open-RMF adoption. The planner needs facts SPP Core does not own: selected subject, initial state, candidate route, task order, active behaviors, resources, and current environment. SPP can express or supply the place-facing constraint; a planner determines whether the particular candidate avoids the scope, crosses it while recording, or can satisfy a restriction such as disabling recording. A positive policy or admission result must not be misrepresented as route feasibility, dispatch approval, or physical enforcement.

**Approximate speaking time:** 1:10

## Slide 8 — Questions for P1872.3

**On-slide content**

- Which concepts already have appropriate representations, and which should collapse into them?
- Are place-originated operational requirements best a class, relation, or existing construct?
- How should scoped admission remain distinct from capability, permission, certification, and task feasibility?
- How should candidate feasibility depend on subject state, place constraints, and planned actions?
- Where is SPP conflating concepts; which gaps are ontology gaps versus profile concerns?

**Speaker notes:** Close with an invitation to critique, not adoption. Ask for established terms and relations, especially around applicability, affordance, capability, constraint or requirement, evidence, conformance, permission, feasibility, and spatial or environmental context. Ask which distinctions are useful enough to preserve, which are redundant, and what should remain profile- or deployment-level rather than ontology-level. The next step is not changing SPP in this meeting; it is documenting corrections and deciding whether any future non-normative ontology work is justified.

**Approximate speaking time:** 1:05

**Estimated total:** approximately 8 minutes 40 seconds, leaving time for interruption or discussion in an 8–10 minute slot.
