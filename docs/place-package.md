# Place Package 0.1

A Place Package is one portable JSON file that carries a place's complete
PlaceRequirementSet and a policy-authority signature. It is additive reference
infrastructure: it does not change normative SPP 0.1 policy, request, or
decision semantics.

## Format

The package has these required fields:

- `place_package_version`: supported format version, currently `"0.1"`.
- `place_id`: applicable primary space; it must equal `requirements.space`.
- `policy_id` and `policy_version`: identifiers mirrored from the requirement
  set (`requirement_set_id` and `policy_version`).
- `scope`: one or more applicable space identifiers, including `place_id`.
- `authority_id`: local trusted-policy-authority lookup key.
- `requirements`: complete SPP PlaceRequirementSet payload.
- `metadata`: optional inspectable object for non-normative information such as
  a human-readable name or description.
- `algorithm`: currently `Ed25519`.
- `package_digest`: SHA-256 digest of all package content except
  `package_digest` and `signature`.
- `signature`: base64 Ed25519 signature over canonical authority ID, algorithm,
  and package digest.

The canonical example is
[`examples/place-packages/clinic-patient-wing.json`](../examples/place-packages/clinic-patient-wing.json).

## Canonicalization and verification

JSON is canonicalized as UTF-8 JSON with lexicographically sorted keys and no
insignificant whitespace. The verifier first validates package structure and
version, looks up the local authority, checks that it is enabled and authorized
for the package's place/scope, validates the embedded requirement set, checks
the recomputed package digest, and finally verifies the Ed25519 signature.

`verify_place_package(...)` returns `PlacePackageVerification` with `valid`,
ordered reason codes, package digest, and authority ID. Typical failures are
`unsupported_place_package_version`, `invalid_place_package`,
`unknown_policy_authority`, `policy_authority_disabled`,
`policy_authority_unauthorized`, and `place_package_signature_invalid`.

The package supplies an authority identifier, not a trust anchor. Consumers
must provision trusted public keys locally in `TrustedPolicyAuthorityRegistry`.
For an installed reference package, verify with:

```sh
spp-place-package verify examples/place-packages/clinic-patient-wing.json \
  --authority-key <base64-raw-ed25519-public-key> --json
```

`--authority-key` is an explicit local trust input for the reference CLI. A
production consumer should obtain its local trusted authority registry through
its own protected configuration.

## Limits

Place Package 0.1 supports single-file offline exchange and deterministic
tamper detection. It does not provide network discovery, a global registry,
PKI or certificate chains, DNS trust, remote revocation, automatic trust-anchor
distribution, or proof that an authority legally or physically controls a
place.
