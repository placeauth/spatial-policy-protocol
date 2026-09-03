# Security

Please do not disclose suspected vulnerabilities in public issues when they
could affect users or deployed policy infrastructure. Report them privately to
security@placeauth.org with a description, reproduction steps, and affected
version.

SPP is experimental. It does not itself authenticate actors, protect policy
transport, or force a robot to obey an operating profile. Trust depends on
evidence assurance, the enforcement point, robot/runtime integrity, site
infrastructure, hardware guarantees, and any attestation or independent
observation mechanisms used by a deployment. No production-security guarantee
is made.

Read spec/security.md and spec/threat-model.md before using it with physical
systems. Conditional decisions, safety controls, and obligations must be
enforced at a trusted point close to the relevant actuator.
