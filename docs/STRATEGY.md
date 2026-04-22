# shadow-architect: Strategy

## 1. Purpose

This tool exists to enforce guardrails, not to enumerate tests or demonstrate delivery velocity.

The purpose of every check, experiment, and validation run is to answer one question: does this system respect its defined boundaries? It does not answer whether the system is correct, complete, or safe in general.

Tests and checks referenced here are empirical boundary enforcement mechanisms. Where formal verification is infeasible — which is the default condition for AI-enabled systems — empirical checks are the available means of enforcing boundaries. They are not approximations of proof.

A passing validation run means: the defined boundaries were not visibly crossed during the checks that were run. It does not mean the system is safe, correct, or ready for arbitrary deployment.

---

## 2. System Boundaries and Red Lines

Boundaries fall into three categories:

### (a) Unacceptable States — Must Never Occur

These states represent failed containment. No score, exception, or deployment decision overrides them:

- Prompt injection achieving instruction override in a deployed AI system
- Sensitive data (PII, credentials, internal system prompts) disclosed via model output
- An agentic system taking an irreversible external action (write, delete, publish, execute) without a confirmed human decision gate
- Unsafe output (executable code, injection payloads, rendered scripts) reaching a downstream consumer without sanitisation

These are enforced by the adversarial evaluator and security containment experiments. If any check targeting these boundaries is absent, the validation run is incomplete — not passing.

### (b) Risky but Tolerable — Must Be Visible and Bounded

These states are permitted under specific, monitored conditions:

- Hallucination or factual error in non-binding, low-stakes output — only tolerable if the system does not present the output as verified
- Integration test absence in early-stage development — tolerable if declared as a tracked finding, not silently absent
- Partial adversarial category coverage — tolerable only if deferred categories are explicitly named
- Missing mock isolation in small suites (≤5 tests) — tolerable; must be surfaced as a finding in larger suites

Tolerable states must appear as findings in the validation output. They do not disappear by configuration.

### (c) Acceptable Variability

These vary without requiring escalation:

- Assertion density differences across test types
- Test file naming conventions
- Coverage percentages in non-boundary-critical source files
- Choice of mocking library or fixture approach

---

## 3. Decisions Subject to Gating

The following decisions require a gate to pass before proceeding. This tool enforces or surfaces the gate condition.

| Decision | Gate Condition |
|---|---|
| Deploying an AI capability to external users | Adversarial coverage must include: prompt injection, data exfiltration, insecure output, sensitive info disclosure |
| Enabling agentic autonomy (write, execute, publish) | Human decision gate must be explicit in code; containment experiments must have passed |
| Releasing after a validation run with CRITICAL findings | Not permitted without explicit override — see Section 8 |
| Exposing an endpoint processing untrusted input | Security test presence check must pass |
| Advancing from development to production for an AI product | All unacceptable-state boundaries must have corresponding checks |

These are gates, not recommendations. A high compliance score does not override a failed gate condition.

---

## 4. Agentic Systems

Agentic and autonomous systems require specific treatment because standard correctness verification assumptions do not apply:

- **Composition is a primary risk.** The behavior of a multi-step or multi-model system cannot be fully inferred from the behavior of its components in isolation.
- **Emergent behavior is expected, not exceptional.** Validation cannot enumerate all behaviors that emerge from agent composition.
- **Containment, not correctness, is the primary goal.** The question is not "does it behave correctly?" but "if it behaves unexpectedly, is the impact bounded?"

### Capability Limits

The following forms of agentic autonomy are treated as gated:

- Write operations to external systems (databases, APIs, file systems)
- Execution of arbitrary code
- Publication of content to external audiences
- Delegation to sub-agents without human-visible context

### Escalation Paths

When an agentic system reaches a decision boundary it cannot classify, the expected behavior is:
1. Stop and surface the decision to a human
2. Log the context and the boundary that was reached
3. Not proceed on the assumption that proceeding is safe

Tools that override this pattern require explicit justification in an ADR.

---

## 5. Epistemic Honesty

This strategy explicitly does not claim:

- **Correctness.** A passing validation run means boundaries were not visibly crossed during checks. It does not mean the system is correct.
- **Exhaustiveness.** The checks defined here do not cover all possible failure modes. Unchecked behavior exists regardless of the validation score.
- **Safety certification.** No output from this tool constitutes a safety certificate.
- **Ethical completeness.** Bias and sensitive disclosure checks probe specific failure classes. They do not encode a complete ethical framework or substitute for human judgment on values questions.
- **Predictability of agentic behavior.** Emergent and compositional behaviors in agentic systems cannot be fully captured by static checks or template tests.

Where formal verification is infeasible, checks are empirical enforcement. They are evidence, not proof.

---

## 6. Role Clarity

Responsibilities are defined by function, not title:

| Function | Responsibility |
|---|---|
| Boundary definition | Define which states are unacceptable, which are tolerable, and which are variable. Update BOUNDARIES.md when context changes. |
| Decision gating | Determine which decisions require a gate. Maintain the gate conditions in this document. Escalate when gate conditions are ambiguous. |
| Escalation conditions | Define the conditions under which a human decision is required. Ensure these are visible in validation output. |
| Override visibility | When a gate is bypassed, record who made the decision, what risk was accepted, and for what scope. |

Role titles such as "QA", "Test Manager", or "Solution Architect" are not used here because they imply process ownership rather than boundary accountability.

---

## 7. Evidence We Require Before Release

Before a system governed by this tool is released, the following must be documented:

1. A completed validation run with no CRITICAL findings unresolved
2. Adversarial coverage for all high-severity failure classes: prompt injection, data exfiltration, insecure output, sensitive information disclosure
3. Security test presence for any system handling untrusted input or external credentials
4. Containment experiment results showing that corrupt-input, security-permission, and network-disruption scenarios do not produce unhandled failures
5. An explicit record of any overridden gate: who accepted the risk, what the risk was, and for which release

Evidence is empirical. Declaring that a boundary holds is not evidence that it holds.

---

## 8. Override and Escalation Protocols

A gate can be bypassed only when:

1. The bypass is explicit and recorded — not implied by skipping a check or reconfiguring a threshold
2. The person accepting the bypass acknowledges the specific risk in writing (commit message, PR description, or issue reference)
3. The bypass is time-bounded — it applies to a named release, not indefinitely
4. The bypass is visible in the audit trail — it must appear in the validation report metadata

Override does not remove the gate. It records that the gate was bypassed, by whom, and for what scope.

When a CRITICAL finding cannot be resolved, the release decision is escalated to a human. The tool surfaces the finding; it does not make the deployment decision.

---

## 9. Failure Classes We Intentionally Ignore

The following are outside the scope of this tool and should not be inferred from its output:

- **General performance optimization.** The tool does not measure or optimize system performance beyond detecting tests that may indicate performance boundary coverage.
- **Business logic correctness.** Whether the system does what the product specification says is outside this tool's scope.
- **Completeness of documentation.** The tool does not assess whether documentation accurately describes system behavior.
- **Test coverage as a delivery metric.** Coverage percentages are boundary gap indicators, not velocity or quality scores.
- **Full ethical review.** The bias and sensitive disclosure checks identify specific failure classes. They are not a substitute for a structured ethical review process.
