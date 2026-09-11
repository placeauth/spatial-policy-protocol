# Experimental Admission-Trust Interoperability Profile

## 1. Status of this document

**Status: EXPERIMENTAL and NON-NORMATIVE.** This document does not modify
Spatial Policy Protocol (SPP) 0.1, does not define an SPP 0.2 revision, and
does not create a mandatory implementation obligation for SPP participants.
It records interoperable behavior demonstrated by the PlaceAuth reference
implementations and test artifacts. It MAY change incompatibly or be withdrawn.

The RFC-style key words in this document apply only to an implementation that
elects to implement this experimental profile. They are candidate text for
future technical review, not normative SPP 0.1 requirements.

## 2. Scope

This profile describes a portable representation and verification boundary for
an experimental signed `AdmissionProfile`. It covers:

- RFC 8785 JSON Canonicalization Scheme (JCS) canonical bytes;
- a SHA-256 profile-payload digest and Ed25519 signature envelope;
- binding an artifact to a subject, place, space, and derived scope;
- local trusted-issuer lookup and authorization expectations;
- issuance and expiry validation;
- exact restriction identity and restriction-profile binding for `DEGRADED`;
  and
- machine-readable verification outcomes.

It does **not** define a PKI, remote issuer discovery, certificate chains,
distributed revocation, physical enforcement proof, planner or Open-RMF
behavior, route evaluation, continuous attestation, consumer authentication,
or a universal capability/restriction ontology. It also does not prove that
evidence-generation equipment or a local enforcement handler behaved as
claimed.

## 3. Canonicalization profile

The profile identifier is exactly:

```text
rfc8785-jcs-v1-experimental
```

An artifact using this profile MUST use RFC 8785 JCS for every profile-payload,
signature-input, and restriction-binding value identified below. Canonical bytes
are UTF-8. JSON object member names use JCS ordering, including its UTF-16 code
unit sort order. Arrays remain ordered. `null`, booleans, strings, arrays, and
objects retain their JSON meaning.

Implementations MUST NOT infer a profile from an envelope shape. The profile
identifier is a required signed value. An unknown identifier, or an envelope
object presented to the wrong profile-specific verifier, MUST fail closed.
`spp-python-json-v1-experimental` is a distinct legacy experimental profile;
its existing signatures, bytes, and digests MUST NOT be relabeled or
reinterpreted as JCS artifacts.

No Unicode normalization is performed. Escaped and literal forms that decode
to the same valid Unicode scalar string have the same JSON value; NFC and NFD
strings remain distinct. Invalid Unicode scalar values, including unpaired
surrogate escapes, MUST be rejected.

## 4. Numeric rules

The portable numeric domain is intentionally narrower than generic JSON.
Implementations MUST reject NaN, Infinity, -Infinity, and every other
non-finite value. A representation of negative zero MUST be rejected when it
can be observed: raw `-0`, raw `-0.0`, and a programmatic negative-zero float
are invalid. A parser MUST NOT normalize an invalid negative-zero lexeme into
an accepted positive zero.

Every mathematically integral numeric value MUST be within
`-(2^53-1)` through `+(2^53-1)`, inclusive. This rule is semantic, not tied to
whether a host parser selects an integer or floating type. Thus
`9007199254740991`, `-9007199254740991`, and `1e3` are valid; `9007199254740992`,
`-9007199254740992`, and `1e20` are invalid. `0`, `0.0`, `0.125`, `1e-7`, and
`5e-324` are valid finite examples. Implementations MUST NOT silently coerce
an unsafe integral value into a float to evade the bound. Valid finite,
non-integral RFC 8785 values remain permitted.

## 5. Timestamp rules

`issued_at` and `expires_at` MUST be UTC timestamps exactly in this form:

```text
YYYY-MM-DDTHH:MM:SSZ
```

Offsets, fractional seconds, lowercase `z`, absent time zones, malformed dates,
and calendar-invalid values MUST be rejected. The envelope is invalid if
`expires_at` is not later than `issued_at`, if `issued_at` is later than the
verification time, or if `expires_at` is equal to or earlier than the
verification time. The equality rule deliberately treats expiry as exclusive.
A verifier needs an authenticated local source of current UTC time; trusted
clock distribution is outside this profile.

