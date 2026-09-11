# Rust JCS verifier (experimental)

This is an independent verifier for `rfc8785-jcs-v1-experimental`. It reads
only the machine-readable vectors and test public keys; it does not shell out
to Python or Node to obtain a canonical representation, digest, or signature
result.

It uses `serde_jcs` for RFC 8785 serialization, RustCrypto `sha2` for
SHA-256, and `ed25519-dalek` for Ed25519 verification. `strict_parse` rejects
duplicate decoded keys, unpaired surrogate escapes, negative zero, non-finite
numbers, and integers outside the JavaScript safe range before canonicalizing.

```powershell
cargo test --manifest-path interop/experimental/admission-trust-jcs/rust-verifier/Cargo.toml
cargo run --manifest-path interop/experimental/admission-trust-jcs/rust-verifier/Cargo.toml -- interop/experimental/admission-trust-jcs/vectors.json
```

This verifier is experimental and does not modify normative SPP 0.1.
