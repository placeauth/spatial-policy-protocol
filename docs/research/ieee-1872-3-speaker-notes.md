# IEEE P1872.3 Discussion Speaker Notes

**Status:** Non-normative meeting preparation. SPP is experimental and pre-standardization. SPP 0.1 remains normative within the project; the ontology mapping research does not change it.

## Slide 1 — Why I’m here

Thanks for having me. I’m here from PlaceAuth, which is working on the Spatial Policy Protocol, or SPP. The narrow problem we are exploring is how a physical place can communicate machine-operational requirements to autonomous systems operating there.

I want to set the boundary clearly at the start. I’m not here to propose that P1872.3 adopt SPP. I’m here because SPP has enough vocabulary that it needs review, and I would rather reuse established concepts than create a parallel vocabulary.

SPP is experimental and pre-standardization. Within the project, SPP 0.1 is the normative policy specification. The conformance, evidence, admission, lifecycle, planner-aware, and ontology-mapping material is research or reference work around that core. PlaceAuth does not claim IEEE endorsement, P1872.3 adoption, or conformance with IEEE 1872, IEEE 1872.2, DUL, DOLCE, SUMO, or P1872.3.

So I am asking for correction. If the terminology is redundant, poorly separated, or already represented by a better-established concept, that is useful feedback.

## Slide 2 — The interoperability problem

The motivating problem is simple to state: a physical environment may need to communicate machine-operational requirements. Think of a hospital room, a warehouse aisle, a secure area, or a loading zone. The requirements might concern movement, sensing, data retention, use of a door or elevator, or a human interaction.

The place authority, robot vendor, fleet operator, planner, application, and facility infrastructure may not be the same system or organization. In a closed deployment, ordinary geofencing or application-specific configuration may be sufficient.

The interoperability question appears when a place wants to express a condition without assuming one robot vendor, fleet stack, or application owns its meaning. SPP is an experiment in making that exchange explicit; it does not claim deployment maturity or sufficiency on its own.

That brings me to the small boundary SPP is trying to keep.

## Slide 3 — The narrow SPP boundary

SPP 0.1 starts with a policy question: may an actor perform an action in a space under a supplied context?

The place authority authors policy. The request brings together an actor, an action, a named space, and context. The decision is `permit`, `deny`, or `conditional`. A conditional outcome is not a weak permit; the action remains blocked until its stated conditions are satisfied and the request is evaluated again.

The diagram deliberately shows the SPP 0.1 core: policy, space, actor, action, and context. Requirements, evidence, conformance, and admission are separate experimental reference-layer work. “Governed scope” is research shorthand for an applicability context that can include place and space, and sometimes action, actor, policy, evidence, or time. It is not a claimed ontology mapping or merely a geometric region.

Also, SPP 0.1 space identifiers are hierarchical policy keys. They are opaque strings with explicit parent relationships. They do not represent geometry, topology, maps, or a complete physical-world model. A deployment may associate a policy `space` key with an external spatial representation, but that mapping is outside the ontology claims in this presentation.

Most importantly, a policy decision is separate from enforcement. The decision point evaluates the rule; a robot runtime, fleet adapter, building controller, or other deployment component has to prevent or allow the real action.

That division motivates the exclusions on the next slide.

## Slide 4 — What SPP should not own

It should not own geometry or maps. It should not become robot identity infrastructure, a PKI, a fleet taxonomy, a task model, a route planner, or a universal capability ontology. It should not claim to certify safety. And it cannot itself physically enforce anything.

These are different authorities and semantic domains. A deployment supplies identity, trust, transport, localization, and authentication. A fleet or planner generates candidates, assigns robots, builds routes and sequences, and decides whether a task fits. A runtime or facility control is responsible for enforcement. Safety systems remain independently authoritative and can override an SPP permit.

The benefit of holding the line is that a place can state a condition without SPP claiming to model the entire robot, the environment, or the planner. The cost is that the boundaries have to be named accurately. That is the semantic issue I most want help with.

## Slide 5 — Semantic distinctions

These are working distinctions, not proposed ontology classes.

A requirement is a place-originated, scope-bound condition; it is not a claim about what a robot can do. A capability is what a subject may be able to do, but a declaration is not evidence that it currently meets a requirement.

Evidence is information supporting a conclusion, such as a test result bound to relevant actor, build, controller, environment, plan, and challenge state. Conformance is the evaluation of that evidence and tests against a requirement. Neither is the capability.

The experimental reference layer can derive an `ADMITTED`, `DEGRADED`, or `DENIED` profile with guarantees, restrictions, unresolved requirements, and reasons. Admission is a scoped operating conclusion, not the SPP 0.1 policy decision, safety certification, or task allocation.

A planner still decides whether a selected robot, current state, route, task order, resources, and place constraints are jointly satisfiable. Enforcement is a separate runtime or facility responsibility.

I’m more interested in discovering which SPP concepts we should delete or reuse than in defending every term we currently have. If this chain contains distinctions that an established ontology already expresses better, I want to know that.

## Slide 6 — Requirement versus affordance

Here is one concrete test case: “Recording is prohibited in this zone.”

In SPP Core, that is a place-originated policy constraint: recording must not occur for the relevant action and space. Separately, an experimental admission result can retain an explicit operating restriction, such as disabling recording.

Neither statement says the place affords recording, the robot can record, or recording is physically possible. Those may matter to a candidate plan, but they are different claims.

The current mapping research does not assert a P1872.3 affordance definition or relation. The questions are therefore genuine: is this distinction already modeled cleanly? Should restriction be independent from affordance? Is there a reusable relation?

I would welcome a correction if the example misses an established modeling pattern.

## Slide 7 — Policy versus planning

The next distinction is policy versus planning.

Suppose Robot A has a candidate route that avoids a restricted recording region. That constraint may not apply to the candidate.

Robot B crosses the same region while recording. The candidate conflicts with the stated constraint. If recording is disabled, the candidate may satisfy this constraint, but still needs to satisfy all others.

The shorthand is: policy asks, “What requirements apply?” The planner asks, “Can this candidate satisfy them?” The place declares the constraint. The planner evaluates the candidate.

This is a conceptual boundary, not a claim about P1872.3 or Open-RMF adoption. The planner needs inputs SPP Core does not own: selected robot, initial state, route, task sequence, active behaviors, resources, and current environment. A policy or admission result is not route feasibility, dispatch approval, or physical enforcement.

An affordance-related relation may be relevant here: a subject, environment state, and action or capability may jointly determine what is possible. The place restriction asks a different question about what is allowed.

## Slide 8 — Questions for P1872.3

I’ll close with the questions I hope will make this useful.

Which SPP concepts already have appropriate representations, and which should disappear into them? Is a place-originated requirement a class, relation, or profile over an existing construct?

How should scoped admission remain distinct from capability, permission, certification, and task feasibility? For candidate routes or tasks, what belongs in an ontology versus a policy, profile, or planner interface?

Where do you see conceptual conflation in SPP today? I am especially interested in terms or relations SPP should stop using before they harden into unnecessary vocabulary.

The short version is: I’m trying to determine which concepts SPP should reuse, which distinctions are actually useful, and which terms we should remove before they harden into unnecessary vocabulary. Criticism and pointers to established concepts are the desired outcome; adoption is not the ask.
