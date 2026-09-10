# Next-Release Hardening Plan

**Status:** Internal, repository-grounded planning document

## Purpose and release-state correction

This document defines the scope of the next implementation hardening release.
It supersedes the earlier internal v0.2-boundary framing. It is not a proposal
to recreate, move, or reissue a v0.2 release: repository history already
records **SPP v0.2.0 Experimental Preview**, while the checked-in package and
latest public release materials identify **0.3.0 Experimental Preview**.

The repository currently has three distinct version layers:

| Layer | Current version / status | Meaning |
| --- | --- | --- |
| Implementation/package release | `0.3.0` | The version of this reference implementation and its published experimental preview. Existing release history follows `0.1.0`, `0.2.0`, and `0.3.0`; a next package release would naturally be considered `0.4.0`, subject to normal release approval. No tag or release is proposed here. |
| Normative SPP protocol | `SPP 0.1` | The policy, request, decision, hierarchy, action-family, conditional, obligation, and fail-closed contract in `spec/SPP-0.1.md`. |
| Experimental component formats | Admission `0.1-experimental`; trace `0.1`; Place Package `0.1`; requirement vocabulary `1.0` | Reference exchange and tooling surfaces with their own compatibility boundaries. Their presence does not change normative SPP versioning. |

The normative `spp_version` must remain **0.1** for now. A normative version
change is justified only by an adopted change to the actual SPP policy/request/
decision contract, not by a package release, a new adapter, or hardening of a
reference admission model. The work below therefore targets a likely next
implementation release, not a protocol-version bump.

## Decision summary

The next hardening release should make the existing SPP 0.1 place-policy core
more dependable at evidence-backed admission boundaries without turning SPP
into a planning, fleet-management, building-automation, identity, or trust-
federation protocol.

The durable boundary is:

```text
place requirements + bound evidence + current subject/context
    -> experimental admission assessment
    -> ADMITTED | DEGRADED | DENIED
    -> host-specific enforcement decision
```

The core SPP answer remains `permit`, `conditional`, or `deny`. An
`AdmissionProfile` is a downstream experimental operating result, not a
replacement for SPP 0.1 authorization semantics. The important limitation is
also the point of the plan: a constructible local profile cannot itself prove
that it is current, authentic, or enforceable.

## Current implementation inventory

### Normative core: retain without expansion

| Surface | State | Next-release boundary |
| --- | --- | --- |
| Policy, request, and decision schemas carrying `spp_version: "0.1"` | Implemented / normative | Retain the existing version and reject unsupported versions. |
| Hierarchical spaces and nearest-matching-rule evaluation | Implemented / normative | Explicit `parent` links determine inheritance; path-shaped IDs do not. |
| Six action families | Implemented / normative | `movement`, `sensing`, `data`, `manipulation`, `infrastructure`, and `human_interaction` remain the bounded families. |
| `permit`, `conditional`, `deny`, obligations | Implemented / normative | Conditional is blocking until verified requirements are satisfied and the request is evaluated again. An unenforceable obligation fails closed. |
| Python evaluator, local policy server, OPA/Rego adapter | Implemented / reference | OPA/Rego is a reference binding, not a second normative evaluator or required runtime. |

SPP 0.1 intentionally does not standardize identity proofing, credential
formats, policy discovery, geometry, robot control, transport authentication,
policy signatures, revocation distribution, or policy merge semantics. A
hardening release must not add any of those indirectly through an integration.

### Experimental admission and trust: harden, do not silently promote

