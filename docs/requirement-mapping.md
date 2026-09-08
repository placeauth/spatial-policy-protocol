# Embodiment-specific requirement mapping

SPP place requirements describe the guarantee a place needs, not a particular
robot test. The experimental reference implementation uses a small local
`RequirementMappingRegistry` to select a deterministic conformance mechanism
from a requirement ID, an embodiment, and a required assurance level.

Built-in mappings support vocabulary version 1.0. An omitted version on a
built-in is the explicit compatibility default; an incompatible requested
version remains unresolved. See the [requirement vocabulary](requirement-vocabulary.md).

The included mappings demonstrate the distinction:

| Place requirement | Mobile-base mechanism | Humanoid mechanism |
| --- | --- | --- |
| `movement.max_speed` | speed-bound check | gait-speed-bound check |
| `human_separation` | separation-bound check | body-proximity-bound check |
| `sensing.facial_recognition` | camera policy check | vision-pipeline privacy check |

Providers are configured explicitly in-process. Each provider declares its
supported requirement ID and embodiment, assurance level, deterministic
priority, and a test factory. The highest-priority compatible provider wins;
provider ID is the tie breaker. If no compatible provider is registered, the
requirement remains in `unresolved_guarantees` and no synthetic test is made.

This is a reference mapping registry, not a plugin system, middleware layer,
vendor certification, or a claim that either mechanism is a physical-safety
guarantee.

## Run the demonstration

```sh
python demo/embodiment_mapping/run_demo.py
```

The demo builds the same place requirement set for a mobile base and a
humanoid, selects the registered mechanisms, executes the selected tests,
binds the results into evidence, and derives an `ADMITTED` profile for each
reference state.
