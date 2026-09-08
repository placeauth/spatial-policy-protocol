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
- supported requirement IDs, embodiments, and assurance levels (`E0` through
  `E4`);
- evidence type; and
- optional description and deterministic priority.

Providers may also declare supported_requirement_versions as an ID-to-version
set. Selection requires an exact compatible version. Existing descriptors that
omit this field retain compatibility with built-in version 1.0 only. Requirement
IDs, versions, units, and comparison meanings are defined by the
[requirement vocabulary](requirement-vocabulary.md).

`evaluate` returns a `ConformanceProviderResult` with the provider identity,
requirement ID, pass/fail result, measured value, assurance level, evidence
type, and optional metadata.

## Local selection

`ConformanceProviderRegistry` accepts providers through explicit registration
and rejects duplicate provider IDs. For a requirement and subject embodiment,
it filters to compatible providers that meet the requested minimum assurance
level. It selects the highest priority provider; provider ID is the stable tie
breaker. An unresolved selection reports whether the requirement, embodiment,
or assurance level was unsupported.

## Evidence and admission

The result's `to_evidence_result()` method adapts the result to the existing
conformance-plan test result. The established path remains:

`provider execution -> existing test result -> EvidenceBundle -> admission`.

Provider identity is distinct from an evidence issuer. When signed evidence is
needed, the existing trusted-issuer verification layer signs and verifies the
generated evidence separately.

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
certificate-based provider trust, remote registry, or vendor certification in
this reference implementation. Registering a provider is a local operator
configuration decision; its execution environment and real-world test quality
remain outside SPP admission.