| Surface | State | Scope decision |
| --- | --- | --- |
| `PlaceRequirementSet` and `ConformancePlan` | Implemented / experimental reference | Deterministically turn place-owned requirements into selected tests and digests. Not normative SPP 0.1 wire objects. |
| Requirement-to-test mapping and embodiment paths | Implemented / experimental reference | Demonstrate mobile-base and humanoid paths, not a universal robot-capability ontology or certification scheme. |
| `EvidenceBundle` / `EvidenceBinding` | Implemented / experimental reference | Bind results to actor, build, controller, environment, policy, plan, scope, challenge, assurance, issue/expiry fields, and digest. |
| Integrity, freshness, binding, replay, and sufficiency checks | Implemented / experimental reference | Admission independently checks current evidence; it does not trust a prior plan or bare profile. |
| Assurance E0–E4 | Partially implemented / documented range | The reference demo is E2 behavioral evidence. The range is not a claim that all assurance levels, physical safety, or external observation are implemented. |
| Local Ed25519 evidence issuer registry | Implemented / experimental reference | Verifies complete signed evidence and local issuer scope/type/enablement. No PKI, remote discovery, HSM, or distributed revocation claim. |
| Local Ed25519 policy-authority registry | Implemented / experimental reference | Separately verifies complete signed requirements and local place/space authorization. This trust role is distinct from evidence issuance. |
| `AdmissionProfile`: `ADMITTED` / `DEGRADED` / `DENIED` | Implemented / experimental reference | A useful operating result only under a trusted current evaluation and an enforcement host that can honor it. |
| Lifecycle and local revocation | Implemented / experimental reference | The assessor returns `VALID`, `REVALIDATE`, `REQUALIFY`, or `INVALID` for supplied current requirements, subject state, evidence, trust state, and time. The registry is in-memory reference infrastructure. |

The next release may harden these interfaces as **experimental components**.
It must not describe them as new normative SPP behavior merely because their
tests or schemas become more precise.

### Explainability, packages, providers, and integrations

`spp-explain` and trace format 0.1 are implemented experimental tooling. A
trace deterministically explains the request, policy path, requirements,
evidence, lifecycle assessment, restrictions, reasons, and result. It is not a
credential, authorization token, audit system, or independent proof of physical
behavior.

Place Package 0.1, requirement vocabulary 1.0, and the external conformance-
provider contract are implemented experimental portability surfaces. They are
useful inputs to a future hardening release, but do not imply discovery,
federation, a provider marketplace, or a universal ontology. Unknown extensions
and incompatible requirement versions remain unresolved or fail closed.

| Integration / demonstration | State | Explicit limitation |
| --- | --- | --- |
| ROS 2 / Nav2 speed-limit adapter | Experimental with bounded Humble runtime validation | The documented fixture changed command speed from 1.0 m/s to 0.5 m/s under one active `FollowPath` goal; it is not a physical stopping, functional-safety, or arbitrary-controller claim. |
| Open-RMF delivery consideration adapter | Experimental with bounded Humble runtime validation | It targets `FleetUpdateHandle.consider_delivery_requests` as an early fleet/bid-consideration hook. It does not prove selected-robot suitability, dispatch execution, traffic negotiation, fleet-wide integration, or physical motion. |
| Facility access adapter | Experimental pure decision boundary | It maps a current profile to a place-access decision; it is not physical-door, building-protocol, vendor, or physical-security validation. |
| Clinic, admission, provider, trust, lifecycle demos | Implemented reference demonstrations | They demonstrate deterministic behavior and failure cases, not production certification. |
| Planner-aware constraints | Experimental only, separate branch | `experiment/planner-aware-constraints` contains a self-contained candidate-plan scope demo and is not merged into `main`. It is neither an SPP extension nor an Open-RMF design commitment. |

## Scope boundary for the next implementation release

### Include: narrowly bounded hardening candidates

1. **Fail-closed evidence-backed admission.** Preserve canonical digest,
   freshness, state-binding, plan/policy/environment binding, sufficiency, and
   replay checks at the admission boundary.
2. **Local trust with explicit roles.** Continue separate locally provisioned
   authority and issuer registries; reject unknown, disabled, unauthorized,
   unsigned, or tampered verified-path inputs.
3. **Lifecycle behavior.** Make it clearer when a result is valid only for its
   bound subject/context and when current evidence, requirements, or state
   demand revalidation or requalification.
4. **Bounded adapters.** Tighten adapter contracts only where they can prove
   the result is current and restrictions are accepted by the host. Keep the
   protocol independent of the adapter.
5. **Experimental profile representation.** A signed/time-bound profile
   representation is a candidate hardening of the experimental admission model,
   provided it remains additive and does not alter SPP 0.1 policy semantics.

### Keep experimental

