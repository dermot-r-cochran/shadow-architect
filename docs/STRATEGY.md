# shadow-architect: Testing Strategy

## 1. Purpose

This strategy exists to enforce system-level guardrails on AI systems and the infrastructure that supports them.

It does not exist to enumerate test cases, increase coverage metrics, or demonstrate delivery velocity. A passing gate means the declared boundary constraints were not visibly violated. It does not mean the system is correct, complete, or safe in all circumstances.

Testing, as applied here, is empirical enforcement of defined boundaries — not approximation of proof.

---

## 2. System Boundaries and Red Lines

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

This strategy does not:

- **Prove correctness.** A passing gate means declared constraints were not visibly violated during the test run. It does not mean the system is correct.
- **Exhaustively test behaviour.** The strategy targets failure classes at system boundaries. Combinatorial coverage of all possible inputs is not the goal and is not claimed.
- **Encode ethics or values.** Bias and sensitive-disclosure checks enforce observable boundary conditions. They do not adjudicate ethical questions or certify alignment.
- **Replace runtime monitoring.** Static analysis and offline test suites are pre-release gates. They do not substitute for observability, alerting, or runtime anomaly detection.
- **Certify third-party components.** Azure service behaviour, LLM model internals, and upstream dependencies are outside the scope of this gate.

Where formal verification is infeasible — which is the default condition for LLM-based systems — testing is empirical enforcement of boundaries, not an approximation of mathematical proof.

---

## 6. Role Clarity

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

The following must be present and passing before a release gate opens:

1. At least one test function exists in the declared suite.
2. For AI/LLM products: adversarial containment tests cover prompt injection and data exfiltration failure classes at minimum.
3. For API/cloud products: authentication, authorisation, and input-validation tests are present.
4. Chaos containment scenarios (`corrupt-inputs`, `security`, `network`) pass for the critical path module.
5. No CRITICAL constraint violations are reported by `shadow-architect run`.
6. Any CRITICAL or HIGH finding that was overridden is recorded with owner identity and written rationale, linked to the finding ID.

---

## 8. Override and Escalation Protocols

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

The following are out of scope. They will not be gated on, reported on, or used as evaluation criteria:

- **Proof of correctness.** Not attempted. Tests are empirical boundary enforcement.
- **Exhaustive input coverage.** Not attempted. Boundary cases are targeted; all-inputs coverage is not claimed.
- **Ethics and value alignment.** Not attempted. Observable boundary conditions are checked; ethical adjudication is not.
- **Third-party component correctness.** Azure service internals, LLM model weights, and upstream package behaviour are not within scope.
- **Runtime and post-deployment behaviour.** This tool is a pre-release gate. Runtime failure modes require a separate observability strategy.
- **Test implementation style.** How a test is written is not evaluated beyond anti-patterns that obscure failures (bare `except`, trivial assertions).
- **Documentation completeness.** Docstring presence and quality are not gated criteria.