## 6. Raw JSON parsing and structure

Before canonicalization, a conforming raw-wire parser MUST reject malformed
JSON, malformed UTF-8, duplicate **decoded** object keys, unsupported numeric
representations, and invalid Unicode scalar values. A final raw-envelope
schema SHOULD define required fields, primitive types, unknown-field handling,
and permitted status values, and SHOULD reject inputs that violate those
definitions. Absent, `null`, empty string, and empty array SHOULD remain
distinct unless a final field definition explicitly states otherwise.

The current Python JCS parser demonstrates fail-closed duplicate-key,
non-finite-number, Unicode, and numeric-boundary behavior, but is explicitly a
generic object-level parser rather than a complete envelope wire schema. The
Python, Node, and Rust experiments demonstrate raw-value agreement; they do
not yet establish a complete cross-language required/unknown-field schema.
Accordingly, strict raw parsing and strict envelope schema validation are
candidate profile requirements and promotion gates, not a claim that the
current reference layer already exposes a finished wire protocol.

## 7. AdmissionProfile payload binding

The signed payload digest is `sha256:` followed by the SHA-256 digest of the
JCS-canonical complete `AdmissionProfile` representation. The demonstrated
profile contains `status`, `actor_id`, `place`, `space`, `policy_version`,
`evidence_digest`, `binding`, `operating_profile`, `restrictions`, `unresolved`,
and `reason_codes`. `binding` includes the actor, build, controller,
environment, plan, and policy binding values used by the reference model.

No field in that representation is treated as advisory once it is covered by
the profile digest. A verifier MUST recompute the digest from the received
profile and compare it exactly to `signed_payload_digest`; a mismatch fails
closed. This profile does not redesign `AdmissionProfile` or prescribe a new
SPP policy decision model.

## 8. JCS signed admission envelope

The experimental envelope fields are:

| Field | Meaning |
| --- | --- |
| `envelope_type` | Exact tested value `spp:admission-envelope`. |
| `envelope_version` | Exact tested value `0.1-experimental`. |
| `canonicalization_profile` | Exact signed profile identifier above. |
| `issuer_id` | Identifier used for local trust-anchor lookup. |
| `algorithm` | Exact tested value `Ed25519`. |
| `subject_id` | Subject for which the profile was issued. |
| `place`, `space` | Governed physical context. |
| `scope` | Derived as `place::space`. |
| `issued_at`, `expires_at` | Canonical UTC validity interval. |
| `signed_payload_digest` | JCS SHA-256 digest of the profile. |
| `signature` | Standard padded Base64-encoded Ed25519 signature. |
| `profile` | The complete bound `AdmissionProfile`. |

The Ed25519 signature input is JCS over an object containing exactly these
metadata fields: `issuer_id`, `algorithm`, `envelope_type`,
`envelope_version`, `canonicalization_profile`, `subject_id`, `place`, `space`,
`scope`, `issued_at`, `expires_at`, and `signed_payload_digest`. The
`AdmissionProfile` content is cryptographically bound through
`signed_payload_digest`; it is not included directly in this metadata
preimage. Implementations of this profile MUST NOT silently substitute another
algorithm; an unsupported algorithm fails closed. The current interoperability
fixtures use standard padded Base64 for both the signature and public-key
fixture representation. That fixture encoding is experimental and MAY be
finalized differently by a future raw-wire schema. The trust model is local:
the verifier receives a registry containing an enabled issuer public key and
authorization for the envelope type and derived scope.

## 9. Verification order

The tested JCS reference verifier fails closed in this effective order:

1. Confirm the envelope object, profile object, required nonempty values,
   supported profile, envelope type/version, and Ed25519 algorithm.
2. Confirm internal subject/place/space/scope consistency and parse canonical
   timestamps.
3. Apply time-range, future-issuance, and expiry checks; recompute the profile
   digest and compare it to the envelope field.
