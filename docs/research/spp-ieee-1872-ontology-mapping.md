# SPP mapping to IEEE 1872 and upper-level ontology concepts

**Status:** Research note. It does not modify normative SPP 0.1, introduce an
ontology dependency, or assert conformance to any ontology or standard.

## Purpose and source discipline

This note examines whether the current PlaceAuth / Spatial Policy Protocol
(SPP) vocabulary can reuse established robotics and upper-level concepts rather
than becoming an isolated vocabulary. It is intentionally a mapping exercise,
not an ontology design, a normative proposal, or a claim that any IEEE working
group has reviewed or endorsed SPP.

The repository is the source of truth for SPP meaning. In particular,
[SPP 0.1](../../spec/SPP-0.1.md) defines the normative place-policy decision
model: whether an actor may perform an action in a space under context. The
[evidence-based admission specification](../../spec/evidence-based-admission.md)
and [evidence-sufficiency guide](../evidence-sufficiency.md) describe an
explicitly experimental reference layer comprising `PlaceRequirementSet`,
`ConformancePlan`, evidence, bindings, and `AdmissionProfile`. The
[Open-RMF architecture note](../design/spp-open-rmf-next-generation.md) is used
only for its stated architecture boundary and its cautions about task planning.

External material was limited to the [IEEE 1872.2-2021 public description](https://standards.ieee.org/ieee/1872.2/7094/),
the public [CORA OWL implementation](https://github.com/srfiorini/IEEE1872-owl),
the [IEEE 1872.2 ontology design pattern](https://github.com/hsu-aut/IndustrialStandard-ODP-IEEE1872-2),
and the [ISO/IEC 21838-3:2023 record](https://www.iso.org/standard/78927.html)
with the [DOLCE maintainers' documentation](https://www.loa.istc.cnr.it/index.php/dolce/).
The implementation aids are not treated as normative standards.

The full IEEE standards were not available locally, so this note does not infer
definitions from labels. The public CORA material identifies `Robot`,
`RoboticSystem`, `RobotGroup`, and `RoboticEnvironment`; the public AuR
implementation discusses functions, executions, interactions, and environment.
That is insufficient to claim every SPP term has an exact IEEE class or
property. DOLCE alignment remains candidate-only, not a conformance claim.

## Current SPP concept inventory

SPP currently has two intentionally different layers.

1. **Normative SPP 0.1 policy.** A policy is anchored in hierarchical `space`
   identifiers. A request names an `actor`, `action`, `space`, and `context`.
   Evaluation yields `permit`, `conditional`, or `deny`; enforcement is
   assigned to a robot, fleet adapter, building controller, or other
   deployment enforcement point. The policy model is spatially scoped but is
   not a general model of geometry, buildings, facilities, robot anatomy, or
   task planning.
2. **Experimental conformance and admission reference layer.** A place-owned
   `PlaceRequirementSet` contains abstract requirements, associated policy and
   environment digests, and a place/space scope. A `ConformancePlan` selects
   adapter-level tests and assurance expectations. An `EvidenceBundle` contains
   resulting evidence and an `EvidenceBinding` makes it applicable to a
   particular actor, build, controller, embodiment, environment, plan, and
   challenge. The resulting `AdmissionProfile` is `ADMITTED`, `DEGRADED`, or
   `DENIED`, with guarantees, unresolved requirements, reasons, and—when
   degraded—explicit restrictions. Lifecycle assessment can return `VALID`,
   `REVALIDATE`, `REQUALIFY`, or `INVALID` when current inputs differ.

Several names therefore carry more than an everyday meaning. `space` is both a
hierarchical policy key and part of a governed scope; it is not defined as a
geometric region. `environment` is represented operationally through data and
digests, not as a world model. `capability` appears in adapters and planning
inputs, while the reference admission conclusion rests on mapped tests and
evidence rather than a universal capability ontology. `admission` is a
place-specific, evidence-backed operating conclusion, not merely access
control or task allocation.

The inventory below includes terms in the requested scope plus terms needed to
make their boundaries legible: policy, action, assurance, and enforcement
point. Counts are classifications of *current SPP meanings*, not counts of
classes in an external ontology.

## Mapping table

The classifications have deliberately narrow meanings:

- **DIRECT REUSE**: the SPP term can denote the established concept without
  adding SPP-specific semantic conditions.
- **SPECIALIZATION**: SPP adds material scope, policy, provenance, or lifecycle
  conditions to a recognizable broader concept.
- **RELATED BUT DISTINCT**: the concepts interact, but substituting one for the
  other would lose meaning or introduce unsupported meaning.
- **POSSIBLE EXTENSION**: a future relation or module may be useful, but the
  present evidence does not justify a normative mapping.
- **NO CONFIDENT MAPPING**: no adequate mapping is supported by the examined
  source material.

| SPP concept | Current SPP meaning | IEEE 1872 / CORA | IEEE 1872.2 | DUL / DOLCE | Classification | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Place | A place identifier used with a space to scope requirements and admission. | `RoboticEnvironment` is related, not equivalent. | Environment is in stated AuR scope. | Candidate physical object, region, or social/organizational context depending on deployment. | RELATED BUT DISTINCT | A hospital, authority, and physical site may be different things; SPP does not separate them. |
| Space | Hierarchical policy location and decision scope. | No verified exact spatial-region mapping in examined CORA artifact. | Public material is insufficient for an exact AuR spatial class. | Candidate region, but geometry/topology are absent from SPP 0.1. | RELATED BUT DISTINCT | Do not equate a string identifier with a physical region. |
| Governed scope | The bound applicability context, including place/space and sometimes action, actor, policy, evidence, or time. | No verified equivalent. | No verified equivalent. | Could be modeled through a situation plus relations, but that is future work. | NO CONFIDENT MAPPING | This is a security and applicability construct, not merely a location. |
| Policy | A place-authored set of action rules with inheritance and obligations. | Outside the verified CORA core classes. | No verified policy model found in public material. | Candidate description/information object. | RELATED BUT DISTINCT | A future information-object mapping would need to preserve authority and scope. |
| PlaceRequirementSet | Place-owned abstract requirements for conformance/admission. | No verified direct class. | Function/environment concepts are adjacent only. | Candidate information object or description. | RELATED BUT DISTINCT | A future mapping would need to preserve provenance, scope, policy and environment digests, and requirement semantics. |
| Requirement | A place demand that can map to an adapter test and may be essential or restricted. | Constraint terminology was not verified. | No verified exact equivalent. | Candidate description/constraint-like information content. | RELATED BUT DISTINCT | A requirement is not a demonstrated capability or a physical quality. |
| Machine / robot | A physical autonomous system may be an SPP actor and evidence subject. | `Robot` is directly reusable only for a narrowed physical-robot subject. | AuR extends robotics concepts for autonomous robots. | Candidate physical object/agent. | RELATED BUT DISTINCT | SPP's generic actor field is broader; a future mapping may reuse `Robot` for the concrete robot case. |
| Autonomous system | A possibly robotic subject operating under place constraints. | `RoboticSystem` is related. | AuR is explicitly an autonomous-robotics ontology. | Candidate agent or system. | RELATED BUT DISTINCT | SPP must not silently classify every software actor as a robot. |
| Embodiment | Build/controller/runtime identity bound to evidence. | Robot parts and systems are adjacent. | Public material is insufficient for this operational identity. | Candidate physical object plus configuration information. | POSSIBLE EXTENSION | SPP uses embodiment as an applicability fingerprint, not merely morphology. |
| Capability | What an adapter or system can potentially do or demonstrate. | No verified capability class in examined CORA artifact. | Public AuR implementation discusses functions provided by robots. | Candidate disposition/function/quality; exact choice needs formal review. | RELATED BUT DISTINCT | SPP should keep evidence of a test distinct from a declaration of capability. |
| Action / action family | Requested operation such as movement, sensing, data, manipulation, infrastructure, or human interaction. | Related to robot behavior, but no exact verified class. | Functions and executions are adjacent. | Candidate event/process. | RELATED BUT DISTINCT | SPP action names are protocol extension points, not a task ontology. |
| Task | A deployment/RMF work item that may invoke SPP evaluation. | No verified task class in examined CORA artifact. | Not established by the examined public material. | Candidate description of an intended process. | RELATED BUT DISTINCT | SPP Core evaluates an action in a space, not a task workflow. |
| Conformance | The relation between requirements, tests, results, and a conclusion. | No verified direct relation. | Functions/executions do not establish conformance semantics. | Candidate relation among description, situation, and information objects. | POSSIBLE EXTENSION | This is a genuine semantic seam worth formalizing only after the evidence model stabilizes. |
| ConformancePlan | Selected tests, bindings, challenge, unresolved guarantees, and assurance target. | No verified direct class. | Adjacent to a functional/test execution plan only. | Candidate information object/description. | RELATED BUT DISTINCT | It is not a robot mission plan or a route plan. |
| Evidence | Result information supporting a requirement conclusion. | No verified evidence model. | No verified trust/provenance model. | Candidate information object about an event/state. | RELATED BUT DISTINCT | Evidence in SPP has applicability, freshness, assurance, and trust conditions. |
| EvidenceBundle | Whole set of evidence results and metadata. | No verified direct class. | No verified direct class. | Candidate composite information object. | RELATED BUT DISTINCT | Bundle integrity alone is not issuer authentication. |
| EvidenceBinding | Fingerprints binding evidence to actor/build/controller/environment/plan/challenge. | No verified equivalent. | No verified equivalent. | Candidate reified relation or information object. | POSSIBLE EXTENSION | It is stronger than a generic association because it determines whether evidence remains applicable. |
| Admission | Place-specific operating conclusion after policy/conformance checks. | No verified equivalent. | No verified equivalent. | Could be represented as a situation or decision information object, but semantics are unsettled. | NO CONFIDENT MAPPING | It must not be collapsed into permission, access control, scheduling, or safety certification. |
| AdmissionProfile | `ADMITTED`, `DEGRADED`, or `DENIED` result with scope, guarantees, restrictions, and reasons. | No verified direct class. | No verified direct class. | Candidate information object describing a decision. | POSSIBLE EXTENSION | Current profile is experimental and not a normative transport contract. |
| Operating profile | The scoped operating conditions a deployment may rely on. | No verified equivalent. | Related to function/capability configuration, not proven equivalent. | Candidate description or information object. | POSSIBLE EXTENSION | Avoid assuming it means a robot configuration profile in external vocabularies. |
| Restriction | Explicit condition retained by a `DEGRADED` profile. | No verified direct class. | No verified direct class. | Candidate constraint in a description. | RELATED BUT DISTINCT | SPP restriction is an operational obligation whose enforceability remains deployment-specific. |
| Lifecycle / revalidation | Deterministic assessment of whether an issued profile remains usable when current state changes. | No verified lifecycle concept. | No verified equivalent. | Candidate process/event plus temporal information. | POSSIBLE EXTENSION | A profile lifecycle is not continuous monitoring or physical attestation. |
| Environment | Current place/system context represented in the reference layer with data and digests. | `RoboticEnvironment` is related. | Environment is stated AuR scope. | Candidate physical/social setting or situation. | RELATED BUT DISTINCT | SPP's environment digest is an integrity/applicability artifact, not the environment itself. |
| Affordance | Not currently a defined SPP object; relevant to capability-place-state analysis. | No affordance class verified in examined CORA material. | No public exact mapping verified. | Candidate relation, but no DOLCE claim is made here. | RELATED BUT DISTINCT | See the dedicated analysis below. |
| Enforcement point | Robot runtime, fleet adapter, building controller, or other component that blocks/allows operation. | Related to robotic system/interface. | Interaction/function execution is adjacent. | Candidate agent or physical system playing an enforcement role. | RELATED BUT DISTINCT | It is an operational responsibility, not proof that enforcement occurred. |
| Assurance level | E0–E4 level assigned to evidence in the reference model. | No verified equivalent. | No verified equivalent. | Could be a quality or information-content classification. | NO CONFIDENT MAPPING | Do not map assurance labels to trust, safety, or certification concepts without a dedicated model. |

This table inventories 26 concepts: 0 `DIRECT REUSE`, 0
`SPECIALIZATION`, 17 `RELATED BUT DISTINCT`, 6 `POSSIBLE EXTENSION`, and 3
`NO CONFIDENT MAPPING`.

## Boundary analysis

The strongest reuse opportunity is not a wholesale replacement of SPP terms
with ontology labels. It is a sharper separation of things that current files
sometimes present together:

- A **physical place/environment** can contain or describe physical regions,
  equipment, people, and organizational authority. An SPP `place` identifier
  currently may stand in for more than one of these. That is operationally
  convenient but ontologically ambiguous.
- A **robot or autonomous system** is a candidate physical agent/system. Its
  type, build, controller, and runtime state are not one concept. SPP's
  evidence binding correctly treats them as separate applicability inputs, but
  does not currently give them stable formal relations.
- A **capability** is not an **evidence result**. A robot may declare a
  capability, execute a test, produce evidence, and still fail a current
  place requirement because the requirement, context, time, or binding differs.
- A **task** is not an SPP **action**. A task can comprise multiple actions,
  paths, resources, states, and timing. SPP 0.1's action-family names should
  not be recast as task classes without a task-model mapping.
- A **requirement** is neither a physical quality nor a capability. It is a
  place-originated, scope-bound condition that may constrain actions, sensing,
  data handling, or evidence assurance.
- **Permission** is SPP 0.1's policy decision. **Admission** is an experimental
  reference conclusion about a particular subject's demonstrated operating
  guarantees. Neither replaces route feasibility, fleet allocation, or
  physical enforcement.

These distinctions support a relation-oriented future model: a place authority
describes requirements; a subject in a particular state is evaluated against
them; evidence supports claims about that state; and an admission result is
issued for a governed scope while its supporting evidence and lifecycle inputs
remain current. That is more defensible than
asserting that `AdmissionProfile` is a kind of capability or that a
`PlaceRequirementSet` is a kind of environment.

## Affordances and SPP

External feedback identified IEEE P1872.3 as relevant to affordances. This
research pass did not locate a public normative P1872.3 artifact or definition
that supports an exact mapping. The analysis therefore uses “affordance” only
in its ordinary architectural sense: a possible action or interaction that
depends on a subject and an environment. It does not assert an IEEE P1872.3
term, relation, or status.

SPP requirements are **not themselves affordances**. A requirement such as
“video capture disabled in operating room 3” is a place-originated normative
condition. It does not state that the room affords video capture, or that the
robot has that capability. Treating it as an affordance would blur what is
allowed with what is physically or functionally possible.

SPP restrictions are likewise **not affordances**. They limit an operating
result; a restriction can require suppression of a capability, a speed ceiling,
or another enforceable condition. The restriction may be relevant to whether a
particular interaction is safe or permitted, but it does not model the
subject-place relation that makes an action possible.

Admission can depend on affordance-like facts without becoming an affordance
model. For example, a robot may be able to traverse a corridor, operate a
door, or maintain a human-separation bound only given a particular embodiment,
controller, current place state, and task path. Those are candidate inputs to
conformance and planner evaluation. The present reference layer validates
mapped requirements against evidence; it does not encode a general relation of
the form “subject affords action in environment under state.”

A future, non-normative ontology module could make that relation explicit if
three conditions hold: (1) an external affordance vocabulary supplies reviewed
semantics; (2) SPP can distinguish physical possibility from policy permission;
and (3) the implementation has stable representations for relevant place and
subject state. Until then, keeping “affordance” out of SPP's normative
vocabulary is preferable. The immediate open question is whether the useful
relation is between a robot capability and a place state, a candidate plan and
a space, or both.

## DUL / DOLCE alignment

DUL/DOLCE is most useful here as a design discipline for separating entities,
processes, information, descriptions, and contexts—not as a label set to paste
onto JSON objects. The following are candidate relationships for future formal
analysis:

| SPP concern | Candidate upper-level reading | Caution |
| --- | --- | --- |
| Robot, controller hardware, building actuator | Physical object; in some cases agent/system | An SPP actor ID is not proof of a physical object or autonomous agent. |
| Place, room, corridor, operating area | Physical setting and/or spatial region | SPP space identifiers do not encode geometry, topology, containment, or ownership. |
| Current machine/place condition | Situation with participating entities and qualities | The reference model uses snapshots/digests, not an explicit situation object. |
| Max speed, controller version, assurance label | Quality or information about a quality | Numeric values and provenance have different semantics; do not conflate them. |
| PlaceRequirementSet and policy | Description/information object | A description need not be authoritative; SPP additionally needs authority and scope. |
| EvidenceBundle, plan, profile, trace | Information objects | Their signatures/digests are technical bindings, not ontological identity conditions. |
| Actor as delivery robot, place authority, enforcement point | Roles played by systems/organizations in a situation | SPP currently does not model role assignment formally. |
| Evaluation, test, revalidation, enforcement | Events/processes | A decision event and later physical enforcement are distinct processes. |

The high-value future relationship is a reified evaluation situation: it could
link a governed space, a subject, an applicable description of requirements,
evidence information, time, and an outcome information object. Such a model
could help explain why a profile is valid only under a particular context.
However, it should remain an ontology-module experiment until SPP has a stable
external admission envelope and a clear distinction between policy identifiers,
physical places, and authorities. ISO/IEC 21838-3:2023 offers a route for
formal conformance work later; this repository has not performed that work.

## Candidate SPP extensions

The following are genuine gaps, not names proposed for immediate normative
classes.

1. **Scope/applicability relation — ontology module candidate.** Existing
   vocabularies observed here do not capture SPP's complete security-relevant
   claim that a result applies to a subject, governed place/space, policy,
   evidence, and time. A relation or reified context would add value by making
   applicability explicit. It should not be added to SPP 0.1 until the
   transport and lifecycle semantics are stable.
2. **Conformance-support relation — ontology module candidate.** A relation
   between a requirement, selected test, evidence result, and conclusion would
   add clarity. Existing information-object vocabulary is too broad to say
   which result supports which requirement under which binding. The current
   implementation data already contains this structure, but it should remain
   implementation documentation for now.
3. **Restriction-enforcement mapping — implementation/documentation first.** A
   `DEGRADED` restriction becomes operationally relevant only when a deployment
   accepts an exact restriction and identifies an enforcement path. An ontology
   relation could describe that mapping, but cannot prove physical enforcement.
   The immediate need is precise implementation documentation, not a normative
   class.
4. **Place-authority relation — future ontology or governance module.** SPP
   has local signed place-requirement support but does not formally model why an
   authority may speak for a place. A formal relation would be valuable only
   with a defined authority/governance model; it is not solved by a general
   “owner” property.
5. **Affordance/candidate-plan relation — P3 research.** A future model could
   link candidate subject, place state, route/sequence, and possible action.
   It belongs outside normative SPP unless planner-facing semantics become an
   actual protocol requirement.

## Terminology risks

- **Place versus environment versus space:** current SPP often needs all three
  intuitions but encodes mostly identifiers and digests. Documentation should
  consistently state whether a term names a physical site, a policy namespace,
  a spatial region, or a state snapshot.
- **Capability versus guarantee/evidence:** a capability declaration, a test
  result, and an admitted guarantee should not be used interchangeably. This is
  the most likely source of a false interoperability claim.
- **Task versus action:** task planners may need route-, order-, and
  candidate-specific information unavailable in an SPP Core action request.
- **Admission versus permission:** policy `permit`/`conditional`/`deny` and
  experimental `ADMITTED`/`DEGRADED`/`DENIED` are different decision families.
  “Admission” also risks suggesting access control or safety certification.
- **Profile:** `AdmissionProfile` and “operating profile” are potentially
  confused with generic robot configuration profiles. The document should keep
  the scope, evidence, and lifecycle qualifiers visible.
- **Restriction:** a free-form or deployment-defined restriction may be
  mistaken for a portable capability taxonomy. It is not one today.

## IEEE 1872.1 note

IEEE 1872.1-2024 is an active standard for robot task representation. Its
public description says it supports representation, reasoning, and
communication of task knowledge, including terms, attributes, structures,
constraints, relationships, and hierarchical planning. That makes a dedicated
future mapping worthwhile because SPP can be queried during task consideration
and candidate-plan evaluation. It does **not** justify importing task semantics
into SPP now: the present SPP Core action model and experimental admission layer
do not define task decomposition, goals, routes, allocation, or planner state.

The appropriate next research step is a narrowly scoped 1872.1 comparison of
task, action, constraint, precondition, outcome, and planner context. It should
test whether place requirements are task constraints, external applicability
conditions, or both. That work should not be combined with this ontology
mapping or treated as a protocol change.

## Questions for IEEE 1872.3 discussion

1. Which published or draft artifact defines the working group's affordance
   term and its intended scope for autonomous robotics?
2. Is an affordance expected to represent physical possibility, functionally
   enabled interaction, policy-permitted interaction, or distinct relations for
   each?
3. How should a model distinguish a robot's capability from an evidence-backed
   claim that the capability currently satisfies a quantified constraint?
4. Is there an established pattern for a place-originated requirement that
   applies across robots, fleets, and planning systems without becoming a robot
   taxonomy property?
5. How should physical region, operational area, facility authority, and policy
   namespace be separated when a deployment calls all of them “place”?
6. Does the affordance work include a recommended representation for dynamic
   place state and candidate-plan-dependent interaction?
7. What existing IEEE ontology relation is most appropriate for a result's
   applicability to a subject, spatial scope, policy version, and time?
8. Should an operational restriction and the configured system that claims to
   enforce it be modeled as separate information and process relations?
9. Are there established modeling patterns for uncertainty, assurance, and
   revocation that avoid equating a signature with truth about physical behavior?

## Recommended SPP actions

### P0 — semantic conflicts that can affect interoperability

1. Define documentation-level distinctions among `place`, `space`,
   `environment`, and `governed scope`; no schema change is required to state
   that current identifiers are not a complete spatial ontology.
2. Preserve the distinction among declared capability, test evidence, admitted
   guarantee, and enforceable restriction in all adapter and integration
   documentation.
3. Avoid presenting `ADMITTED` as a synonym for policy `permit`, task
   feasibility, physical enforcement, or safety certification.

### P1 — clear reuse opportunities

1. Where an SPP actor is a physical robot, use CORA/IEEE robot terminology
   rather than inventing a competing robot taxonomy.
2. In architecture documentation, describe a physical environment and a
   robotic system as external domain concepts while keeping SPP's bindings as
   protocol applicability data.
3. Use an explicit information-object framing for policies, requirements,
   plans, evidence, and profiles in non-normative integration materials.

### P2 — possible future formal alignment

1. Prototype a separate ontology mapping for governed-scope applicability,
   conformance support, and restriction-enforcement relationships after the
   experimental admission envelope and lifecycle boundary stabilize.
2. Conduct the dedicated IEEE 1872.1 task-representation comparison before
   making planner-facing normative claims.
3. Ask the appropriate IEEE group to review the affordance boundary before
   defining any SPP affordance term.

### P3 — interesting but premature work

1. Publish OWL/RDF, import DUL/DOLCE, or require ontology-aware runtimes.
2. Build a universal capability, restriction, place, or facility ontology.
3. Treat an ontology mapping as proof of robot behavior, place authority,
   enforcement, security, or standards adoption.

## Conclusion

No current SPP semantic needs an immediate normative change solely for ontology
alignment. The near-term value is terminological discipline: reuse robotics
terms for actual robots and environments where their meanings fit, and retain
SPP-specific policy, applicability, evidence, and admission semantics where
they add necessary information. A future formal ontology module may be worth
separate, non-normative review after governed-scope and conformance-support
semantics stabilize; it is not a replacement for SPP 0.1.
