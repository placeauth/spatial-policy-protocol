# IEEE P1872.3 Discussion Speaker Notes

**Status:** Non-normative meeting preparation. SPP is experimental and pre-standardization. SPP 0.1 remains normative within the project; the ontology mapping research does not change it.

## Slide 1 — Why I’m here

Thanks for having me. I’m here from PlaceAuth, which is working on the Spatial Policy Protocol, or SPP. The narrow problem we are exploring is how a physical place can communicate machine-operational requirements to autonomous systems operating there.

I want to set the boundary clearly at the start. I’m not here to propose that P1872.3 adopt SPP. I’m here because SPP has reached a point where ontology alignment matters, and I’d rather reuse established concepts than accidentally create a parallel vocabulary.

SPP is experimental and pre-standardization. Within the project, SPP 0.1 is the normative policy specification. The conformance, evidence, admission, lifecycle, planner-aware, and ontology-mapping material is research or reference work around that core. PlaceAuth does not claim IEEE endorsement, P1872.3 adoption, or conformance with IEEE 1872, IEEE 1872.2, DUL, DOLCE, SUMO, or P1872.3.

So I am asking for correction. If the terminology is redundant, poorly separated, or already represented by a better-established concept, that is useful feedback.

## Slide 2 — The interoperability problem

The motivating problem is simple to state: a physical environment may need to communicate machine-operational requirements. Think of a hospital room, a warehouse aisle, a secure area, or a loading zone. The requirements might concern movement, sensing, data retention, use of a door or elevator, or a human interaction.

The difficult part is that the place authority, robot vendor, fleet operator, planner, application, and facility infrastructure may not be the same system or organization. In a closed deployment, ordinary geofencing or an application-specific configuration may be entirely sufficient. We do not want to overstate the need for another layer.

The interoperability question appears when a place wants to express a condition in a way that does not assume one robot vendor, one fleet stack, or one application owns the meaning. SPP is an experiment in making that exchange explicit. It does not claim that the exchange is mature, broadly deployed, or sufficient on its own.

That brings me to the small boundary SPP is trying to keep.

## Slide 3 — The narrow SPP boundary

SPP 0.1 starts with a policy question: may an actor perform an action in a space under a supplied context?

The place authority authors policy. The request brings together a subject or actor, an action, a named space, and context. The decision is `permit`, `deny`, or `conditional`. A conditional outcome is not a weak permit; the action must remain blocked until its stated conditions are satisfied and the request is evaluated again.

The diagram says “governed scope plus requirements.” That is presentation shorthand, not a claimed ontology mapping. In the existing SPP research, governed scope means the applicable context that can include place and space, and sometimes action, actor, policy, evidence, or time. It is not merely a geometric region.

Also, SPP 0.1 space identifiers are hierarchical policy keys. They are opaque strings with explicit parent relationships. They do not represent geometry, topology, maps, or a complete physical-world model.

Most importantly, a policy decision is separate from enforcement. The decision point evaluates the rule; a robot runtime, fleet adapter, building controller, or other deployment component has to prevent or allow the real action.

That division motivates the exclusions on the next slide.

## Slide 4 — What SPP should not own

For interoperability, I think the most useful thing SPP can do is remain narrow.

It should not own geometry or maps. It should not become robot identity infrastructure, a PKI, a fleet taxonomy, a task model, a route planner, or a universal capability ontology. It should not claim to certify safety. And it cannot itself physically enforce anything.

Those are not just implementation omissions. They are different authorities and different semantic domains. A deployment supplies its own identity, trust, transport, localization, and authentication mechanisms. A fleet or planner generates candidates, assigns robots, builds routes and sequences, and decides whether a task actually fits. A runtime or facility control is responsible for enforcement. Safety systems can remain independently authoritative and override an SPP permit.

The benefit of holding the line is that a place can state a condition without SPP claiming to model the entire robot, the environment, or the planner. The cost is that the boundaries have to be named accurately. That is the semantic issue I most want help with.

## Slide 5 — Semantic distinctions

SPP currently preserves a sequence of distinctions that can easily collapse in casual discussion.

First, a requirement is a place-originated, scope-bound condition. It is not a claim about what a robot can do.

