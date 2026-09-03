# SPP 0.1 security considerations

SPP decisions can affect physical movement, sensing, data collection,
infrastructure, manipulation, and human contact. A syntactically valid response
is not sufficient evidence that an action is safe.

## Deployment requirements

- Authenticate the spatial authority, actor, and decision service.
- Use authenticated, integrity-protected transport such as mutually
  authenticated TLS on untrusted networks.
- Verify authorization credentials before converting them into context strings.
- Protect policy administration with strong access control, review, and audit.
- Bind decisions to the complete request, policy version, and short lifetime.
- Keep trusted time and reject decisions outside their validity window.
- Fail closed on timeout, parse failure, unknown space, unsupported obligation,
  engine failure, or ambiguous location.
- Minimize context attributes because they may reveal identity, purpose,
  health, location, or operational details.
- Separate safety controls from SPP. Emergency stops, collision avoidance, speed
  limits, and applicable human-safety systems remain independently authoritative.

## Policy integrity and provenance

Version 0.1 does not standardize signatures. Production deployments MUST use a
trusted delivery channel or an external signing scheme and MUST prevent rollback
to an older policy version. Cache keys SHOULD include authority ID, policy ID,
and policy version. Cached decisions MUST expire.

## Conditional decisions and obligations

A conditional response MUST be enforced as a denial until all requirements are
verified and the request is re-evaluated. Authorization names supplied by an
actor are untrusted claims unless a credential verifier attests them.

An obligation is part of the permission. If the enforcement point cannot apply
\`data.no_retention\`, for example, it must not treat the underlying video
capture as permitted.

## Context correctness

The decision point cannot detect a caller that lies about its location, sensor,
purpose, emergency state, or intended action. Deployments SHOULD source
security-critical context from trusted hardware, building infrastructure, or
independently authenticated systems where proportionate.

## Availability

Fail-closed behavior can stop operations when the service is unavailable.
Deployments should use local evaluation, bounded caches, redundant decision
points, and explicit safety-reviewed degraded modes. Availability measures must
not turn stale or unverifiable permissions into indefinite access.

## Privacy

Logs can create a sensitive history of people, robots, facilities, restricted
spaces, and denied behavior. Collect the minimum fields, restrict access, define
retention, and avoid placing secrets or personal data in free-form identifiers.

## Experimental evidence-based admission

The Conformance and Admission extensions are EXPERIMENTAL / PRE-PUBLICATION.
Evidence must be rejected when it is forged, modified, stale, replayed, bound to
the wrong robot build or controller configuration, or associated with a changed
policy or environment digest. A challenge prevents simple replay when the
deployment verifies it.

Evidence assurance ranges from E0 declaration through E4 trusted external
observation. The demo implements E2 behavioral evidence only. A place should
learn the demonstrated guarantee and a digest, not proprietary source code,
model weights, or controller internals. Signed or hardware-attested evidence
can strengthen the binding later; SPP does not define custom cryptography.

Degraded admission must name its restrictions. Essential safety requirements
must fail closed to DENIED; a degraded profile must never be treated as a full
permit. Attestation hardware may be unavailable, and a compromised adapter or
dishonest self-report can still produce misleading evidence. Enforcement points
and robot runtimes must independently enforce the resulting operating profile.
PlaceAuth does not magically force a malicious robot to comply.
