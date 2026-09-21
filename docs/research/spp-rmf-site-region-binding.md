# SPP <-> RMF Site Region Binding

*Experimental interoperability research note*

## 1. Status and Scope

This note is non-normative and experimental. It explores a thin interoperability boundary between the Spatial Policy Protocol (SPP) and an externally represented Open-RMF site region or zone. It does not change SPP 0.1, define a protocol extension, or prescribe an implementation.

This note makes no claim of Open-RMF endorsement of SPP, Open-RMF adoption of SPP, or agreement on a binding format. It is a discussion artifact for testing whether the two layers can remain independently useful while a deployment connects them. Any future format or adapter would need separate design, review, and validation.

## 2. Problem

SPP needs a way to express a simple applicability statement: *these place-originated requirements apply to this governed physical scope.* The scope matters because a policy may apply to an imaging area, a public corridor, or a treatment room without applying throughout a facility.

That need does not require SPP to own the physical model. SPP should not need to define or interpret polygon geometry, building maps, navigation graphs, robot route planning, or site editing. Nor should it become the owner of queueing, traffic scheduling, reservation behavior, or execution behavior. Those concerns depend on a deployment's site model and operating system. An external site representation can define the physical region while SPP retains the place-originated requirement that becomes applicable there.

## 3. Proposed Separation of Responsibilities

| Concern | SPP | RMF / Site Representation |
| --- | --- | --- |
| Place authority | Expresses requirements asserted by the place authority. | May carry deployment-recognized site information; does not replace the authority for a place policy. |
| Policy identifier/version | Identifies the policy and its applicable version. | May retain a binding or audit reference, but does not define the policy. |
| Governed-scope reference | Carries a reference to the scope to which requirements apply. | Resolves the reference in the site model. |
| Physical geometry | Does not model or interpret geometry. | Represents physical geometry where the site model supports it. |
| Zone/region authoring | Does not author zones or regions. | Authors and maintains site regions or zones. |
| Subject/action/context | Evaluates supplied subject, action, and context inputs. | Supplies relevant operational context when a deployment chooses to integrate it. |
| Policy evaluation | Produces a normalized policy outcome and obligations. | Does not need to become an SPP policy evaluator. |
| Obligations/restrictions | States place-originated obligations or restrictions. | Accepts only requirements it can apply or enforce in the relevant workflow. |
| Candidate route/task planning | Does not generate candidate routes or tasks. | Generates candidate routes, tasks, assignments, and schedules. |
| Feasibility | Does not decide whether a particular candidate route or task is feasible. | Evaluates whether a candidate can satisfy all relevant constraints. |
| Waiting/queueing/reservation | Does not model queue, traffic, or reservation semantics. | Owns any such site- or fleet-side mechanisms. |
| Execution/enforcement | Does not dispatch, control, or physically enforce behavior. | Coordinates execution; downstream controls remain responsible for actual enforcement. |

The boundary is deliberately conservative. A policy result can inform planning, but it is not itself a route plan, a reservation, or proof that a runtime will enforce a restriction.

## 4. Governed-Scope Binding Concept

A deployment could associate an SPP governed scope with an external site scope using a small binding concept such as:

```text
SPP governed scope:
  external_system: "rmf-site"
  external_scope_ref: "<opaque-region-identifier>"
```

This illustration is not a normative schema and does not assign semantics to any particular RMF Site field or identifier. The important principle is that SPP treats `external_scope_ref` as opaque: it stores or carries a reference but does not parse its geometry, infer containment, or redefine the referenced region. The deployment or integration layer resolves that identifier to the corresponding region in its site representation.

Keeping resolution outside SPP permits the site model to evolve independently. It also avoids treating a site identifier as proof that a robot is currently inside a region. Runtime location association, site-model access, and the choice of a suitable external object remain deployment questions.

## 5. Example

Consider a hospital corridor that leads to an imaging area. The RMF Site representation defines a physical region for the imaging area. A place policy references that region using its external identifier and states that recording is prohibited within the governed scope.

Robot A has a candidate route that avoids the region, so the restriction does not make that candidate route infeasible. Robot B has a candidate route that crosses the region while recording. Its plan may become feasible if recording is disabled for the affected portion of the work and the deployment has a real way to enforce that condition. Otherwise, the planner may reject, redirect, or defer the candidate.

These are distinct questions:

- **Policy evaluation:** “What requirements apply here?”
- **Planner feasibility:** “Can this candidate route/task satisfy them?”

The place declares the constraint. The planner evaluates the candidate. SPP need not decide which route is preferable, and the planner need not become the authority that authors the place's recording rule.

## 6. Queueing / Waiting Boundary

Some place requirements cannot be satisfied immediately. For example, a policy may require an escort, while the selected robot is ready to proceed but no escort is currently available. A future deployment may let an RMF-side system wait, queue, redirect, or otherwise defer progress, then reevaluate the requirement when relevant conditions change.

This note does not claim that RMF Next Generation currently provides a general queueing architecture for such requirements. Open-RMF has destination-specific reservation and waiting concepts in some contexts; those should not be silently generalized into a universal policy-queue mechanism. A generalized queueing or waiting design, if wanted, is an execution-side question for RMF and its deployments. SPP's narrower role is to state the requirement and return the appropriate policy outcome when evaluated with current inputs.

## 7. Binding Lifecycle Questions

The following questions remain unresolved and should not be answered by this research note alone:

- How stable are external region identifiers across site revisions?
- What should occur when site geometry changes?
- Do region revisions require explicit version identifiers?
- How are deleted or renamed regions detected?
- Which component resolves an opaque external reference?
- Should bindings reside in site metadata, deployment configuration, or an adapter?
- May one SPP governed scope map to multiple site regions?
- Do overlapping regions require precedence rules outside SPP?
- How is runtime location associated with the referenced region?

## 8. Non-Goals

This work does not propose an SPP map format, SPP zone ontology, SPP navigation planner, SPP queueing system, SPP traffic scheduler, SPP fleet model, or SPP physical-enforcement layer. It also does not propose a finalized RMF Site mapping, an RMF adapter, or a new interpretation of RMF Site concepts.

## 9. Open-RMF Integration Questions

The following questions are suitable for future discussion with Open-RMF contributors:

1. What RMF Site object is the most appropriate stable target for an external governed-scope reference?
2. Are region identifiers expected to remain stable across site revisions?
3. Should an external policy binding live inside site metadata or outside the site model?
4. Where should candidate-route feasibility consume place-originated constraints?
5. What runtime input can reliably associate a robot or route segment with a referenced region?
6. Could future queueing or waiting infrastructure consume unsatisfied obligations without requiring SPP to model queue semantics?
7. How should a site-model change invalidate, revise, or retire an external governed-scope binding?

## 10. Current Conclusion

The likely interoperability boundary is intentionally small:

```text
SPP = place-originated constraints + opaque governed-scope reference
RMF = site geometry + planning + candidate feasibility + waiting/queueing + execution
```

Under this model, SPP identifies the policy constraint and the external scope to which it applies. RMF or the deployment retains responsibility for geometry, site resolution, candidate planning, feasibility, waiting or queueing, and execution. Further Open-RMF feedback is needed before any adapter or binding format should be standardized.
