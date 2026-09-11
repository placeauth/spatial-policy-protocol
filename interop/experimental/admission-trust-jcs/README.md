# Experimental RFC 8785 JCS admission-trust profile

**RFC 8785 JCS support is experimental and does not modify normative SPP 0.1.**

This directory evaluates a second, portable canonicalization profile for
experimental signed AdmissionProfile envelopes. It does not replace the
existing `spp-python-json-v1-experimental` reference profile, rewrite its
signatures, or infer a profile when one has not been explicitly selected.

## Profile and implementation

The JCS profile identifier is:

```text
rfc8785-jcs-v1-experimental
```

The Python reference uses the small [`rfc8785`](https://pypi.org/project/rfc8785/)
package (0.1.4 in the validated environment) for canonical bytes. The package
is used because Python's standard JSON encoder is not an RFC 8785
implementation; a hand-written approximation would be unsafe for a signature
format. The independent `verify_vectors.mjs` implementation uses only Node's
standard library and does not invoke Python.

`canonicalization_profile` is a required field of `JCSSignedAdmissionEnvelope`
and is included in the JCS canonical signature input. Changing a valid JCS
artifact's profile identifier without resigning invalidates the signature.
`verify_profiled_admission_envelope(...)` requires an explicit profile choice:

- `spp-python-json-v1-experimental` dispatches only to the pre-existing Python
  envelope type.
- `rfc8785-jcs-v1-experimental` dispatches only to the JCS envelope type.
- Unknown profiles and cross-profile envelope/type combinations fail closed.

The legacy profile has no retroactively added field. Its direct legacy verifier
continues to preserve its original bytes and behavior. It must not be described
as a JCS artifact.

## Portable-profile restrictions

The JCS experimental profile accepts JSON `null`, booleans, strings, arrays,
objects, finite numbers, and integers only within JavaScript's safe integer
range (`-(2^53-1)` through `2^53-1`). It fails closed for:

- non-finite numbers;
- negative zero;
- integers outside that range;
- non-string object keys;
- malformed Unicode scalar values, including unpaired surrogates;
- unsupported values;
- duplicate decoded JSON keys; and
- unknown profile identifiers.

Arrays remain ordered. The only set-like normalization is the existing
restriction-acknowledgement rule: top-level and embedded restriction lists are
unioned, de-duplicated, and ordered by UTF-16 code units before JCS profile
binding. Guarantees, reason codes, unresolved values, test results, and all
other arrays are not reordered.

## Time and raw JSON handling

JCS envelopes require UTC timestamps exactly in this form:

```text
YYYY-MM-DDTHH:MM:SSZ
```

Fractional seconds, offset spellings, naive timestamps, and invalid calendar
values are rejected. This prevents equivalent instants from becoming distinct
valid JCS envelope representations.

`parse_jcs_json(...)` is a small fail-closed generic JSON parsing boundary, not
a complete normative envelope parser. It rejects duplicate keys and constants
such as `NaN` before JCS value validation. A future wire format must retain
these rejection rules and define its required/optional fields explicitly;
absent, `null`, empty string, and empty array are not silently interchangeable.

## Vectors and independent verification

`vectors.json` contains ten deterministic test-only vectors: valid ADMITTED
and DEGRADED envelopes; tampering; subject/place/scope mismatch; expiry; exact
restriction acknowledgement; unsupported profile; exponent-form numeric data;
and Unicode data. `profile-comparison.json` shows the same logical profile
under both existing Python and JCS profiles. The canonical bytes, digests, and
signatures intentionally differ.

```powershell
python interop/experimental/admission-trust-jcs/generate_vectors.py --check
node interop/experimental/admission-trust-jcs/verify_vectors.mjs interop/experimental/admission-trust-jcs/vectors.json
```

The generator uses a deterministic test-only key seed; no private key is stored
in any fixture. Future migration would require a newly signed JCS envelope and
explicit profile selection. Existing Python-profile signatures cannot be
converted or reinterpreted in place.
