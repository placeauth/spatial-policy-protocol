# Experimental P0 Trust Pipeline

**Status:** Experimental reference composition. This document and the
corresponding code do not modify normative SPP 0.1.

The P0 pipeline answers a narrow operational question: may a local consumer
rely *now* on an experimental `AdmissionProfile` received in a signed envelope?
It composes three independently useful reference mechanisms without turning
any of them into a new protocol decision or a claim of physical enforcement.

## Required order

`assess_admission_reliance(...)` applies the following fail-closed sequence:

1. Verify the signed admission envelope: local issuer trust, Ed25519 signature,
   experimental envelope version, issuance/expiry, exact subject, and exact
   place/space scope.
2. Reject a signed `DENIED` profile immediately; it is terminal and never
   reaches a reusable lifecycle path.
3. Evaluate an `ADMITTED` or `DEGRADED` signed profile against a caller-supplied
   current evaluation context. Only a subject-bound lifecycle result of `VALID`
   permits reuse. The original admission status is never converted.
4. For `DEGRADED` only, require exact acknowledgement of every restriction and
   one matching nonempty local enforcement-handler mapping for each restriction.
5. Return `RELIABLE_ADMITTED`, `RELIABLE_DEGRADED`, or `BLOCKED`, including the
   first blocking stage and structured reason codes.

The orchestrator obtains the profile only from a successfully verified envelope.
It does not accept an adjacent unsigned profile that could be substituted after
verification. `RELIABLE_DEGRADED` retains the exact restrictions from the
profile; it does not synthesize a less restrictive operating result.

## Result boundary

| Profile status after valid envelope and lifecycle | Additional requirement | Reliance outcome |
| --- | --- | --- |
| `ADMITTED` | None | `RELIABLE_ADMITTED` |
| `DEGRADED` | Exact acknowledgement and matching handler mapping for every restriction | `RELIABLE_DEGRADED` |
| `DENIED` | None can override it | `BLOCKED` |

Any envelope, trust, time, scope, subject, profile-revocation, evidence,
lifecycle, acknowledgement, restriction, or mapping failure returns `BLOCKED`.
`REVALIDATE`, `REQUALIFY`, and `INVALID` lifecycle outcomes are not temporary
permission. A deployment must perform a fresh assessment at its reliance
boundary after material context or configuration changes.

## Scope and trust boundaries

The envelope uses the repository's existing local Ed25519 and
`TrustedIssuerRegistry` reference model. The lifecycle step takes authenticated
current subject state, place requirements, evidence, time, and optional local
revocation registries. The acknowledgement step proves only that a local
consumer recognized every exact restriction and named matching configured
handler identifiers.

This composition does not provide a PKI, remote discovery, distributed
revocation, trusted clocks, consumer authentication, hardware attestation,
continuous monitoring, or proof that a handler executed or physically enforced
a restriction. Local trust anchors, current-state sources, handler
configuration, and physical enforcement remain deployment responsibilities.

The three underlying representations are still experimental and have distinct
reference-level bindings: the envelope signs the full Python dataclass payload,
whereas acknowledgement treats the established effective restriction lists as
a set. The former authenticates the issued representation; the latter prevents
ordering or duplicate-list placement from silently changing required handler
coverage. Neither is a cross-language normative signature/canonicalization
contract.

## Reference use

Run the deterministic demo:

```powershell
python demo/p0_trust_pipeline/run_demo.py
```

It demonstrates a successful `DEGRADED` reliance decision, an expired envelope,
a material subject capability change, missing acknowledgement, tampering after
signing, and an immutable `DENIED` outcome.
