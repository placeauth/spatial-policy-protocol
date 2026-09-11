# Admission-trust interoperability (experimental)

**Status:** Experimental. This document does not modify normative SPP 0.1.

The current admission-trust reference code can be reproduced outside Python for
the published test-vector subset: a dependency-free JavaScript verifier
independently recreates the current Python canonical representation, SHA-256
payload and restriction digests, Ed25519 envelope verification, subject/place
binding, and exact restriction-acknowledgement binding.

That result is intentionally narrower than a general interoperability claim.
The present Python serializer depends on `json.dumps` defaults and dataclass
construction, which leave important cross-language issues around floating
numbers, large integers, Unicode ordering, malformed Unicode, raw JSON parser
behavior, and timestamp spellings. Existing experimental envelopes must not be
treated as a portable wire standard merely because the reference vectors pass.

The full inventory, vectors, independent verifier, hazards, and proposed future
canonicalization direction are in [the experimental interoperability
directory](../interop/experimental/admission-trust/README.md).

The current recommendation is to retain the Python representation as a labeled
reference profile and evaluate an explicitly versioned RFC 8785 JCS profile for
any later portable experimental artifact. This would be a new compatibility
profile, not a reinterpretation of existing signatures.