4. Look up the issuer locally; require that it is enabled and authorized for
   the envelope type and scope.
5. Decode and verify the Ed25519 signature over the JCS metadata input.
6. Compare the verified envelope to the caller's expected subject, place, and
   space; apply an optional local revocation/lifecycle hook.

Issuer authorization precedes signature verification in the reference path
because it selects the trusted public key. A raw-wire implementation SHOULD do
strict parsing and schema validation before this sequence. Any failure is
terminal for that reliance attempt.

## 10. Restriction identity and DEGRADED support

A restriction is identified by its exact nonempty string. Its identifier is
`sha256:` plus SHA-256 over JCS of `{"restriction": <exact string>}`. An
implementation MUST NOT trim, case-fold, fuzzy-match, or Unicode-normalize a
restriction. Whitespace-only restrictions are invalid.

For the demonstrated `DEGRADED` acknowledgement flow only, top-level profile
restrictions and `operating_profile.restrictions` are unioned, de-duplicated,
and sorted by UTF-16 code units to create the effective restriction list. The
restriction-profile binding covers profile status, actor/place/space, policy
version, evidence digest, evidence binding, operating profile without its
embedded restrictions, effective restrictions, unresolved values, and reason
codes. Other arrays, including guarantees, reason codes, unresolved values,
and test results, MUST remain ordered and MUST NOT be treated as sets.

A `RestrictionAcknowledgement` carries the restriction-profile identifier and
the exact restriction digest. A local enforcement mapping is matched using
that exact restriction digest and a matching nonempty handler identifier; the
mapping itself does not carry the restriction-profile identifier. One matching
acknowledgement and mapping are required for each effective restriction. This
establishes recognized configured mapping, not physical enforcement proof.

## 11. Failure taxonomy

Implementations MAY expose granular local reason codes. For portability,
equivalent outcomes SHOULD map to these non-normative categories:

| Category | Representative reference reasons |
| --- | --- |
| `malformed` | `malformed_envelope`, invalid JSON/value, wrong type, internal binding inconsistency. |
| `unsupported_profile` | `unsupported_canonicalization_profile`, cross-profile mismatch. |
| `invalid_signature` | malformed Base64/key/signature or failed Ed25519 verification. |
| `untrusted_issuer` | unknown, disabled, type-unauthorized, or scope-unauthorized issuer. |
| `subject_mismatch` | `envelope_subject_mismatch`. |
| `scope_mismatch` | `envelope_place_mismatch`. |
| `expired` | `envelope_expired`. |
| `invalid_time` | malformed, future, or invalid-range timestamp. |
| `binding_mismatch` | payload-digest or restriction-profile binding mismatch. |

Identical exception names are neither required nor demonstrated. An adapter
should preserve the underlying reason where it can do so safely.

## 12. Security considerations

Subject and place/space binding causes rejection when an artifact is presented
for a different expected subject or governed scope. Same-subject, same-scope
reuse remains allowed until expiry or local revocation; deployments needing
one-time use require an additional replay mechanism. The signature
binds the canonicalization profile, so profile-identifier tampering invalidates
the signature. Strict parsing avoids duplicate-key and numeric-normalization
confusion before signed bytes are trusted.

Trust state can become stale. Issuer disablement, revocation, policy changes,
subject changes, place changes, evidence expiry, and configuration changes
need local lifecycle/revalidation decisions at the reliance boundary. The
experimental P0 composition also requires a valid lifecycle result and exact
restriction acknowledgement for `DEGRADED`; `DENIED` remains terminal.

This profile does not prove enforcement, prevent TOCTOU after verification, or
attest physical state. A deployment remains responsible for revalidation after
material changes, safe enforcement, handler configuration, trusted clocks, and
the security of its local issuer registry.

## 13. Interoperability evidence