A capability is what a subject may be able to do or demonstrate. But a capability declaration is not evidence that the subject currently meets a particular requirement, under this place’s current conditions.

Evidence is information supporting a conclusion: for example, a test result with bindings to relevant actor, build, controller, environment, plan, and challenge state. Conformance is the evaluation or relation between requirements, tests, results, and a conclusion. Evidence is not the conclusion itself, and neither is the capability.

The experimental reference layer then derives an admission profile: `ADMITTED`, `DEGRADED`, or `DENIED`, with guarantees, restrictions, unresolved requirements, and reasons. Admission is a scoped operating conclusion. It is not the SPP 0.1 policy decision, not access control in the general sense, not safety certification, and not task allocation.

Then there is task or route feasibility. A planner may need to decide whether a selected robot, its current state, a route, task order, resources, and applicable place constraints are jointly satisfiable. That is still separate from whether a runtime or facility controller actually enforces the resulting restriction.

I’m more interested in discovering which SPP concepts we should delete or reuse than in defending every term we currently have. If this chain contains distinctions that an established ontology already expresses better, I want to know that.

## Slide 6 — Requirement versus affordance

Here is one concrete test case: “Recording is prohibited in this zone.”

SPP currently treats that as a place-originated requirement, or as an explicit restriction on a degraded operating result. The statement is normative: the place says what must not happen in the governed scope.

It does not say the place affords recording. It does not say the robot is capable of recording. It does not say whether recording is physically possible, useful, safe, or enforceable in that situation. Those might be related facts, and they can matter to a candidate plan, but they are not the same claim.

The current mapping research deliberately does not assert a P1872.3 affordance definition or relation. Public material reviewed in that work was not enough to support one. So the questions are genuine questions: is this distinction already modeled cleanly in IEEE robotics ontology work? Should a restriction be independently represented from affordance? Is there an existing relation that a future SPP-oriented profile should reuse?

I would welcome a correction if the example misses an established modeling pattern.

## Slide 7 — Policy versus planning

The next distinction is policy versus planning.

Suppose Robot A has a candidate route that avoids a restricted recording region. Its candidate may remain feasible, subject to all the other planning constraints.

Robot B has a candidate route that crosses the same region while recording. That candidate is infeasible under the place requirement.

If Robot B disables recording, the candidate becomes potentially feasible. Potentially is important: it still needs to satisfy every other route, resource, safety, authorization, and enforcement condition.

The shorthand is: policy asks, “What requirements apply?” The planner asks, “Can this candidate satisfy them?” The place declares the constraint. The planner evaluates the candidate.

This is only a conceptual boundary. It does not claim that P1872.3 or Open-RMF has adopted it. The planner needs inputs that SPP Core does not own: selected robot identity, initial state, route, task sequence, active behaviors, resources, and current environment. A policy or admission result must not be promoted into a promise of route feasibility, dispatch approval, or physical enforcement.

This boundary is also where an affordance-related relation might be relevant: a subject, an environment or place state, and an action or capability may jointly determine what is possible. The place restriction adds a different question about what is allowed.

## Slide 8 — Questions for P1872.3

I’ll close with the questions I hope will make this useful.

Which of these concepts already have appropriate representations in the 1872 family or related ontology work? Which distinctions should collapse into existing concepts rather than becoming SPP vocabulary?

Are place-originated operational requirements best treated as a class, a relation, or an existing construct with a profile-specific interpretation? How should scoped admission remain distinct from capability, permission, certification, and task feasibility?

For candidate routes or tasks, what is the right way to represent a conclusion that depends jointly on subject state, place-originated constraints, and planned actions? And which apparent gaps are actually ontology gaps, versus details that should remain in a deployment profile, policy model, or planner interface?

Finally, where do you see conceptual conflation in SPP today? I am especially interested in terms or relations that SPP should stop using before they harden into unnecessary vocabulary.

The short version is: I’m trying to determine which concepts SPP should reuse, which distinctions are actually useful, and which terms we should remove before they harden into unnecessary vocabulary. Criticism and pointers to established concepts are the desired outcome; adoption is not the ask.
