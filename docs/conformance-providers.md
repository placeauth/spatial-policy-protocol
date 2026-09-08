# External conformance providers

An external conformance provider is a locally registered implementation that
evaluates a place requirement for a particular embodiment. It lets a provider
add a conformance mechanism without changing the core admission model.

This is a reference interface, not a provider marketplace or certification
program. Providers are configured explicitly in-process.

## Contract

An `ExternalConformanceProvider` exposes a `ConformanceProviderDescriptor` and
an `evaluate(requirement, subject)` method. The descriptor contains:

- provider ID and version;
- supported requirement IDs with an exact version set, embodiments, and
  assurance levels (`E0` through `E4`);
- evidence type; and
- optional description and deterministic priority.

`supported_requirement_versions` is an ID-to-version set. Every supported
requirement must have an explicit non-empty set; registration rejects an
incomplete descriptor. Selection requires an exact compatible version.
Requirement IDs, versions, units, and comparison meanings are defined by the
[requirement vocabulary](requirement-vocabulary.md).

```python
ConformanceProviderDescriptor(
    provider_id="gait-speed-provider", provider_version="1.0",
    supported_requirement_types=frozenset({"movement.max_speed"}),
    supported_requirement_versions={"movement.max_speed": frozenset({"1.0"})},
    supported_embodiments=frozenset({"humanoid"}),
    supported_assurance_levels=frozenset({"E2", "E3"}),
    evidence_type="behavioral_test", priority=100,
)
```

`evaluate` returns a `ConformanceProviderResult` with provider ID/version,
requirement ID/version, pass/fail result, measured value, canonical unit,
assurance level, evidence type, reasons, and metadata.

## Local selection

`ConformanceProviderRegistry` accepts providers through explicit registration
and rejects duplicate provider IDs. For a requirement and subject embodiment,
it resolves the vocabulary definition, then filters by exact requirement
ID/version, exact embodiment, and requested minimum assurance level. It selects
the highest priority provider; provider ID is the stable tie breaker. An
unresolved selection reports whether the requirement, version, embodiment, or
assurance level was unsupported. It never guesses a provider, lowers assurance,
or coerces an embodiment.

## Evidence and admission

Before `to_evidence_result()` may be used, the registry verifies the selected
descriptor and vocabulary bindings: provider ID/version, requirement ID/version,
embodiment, assurance, evidence type, canonical unit, pass/fail type, reasons,
and metadata. A mismatch fails closed with a deterministic provider-result
error. The established path remains:

`Place Package -> vocabulary -> provider execution -> validated test result -> EvidenceBundle -> trusted evidence issuer signature -> admission`.

Provider identity is distinct from an evidence issuer. When signed evidence is
needed, the existing trusted-issuer verification layer signs and verifies the
generated evidence separately. Provider registration does not imply trust.

## Minimal example

```python
from spp_admission import ConformanceProviderRegistry
from gait_speed_provider import GaitSpeedProvider

registry = ConformanceProviderRegistry([GaitSpeedProvider()])
selection, result = registry.evaluate(requirement, subject)
```

Run the deterministic reference demo:

```sh
python demo/conformance_provider/run_demo.py
```

## Limits

There is no provider discovery, dynamic loading, network service, sandboxing,
certificate-based provider trust, remote registry, provider installation,
supply-chain attestation, or vendor certification in this reference
implementation. Registering a provider is a local operator configuration
decision; its execution environment and real-world test quality remain outside
SPP admission.