The evidence is limited but concrete: a Python reference implementation, a
dependency-free Node verifier, and an independent Rust verifier processed ten
deterministic golden vectors. They agreed on canonical bytes, SHA-256 digests,
Ed25519 signature inputs, profile bindings, restriction digests, and expected
admission/rejection outcomes. A 35-case deterministic adversarial corpus then
exercised duplicate keys, numeric boundaries, Unicode, container forms, and
timestamp spellings. After the Python numeric-boundary correction, all three
implementations produced zero disagreements and matched expected outcomes.

This demonstrates bounded reference interoperability. It is not a standards
certification, a production-security guarantee, or evidence that arbitrary
third-party implementations will interoperate without conformance testing.

## 14. Versioning

`canonicalization_profile` is independently versioned and included in the
signed metadata. An artifact issued under one profile MUST NOT be interpreted
under a later profile, even if its logical JSON appears similar. A profile
revision requires a new identifier and newly created signature; existing
experimental artifacts are not converted in place. This decouples a future
canonicalization-profile decision from the normative SPP 0.1 version.

## 15. Reference vectors

Implementers can use the committed materials in
`interop/experimental/admission-trust-jcs/`:

- `vectors.json` provides the ten golden envelope and restriction vectors;
- `profile-comparison.json` shows why legacy Python-profile bytes cannot be
  reused as JCS bytes;
- `adversarial-corpus.json` supplies the 35 raw-value cases; and
- the Python generator, Node verifier, Rust verifier, and differential runner
  provide repeatable reference checks.

Conformance testing SHOULD compare canonical UTF-8 bytes, digest, signature
input, signature verification, binding outputs, and expected failure category;
it SHOULD NOT merely compare a final allow/deny result.

## 16. Promotion gates

Before consideration for normative adoption, this candidate needs: a final
raw-wire schema with stable required/optional/unknown-field policy; broader
independent implementation review; stable envelope and `AdmissionProfile`
field definitions; trust-anchor, key lifecycle, and revocation decisions;
security review; compatibility/migration policy; and an explicit governance
decision. Additional implementation languages MAY add confidence, but are not
a substitute for resolving those design gates.

## 17. Conformance examples and expected behavior

The reference vectors are examples of exact bytes and outcomes, not merely
illustrations. A conforming experimental implementation SHOULD first use them
as black-box inputs, before attempting to create its own envelope. The valid
`ADMITTED` vector demonstrates a profile whose subject, place, space, scope,
payload digest, issuer authorization, canonical signature input, and Ed25519
signature all agree. A verifier returns a successful verification result only
after every applicable check succeeds. Successful signature verification alone
is not sufficient: a signed envelope presented for a different subject or
space is not valid for that requested context.

The valid `DEGRADED` vector demonstrates that canonicalization does not erase
restrictions. Its `AdmissionProfile` remains a `DEGRADED` profile after
verification; the envelope verifier does not upgrade it to `ADMITTED`. The
restriction acknowledgement vector separately demonstrates the existing
experimental rule for producing an effective restriction list and binding each
exact restriction to a digest and an enforcement handler identifier. This
profile does not state that the handler is technically capable of enforcement,
that it was executed, or that a physical robot complied. Those claims remain
outside the artifact-verification boundary.

Several negative vectors demonstrate why a final status alone is too coarse
for diagnostics. A changed profile causes a payload-digest mismatch before the
signature can be treated as evidence for the changed content. A changed
expected subject produces a subject-mismatch outcome after the artifact itself
has been validated. A changed expected place or space produces a scope-mismatch
outcome. An expired envelope is rejected even when its signature and issuer
remain valid. An unsupported profile is rejected rather than directed through
the legacy verifier. These distinctions help a deployment decide whether to
obtain a new artifact, correct its requested context, refresh time/trust state,
or stop reliance entirely.

The raw-value corpus complements those envelope vectors. It deliberately keeps
generic JSON acceptance separate from envelope-schema validity. For example,
an object with an `unexpected` field, a `null`, or an empty container can be a
valid generic canonicalizable JSON value; that does not mean it is a valid
envelope. Conversely, duplicate decoded keys, an unpaired surrogate, `NaN`,
negative zero, or an unsafe integral value are rejected before an envelope
schema is relevant. This distinction is intentional: canonicalization must
not turn malformed raw input into trusted bytes, and schema validation must
not be inferred from a generic parser's success.

