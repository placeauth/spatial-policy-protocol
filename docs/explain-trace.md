# Explain an SPP decision

`spp-explain` is a developer-facing view of the existing experimental
conformance and admission outputs. It does not evaluate policy, select a
different outcome, or add protocol fields.

After installing the project, run:

```sh
spp-explain --scenario patient-wing
```

The module form is equivalent and works from a source checkout with the
package on `PYTHONPATH`:

```sh
python -m spp_admission.explain --scenario patient-wing
```

Use `--json` for a deterministic object containing applicable requirements,
provider selection, evidence sufficiency assessment, requirement delta,
selected tests, reused guarantees, and the admission result with restrictions
and reason codes.

Available scenarios reuse the admission demo fixtures:

- `patient-wing` shows a prior movement bound rejected as insufficient and new
  tests selected.
- `reused` shows accepted source movement evidence.
- `tampered` exposes the existing `evidence_digest_mismatch` rejection.
- `denied` shows an essential failed test reaching a `DENIED` profile.

The trace is a local reference/debugging aid. It does not replace evidence,
admission, enforcement, or physical-safety controls.
