# Evidence sufficiency and selective requalification

The additive `spp_admission.sufficiency` API checks whether an original test
record still proves a destination requirement. It returns reasons and builds the
existing `ConformancePlan`; it adds no wire objects or normative protocol rules.

Run from a clone with the normal development dependencies installed:

```sh
python demo/requalification/run_demo.py
python demo/requalification/run_demo.py --scenario tamper
python demo/requalification/run_demo.py --scenario stale
python demo/requalification/run_demo.py --scenario controller-change
python demo/requalification/run_demo.py --scenario toctou
python demo/requalification/run_demo.py --json
```

The normal route reuses the lobby speed proof in a more permissive corridor,
retests speed for a stricter patient wing, and stops when the restricted room
requires more human separation than the reference robot can demonstrate.
This uses the existing deterministic capability checks, not simulated sensors
or a connected robot. The variants invalidate the original evidence and expose
the resulting retest. JSON output includes the actual requirement delta,
assessments, selected tests, results, and admission outcome.

## API and integration

`EvidenceRecord(requirements, plan, evidence)` groups the **original** source
PlaceRequirementSet, ConformancePlan and EvidenceBundle. Supply records from
your trusted local test runner, in preferred selection order. Do not accept
arbitrary remote records as authenticated evidence: SHA-256 is not a signature.

`assess_sufficiency(destination, robot, records, *, now=None,
required_assurance_level="E2")` returns one
`Sufficiency(requirement_id, sufficient, reason, evidence_id)` per requirement,
in destination order. The first sufficient record wins. If none is sufficient,
the result explains a relevant rejection (or `missing_evidence`). A record with
no direct test does not hide a previously identified insufficient bound.
Explicit `now` must be timezone-aware and supports reproducible clock tests.

`derive_requalification_plan(destination, robot, records, *, challenge=None,
now=None)` returns `(plan, assessments)`. Execute the selected tests with
`execute_plan`, collect a new bundle with `build_evidence`, and evaluate through
`admit_evidence_backed` with original source records and the deployment's
ReplayRegistry. Unknown mappings remain unresolved
with no invented test. The existing admission evaluator denies unresolved
requirements without a configured degraded restriction.

Invalid destination structure, duplicate IDs or an environment mismatch stop
planning with an exception. The caller must stop the operation on exceptions.
Source-record failures cause retesting rather than evidence reuse.

## Reuse rules

| Check | Required for reuse |
|---|---|
| Integrity | Recomputed bundle and plan digests; actual source requirement-set digest |
| Binding | Same actor, build, controller, embodiment and environment; consistent top-level and nested fields |
| Scope | Same place, action and unit; space may change within that place |
| Freshness | Explicit timezone-aware issue/expiry times; issued <= now < expiry |
| Assurance | At least E2 and at least the source plan's requested level |
| Coverage | Unique test/result IDs, exact result coverage and known test mapping |
| Proof | A directly executed passing source test for this requirement |
| Numeric bound | Source <= bound must be <= destination bound; source >= bound must be >= destination bound |
| Equality | Same operator, value and Python type (booleans do not equal numeric thresholds) |
| Prohibition | Both source and destination express `prohibited: true` |

A source test for speed <=0.8 proves <=0.8. It does not prove <=0.7 even if a
capability dictionary elsewhere says 0.6. Units are compared exactly, not
converted. Changes to operators are conservatively retested. A policy version
or destination space change is allowed only after re-evaluating these conditions;
the original bundle stays bound to its source policy and plan.

Retain the originals across transitions. A bundle whose guarantee was only
reused has no direct test for that guarantee and cannot refresh its expiry.
The original can still support another transition until its own expiry.

## Admission boundary

Planning determines which evidence appears reusable. Admission independently
verifies that reused evidence is still sufficient:

```python
profile = admit_evidence_backed(
    current_requirements, plan, fresh_evidence, current_robot,
    source_records=original_records, replay_registry=registry,
)
```