## 18. Implementation and integration boundary

An implementation normally has three separable roles. A producer constructs an
`AdmissionProfile`, validates its values against the selected profile, derives
the JCS payload digest, and signs the required metadata with an authorized
private key. A verifier accepts an already-received artifact, applies the
profile-specific parsing and validation sequence, consults its locally
provisioned trust registry, and returns structured success or failure. A
consumer uses a successful result only for the exact requested
subject/place/space context, subject to its own lifecycle and operational
controls. These roles may reside in one process for a reference deployment,
but their trust responsibilities remain distinct.

The trusted issuer registry in the reference model is intentionally local. It
maps `issuer_id` to a public key, enabled state, allowed envelope types, and
allowed scopes. The registry is not a certificate authority and has no remote
key discovery behavior. An implementation MUST treat absence of the issuer,
disabled state, an unauthorized envelope type, or an unauthorized scope as
failure. It MUST NOT attempt an online lookup or accept a key carried by the
untrusted envelope as a replacement for its local trust anchor unless a future
profile explicitly defines that process.

The JCS-specific verifier is similarly not an invitation to use generic JSON
serialization for signature material. The Python reference calls an RFC 8785
library; the Node verifier has a dependency-free implementation for the fixed
profile; and the Rust verifier uses `serde_jcs`. Each independently calculates
canonical material from fixture content. A different implementation MAY use a
different maintained RFC 8785 library, but it still needs to reproduce the
committed canonical bytes and profile restrictions. Merely emitting compact
JSON, sorting keys according to a host-language default, or relying on
language-specific floating-point serialization is insufficient evidence of
conformance.

Likewise, the restriction rules do not turn arbitrary policy prose into a
portable ontology. The demonstrated identity is intentionally narrow: the
exact restriction string is the value bound and acknowledged. Two visually
similar strings can be different restrictions. A future SPP vocabulary may
offer structured restriction fields, but this profile neither requires nor
assumes one. Until then, integrations should preserve exact received strings,
their calculated digest, and the associated profile binding rather than
attempting to infer equivalence.

## 19. Candidate conformance procedure

For this experimental profile, a prospective implementation can use the
following bounded procedure. It SHOULD load `vectors.json` as UTF-8, parse it
with duplicate-key rejection, and check every golden vector's expected result.
For valid envelope vectors, it SHOULD reproduce the supplied canonical profile
bytes, payload digest, and signature-input bytes exactly before attempting
signature verification. It SHOULD then verify the supplied Ed25519 signature
using the supplied public test key and compare the expected subject/place/space
result. For the restriction vector, it SHOULD reproduce effective restriction
ordering, each restriction digest, and the full restriction-profile identifier.

It SHOULD next run `adversarial-corpus.json` through its raw parser and JCS
value validator. A result is conformant to the demonstrated corpus when it
matches each declared `accepted` or `malformed` outcome and has no unexplained
cross-language difference. The corpus includes safe integer endpoints, unsafe
integer values, positive and negative zero forms, exponent values, finite
fractions, non-finite constants, Unicode representations, and malformed JSON.
It is deliberately finite. Passing it does not prove a parser is secure under
unbounded malformed input, nor does it replace an implementation's own limits
for nesting depth, input size, or resource exhaustion.

Finally, the implementation SHOULD preserve enough local diagnostic detail to
map a failure to the categories in Section 11. It need not expose private trust
configuration, raw signatures, or internal stack traces. A deployment can
return a safe machine-readable category to an adapter while retaining detailed
audit material in a protected local log. That choice is deployment policy and
does not affect the canonical bytes or verification outcome defined here.

The procedure intentionally does not define universal resource limits. A
production receiver still needs deployment-specific limits for message size,
nesting depth, signature-verification rate, trusted-issuer registry size, and
clock-skew handling. Such limits can affect availability and denial-of-service
resistance, but they have not been harmonized across the reference
implementations and therefore are not profile conformance rules in this draft.
