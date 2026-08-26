---
name: clean-code-ai-collaboration
description: Use when AI coding changes need Clean Code judgment across readability, tests, design boundaries, collaboration, or estimates while repository context and behavior contracts must remain authoritative.
---

# Clean Code AI Collaboration

Use this Skill to turn Clean Code ideas into repeatable AI collaboration decisions. The Skill supplies a decision process; the repository supplies facts; responsible Owners retain risk, priorities, approvals, and final commitments.

## Workflow

1. Read the repository instructions, the User's task, and the directly affected code or documents.
2. Choose one execution path:
   - **Lightweight Path:** use only for a local, reversible readability change with no public contract, data, side effect, dependency, ownership, or deployment impact and one obvious option.
   - **Full Path:** use when behavior, a public contract, data, side effects, dependencies, concurrency, security, ownership, deployment, multiple options, or formal review matters. Use [repository-context-template.md](references/repository-context-template.md) to collect decision-changing facts.
3. Select the smallest applicable reference set:
   - Names, comments, functions, models, or classes: [code-readability.md](references/code-readability.md)
   - Features, defects, refactoring, tests, or risky behavior: [testing-and-change-safety.md](references/testing-and-change-safety.md)
   - Abstractions, providers, components, concurrency, or architecture: [design-and-dependency-boundaries.md](references/design-and-dependency-boundaries.md)
   - Multi-agent work, handoffs, teamwork, or estimates: [collaboration-and-estimation.md](references/collaboration-and-estimation.md)
4. On the Full Path, distinguish repository facts from assumptions and unknowns. Compare viable options, choose one for the current context, and state when another option fits better.
5. Define behavior that must remain stable, the expected Diff boundary, and validation. Treat tests as evidence for covered behavior, not proof of every requirement.
6. Apply the Authorization Gate before any mutation, then work inside the approved boundary.

## Authorization Gate

- **evidence does not grant authority.** Valid authority is the intersection of platform limits, repository instructions, explicit User authorization, and responsible Owner approval.
- Without explicit authority, stop before changing a public contract, dependency, production data or migration, external side effect, secret or privilege, CI or infrastructure, deployment, or any destructive operation.
- When evidence supports a change outside the authorized boundary, analyze it, propose a Diff or decision, name the required Owner, and leave the external state unchanged.
- Stop for conflicting instructions, a critical unknown, or high-risk behavior that available evidence cannot validate.

## Decision Rules

- Prefer the simplest structure that preserves behavior and leaves the next likely change local.
- Judge alternatives by change pressure, dependency direction, side effects, and maintenance cost rather than file count, line count, or pattern count alone.
- Preserve useful repository conventions unless the task supplies evidence that they are causing harm.
- Keep public contracts, persistence, notifications, failure order, and cancellation semantics explicit.
- Use Token and tool-call counts only to compare candidates that already satisfy the same quality and behavior gates.
- Escalate estimates and business commitments to the responsible human; the Agent may expose assumptions, ranges, and evidence.

## Required Output

- Lightweight Path: report repository facts used, behavior boundary, change and reason, validation evidence, and human decisions.
- Full Path: follow [review-output-contract.md](references/review-output-contract.md) exactly. Include rejected options and the conditions that would make them preferable.
