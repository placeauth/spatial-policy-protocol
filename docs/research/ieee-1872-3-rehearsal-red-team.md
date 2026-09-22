# IEEE P1872.3 Presentation Rehearsal Red Team

**Purpose:** Skeptical rehearsal material for a non-normative discussion. It is not a proposed ontology, an adoption request, or a claim about finalized P1872.3 semantics.

# Red-Team Findings

1. **Slide 5 risked presenting a chain of settled ontology distinctions.** The compact inequality chain made the terms appear to be a single pipeline and partially grouped evidence with conformance. It now presents separate working distinctions and says explicitly that they are not asserted ontology classes.
2. **Slide 6 conflated a Core policy constraint with an experimental admission restriction.** “Recording is prohibited” belongs to the Core place-policy example; a restriction can instead be carried by a degraded experimental admission result. The revised wording keeps those layers separate and does not treat either as an affordance.
3. **“Governed scope” could be mistaken for a spatial region.** The presentation now identifies it as research shorthand for applicability context and repeats that SPP `space` is an opaque hierarchical policy key, not geometry.
4. **The original timing encouraged a fast close.** Slide 8 now has 90 seconds and the script cuts repeated boundary explanations, so the ontology questions receive more time than implementation background.
5. **The main unresolved terminology remains real.** `place`, `space`, `environment`, `governed scope`, `admission`, and `restriction` should be treated as review targets. The current mapping establishes no exact IEEE equivalence for them.

# Likely Hard Questions

## 1. Isn’t SPP simply authorization or ABAC with spatial context?

**Why the question is legitimate:** SPP 0.1 evaluates an actor, action, space, and context and returns a policy decision. Those are recognizable authorization-like elements.

**Response anchor:** SPP Core is deliberately a narrow place-policy decision and may be implementable with an authorization-oriented mechanism. The question for this discussion is not whether SPP replaces ABAC, but whether the place, scope, action, and context distinctions reuse existing ontology terms cleanly. The experimental evidence and admission work is separate from the Core decision.

**Do not claim:** That SPP is categorically unlike authorization, that ABAC cannot model it, or that an ontology is required for SPP to function.

## 2. Why is a place-originated requirement not just an affordance or environmental constraint?

**Why the question is legitimate:** A condition involving a subject, place state, and possible action can look similar to an affordance or environmental constraint.

**Response anchor:** In current SPP usage, a place-originated requirement is a normative policy condition about what must or must not occur. An affordance-like relation may concern what is physically or functionally possible for a subject in an environment and state. The mapping work has not established how P1872.3 represents either relation, so it asks whether existing terms can express the distinction.

**Do not claim:** That affordance has a settled P1872.3 meaning, that SPP requirements are an ontology-wide replacement for affordances, or that the two can never be related.

## 3. Why does admission need to exist separately from permission or capability?

**Why the question is legitimate:** “Admission” can sound like access permission, while a positive result can sound like evidence of capability.

**Response anchor:** In the experimental reference layer, admission is a place-specific conclusion about demonstrated operating guarantees under current scope, bindings, evidence, and lifecycle inputs. It is not the Core `permit` / `deny` / `conditional` decision, a general capability statement, certification, or task allocation. Whether this distinct conclusion needs its own ontology term remains open.

**Do not claim:** That admission is a finalized protocol-wide concept, a security credential, safety certification, or a reason to introduce a new class.

## 4. Why represent evidence and conformance in an ontology instead of implementation metadata?

**Why the question is legitimate:** Evidence provenance, signatures, test records, and freshness may be better represented as implementation or security metadata.

**Response anchor:** SPP does not currently require ontology representation for evidence or conformance. The research question is whether an established information, provenance, or evaluation pattern would clarify the relation among a requirement, a test, an evidence result, and a conclusion. If not, these may remain profile or implementation concerns.

**Do not claim:** That an ontology can prove evidence is true, substitute for issuer trust, or require OWL/RDF in an SPP deployment.

## 5. How is governed scope different from an ordinary spatial region?

**Why the question is legitimate:** “Scope” may be heard as a location, and SPP spaces are often given human-readable spatial names.

**Response anchor:** SPP 0.1 `space` is a hierarchical, opaque policy key; it does not encode geometry, topology, or containment. The research shorthand “governed scope” additionally concerns applicability to a place/space and may include actor, action, policy, evidence, or time. The current mapping has no confident external equivalent.

**Do not claim:** That governed scope is an established ontology class, that SPP space IDs identify physical regions, or that the current model resolves place, authority, and environment ambiguity.

## 6. Does SPP need ontology terms, or only a profile over existing terms?

**Why the question is legitimate:** A new vocabulary is costly, and the mapping work found no verified direct reuse among the examined concepts.

