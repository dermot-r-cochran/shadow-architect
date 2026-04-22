# shadow-architect: Strategy

## 1. Purpose

This tool exists to enforce guardrails, not to enumerate tests or demonstrate delivery velocity.

The purpose of every check, experiment, and validation run is to answer one question: does this system respect its defined boundaries? It does not answer whether the system is correct, complete, or safe in general.

Tests and checks referenced here are empirical boundary enforcement mechanisms. Where formal verification is infeasible — which is the default condition for AI-enabled systems — empirical checks are the available means of enforcing boundaries. They are not approximations of proof.

A passing validation run means: the defined boundaries were not visibly crossed during the checks that were run. It does not mean the system is safe, correct, or ready for arbitrary deployment.
# shadow-architect: Testing Strategy

## 1. Purpose

This strategy exists to enforce system-level guardrails on AI systems and the infrastructure that supports them.

It does not exist to enumerate test cases, increase coverage metrics, or demonstrate delivery velocity. A passing gate means the declared boundary constraints were not visibly violated. It does not mean the system is correct, complete, or safe in all circumstances.

Testing, as applied here, is empirical enforcement of defined boundaries — not approximation of proof.

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
Constraints are categorised into three groups. The classification determines the response when a constraint is violated.

### (a) Unacceptable System States — Must Never Occur

These are red lines. A release gate does not open while any of these violations exist. Override is possible but requires escalation (see §8).

| Constraint | Trigger Condition |
|---|---|
| No tests present | The declared test suite contains zero test functions |
| No adversarial coverage for AI/LLM products | Product context indicates AI/LLM capability; no adversarial or robustness tests exist |
| No security tests for external-facing products | Product context indicates API, authentication, or cloud exposure; no security tests exist |
| Syntax errors in test files | A declared test file cannot be parsed; tests may not run at all |

### (b) Risky but Tolerable States — Must Be Visible and Bounded

These states are permitted but must surface as MEDIUM or HIGH findings in every report. They may not be silently ignored.

| Constraint | Trigger Condition |
|---|---|
| Missing integration tests | No cross-component boundary checks detected |
| Missing test isolation | External services called without mocking in a suite with more than 5 tests |
| Low symbol coverage | Fewer than 80% of declared source symbols referenced in tests |
| Missing parametrised tests | No boundary-value or equivalence-class coverage detected |
| Potential secrets in environment | Environment variables matching known secret patterns are present at analysis time |

### (c) Acceptable Variability

The following are tracked but do not produce findings or gate decisions:

- Test function naming conventions beyond the `test_` prefix.
- Choice of assertion library (pytest assert, unittest, etc.).
- File structure within the test directory.
- Number of tests per file.
- Use of async vs synchronous test functions.

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
The following decision classes require passing constraint checks before they proceed.

**Gating means the CI pipeline fails.** It is not advisory.

### Irreversible Decisions

Any operation that cannot be rolled back — including data deletion, tenant-level configuration changes, or permanent state mutations in external systems — requires:

- Adversarial test evidence covering the affected operation class.
- Isolation evidence (mocking of external systems in tests for the affected code path).

### External Exposure

Any component that accepts or emits data across a trust boundary — API endpoints, LLM prompt construction, output rendering pipelines — requires:

- Security test evidence.
- Insecure-output containment evidence (for LLM output paths).

### Agentic Autonomy Expansion

Any change that increases an agent's capability scope, tool access, or action authority requires:

- Adversarial coverage of the new capability class before the gate passes.
- Chaos containment evidence for the expanded action path.

### Non-Rollbackable Failure Modes

Failure modes that cannot be silently rolled back — credential leakage, schema mutations, irreversible writes to external systems — trigger escalation regardless of overall constraint score.

---

## 4. Agentic Systems

Agentic and autonomous systems present qualitatively different risk profiles from deterministic software. This strategy treats them accordingly.

**Composition is a primary risk vector.** Individual components may behave within their declared envelopes; composed systems may not. Integration-boundary containment tests are required for any agentic pipeline.

**Emergent behaviour is not predictable from component tests alone.** The strategy does not attempt to prove correctness of composed agentic systems. It enforces boundary conditions at the interfaces between components.

**Capability limits must be explicit and tested.** Each capability boundary must have a corresponding containment test that verifies the system refuses or escalates actions outside its declared scope.

**Escalation paths must be reachable.** Tests must verify that failure modes surface to a human-observable channel rather than being silently suppressed or retried without limit.

The chaos module's security and corrupt-inputs scenarios are the primary containment tests for agentic system boundaries. They are not optional for AI/LLM products.

---

## 5. Epistemic Honesty

This strategy explicitly does not claim:

- **Correctness.** A passing validation run means boundaries were not visibly crossed during checks. It does not mean the system is correct.
- **Exhaustiveness.** The checks defined here do not cover all possible failure modes. Unchecked behavior exists regardless of the validation score.
- **Safety certification.** No output from this tool constitutes a safety certificate.
- **Ethical completeness.** Bias and sensitive disclosure checks probe specific failure classes. They do not encode a complete ethical framework or substitute for human judgment on values questions.
- **Predictability of agentic behavior.** Emergent and compositional behaviors in agentic systems cannot be fully captured by static checks or template tests.

Where formal verification is infeasible, checks are empirical enforcement. They are evidence, not proof.
This strategy does not:

