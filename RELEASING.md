# Releasing

## Version boundary

**SPP 0.1** is the normative protocol version. It is not the same as the
reference project/package release in `pyproject.toml`. The checked-out project
package declares `0.3.0`; the repository contains the annotated
`v0.3.0-experimental-preview` tag. Place Package and explain-trace formats are
also 0.1. A package version and local tag establish a versioned repository
state, not an externally published GitHub prerelease. For the current 0.3
release, GitHub verification separately establishes that publication.

An implementation release must not imply a normative protocol revision.

## What the repository establishes

Release history uses annotated tags named
`v<package-version>-experimental-preview` for 0.1.0, 0.2.0, and 0.3.0.
`docs/releases/` holds release notes and a 0.3 release checklist. The general
test workflow installs `requirements-dev.txt` and runs `python -m pytest`.

For 0.3, the repository establishes package version `0.3.0`, an annotated
`v0.3.0-experimental-preview` tag, a release-note file, and a historical commit
titled `Record SPP 0.3 public release` that changes README status text. Live
GitHub verification additionally establishes the public release:
**SPP v0.3.0 Experimental Preview** for `v0.3.0-experimental-preview`,
published as a prerelease (`prerelease: true`, `draft: false`) at
`2026-09-08T17:14:29Z`.

The 0.3 checklist records these release-ready checks: clean worktree, package
version, unchanged SPP/Place Package/trace versions, dependency-free tests,
general and optional runtime workflows, release notes, README wording, and
absence of private material or unsupported claims.

## Pre-release checks

Run the repository-supported baseline checks from the root:

```sh
python -m pip install -r requirements-dev.txt
python -m pytest
python demo/admission/run_demo.py --canonical
```

For a release that affects an optional integration surface, run or obtain the
matching documented GitHub Actions result for the ROS 2/Nav2 or Open-RMF
runtime workflow. Their requirements and commands are intentionally separate
from the dependency-free suite.

Confirm by review that:

- the package version and release-note name agree;
- SPP 0.1 has not changed unless a separate normative protocol process has
  approved it;
- release notes, `CHANGELOG.md`, README, roadmap/status wording, and relevant
  documentation make the same bounded claims; and
- experimental material remains labeled as experimental and no private
  material is included.

There is no documented automated documentation/link check in this repository.
**NEEDS MAINTAINER CONFIRMATION:** whether a documentation check is required
and which command or service is authoritative.

## Release notes and publication

Draft the release note under `docs/releases/` and keep the changelog and
README status language consistent with it. For 0.3, the release note exists and
describes the preview as release-ready, while the historical checklist leaves
“Release created as a prerelease” unchecked. The checklist records the
pre-publication tag convention; that unchecked item is stale documentation and
does not contradict the verified published prerelease.

**NEEDS MAINTAINER CONFIRMATION:** the authorized person or approval path;
the exact command or UI procedure for creating and pushing a tag; whether a
GitHub prerelease is required; its title/body/assets; and whether a package is
published anywhere beyond this repository. Do not infer credentials, release
targets, or publication destinations.

## Post-release checks

The repository establishes that release notes, tags, and GitHub Actions are
release evidence, but it does not document a post-publication verification
procedure.

**NEEDS MAINTAINER CONFIRMATION:** for future releases, verify the remote tag
and intended GitHub release/prerelease, confirm the public release note and
README point to the right release, record the relevant workflow results, and
decide whether any external package registry or announcement exists. For 0.3,
the GitHub prerelease is verified as published. No external package registry,
announcement channel, or release-owner process can be inferred from this
repository.

## Current 0.3 record

The conservative maintainer conclusion is:

- **Normative protocol:** SPP 0.1.
- **Package/project version:** 0.3.0.
- **Tag:** annotated `v0.3.0-experimental-preview`.
- **Release notes:** `docs/releases/SPP-0.3.0-experimental-preview.md` exists.
- **GitHub publication:** published prerelease **SPP v0.3.0 Experimental
  Preview** (`prerelease: true`, `draft: false`,
  `published_at: 2026-09-08T17:14:29Z`).
- **Checklist:** the historical prerelease-creation item remains unchecked and
  is stale documentation.

`README.md` and the historical `Record SPP 0.3 public release` commit describe
0.3 as published, while `ROADMAP.md` calls publication pending. The verified
GitHub release resolves the current-state question: 0.3 is published as a
prerelease. Do not alter historical documents merely to erase their stale
status wording; describe the current state using the verified release record.
