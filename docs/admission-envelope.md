# Experimental signed AdmissionProfile envelope

`SignedAdmissionEnvelope` is an additive reference wrapper for an existing
experimental `AdmissionProfile`. It is **not normative SPP 0.1** and does not
change the SPP policy, request, or decision schemas.

## What it authenticates

The envelope reuses the reference layer's local Ed25519 signing and
`TrustedIssuerRegistry` model. Its signature covers a canonical SHA-256 digest
of the complete `AdmissionProfile`, plus the issuer ID, signature algorithm,
envelope type and experimental version, subject ID, place, space, derived local
scope, issuance time, and expiration time. Changing an included profile field,
including a `DEGRADED` restriction, changes the digest and invalidates
verification.

`verify_signed_admission_envelope(...)` requires the expected subject, place,
and space. It returns a structured result with `verified`, a reason code, and,
on success, the locally trusted issuer. It fails closed for malformed envelopes,
unsupported versions, invalid signatures, unknown or disabled issuers,
unauthorized scope/type, subject mismatch, place mismatch, malformed times,
invalid time ranges, expiration, future issuance, and local profile revocation.

## Canonicalization and interoperability status

This experiment uses the repository's existing Python reference canonicalizer:
the complete dataclass is converted with `dataclasses.asdict`, serialized with
`json.dumps(value, sort_keys=True, separators=(",", ":"))`, UTF-8 encoded, and
SHA-256 hashed. The signature then covers that digest and a second canonical
JSON object containing all envelope metadata. Python's default JSON encoder
uses ASCII escaping (`ensure_ascii=True`), lexicographic Python string key
ordering, JSON `null`/`true`/`false`, and its own finite-number rendering. The
envelope rejects `NaN`, positive infinity, and negative infinity so it never
signs non-standard JSON number tokens.

This is a precise **reference-implementation contract**, not a normative
cross-language canonical JSON standard. Profile content can contain finite
floating-point values, and Python number formatting, Unicode sort ordering, and
escaping rules are not yet specified as a portable SPP signature format. An
independent implementation must not claim interoperable envelope signature
generation or verification merely by serializing semantically similar objects.
A future normative proposal should select a defined canonicalization scheme
such as RFC 8785 JCS, or define a deliberately restricted SPP JSON subset and
published vectors. That decision is outside this experiment.

The current API accepts a constructed Python dataclass rather than raw JSON.
It therefore has no raw JSON parser and no duplicate-key or unknown-field
acceptance path. A future wire parser must reject duplicate object keys before
constructing the envelope and must define unknown-field handling. Subject,
place, space, scope, and issuer identifiers are exact opaque strings: no case,
Unicode, path, or other normalization is performed. Deployments must supply
canonical identifiers before signing and verification.

## Time, scope, and trust

`issued_at` and `expires_at` are timezone-aware UTC timestamps. Verification
requires `issued_at <= now < expires_at`; it grants no implicit clock-skew grace
period. The signing API renders UTC timestamps with `Z`; the verifier parses an
offset-aware timestamp but verifies the exact signed timestamp string. There is
currently no maximum envelope lifetime; a deployment may impose one later as a
local policy control. An envelope is bound to one `subject_id`, `place`, and
`space`, with a local scope of `place::space`. The verifier recomputes that
scope from the signed profile and rejects an internally inconsistent envelope.
A valid envelope for a different subject or governed space is rejected rather
than reused.

Issuers are configured locally with raw Ed25519 public keys, allowed envelope
types, allowed scopes, and an enabled flag. Cryptographic validity alone is not
trust: an unknown, disabled, or unauthorized issuer is rejected. This reuses
the existing reference trust machinery; it is not PKI, remote discovery,
certificate management, federation, HSM custody, or evidence of real-world
behavior.

## Lifecycle and enforcement limits

The optional `ProfileRevocationRegistry` invalidates an envelope by the existing
deterministic profile identifier. It is an in-memory local reference registry,
not distributed revocation or push invalidation. Expiry is mandatory, but a
caller must still provide trusted current time, current subject/context, and
any lifecycle checks required after material changes.

Revocation is profile-scoped, not envelope- or issuer-scoped: multiple envelopes
that wrap the same complete AdmissionProfile share the same deterministic
identifier and are all invalidated together. Disabling a locally configured
issuer invalidates verification through the issuer registry; it does not create
a separate envelope revocation record. The envelope has no single-use nonce:
same-subject, same-place, same-space reuse is allowed until expiry or local
revocation. Cross-context reuse fails through exact subject and place/scope
comparison.

An envelope authenticates an experimental admission decision and describes any
restrictions. It does **not** prove that an `ADMITTED` profile is physically
safe, that a `DEGRADED` restriction can be enforced, or that the evidence issuer
observed reality. Exact restriction acknowledgement and physical/runtime
enforcement remain deployment responsibilities and a separate hardening task.
Verification authenticates content; it does not convert status. A verified
`DENIED` envelope remains denied and must never be interpreted as permission.

Run the deterministic reference demonstration with:

```sh
python demo/admission_envelope/run_demo.py
```