- **Prove correctness.** A passing gate means declared constraints were not visibly violated during the test run. It does not mean the system is correct.
- **Exhaustively test behaviour.** The strategy targets failure classes at system boundaries. Combinatorial coverage of all possible inputs is not the goal and is not claimed.
- **Encode ethics or values.** Bias and sensitive-disclosure checks enforce observable boundary conditions. They do not adjudicate ethical questions or certify alignment.
- **Replace runtime monitoring.** Static analysis and offline test suites are pre-release gates. They do not substitute for observability, alerting, or runtime anomaly detection.
- **Certify third-party components.** Azure service behaviour, LLM model internals, and upstream dependencies are outside the scope of this gate.

Where formal verification is infeasible — which is the default condition for LLM-based systems — testing is empirical enforcement of boundaries, not an approximation of mathematical proof.

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
This strategy does not use titles like QA, Test Manager, or Solution Architect. Responsibilities are described by function:

| Responsibility | Description |
|---|---|
| **Boundary definition** | Determines what constitutes a red line, tolerable state, and acceptable variability for a specific system. Documents these in the project's constraint configuration. |
| **Decision gating** | Operates the CI gate. Interprets findings. Determines whether a gate failure is a true violation or a false positive requiring override. |
| **Escalation conditions** | Defines when a gate failure triggers escalation beyond the immediate team. Owns the escalation path for red-line violations. |
| **Override visibility and accountability** | Records overrides, links them to finding IDs, and ensures they are visible to the person responsible for boundary definition. Overrides do not carry forward across releases. |

These responsibilities may be held by the same person on a small team or distributed on a large one. What matters is that each responsibility is explicitly assigned, not assumed.

---

## 7. Evidence We Require Before Release

Before a system governed by this tool is released, the following must be documented:

1. A completed validation run with no CRITICAL findings unresolved
2. Adversarial coverage for all high-severity failure classes: prompt injection, data exfiltration, insecure output, sensitive information disclosure
3. Security test presence for any system handling untrusted input or external credentials
4. Containment experiment results showing that corrupt-input, security-permission, and network-disruption scenarios do not produce unhandled failures
5. An explicit record of any overridden gate: who accepted the risk, what the risk was, and for which release

Evidence is empirical. Declaring that a boundary holds is not evidence that it holds.
The following must be present and passing before a release gate opens:

1. At least one test function exists in the declared suite.
2. For AI/LLM products: adversarial containment tests cover prompt injection and data exfiltration failure classes at minimum.
3. For API/cloud products: authentication, authorisation, and input-validation tests are present.
4. Chaos containment scenarios (`corrupt-inputs`, `security`, `network`) pass for the critical path module.
5. No CRITICAL constraint violations are reported by `shadow-architect run`.
6. Any CRITICAL or HIGH finding that was overridden is recorded with owner identity and written rationale, linked to the finding ID.

---

## 8. Override and Escalation Protocols

A gate can be bypassed only when:

1. The bypass is explicit and recorded — not implied by skipping a check or reconfiguring a threshold
2. The person accepting the bypass acknowledges the specific risk in writing (commit message, PR description, or issue reference)
3. The bypass is time-bounded — it applies to a named release, not indefinitely
4. The bypass is visible in the audit trail — it must appear in the validation report metadata

Override does not remove the gate. It records that the gate was bypassed, by whom, and for what scope.

When a CRITICAL finding cannot be resolved, the release decision is escalated to a human. The tool surfaces the finding; it does not make the deployment decision.
### Who Can Override

The person responsible for boundary definition for the affected system. Override authority cannot be self-assigned for red-line violations.

### What Is Required

A written rationale explaining why the constraint does not apply or why the risk is accepted. The rationale must reference the finding ID from the report. Rationales of the form "no time" or "not important" are not accepted.

### How Overrides Are Recorded

Overrides are recorded in the Azure DevOps work item created for the finding. A work item without a recorded rationale means the gate was bypassed, not overridden. Bypasses are escalation triggers.

### Escalation Triggers

Any override of a red-line constraint (unacceptable state) escalates automatically. It cannot be closed by the same person who opened it.

Any CRITICAL finding present at release without either passing evidence or a recorded override is a post-release escalation item.

### Override Expiry

Overrides do not carry forward across releases. Each release gate requires fresh evidence or a fresh override. Overrides from a previous release are not inherited.

---

## 9. Failure Classes We Intentionally Ignore

The following are outside the scope of this tool and should not be inferred from its output:

- **General performance optimization.** The tool does not measure or optimize system performance beyond detecting tests that may indicate performance boundary coverage.
- **Business logic correctness.** Whether the system does what the product specification says is outside this tool's scope.
- **Completeness of documentation.** The tool does not assess whether documentation accurately describes system behavior.
- **Test coverage as a delivery metric.** Coverage percentages are boundary gap indicators, not velocity or quality scores.
- **Full ethical review.** The bias and sensitive disclosure checks identify specific failure classes. They are not a substitute for a structured ethical review process.
The following are out of scope. They will not be gated on, reported on, or used as evaluation criteria:

- **Proof of correctness.** Not attempted. Tests are empirical boundary enforcement.
- **Exhaustive input coverage.** Not attempted. Boundary cases are targeted; all-inputs coverage is not claimed.
- **Ethics and value alignment.** Not attempted. Observable boundary conditions are checked; ethical adjudication is not.
- **Third-party component correctness.** Azure service internals, LLM model weights, and upstream package behaviour are not within scope.
- **Runtime and post-deployment behaviour.** This tool is a pre-release gate. Runtime failure modes require a separate observability strategy.
- **Test implementation style.** How a test is written is not evaluated beyond anti-patterns that obscure failures (bare `except`, trivial assertions).
- **Documentation completeness.** Docstring presence and quality are not gated criteria.
