# ADR 002: Gating Authority for Irreversible Decisions

**Status:** Accepted  
**Date:** 2024-01-01

---

## Context

Several decisions in AI system deployment are irreversible or carry asymmetric risk:

- Exposing an AI capability to external users who can probe its failure modes
- Enabling agentic write, execute, or publish actions against external systems
- Deploying a system with known CRITICAL findings under a "we'll fix it later" assumption

The original framing treated validation output as advisory: teams received findings and recommendations and decided how to respond. This is appropriate for low-stakes decisions but inappropriate for decisions that cannot be cleanly reversed.

---

## Decision Boundary

**Certain decisions are gated, not advisory.**

A gate differs from a recommendation in the following way: a recommendation can be acknowledged and ignored; a gate cannot proceed without the gate condition being met or an explicit override being recorded.

The following decisions are gated in this tool:

1. **Deploying an AI capability to external users:** Adversarial coverage must include prompt injection, data exfiltration, insecure output, and sensitive information disclosure categories.
2. **Enabling agentic autonomy:** Human decision gate must be explicit in code; containment experiments must have passed.
3. **Releasing after CRITICAL findings:** Not permitted without an explicit override record.
4. **Exposing endpoints that process untrusted input:** Security test presence check must pass.

---

## What Is Prevented

- Treating CRITICAL findings as informational
- Deploying without adversarial coverage on AI products
- Using score-based thresholds as substitutes for gate conditions
- Implicit approvals (silence, configuration skips) that bypass gates without a record

---

## Rejected Alternatives

### Advisory-only review for all deployment decisions

**Rejected because:** Advisory reviews depend on reviewers choosing to act on findings. For irreversible decisions, the cost of a missed finding is asymmetric — the harm from proceeding without adversarial coverage is not recoverable by adding tests after deployment.

**Failure mode of this alternative:** Teams proceed to deployment with unresolved CRITICAL findings because the advisory output is present but not blocking. The finding is acknowledged but not acted upon before the decision is irreversible.

### Score threshold as the deployment gate

**Rejected because:** A score threshold can be satisfied without closing the specific boundaries that matter. See ADR 001. A score-based gate permits a team to deploy an AI product with no adversarial coverage as long as other criteria raise the score above the threshold.

**Failure mode of this alternative:** An AI product is deployed to external users with no prompt injection checks because the overall score was 72/100.

---

## Gating Conditions

A gate is considered met when:

1. The specific boundary check for the gate condition passes in the validation run, OR
2. An explicit override is recorded with the specific risk acknowledged, the scope defined, and a named person accepting responsibility

The tool surfaces gate failures as CRITICAL or HIGH findings. It does not enforce the deployment decision itself — that requires integration into the deployment pipeline.

---

## Epistemic Honesty

**Known:** The gate conditions defined here cover the failure classes most consistently observed in AI system incidents. They are not exhaustive.

**Assumed:** Teams integrating this tool into their deployment pipeline will configure it to block deployment on CRITICAL findings absent an override record.

**Unverified:** Whether the specific gate conditions defined are calibrated correctly for all system contexts. Gate conditions should be reviewed when the system's risk profile changes (e.g., new user population, new agentic capability).

---

## Override Protocol

A gate can be bypassed only when:

1. The bypass is explicit — recorded in a commit message, PR description, or issue reference
2. The risk being accepted is named specifically (e.g., "accepting deployment without PROMPT_INJECTION coverage for internal-only beta")
3. The bypass is time-bounded — it applies to a named release, not all future releases
4. The bypass record is visible in the validation report metadata

Implicit bypasses (e.g., disabling a criterion in configuration without documentation) are not valid overrides.
