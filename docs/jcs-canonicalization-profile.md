# RFC 8785 JCS canonicalization profile (experimental)

**RFC 8785 JCS support is experimental and does not modify normative SPP 0.1.**

PlaceAuth is evaluating `rfc8785-jcs-v1-experimental` as a future portable
canonicalization profile for experimental AdmissionProfile envelopes. The
existing `spp-python-json-v1-experimental` profile remains unchanged. It has
different bytes, digests, and signatures for the same logical object and must
not be reinterpreted as JCS.

The JCS profile signs its explicit profile identifier alongside envelope type,
version, issuer, subject, place, space, scope, timestamps, and profile digest.
It accepts only a safe portable subset: well-formed Unicode, exact UTC-second
timestamps, and finite numbers. A numeric value that is mathematically integral
(including exponent-form values) must be within `-(2^53-1)` through
`2^53-1`. A zero value may not carry a negative sign: raw `-0`, raw `-0.0`,
and programmatic negative-zero floats fail closed. Finite non-integral numbers
remain valid RFC 8785 values. Unknown profiles, cross-profile artifacts,
duplicate JSON keys, malformed Unicode, non-finite numbers, oversized
integral values, and noncanonical timestamps fail closed.

The experimental vectors, independent Node verifier, byte comparison, profile
dispatch rules, and migration limits are documented in the [JCS interoperability
directory](../interop/experimental/admission-trust-jcs/README.md).