- Admission objects, place requirements, conformance plans, evidence bundles,
  assurance levels, provider contracts, signatures, lifecycle results, traces,
  and Place Packages.
- Nav2, Open-RMF, and facility-access mappings, including their exact runtime
  fixtures and deployment-specific restriction strings.
- Planner-aware constraints and the separate experiment branch.

Experimental does not mean untested; it means that these surfaces have not yet
been adopted as the normative SPP contract. A future normative proposal would
need independent interoperability evidence, a stable data model, precise trust
and lifecycle semantics, and a deliberate specification process.

### Defer

- Route/planner semantics, route generation, path geometry, task planning, and
  planner-native constraint inheritance.
- Open-RMF API changes, Next Generation group/fleet modeling, scheduler
  ownership, robot assignment/reassignment controls, dispatch interception, or
  presumed RMF adoption.
- Discovery, remote trust discovery, PKI, certificates, HSMs, federated
  identity, distributed replay/revocation, or online attestation services.
- Universal capability/requirement ontology, generalized requirement
  inheritance, provider marketplace, vendor certification, or a new generic
  policy language.
- Physical door/building expansion, physical safety claims, or production
  deployment certification.

## Portable subject-bound revalidation

The core lifecycle concern is not "selected-robot revalidation." It is
**subject-bound revalidation after material context change**.

An admission/conformance result is applicable only to the subject and context
that its evidence and requirements bind. Before a host uses it, the host must
be able to determine whether a material covered input has changed. Examples
include:

- subject identity or authenticated subject instance;
- subject capabilities, build, controller, embodiment, or other bound state;
- evidence contents, evidence source/issuer status, expiry, replay status, or
  revocation;
- applicable place requirements, policy version/digest, space, scope, or
  environment digest;
- plan or configuration state where that state is covered by the conformance
  result; and
- trusted time or another explicitly bound context value.

The appropriate outcome is then explicit: retain only a `VALID` result;
perform `REVALIDATE` or `REQUALIFY` when indicated; otherwise mark it
`INVALID` and deny. Robot selection or reassignment is only one adapter-level
example: an RMF fleet may consider a request before it knows the eventual robot,
so the host must evaluate the selected subject before execution. The same rule
applies to any fleet manager, robot runtime, door controller, or non-RMF host.

## P0 reassessment and promotion path

The following are not all the same kind of blocker. The table separates a
blocker for the next **experimental implementation** release from a prerequisite
for a possible future **normative** SPP revision.

| Candidate | Next implementation release | Future normative SPP revision | Decision and promotion condition |
| --- | --- | --- | --- |
| Signed, time-bound admission envelope | **P0 only if** the next release exposes AdmissionProfiles across a trust boundary or presents them as portable integration inputs. Otherwise P1 experimental hardening. | Not currently required. It becomes a prerequisite only if a future proposal standardizes admission-result exchange. | Keep experimental. Define canonical contents, issuer identity, signature, issue/expiry, subject/place scope, and fail-closed verification. Do not call it SPP 0.1 or change `spp_version`. |
| Enforceable `DEGRADED` acknowledgement | **P0 for each adapter that claims DEGRADED support.** Not a package-wide blocker for adapters that reject DEGRADED. | Not currently required. A normative admission proposal would need a standard restriction/enforcement model first. | Keep experimental and deployment-specific. The host must accept every exact restriction from trusted configuration; missing, unknown, partial, or stale acknowledgement rejects the profile. |
| Subject-bound lifecycle/revalidation | **P0 for the experimental admission layer** if it is consumed by adapters or long-lived operations. | Not currently required, but a prerequisite concept for any normative admission semantics. | Keep experimental. Specify covered inputs and outcomes without naming a robot, fleet, or middleware as the general subject. |

There is therefore no contradiction: a next package release may harden an
experimental profile envelope and lifecycle model without promoting either to
normative SPP. A concept becomes a normative release blocker only after the
project separately decides to make admission-result exchange part of the
normative protocol.

## Release challenge

Every candidate must answer all of the following before inclusion:

1. Does it preserve the SPP 0.1 question—may this actor perform this action in
   this space under this context—rather than replace it?