`admit_evidence_backed` accepts the existing objects and an optional list of
`EvidenceRecord` originals. Omitting records cannot authorize planned reuse.
It snapshots the input data, reads admission time (or a trusted `now` override),
and validates both fresh and historical evidence. It calls the same record
validator and `assess_sufficiency`; it never accepts prior assessment verdicts
or guarantee dictionaries in lieu of source records.

The current plan must be bound to the actual admission-time requirement set.
Any policy change, even relaxation, requires a new current plan and fresh
challenge/bundle. Original evidence may still be reused under the updated
plan if it proves the relaxed requirement. A recomputed plan that falsely
claims weaker evidence proves a stricter bound is rejected by sufficiency.

The boundary also checks exact coverage: reused IDs and unresolved IDs must
partition the destination requirements; selected tests must be unresolved;
test and reuse sets cannot overlap; fresh results must exactly cover selected
tests. Missing evidence, inconsistent coverage, invalid provenance or failed
validation produces DENIED with no partial guarantees. Essential failures
cannot be downgraded using a degraded restriction. Non-essential fresh failures
retain the existing DEGRADED behavior with explicit restrictions.

Reused evidence must satisfy at least E2, its source plan's assurance floor,
and the destination plan's assurance floor. Existing reason codes are reused:
`missing_evidence`, `stale_evidence`, `evidence_digest_mismatch`,
`plan_digest_mismatch`, `policy_digest_mismatch`, `evidence_binding_mismatch`,
`scope_mismatch`, `insufficient_proven_bound`, `insufficient_assurance`,
`result_coverage_mismatch`, and `malformed_source_record`, among others.
Rejected requirement IDs are available in `AdmissionProfile.unresolved` when
the failure can be assigned to specific guarantees.

In `--scenario toctou`, the corridor planner accepts the lobby proof. The
controller then changes. Fresh destination evidence reflects the current
controller, but admission rejects the original proof with
`evidence_binding_mismatch`, returning DENIED and stopping at the corridor.

## Boundaries and compatibility

Existing `derive_plan(..., proven_guarantees=...)` remains a low-level trusted
caller API. It does not perform these checks. Similarly, `admit` is the trusted
legacy entry point, retained for existing callers and A-D demos. It must not
serve as a provenance-enforced endpoint. Migrate evidence-backed integrations
to `admit_evidence_backed`; the requalification demo now uses it for every
boundary. Schemas and Core evaluation retain their behavior. `build_evidence`
and legacy `admit` accept optional keyword-only `now` for deterministic testing;
existing positional calls are unchanged.

Admission evaluates a snapshot of current state and time. The service must
provide authenticated current requirements, robot state and trusted time, and
serialize admission with relevant runtime state updates. Changes after profile
issuance require another evaluation; a returned profile is not an indefinitely
valid authorization. No profile schema or external locking protocol is added.

The enforced entry point delegates to the existing replay registry only after
validation. Invalid reuse does not consume the destination nonce. Accepted
nonces remain single-use, including across legacy/enforced callers sharing the
registry. Historical proof reuse does not claim the original source challenge
again. Registry persistence, concurrency and distribution remain deployment
concerns. Current source checks use the four existing reference mappings.

This is structural provenance and sufficiency, not issuer authentication.
A malicious issuer can fabricate a passing result and recompute SHA-256.
`AdmissionProfile` remains a constructible Python dataclass: downstream systems
must trust the service that issued it, not arbitrary profile dictionaries or
the mere presence of a status field. The enforced entry point is not exposed as
a network endpoint. Keep records and issuer channels authenticated; do not expose
the legacy API or the `now` override as user-selectable security modes.

Opaque manually supplied `policy_digest` identifiers are rejected for reuse:
the evaluator requires a digest derived from the actual source requirement set.
Policy discovery, independent attestation, revocation, dependency graphs, unit
conversion, distributed replay storage and middleware integration remain outside
this implementation. Schema validation uses the current repository resources,
consistent with the reference package's existing clone-based setup.
