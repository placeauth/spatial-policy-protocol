# SPP Core Profile — Independent Implementation Challenge

## What this is

This is a small, **non-normative interoperability challenge** for the
experimental SPP Core Profile. It asks a practical question: can an engineer
who has not worked on PlaceAuth implement the profile from its public contract
and eight shared fixtures, then obtain the same normalized results?

Use any language, runtime, policy engine, or architecture. OPA, XACML, Cedar,
and custom code are all reasonable choices. This is not a benchmark contest,
certification program, or claim that SPP 0.1 has changed. A disagreement is a
useful result: it may expose an ambiguous rule, an unnecessary field, an
engine-dependent assumption, or a better existing-policy mapping.

For the first pass, implement independently. Do not reuse PlaceAuth evaluator
code or the existing Rego implementation. Those are reference implementations,
not the challenge specification.

## What you are given

Use only these materials during your first independent attempt:

1. [The experimental SPP Core Profile](../../docs/experimental/spp-core-profile.md).
2. The eight canonical JSON files linked from [`fixtures/`](fixtures/).
3. The normalized expected outputs in [`expected/`](expected/).

`fixtures/` contains portable relative links to the one canonical fixture set
in [`experiments/core-profile/fixtures/`](../../experiments/core-profile/fixtures/);
the JSON is intentionally not duplicated. The expected files are the `expected`
objects already established for those canonical fixtures; they do not add policy
semantics.

To preserve the value of the exercise, first derive outcomes from the profile
and fixtures, then compare them with the expected outputs. This is
interoperability testing, not a blind test: expected results are deliberately
available for review.

## Your task

Build a small evaluator that accepts each fixture/profile input and produces
exactly this normalized JSON object:

```json
{"decision":"PERMIT|DENY|CONDITIONAL","obligations":[],"reason_codes":[]}
```

Your implementation must handle the supported-versus-unsupported required
obligation distinction, governed-scope and context semantics, and deterministic
results. Use the Core Profile as the source of meaning. In particular,
`CONDITIONAL` is not permission, and an unrecognized required obligation must
fail closed using the profile-defined result. Do not silently invent behavior
when the profile is unclear—record the ambiguity instead.

## Rules for the independent pass

**Do:**

- use a language and policy engine of your choice;
- interpret the public Core Profile literally;
- retain the requested normalized fields and deterministic JSON values; and
- document any ambiguity, assumption, or disagreement.

**Do not:**

- copy `experiments/core-profile/native/`;
- copy `experiments/core-profile/opa/`;
- inspect those implementations before completing the first pass; or
- silently supply semantics that the profile does not state.

If something is unclear, write it down. Discovering unclear wording is part of
the experiment.

## Fixtures

| Fixture | Purpose |
| --- | --- |
| `permit` | Tests inherited permission from a governed parent scope. |
| `deny` | Tests a nearer scope denying an otherwise permitted action. |
| `conditional` | Tests a conditional result with a required authorization and obligation. |
| `unknown-required-obligation` | Tests fail-closed reliance when the deployment does not support a required obligation. |
| `scope-mismatch` | Tests denial when the requested scope is outside the supplied governed chain. |
| `context-normal` | Tests the normal-context branch of context-sensitive rules. |
| `context-emergency` | Tests the emergency-context branch of context-sensitive rules. |
| `inheritance-conflict` | Tests nearest-scope precedence over a broader wildcard rule. |

The names are for reporting only. They do not replace the Core Profile's
contract or disclose a required implementation approach.

## Optional self-check

After your evaluator writes one normalized JSON output per fixture, compare
your result directory without exposing any PlaceAuth policy logic:

```sh
python challenges/core-profile-independent/check_results.py path/to/my/results
```

The directory must contain files named `permit.json`, `deny.json`, and so on.
The script compares parsed JSON values only; it does not evaluate SPP rules,
provide a reference implementation, or normalize your output.

## How to report results

Open a GitHub issue or discussion using this suggested title:

```text
Independent Core Profile Implementation — <language/engine>
```

Include the information in [REPORT-TEMPLATE.md](REPORT-TEMPLATE.md): language,
runtime, policy engine and version, fixtures matched, disagreements,
ambiguities, missing information, unnecessary rules, and useful mappings to
existing standards. Categorize the feedback as an **ambiguity**, **semantic
disagreement**, **implementation result**, or **existing-standard mapping**.
For an issue that is security-sensitive, use `security@placeauth.org` rather
than a public report.

Blunt feedback is welcome. An 8/8 match alone is not the only successful
outcome. It is at least as valuable to find ambiguity, redundant data,
engine-specific behavior, or an existing standard that implements the profile
cleanly.

## What this does not prove

This challenge is not certification, production security validation, proof of
robot safety, proof of enforcement, IEEE endorsement, proof that SPP should
become a standard, or a modification to normative SPP 0.1. It does not test
identity, PKI, geometry, mapping, planning, task allocation, evidence,
admission, lifecycle, or physical enforcement.

## After you finish

**REFERENCE IMPLEMENTATIONS — DO NOT CONSULT UNTIL AFTER YOUR FIRST
INDEPENDENT PASS**

Once you have recorded your independent result, you may compare it with the
repository's reference implementations:

- [`experiments/core-profile/native/`](../../experiments/core-profile/native/)
- [`experiments/core-profile/opa/`](../../experiments/core-profile/opa/)

Those implementations are useful comparison points, not authoritative proof
that an interpretation is correct. If they reveal a difference from your
implementation, report the difference and the Core Profile wording that led to
it.
