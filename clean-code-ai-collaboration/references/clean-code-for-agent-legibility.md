# Clean Code for Agent Legibility

## Use This Reference When

Use this reference when a request requires an Agent to locate the relevant behavior, make a bounded change, choose validation, or explain the result to a reviewer. Read repository instructions and the affected code first. Repository facts outrank these mechanisms.

## Mechanisms to Evaluate

- **Naming and search:** names should expose domain intent and make the behavior discoverable through repository search. Prefer a precise local name over an abstract label that hides the concept.
- **Cohesion and Context scope:** keep related decisions together so the necessary Context is available without tracing unrelated modules. Split only when a stable boundary reduces change pressure.
- **Dependency boundaries and Diff:** make dependency direction visible, confine the Expected Diff, and avoid changing callers, configuration, or public contracts without evidence and authority.
- **Tests and Oracle:** select tests that observe the required behavior through an independent Oracle. Record what validation covers and what it cannot prove.
- **Continuous cleanup and pattern copying:** improve nearby clarity when it stays within the approved Diff. Copy an existing pattern only after confirming its behavior, ownership, and current suitability.

## Counter-Effects

Over-abstraction can hide a local decision behind indirection. Incorrect names can direct search to the wrong behavior. Stale comments can contradict code. Brittle tests can reward implementation shape instead of behavior. Documentation drift can turn a once-correct route into misleading Context. Treat each as a reason to narrow the claim, inspect evidence, or stop.

## Evidence Questions

- Which repository files, callers, tests, configuration, or contracts establish the relevant Context?
- What is the Expected Diff, and which behavior must remain stable?
- Which Oracle validates the behavior, which failure path or side effect is covered, and which gap remains?
- Does the proposed pattern match current repository evidence or only an example?

## Claim Boundaries

These mechanisms do not guarantee lower Token use, task correctness, generalization across models, or removal of human responsibility. They support reviewable decisions for the observed repository and authorized scope. Validation is evidence for covered behavior, not proof of every requirement.

## Stop Conditions

Stop and escalate when the relevant Context is unavailable, repository facts conflict, the required Oracle cannot validate high-risk behavior, the Expected Diff must cross an unauthorized boundary, or the proposed cleanup would broaden the approved change.
