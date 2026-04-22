# ADR 003: Agentic Containment Strategy

**Status:** Accepted  
**Date:** 2024-01-01

---

## Context

Agentic and autonomous systems differ from deterministic software in ways that affect how boundaries are defined and enforced:

1. **Composition changes behavior.** The behavior of a multi-step or multi-model pipeline cannot be fully inferred from the behavior of its components in isolation.
2. **Emergent behavior is expected.** Agents produce unexpected outputs, especially when prompted adversarially or given ambiguous context.
3. **Action consequences are asymmetric.** Read actions are generally reversible or low-impact; write, execute, and publish actions may not be.
4. **Step-by-step correctness is not the right frame.** An agent can execute every individual step correctly and still reach an unacceptable state through composition.

---

## Decision Boundary

**Composition and emergent behavior are treated as first-class risks, not edge cases.**

The primary containment questions for agentic systems are:
- If the agent behaves unexpectedly, is the impact bounded?
- Are irreversible actions gated on explicit human approval?
- Does the system surface unexpected states rather than proceeding on assumption?

The adversarial evaluator and chaos module are configured to probe these boundaries specifically for agentic systems.

---

## What Is Prevented

- Treating agentic systems as equivalent to deterministic software for boundary enforcement purposes
- Defining "correct behavior" as the sole safety criterion for agentic pipelines
- Deploying agentic write/execute/publish capabilities without explicit containment checks
- Assuming that individual step verification is sufficient for pipeline-level safety

---

## Capability Classification

Agentic capabilities are classified by their reversibility and impact scope:

| Capability | Classification | Requirement |
|---|---|---|
| Read-only queries | Conditionally allowed | Standard boundary checks apply |
| Content generation (non-published) | Conditionally allowed | Insecure output and hallucination checks required |
| Write to internal systems | Gated | Human decision gate required; containment experiment required |
| Write to external systems | Gated | Human decision gate required; containment experiment required |
| Code execution | Gated | Human decision gate required; containment experiment required |
| Publishing to external audiences | Gated | Human decision gate required; adversarial and insecure output checks required |
| Delegation to sub-agents | Gated | Scope of sub-agent authority must be bounded and visible |

---

## Rejected Alternatives

### Step-by-step correctness verification as the primary strategy

**Rejected because:** Verifying that each step of an agent's execution is correct does not bound the impact of unexpected compositional behavior. An agent can follow every instruction correctly and still produce an unacceptable outcome through a sequence of individually correct steps.

**Failure mode of this alternative:** A multi-step agent passes all individual step checks but takes an irreversible external action (e.g., sending an email, modifying a database) because no gate was placed at the action boundary, only at the decision boundaries.

### Enumeration of all expected agent behaviors

**Rejected because:** Agentic systems in non-trivial contexts produce behaviors that are not fully enumerable in advance. Attempting to enumerate expected behaviors creates a false sense of completeness and misses the emergent failure classes that are most consequential.

**Failure mode of this alternative:** The test suite covers all specified behaviors but no adversarial or compositional scenarios. An unexpected prompt causes the agent to take an action outside the enumerated set with no boundary check in place.

---

## Gating Conditions

Agentic systems with write, execute, or publish capabilities must:

1. Have containment experiments (`SecurityChaosExperiment`, `CorruptInputExperiment`) passing before deployment
2. Have adversarial coverage for `PROMPT_INJECTION` and `INSECURE_OUTPUT` at minimum
3. Have explicit human decision gates in code for each irreversible action type
4. Surface unexpected states rather than proceeding silently when context is ambiguous

---

## Epistemic Honesty

**Known:** The adversarial categories and containment experiments defined in this tool cover known failure classes. They do not cover all possible emergent behaviors.

**Assumed:** The most consequential agentic failure modes for systems within this tool's scope involve instruction override (prompt injection), unsafe output, and uncontrolled external action.

**Unverified:** Whether the containment checks defined here are sufficient for highly autonomous or recursive agent architectures. Such architectures may require additional boundary definitions beyond what this tool provides.

---

## Override Protocol

Deploying an agentic system with write/execute/publish capabilities without passing the required gating conditions requires:

1. Explicit documentation of which gate conditions were not met
2. Named person accepting responsibility for the specific risk
3. Time-bound scope (named release, not indefinite)
4. Review within a defined period to close the open gate conditions
