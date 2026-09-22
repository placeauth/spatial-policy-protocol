# Place-Originated Requirements and Robotics Ontology Interoperability

**Purpose:** Non-normative presentation preparation for an IEEE P1872.3 discussion. SPP is experimental and pre-standardization; SPP 0.1 remains the project's normative specification. This is an interoperability and vocabulary-review discussion, not an adoption proposal or a claim of IEEE endorsement, adoption, or conformance.

## Slide 1 — Why I’m here

**On-slide content**

- **Place-Originated Requirements and Robotics Ontology Interoperability**
- PlaceAuth / Spatial Policy Protocol (SPP): an experimental place-policy project
- SPP 0.1 is normative within the project; ontology mapping is non-normative research
- Objective: identify reusable concepts and terminology needing correction

**Speaker notes:** Thank the group and state the boundary immediately: “I’m not here to propose that P1872.3 adopt SPP. I’m here because SPP has enough vocabulary that it needs review, and I’d rather reuse established concepts than create a parallel vocabulary.” PlaceAuth does not claim IEEE endorsement, P1872.3 adoption, or conformance with IEEE 1872, IEEE 1872.2, DUL, DOLCE, SUMO, or P1872.3. Ask the group to correct terminology and point to existing constructs.

**Approximate speaking time:** 0:45

## Slide 2 — The interoperability problem

**On-slide content**

- A physical environment may impose machine-operational requirements
- Those requirements can cross robot vendors, fleets, planners, applications, and infrastructure
- Example concerns: movement, sensing, data handling, access to infrastructure, human interaction
- More than ordinary geofencing or application-local configuration

**Speaker notes:** The problem is not that a map needs another polygon layer. A governed environment may need to state conditions that apply to an action in a named scope and context, independently of a visiting robot vendor or fleet. A local configuration can solve this in a closed deployment. The interoperability question arises when the place authority, robot operator, planner, and enforcement point are separate. SPP is an experiment in making that policy-facing exchange explicit; it does not establish deployment maturity or replace those systems.

**Approximate speaking time:** 1:00

## Slide 3 — The narrow SPP boundary

**On-slide content / diagram**

```text
PLACE AUTHORITY
        ↓
POLICY: SPACE + ACTION RULES
        ↓
ACTOR + ACTION + CONTEXT
        ↓
PERMIT / DENY / CONDITIONAL
```

- SPP 0.1 asks whether an actor may perform an action in a space under context
- Core inputs: actor, action, hierarchical space, context
- Requirements and admission are separate, experimental reference-layer work
- A policy decision is separate from its enforcement point

**Speaker notes:** This is deliberately a small place-policy boundary, not a universal robotics architecture. In SPP 0.1, a policy authority supplies rules scoped through hierarchical opaque space identifiers. A request supplies actor, action, space, and context; evaluation returns `permit`, `deny`, or `conditional`. Requirements, conformance, evidence, and admission belong to an explicitly experimental reference layer, not this core decision. “Governed scope” is presentation shorthand for the policy applicability scope, not a geometric-region model. A deployment may associate that policy `space` key with an external spatial representation; that mapping is outside the ontology claims made here.

**Approximate speaking time:** 1:00

## Slide 4 — What SPP should not own

**On-slide content**

- Geometry and maps
- Robot identity infrastructure and PKI
- Fleet taxonomy; route, task, and resource planning
- Universal capability ontology
- Physical enforcement and safety certification

**Speaker notes:** These exclusions are as important as the policy model. SPP space IDs are policy keys, not geometry or topology. A deployment must supply identity, trust, and transport mechanisms. A fleet or planner owns candidate generation, assignment, routes, sequences, and final plan feasibility. The robot runtime, fleet adapter, building controller, or another deployment component owns enforcement. Safety systems remain independently authoritative. Keeping this boundary small reduces accidental semantic duplication and lets SPP exchange place-originated conditions without claiming ownership of the surrounding robotics stack.

**Approximate speaking time:** 1:00

## Slide 5 — Semantic distinctions

**On-slide content**

```text
Requirement ≠ Capability       Capability ≠ Evidence
Evidence ≠ Conformance         Conformance ≠ Admission
Admission ≠ Task Feasibility   Task Feasibility ≠ Enforcement
```

- Working SPP distinctions, not asserted ontology classes
- Requirement: a place-originated, scope-bound condition
- Evidence supports a conclusion; conformance evaluates it against a requirement
- Core policy decision, experimental admission, planning, and enforcement remain distinct

**Speaker notes:** These are working distinctions, not proposed ontology classes. A requirement is not a capability; a capability declaration is not evidence. Evidence supports a conclusion, while conformance evaluates evidence and tests against a requirement. The experimental reference layer can derive an `ADMITTED`, `DEGRADED`, or `DENIED` operating conclusion, but that is distinct from the SPP 0.1 policy decision, safety certification, and task allocation. A planner still evaluates a particular candidate route and sequence; an enforcement point must actually act. “I’m more interested in discovering which SPP concepts we should delete or reuse than in defending every term we currently have.”

**Approximate speaking time:** 1:30

## Slide 6 — Requirement versus affordance

**On-slide content**

- Example: **“Recording is prohibited in this zone.”**
- SPP Core: a place-originated policy constraint
- Experimental admission: may carry an explicit operating restriction
- It does not assert that the place affords recording or that the robot can record
- Questions: existing representation? independent restriction? reusable relation?

**Speaker notes:** This example exposes a possible modeling seam. In SPP Core, it is a place-originated policy constraint: recording must not occur for the relevant action and space. Separately, an experimental admission result can retain a restriction such as disabling recording. Neither statement claims the place affords recording, that the robot can record, or that recording is physically possible. Ask whether established robotics ontology work already separates these ideas, whether restriction should be represented independently of affordance, and whether a reusable relation exists. Do not assume an answer or describe preliminary P1872.3 concepts as finalized semantics.

**Approximate speaking time:** 1:15

## Slide 7 — Policy versus planning

**On-slide content / diagram**

```text
Robot A: route avoids restricted recording region → constraint may not apply
Robot B: route crosses region while recording → candidate conflicts with constraint
Robot B: recording disabled → may satisfy this constraint
```

- **Policy:** “What requirements apply?”
- **Planner:** “Can this candidate satisfy them?”
- “The place declares the constraint. The planner evaluates the candidate.”

**Speaker notes:** The example is conceptual, not a claim about P1872.3 or Open-RMF adoption. The planner needs facts SPP Core does not own: selected subject, initial state, candidate route, task order, active behaviors, resources, and current environment. SPP can supply the place-facing constraint; the planner determines whether a particular candidate meets it and all other constraints. A policy or admission result is not route feasibility, dispatch approval, or physical enforcement.

**Approximate speaking time:** 1:15

## Slide 8 — Questions for P1872.3

**On-slide content**

- Which SPP concepts should reuse existing representations or disappear?
- Is a place-originated requirement a class, relation, or profile over an existing construct?
- How should admission remain distinct from capability, permission, certification, and feasibility?
- Which concerns belong in an ontology, versus a policy, profile, or planner?

**Speaker notes:** Close with an invitation to critique, not adoption. Ask for established terms and relations around applicability, affordance, capability, constraint or requirement, evidence, conformance, permission, feasibility, and spatial or environmental context. Ask which distinctions are worth preserving, which are redundant, and what belongs in a profile or deployment rather than an ontology. The next step is not changing SPP in this meeting; it is documenting corrections and deciding whether further non-normative research is justified.

**Approximate speaking time:** 1:30

**Estimated total:** approximately 9 minutes 15 seconds.