**Response anchor:** A profile over existing terms may be the better result. The purpose of the meeting is to learn whether the distinctions can be expressed with existing concepts and relations, and which remaining semantics are only deployment-profile details. No SPP ontology module or dependency is proposed here.

**Do not claim:** That a perceived gap requires a new SPP class, that the public-source review proves absence from IEEE work, or that SPP is competing with an ontology.

## 7. Who decides whether a candidate route satisfies a place requirement?

**Why the question is legitimate:** Route feasibility depends on a candidate robot, route, ordering, state, resources, and changing environment—not merely a place policy.

**Response anchor:** The place declares its policy constraint; a planner or deployment evaluates whether its candidate can satisfy that constraint together with its other constraints. SPP Core does not generate routes, select a robot, or make a final feasibility decision. An experimental admission result also must not be treated as a route-feasibility conclusion.

**Do not claim:** That SPP owns planning, that a policy decision certifies a route, or that an external planner has adopted a particular integration pattern.

## 8. What happens when requirements conflict across overlapping scopes?

**Why the question is legitimate:** A place may contain overlapping physical areas, multiple authorities, or conflicting policy sources.

**Response anchor:** SPP 0.1 defines inheritance through an explicit parent graph for policy spaces and a nearest matching rule; it does not define geometric overlap, multi-authority composition, or merge semantics. Those are limitations to acknowledge, not gaps this presentation resolves. A future ontology or policy-language discussion would need to distinguish those concerns.

**Do not claim:** That hierarchy solves physical overlap, that SPP already has conflict-resolution semantics for multiple authorities, or that P1872.3 should solve policy composition.

## 9. Why is this a robotics ontology problem rather than a policy-language problem?

**Why the question is legitimate:** The Core problem is policy evaluation, while many terms under discussion concern robots and environments.

**Response anchor:** It may primarily be a policy-language problem. The ontology question arises only where SPP refers to robots, environments, actions, capabilities, or subject-place-state relationships that need shared meaning across systems. The meeting should help separate ontology-reuse opportunities from policy syntax and deployment design.

**Do not claim:** That ontology alignment is necessary for every policy deployment or that P1872.3 must absorb SPP policy semantics.

## 10. Which SPP terms would you remove if IEEE already models them?

**Why the question is legitimate:** A request for interoperability should include willingness to eliminate redundant vocabulary.

**Response anchor:** For a physical robot, SPP should reuse established robot terminology rather than maintain a competing taxonomy. The group’s strongest value is identifying whether concepts such as environment, capability, applicability, evidence support, or a context pattern can be reused or profiled. “Admission,” “governed scope,” and “restriction” are candidates for review, not terms being defended as permanent.

**Do not claim:** That a same-sounding term is semantically equivalent, that a mapping has been verified during the meeting, or that SPP will change without separate review.

# Presentation Failure Modes

## 1. Reaching the ontology questions too late

**Corrective behavior:** Keep Slides 1–4 to their stated times. Use the Core boundary only to establish what is and is not being discussed, then move directly to the distinctions and questions.

## 2. Explaining implementation mechanics instead of semantics

**Corrective behavior:** Do not discuss schemas, hashes, signatures, adapters, or demos unless a question specifically requires an example. Return to requirement, capability, evidence, conformance, admission, feasibility, and enforcement as separate concerns.

## 3. Defending SPP terminology unnecessarily

**Corrective behavior:** Say that the distinctions are working hypotheses and ask which terms should be reused, profiled, or removed. Do not argue that a new name is valuable merely because it exists in the repository.

## 4. Confusing Core permission with experimental admission

**Corrective behavior:** Name the two decision families explicitly: Core `permit` / `deny` / `conditional`; experimental `ADMITTED` / `DEGRADED` / `DENIED`. Never call one a synonym for the other.

## 5. Treating affordance as resolved by SPP

**Corrective behavior:** Use the recording example only to distinguish a policy constraint from claims about physical or functional possibility. Ask whether an existing affordance relation applies; do not supply an IEEE answer.

## 6. Drifting into planner or Open-RMF architecture

**Corrective behavior:** State once that the planner evaluates candidate feasibility and SPP does not own it. Avoid route APIs, fleet architecture, or claims about external integration unless asked.

## 7. Sounding as though PlaceAuth seeks adoption

**Corrective behavior:** Open and close with the correction-and-reuse objective. Frame every proposed relation as a question, candidate, or profile possibility—not as a request for P1872.3 action.

## 8. Answering preliminary P1872.3 questions as finalized semantics

**Corrective behavior:** Ask for the authoritative working-group artifact and defer to participants’ terminology. State that the repository review did not verify a public finalized definition suitable for mapping.
