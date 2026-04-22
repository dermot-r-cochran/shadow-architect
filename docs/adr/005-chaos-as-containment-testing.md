# ADR 005: Chaos as Containment Testing

**Status:** Accepted  
**Date:** 2024-01-01

---

## Context

The `chaos` module was initially framed as "fault injection primitives for resilience testing" inspired by chaos engineering practices. This framing has a specific connotation: chaos engineering explores the system's behavior under unknown or unexpected conditions to discover emergent failure modes through experimentation.

This framing is appropriate for systems where the goal is to discover unknown unknowns. However, for this tool's primary purpose — boundary enforcement — the framing is too open-ended. It implies:
- General exploration rather than targeted boundary enforcement
- Resilience as a spectrum rather than a containment binary
- Experiment results as data points rather than findings

For AI-enabled systems governed by this tool, the chaos module must answer a specific question: **does the system respect its containment boundaries when specific adverse conditions are applied?**

---

## Decision Boundary

**The chaos module enforces containment boundaries under adverse conditions. It does not perform general resilience exploration.**

Each experiment targets a specific boundary:

| Experiment | Boundary | Question |
|---|---|---|
| `CorruptInputExperiment` | Input containment | Does the system fail in a controlled, visible way under malformed input, or does it fail silently or uncontrollably? |
| `SecurityChaosExperiment` | Credential containment | Does the system surface authentication and authorization failures, or does it silently proceed when credentials are absent or insufficient? |
| `NetworkChaosExperiment` | Network failure containment | Does the system surface network failures, or does it swallow them and proceed as if the operation succeeded? |

An experiment that returns `FAILED` means the containment boundary was crossed. This is a finding, not a data point.

---

## What Is Prevented

- Using chaos experiments to generate general resilience metrics
- Treating experiment results as evidence of overall system robustness
- Running chaos experiments without specific boundary hypotheses
- Interpreting a `PASSED` experiment result as proof that the system handles all fault conditions of that type

---

## Rejected Alternatives

### Chaos as general resilience exploration

**Rejected because:** General resilience exploration produces data about system behavior under a range of conditions. This data is useful for system understanding but does not directly enforce boundaries. For this tool's context, the question is not "how does the system behave under fault X?" but "does the system maintain its containment boundary under fault X?"

**Failure mode of this alternative:** Experiments are run, observations are collected, and the results inform future development. However, no specific boundary check is enforced, and a system that silently proceeds after a credential failure is not flagged as a finding — it is logged as an observation.

### Chaos as a coverage percentage metric

**Rejected because:** This is equivalent to the coverage-as-quality framing rejected in ADR 001, applied to chaos experiments. "80% of fault scenarios handled" is not a meaningful safety claim. The relevant question is whether the specific containment boundaries are enforced, not whether a percentage of scenarios were handled.

**Failure mode of this alternative:** A system passes a chaos coverage threshold but fails on the specific fault type most likely to occur in production (e.g., expired credentials, which is common in cloud systems with rotating tokens).

---

## Gating Conditions

For systems with agentic capabilities or external integrations, containment experiments must pass before deployment:

1. `CorruptInputExperiment` must pass (or explicitly override) for any system that processes untrusted external input
2. `SecurityChaosExperiment` must pass for any system using Azure credentials or external authentication
3. `NetworkChaosExperiment` must pass for any system with dependencies on external network services

A `FAILED` experiment result is a CRITICAL or HIGH finding depending on the boundary involved. It must be resolved or explicitly overridden before the gate condition is met.

---

## Epistemic Honesty

**Known:** The three experiment types in the chaos module cover the most common adverse conditions for cloud-hosted AI systems: corrupt input, credential failure, and network disruption.

**Assumed:** Systems that pass these three experiment types under the defined fault conditions are more likely to surface failures visibly in production than systems that do not.

**Unverified:** Whether the specific fault conditions injected by each experiment type are representative of the faults that will occur in production. The experiments are representative, not exhaustive. A system that passes all three experiment types may still fail under fault conditions not covered by these experiments.

---

## Override Protocol

If a containment experiment fails and cannot be fixed before a required deployment:

1. The specific boundary that was crossed must be named (e.g., "SecurityChaosExperiment FAILED: system proceeded silently with expired token")
2. The person accepting the risk must acknowledge specifically what containment was not maintained
3. A remediation plan must be attached (not implied)
4. The override is valid only for the named release and expires at the next release boundary

Running chaos experiments in `--dry-run` mode without executing the experiments is not a valid substitute for a passing result.
