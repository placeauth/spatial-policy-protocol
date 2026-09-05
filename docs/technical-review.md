# Technical Review

PlaceAuth is an experimental interoperability project for autonomous systems in physical environments. Its Spatial Policy Protocol (SPP) gives a place a way to express machine-readable requirements and gives an autonomous system a way to demonstrate conformance within a particular space, context, and time window. The project is deliberately a reference implementation rather than an adopted standard or production security product.

The implemented lifecycle is:

```text
Place requirements
  -> conformance
  -> evidence
  -> sufficiency
  -> admission
  -> operating profile
  -> runtime enforcement adapter
```

Place requirements describe the operating conditions of a specific physical space. The reference conformance layer maps those requirements to tests and records their results as evidence. Sufficiency assessment determines whether earlier evidence still proves a destination requirement. Admission independently revalidates relied-on evidence at the time it issues an `ADMITTED`, `DEGRADED`, or `DENIED` operating profile. The optional ROS 2/Nav2 adapter maps `movement.max_speed` from that profile to Nav2's `SpeedLimit` interface.

The current repository includes a reference policy server, schemas and examples, deterministic admission/requalification demos, and an optional ROS 2 adapter. The Nav2 work has been validated through real Humble `SpeedLimit` publication and through an unmodified ControllerServer into a test-only controller plugin's official `setSpeedLimit()` method. It has not demonstrated stock-controller motion behavior, physical speed enforcement, or stopping. Likewise, evidence integrity and sufficiency checks do not themselves authenticate an issuer. Review should distinguish what the reference implementation proves from the deployment infrastructure it intentionally leaves external.

The project needs critical technical feedback more than general encouragement. In particular, reviewers are invited to assess the following questions.

1. **Interoperability boundary.** Does SPP occupy a useful boundary between autonomous systems and physical places, or does it substantially duplicate existing robotics, facility, authorization, or policy infrastructure? If it overlaps, where should the boundary be narrowed or made more explicit?

2. **Selective requalification.** Is selective evidence reuse and requalification across spaces operationally useful? Are the proposed conditions for reusing a guarantee—requirement bounds, scope, bindings, freshness, assurance, and current plan coverage—credible for real deployments?

3. **Evidence and trust.** Where are the evidence and trust assumptions weakest? The reference implementation verifies structural integrity, freshness, binding, replay and sufficiency, but it does not define cryptographic issuer authentication or hardware attestation. Which trust relationships require standardization first?

4. **System placement.** Where should SPP sit relative to ROS 2, Nav2, Open-RMF, building systems, policy engines, and attestation infrastructure? Which interfaces should remain outside SPP, and which interoperability fixtures would make the separation testable?

5. **Most valuable next proof.** What single implementation or integration would most increase confidence in the model? Examples might include an independent policy/admission implementation, authenticated evidence issuer, building-system integration, stock Nav2-controller behavior measurement, or a cross-vendor interoperability fixture.

Start with the [five-minute quickstart](quickstart.md), then review the [SPP 0.1 specification](../spec/SPP-0.1.md), [evidence sufficiency guidance](evidence-sufficiency.md), and [ROS 2 / Nav2 integration notes](../reference/ros2-enforcer/README.md). The design rationale is in the [Markdown Whitepaper](whitepaper.md) and [PDF Whitepaper](whitepaper/PlaceAuth-SPP-White-Paper.pdf). The [documentation index](README.md) links to implementation guides, examples, security material, and release history.

Please use the repository's protocol-feedback, interoperability-proposal, or implementation-bug issue templates for focused, reproducible feedback. Do not post suspected vulnerabilities publicly; follow [security reporting](../SECURITY.md).
