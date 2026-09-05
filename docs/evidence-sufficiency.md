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

`assess_sufficiency(destination, robot, records, *, now=None)` returns one
`Sufficiency(requirement_id, sufficient, reason, evidence_id)` per requirement,
in destination order. The first sufficient record wins. If none is sufficient,
the result explains a relevant rejection (or `missing_evidence`). A record with
no direct test does not hide a previously identified insufficient bound.
Explicit `now` must be timezone-aware and supports reproducible clock tests.

`derive_requalification_plan(destination, robot, records, *, challenge=None,
now=None)` returns `(plan, assessments)`. Execute the selected tests with
`execute_plan`, collect a new bundle with `build_evidence`, and evaluate through
`admit` with the deployment's ReplayRegistry. Unknown mappings remain unresolved
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

## Boundaries and compatibility

Existing `derive_plan(..., proven_guarantees=...)` remains a low-level trusted
caller API. It does not perform these checks. Existing A-D demos, schemas and
Core evaluation retain their behavior. The new helper is a local planner, not
an authorization endpoint or a replacement for `admit`.

Assess and execute within a trusted synchronous boundary. If state, time or
source evidence changes between planning and action, assess again. The helper
does not extend the admission profile with provenance or expiry, consume replay
nonces, authenticate the issuer, verify hardware, or enforce physical behavior.
Do not persist a plan as an indefinitely valid authorization. Replay protection
remains at `admit`; historical proof reuse is not a second admission using the
old challenge. Current source checks use the four existing reference mappings.

Opaque manually supplied `policy_digest` identifiers are rejected for reuse:
the evaluator requires a digest derived from the actual source requirement set.
Policy discovery, independent attestation, revocation, dependency graphs, unit
conversion, distributed replay storage and middleware integration remain outside
this implementation. Schema validation uses the current repository resources,
consistent with the reference package's existing clone-based setup.
