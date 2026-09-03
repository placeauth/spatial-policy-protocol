# Evidence-Based Spatial Admission

Status: EXPERIMENTAL / PRE-STANDARDIZATION. This is a reference design, not an
adopted standard or production security system.

SPP Core answers whether an actor may perform an action in a space. The
Conformance and Admission extensions answer what operating guarantees this
particular machine has demonstrated for this place.

## Flow

PlaceRequirementSet -> ConformancePlan -> embodiment adapter tests ->
EvidenceBundle -> EvidenceBinding -> AdmissionProfile -> RequirementDelta and
selective requalification on spatial transition.

## Canonical objects

- PlaceRequirementSet: abstract place-owned requirements such as
  movement.max_speed <= 0.8 m/s, without naming a robot vendor or runtime.
- ConformancePlan: selected tests, policy/environment digests, challenge,
  unresolved guarantees, and required assurance level.
- ConformanceTest: an adapter-level test mapped from one abstract requirement.
- EvidenceBundle: test results bound to robot build, controller configuration,
  policy, environment, plan, and challenge.
- EvidenceBinding: state fingerprints that make evidence applicable.
- AdmissionProfile: ADMITTED, DEGRADED, or DENIED with guarantees,
  restrictions, unresolved requirements, and reasons.
- RequirementDelta: transition requirements classified as REUSED, NEW,
  STRICTER, RELAXED, NO_LONGER_APPLICABLE, or UNRESOLVED.

## Reference behavior

The demo maps abstract requirements to deterministic tests for a simple
mobile-base adapter: speed bound, human separation, facial-recognition
disabled, and zero video retention. A Nav2 speed filter, humanoid locomotion
controller, forklift safety PLC, or drone flight controller could implement the
same place-facing requirements through a different adapter.

Evidence is hashed with SHA-256. The reference implementation demonstrates E2
behavioral test evidence; the schema reserves E0 through E4. Signed or
hardware-attested binding can be added later.

The implementation exposes fingerprints and results, not source code, model
weights, or proprietary controller internals. It does not provide
zero-knowledge proofs.

## Admission and transition

Essential safety failures, including human separation, fail closed to DENIED.
A non-essential failure can produce DEGRADED with an explicit restriction, such
as disabling video capture while retaining other approved guarantees.

When a robot moves from the lobby to the patient wing, RequirementDelta compares
proven guarantees with the new requirement set. Only NEW, STRICTER, or
UNRESOLVED requirements are selected for fresh testing; REUSED guarantees are
not rerun.

## Open protocol elements vs reference details

Open protocol elements are the abstract requirement vocabulary, hierarchy,
admission states, evidence binding fields, assurance levels, and delta
classifications. YAML serialization, SHA-256 digests, the fixed demo nonce,
Python dataclasses, and the mobile-base adapter are reference implementation
details.

SPP does not itself force a malicious autonomous system to comply. Enforcement
strength depends on evidence assurance, the enforcement point, robot runtime,
external infrastructure, and hardware guarantees.
