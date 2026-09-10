# Exact DEGRADED Restriction Acknowledgement (Experimental)

**Status:** Experimental reference mechanism. This mechanism does not modify
normative SPP 0.1.

An `ADMITTED` experimental `AdmissionProfile` has no `DEGRADED` restriction
acknowledgement requirement. A `DENIED` profile is never operationally usable.
For a `DEGRADED` profile, a generic deployment statement such as "supports
degraded" is insufficient: the consumer must acknowledge every exact
restriction in the issued profile and name a configured enforcement handler for
each one.

## Exact local binding

The reference model uses the deployment-defined restriction strings already
carried by an `AdmissionProfile`. Each string has a canonical SHA-256 identity
computed as `digest({"restriction": restriction})`, using the reference
engine's sorted-key, compact JSON serialization encoded as UTF-8. There is no
fuzzy or natural-language matching, trimming, case folding, or Unicode
normalization. Leading/trailing whitespace, case changes, and distinct Unicode
code-point sequences are therefore distinct restriction values; whitespace-only
restrictions are malformed. An acknowledgement includes:

- a deterministic profile binding covering profile content and the effective
  restriction set;
- the exact restriction text and its digest;
- the nonempty local enforcement-handler identifier; and
- a local consumer/deployment identifier.

The profile binding treats restrictions as a set because the existing reference
adapters combine the top-level and embedded restriction lists that way. This is
an experimental set-semantics decision, not a new SPP 0.1 rule. Thus ordering,
duplicates, and equivalent placement in either existing list do not change the
acknowledgement identity. Other profile content—including outcome, subject,
place/space, evidence and runtime binding, reason codes, unresolved items, and
non-restriction operating-profile content—remains bound.

The deployment separately supplies an exact `restriction -> handler` mapping.
Every required restriction must have exactly one nonempty mapping, and its
handler must match the handler named in the acknowledgement. A handler may
intentionally serve more than one distinct restriction, but duplicate mappings
for the same required restriction are ambiguous and fail closed. Mappings for
restrictions unrelated to the profile are permitted as unused local deployment
configuration. Unknown, omitted, altered, malformed, wrong-profile,
duplicated/conflicting, or ambiguous inputs fail closed. A `DEGRADED` profile
with no effective restrictions also fails closed: it is inconsistent with the
experimental admission meaning.

The result is `ACKNOWLEDGED` only when the consumer may rely on the `DEGRADED`
profile at this boundary. `NOT_REQUIRED` is the successful result for an
`ADMITTED` profile; `BLOCKED` covers all failures and is not permission to
operate. The reference object exposes structured reason codes, required and
acknowledged restrictions, and the validated local mappings. Its `may_rely`
flag means only that this acknowledgement boundary succeeded; it cannot make a
stale, unauthenticated, or otherwise invalid profile operationally usable.

## What this proves—and does not prove

This check proves only that a local consumer explicitly recognized every
required restriction, accepted responsibility for it, and had a configured
handler identifier for each restriction. It does **not** prove that the
handler is correct, executed, remains active, controls the relevant actuator,
or physically enforced the restriction. It supplies no hardware attestation,
continuous enforcement monitoring, PKI, distributed acknowledgement, or
universal restriction/capability ontology. The deployment remains responsible
for trustworthy configuration and actual enforcement.

`consumer_id` is a nonempty local descriptive identifier only. This module does
not authenticate the consumer or establish that the named deployment generated
the acknowledgement. A deployment that needs that property must establish it
outside this reference mechanism (for example, through its authenticated
configuration and signed-envelope boundary).

## Intended composition

For a long-lived or externally received profile, the intended order is:

1. Verify a signed experimental admission envelope's issuer, integrity, time,
   scope, and profile binding when that optional envelope is used.
2. Assess current lifecycle / subject-bound revalidation state when that
   optional experimental mechanism is used. Only its `VALID` result allows
   reliance on the issued profile.
3. If the profile is `DEGRADED`, evaluate exact restriction acknowledgement.
4. Only then may the adapter or deployment rely on the profile; its handlers
   remain independently responsible for enforcement.

This module deliberately imports neither experimental branch. It can compose
with their results later, but neither a signature nor lifecycle assessment is
substituted by an acknowledgement.

## Configuration freshness / TOCTOU

The assessment compares the handler identifier named by each acknowledgement
with the mapping supplied *at assessment time*. If the mapping or enforcement
configuration changes afterward, that prior result is not proof that the later
configuration is still adequate. A deployment must perform this check at its
own reliance boundary again after material configuration changes. This module
does not create a lifecycle or continuous-monitoring system.

## Reference use

```powershell
python demo/degraded_restriction_ack/run_demo.py
```

The demo shows a complete exact acknowledgement, a missing speed restriction,
and an altered restriction. It is deterministic local reference code, not a
physical-system validation.
