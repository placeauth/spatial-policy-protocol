# Independent Rust verification of the experimental JCS admission profile

**Status: experimental. This work does not modify normative SPP 0.1.**

## Purpose and approach

`interop/experimental/admission-trust-jcs/rust-verifier` is a deliberately
separate verifier for `rfc8785-jcs-v1-experimental`. It consumes the committed
JSON fixtures and their public Ed25519 key material. It does not invoke the
Python producer or the Node verifier to calculate canonical bytes, digests, or
signature decisions.

The Rust implementation uses `serde_jcs` for RFC 8785 serialization,
RustCrypto `sha2` for SHA-256, and `ed25519-dalek` for Ed25519 verification.
Its raw JSON boundary uses a custom Serde visitor to reject duplicate decoded
keys, and a small lexical guard to reject unpaired surrogate escapes and
integer `-0` before parsing loses those distinctions.

## Portable-profile rules tested

The verifier applies the existing experimental constraints: JCS profile
identifier is signed and exact; timestamps are UTC seconds; scope equals
`place::space`; subject/place/space bind the signed profile; issuer type and
scope authorization are local; and restriction profile identifiers use the
same effective-restriction set semantics. Arrays otherwise remain ordered.

The raw-value boundary rejects non-finite values, negative zero, and integral
values outside the JavaScript safe range. The explicit numeric contract is:

- a zero value must not carry a negative sign (`-0` and `-0.0` are invalid at
  the raw boundary, as is a programmatic negative-zero float);
- every mathematically integral numeric value, including exponent-form values,
  must be within `-(2^53-1)` through `2^53-1`; and
- finite non-integral values remain valid RFC 8785 inputs.

Python applies this contract using `json.loads` numeric callbacks, which reject
lexical `-0` before parsing erases the sign, and its direct value validator
applies the same integral-float rule. Node and Rust enforce the same semantic
checks.

`adversarial-corpus.json` contains 35 deterministic raw-JSON cases covering
duplicate keys, nesting, null/empty containers, number boundaries, Unicode,
and timestamp spellings. `run_adversarial_corpus.py` runs the same corpus
through Python, Node, and Rust and reports disagreements without suppressing
them. It is deliberately bounded rather than a broad fuzzing framework; a
future fuzz stage should generate minimized fixture files from a fixed seed.

## Parser and taxonomy recommendation

Future wire-format work should validate twice: a strict raw JSON parse before
canonicalization (duplicate keys, UTF-8/scalar values, and numeric form), then
schema/profile validation before signature verification (required fields,
unknown fields, types, status values, and bindings). The current object-level
reference verifier is not yet a full raw-envelope parser, so extra/missing
field handling must not be claimed as cross-language interoperable.

A non-normative common taxonomy is: `malformed`, `unsupported_profile`,
`invalid_signature`, `untrusted_issuer`, `subject_mismatch`, `scope_mismatch`,
`expired`, `invalid_time`, and `binding_mismatch`. Implementations may retain
more granular local reason codes.

## Remaining risks

The independent verifier is a useful interoperability check, not an SDK or a
standards claim. It does not provide a normative raw-wire schema, issuer
federation, key lifecycle, physical evidence trust, or production performance
guarantees. Canonically equivalent Unicode strings are intentionally not
normalized; escaped and literal valid Unicode must decode to the same scalar
string, while NFC/NFD remain distinct values.
