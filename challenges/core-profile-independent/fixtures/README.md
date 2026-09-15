# Canonical shared fixtures

The challenge deliberately references, rather than copies, the engine-neutral
Core Profile fixtures. This prevents a challenge copy from drifting from the
fixtures evaluated by the native and OPA reference implementations.

- [permit](../../../experiments/core-profile/fixtures/permit.json)
- [deny](../../../experiments/core-profile/fixtures/deny.json)
- [conditional](../../../experiments/core-profile/fixtures/conditional.json)
- [unknown required obligation](../../../experiments/core-profile/fixtures/unknown-required-obligation.json)
- [scope mismatch](../../../experiments/core-profile/fixtures/scope-mismatch.json)
- [normal context](../../../experiments/core-profile/fixtures/context-normal.json)
- [emergency context](../../../experiments/core-profile/fixtures/context-emergency.json)
- [inheritance/conflict](../../../experiments/core-profile/fixtures/inheritance-conflict.json)

Use these files unchanged as the input corpus for an independent implementation.
