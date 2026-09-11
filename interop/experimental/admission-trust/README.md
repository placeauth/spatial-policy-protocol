# Experimental admission-trust interoperability vectors

This directory is an **experimental** interoperability profile for the current
Python reference implementation. It does not modify normative SPP 0.1, define
a new wire format, or establish general cross-language interoperability.

## Contents

- `vectors.json` — eight deterministic public test vectors; no private key is
  included.
- `generate_vectors.py` — the Python reference producer using a deterministic,
  test-only Ed25519 seed.
- `verify_vectors.mjs` — a dependency-free JavaScript verifier using only Node
  standard-library cryptography. It does not invoke Python.

Run both sides from the repository root:

```powershell
python interop/experimental/admission-trust/generate_vectors.py --check
node interop/experimental/admission-trust/verify_vectors.mjs interop/experimental/admission-trust/vectors.json
```

The vectors cover a valid `ADMITTED` envelope, a valid `DEGRADED` envelope,
post-signing profile modification, wrong subject, wrong place/space, expiry,
exact restriction acknowledgement, and an unsupported envelope version.

## Current Python reference encoding inventory

| Logical representation | Producer | Bytes / algorithm | Ordering and presence behavior |
| --- | --- | --- | --- |
| AdmissionProfile payload digest | `admission_envelope._profile_digest` | `dataclasses.asdict(profile)`, then `engine._canonical(...).encode("utf-8")`, SHA-256 with `sha256:` prefix | Object keys sorted by Python string order. Dataclass fields are all present. Arrays are preserved in order. No Unicode normalization. |
| Envelope signature input | `admission_envelope._signature_payload` | Canonical JSON object with issuer, algorithm, type/version, subject, place, space, scope, literal timestamps, and profile digest; UTF-8; Ed25519 | Object keys sorted. All listed fields are required. Metadata string changes—including an equivalent timestamp spelling—change the signature bytes. |
| Envelope scope | `admission_scope` | Exact string concatenation: `place + "::" + space` | Place and space are opaque exact strings; no normalization. |
| Lifecycle profile identity | `lifecycle.profile_identifier` | `asdict(profile)`, reference canonical JSON, SHA-256, `urn:spp:profile:` prefix | Full profile list ordering and duplicate values are semantic. |
| Restriction identity | `restriction_acknowledgement.restriction_identifier` | Canonical JSON `{"restriction": <exact string>}`, UTF-8, SHA-256 | Exact string only: no trimming, case folding, or Unicode normalization. |
| Restriction acknowledgement profile binding | `restriction_profile_identifier` | Canonical JSON over full profile except the two restriction locations are replaced by sorted, de-duplicated effective restrictions; SHA-256, `urn:spp:restriction-profile:` prefix | `profile.restrictions` and `operating_profile.restrictions` are unioned as a set. Other arrays, including guarantees, remain ordered. |
| Evidence digest relevant to a profile | `engine.build_evidence` / `engine.digest` | Evidence object excluding no fields at creation, UTF-8 reference canonical JSON, SHA-256 | At admission verification, `evidence_digest` itself is excluded to avoid recursion. `EvidenceBinding` is not separately digested; its six fields are carried inside evidence and the signed profile. |

`engine._canonical` currently means Python `json.dumps(value, sort_keys=True,
separators=(",", ":"))` with its defaults. Those defaults include
`ensure_ascii=True` and `allow_nan=True`. Envelope signing rejects non-finite
numbers before signing, but the general digest helper does not. This distinction
is intentional in the inventory because it is a cross-language hazard.

## Current Python profile versus future portable profile

The fixture profile name `spp-python-json-v1-experimental` identifies the
current behavior reproduced by the JavaScript verifier. It is **not** a promise
that arbitrary Python values can be serialized identically by every language.
The verifier deliberately supports the vector subset and demonstrates the
actual Ed25519, SHA-256, scope, restriction, and reason-code boundaries.

### Numbers

Current Python accepts arbitrary-size integers and serializes Python floats.
Its generic JSON helper can render `NaN` and infinities, while the envelope
signer rejects non-finite values. JavaScript uses IEEE-754 binary64 and cannot
losslessly represent all Python integers; exponent spelling and negative-zero
rendering can also differ across runtimes. A future portable profile should
allow only finite IEEE-754 values, reject integers outside the interoperable
range unless encoded as strings, and use its chosen canonicalization standard
for rendering. Do not infer portability from the fixture's `0.5` value.

### Strings and object keys

Current Python emits UTF-8 bytes containing ASCII JSON escapes for non-ASCII
characters (`ensure_ascii=True`). It sorts keys using Python Unicode string
ordering, performs no NFC/NFD normalization, and has no raw-JSON parser at the
envelope boundary. Consequently composed `"café"` and decomposed
`"cafe\u0301"` are distinct values and digests. Unpaired surrogates and
language-specific string comparison are not suitable for portable artifacts.

The JavaScript verifier independently recreates Python escape output and
code-point key sorting for the vectors. A future portable format should require
well-formed Unicode scalar values, UTF-8, no normalization unless explicitly
specified, and a parser that rejects duplicate decoded object keys.

### Arrays, optional values, and timestamps

Arrays are ordered unless a representation explicitly defines set behavior.
Only the two existing restriction lists are unioned, sorted, and de-duplicated
for the acknowledgement binding. Guarantees, reason codes, unresolved values,
and test results are not sorted by this experimental profile.

The current dataclass API materializes all AdmissionProfile fields. A future raw
wire parser must declare required fields and distinguish absent, JSON `null`,
empty string, and empty array; they must not be silently coerced. The current
envelope signer renders UTC `Z` timestamps, but its verifier accepts any
offset-aware ISO-8601 form and signs the literal string. Equivalent instants
with different textual forms therefore have different signature bytes.

The future portable profile should require UTC RFC 3339 timestamps in exactly
`YYYY-MM-DDTHH:MM:SSZ` form, reject fractional seconds unless a later explicit
precision version allows them, and reject duplicate keys before semantic
processing.

## Canonicalization options

| Option | Assessment |
| --- | --- |
| A. Restricted current Python JSON | Useful for the checked test vectors and a short-lived reference-only profile. It has no dependency burden, but requires each language to reproduce Python escaping, number rendering, and key order. It is not adequate as a broad future interoperability contract. |
| B. RFC 8785 JSON Canonicalization Scheme (JCS) | Recommended candidate for a future portable experimental profile. It provides an established UTF-8 canonical JSON algorithm with defined object sorting and number rules, supports the current JSON-shaped AdmissionProfile structures, and has mature implementations in the requested languages. Migrating would change bytes, digests, and signatures, so existing experimental artifacts must remain labeled with the current profile rather than being reinterpreted. |
| C. Existing Place Package convention | Not an independent alternative: `place_package.py` also uses `engine._canonical`. It does not solve the current Python-specific serialization risks. |

The recommendation is **JCS for a later explicitly versioned portable
experimental profile**, not retroactive reinterpretation of current envelopes.
The current fixture profile remains useful as a migration baseline and test
oracle.

## Versioning recommendation

Any future interoperable signed artifact should include one required immutable
field such as `canonicalization_profile`, for example
`jcs-rfc8785-v1-experimental`. It should be covered by the signature alongside
the envelope schema/type version. An envelope version alone is insufficient:
the same logical envelope fields can have different bytes if canonicalization
rules change. Existing artifacts should be treated as
`spp-python-json-v1-experimental` by out-of-band context only; do not alter the
current experimental envelope schema to backfill the field without a separate
compatibility design.
