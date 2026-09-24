# Maintainers

This repository needs technical stewardship that preserves the distinction
between normative SPP and experimental PlaceAuth work.

## Technical stewardship

Technical maintainers keep the specification, schemas, examples, reference
implementation, tests, demos, and public documentation internally consistent.
They should require focused changes, reproducible test results, and an
explicit compatibility statement for changes to published exchange surfaces.
Security-sensitive reports follow `SECURITY.md`, not public issue discussion.

## Review expectations

Reviewers should reject unrelated formatting churn and ask contributors to run
the full test suite and the affected demo. A proposed protocol change should
identify the specification, schema, examples, and tests it affects. Per
`CONTRIBUTING.md`, protocol changes remain experimental proposals until
independently reviewed.

## Protocol maintenance and Foundation governance

Technical maintenance is not Foundation governance. The repository identifies
[PlaceAuth Foundation, Inc.](https://github.com/placeauth/governance) as the
steward, but this repository does not establish officers, a maintainer roster,
or a voting process. Do not infer them here.

Changes to normative SPP 0.1 require deliberate review: they must not be
smuggled in as an implementation, adapter, documentation, or package-release
change. Experimental and research documents must retain prominent status and
scope labels and must not imply standards adoption, external endorsement, or
production guarantees. Follow the [SPP Technical Change Process](docs/governance/spp-change-process.md)
to classify a change, gather evidence, and distinguish technical review from
Foundation-governance approval.

## Release-state stewardship

Maintain the distinction between a package version, an annotated Git tag,
release notes, and an externally published GitHub release. The first three are
repository evidence; they do not by themselves prove that a GitHub prerelease
was published. Where publication cannot be independently verified, record
**NEEDS MAINTAINER CONFIRMATION** rather than treating a version string, tag, or
historical commit message as conclusive.

For the current `v0.3.0-experimental-preview` release, GitHub verification is
available: **SPP v0.3.0 Experimental Preview** is published as a prerelease
(`prerelease: true`, `draft: false`) at `2026-09-08T17:14:29Z`. The historical
0.3 checklist's unchecked prerelease-creation item is stale documentation and
must not be used to describe this verified release as unpublished.