2. Is its input/output boundary deterministic, versioned, and schema-valid?
3. Can a non-RMF consumer use it without fleet, planner, ROS, or vendor terms?
4. Does it identify the trust owner and fail closed on unknown or unverifiable
   input?
5. Does it bind the result to subject, place/space, policy, evidence, relevant
   state, and time at the enforcement point?
6. Are `ADMITTED`, `DEGRADED`, and `DENIED` unambiguous, and can the real host
   enforce every asserted restriction?
7. Does it explicitly handle stale results, changed requirements/state, revoked
   trust, expired evidence, and replay?
8. Is the claimed behavior backed by a focused test or fixture, with untested
   layers clearly separated?
9. Does it avoid creating a duplicate policy source of truth for a place?
10. Can it be described without implying endorsement, planned API adoption,
    production certification, or physical safety?

A negative answer to questions 3–6 or 9 excludes the feature. A negative
answer to questions 7, 8, or 10 requires the gap to be closed or the claim to
be narrowed before release.

## Prioritized implementation sequence

| Priority | Job / affected components | Rationale and acceptance checks | Complexity / dependencies |
| --- | --- | --- | --- |
| P0 | **Harden the experimental AdmissionProfile as a signed, time-bound, subject/place-scoped envelope** (`reference/admission`, additive admission schema, lifecycle tests, adapter mappers). | This is the first job only as experimental admission hardening, not a normative protocol change. Verify tamper, unknown issuer, disabled issuer, expiry, wrong subject/place, changed policy/evidence/binding, and revoked-profile rejection. | Medium. Reuses canonicalization and local Ed25519; must remain backward-compatible and add no remote service. |
| P0 | **Make subject-bound revalidation explicit at every profile-consuming boundary** (lifecycle contract, integration callbacks/mappers, focused tests). | Prevents a once-valid profile from authorizing changed subject or context. Verify `VALID`, `REVALIDATE`, `REQUALIFY`, and `INVALID` behavior under each covered material change. | Small-to-medium. Requires host-supplied authenticated current state and time. |
| P0 | **Require exact `DEGRADED` restriction acceptance wherever an adapter supports DEGRADED** (Nav2, Open-RMF, facility mapper, tests, documentation). | Restriction handling has no value unless the local enforcement host can accept each exact restriction. Verify missing, unknown, partial, and stale acceptance fail closed. | Medium. Deployment configuration only; does not claim physical enforcement. |
| P1 | Publish an experimental admission-profile interchange guide and canonical fixtures. | Gives independent consumers a precise experimental contract rather than relying on a Python dataclass. Verify fixture compatibility and unsupported-version rejection. | Medium. Depends on P0 profile envelope semantics. |
| P1 | Add lifecycle checkpoint guidance and fixtures for long-running operations. | Makes periodic revalidation auditable without claiming continuous attestation. | Small. Depends on subject-bound semantics. |
| P2 | Evaluate planner-aware constraints as a separately versioned proposal on its experiment branch. | Candidate-plan facts must not enter the core until the release challenge is met for non-RMF consumers. | High. No merge by default. |
| P2 | Continue Open-RMF Next Generation discussion as architecture collaboration only. | Avoids embedding fleet/group taxonomy or assuming unpublished RMF interfaces. | High / external dependency. No API work without an RMF-owned boundary. |

## Approval recommendation

This corrected roadmap is ready to commit as an internal scope-control document.
Approve it with these constraints:

1. Treat the next package release as a potential **0.4.0 Experimental Preview**
   only after ordinary release approval; do not invent a tag now.
2. Keep normative SPP at **0.1** until an explicit specification process adopts
   a changed normative policy/request/decision contract.
3. Treat P0 admission work as hardening of an experimental component. It
   prepares that component for later normative consideration but does not
   itself promote it.
4. Keep the planner experiment and Open-RMF-specific concerns outside the
   core release boundary.

The first recommended implementation job is the signed, time-bound,
subject/place-scoped AdmissionProfile envelope. Its purpose is to make existing
experimental integration inputs verifiable and short-lived; it does not change
SPP 0.1 authorization behavior.
