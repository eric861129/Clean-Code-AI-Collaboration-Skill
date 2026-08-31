---
name: clean-code-ai-collaboration
description: Use when a coding agent must plan, implement, refactor, or review repository changes where readability, behavior preservation, tests, design boundaries, side effects, dependencies, handoffs, or estimates require repository-aware Clean Code judgment.
license: MIT
compatibility: Agent Skills-compatible coding agents.
metadata:
  author: eric861129
  version: "0.2.0"
---

# Clean Code AI Collaboration

## Core Principle

The repository provides facts; Clean Code provides quality judgment. CLEAN controls collaboration responsibilities between the User and Agent. Repository facts override examples in this Skill. Evidence supports a decision but does not enlarge authorization.

## Path Selection

- **Lightweight Path:** use only for a local, reversible readability change with no public contract, data, side effect, dependency, ownership, or deployment impact and one obvious option.
- **Full Path:** use when behavior, a public contract, data, side effects, dependencies, concurrency, security, ownership, deployment, multiple options, or formal review matters. Read [repository-context-template.md](references/repository-context-template.md) for decision-changing facts.

## Reference Routing

Read [clean-code-for-agent-legibility.md](references/clean-code-for-agent-legibility.md) first when judging whether code lets an Agent find, change, validate, and explain the relevant behavior. Load only references that change the current decision:

- Code structure or naming: [code-readability.md](references/code-readability.md)
- Tests, defects, refactoring, or risky behavior: [testing-and-change-safety.md](references/testing-and-change-safety.md)
- Abstractions, providers, components, concurrency, or architecture: [design-and-dependency-boundaries.md](references/design-and-dependency-boundaries.md)
- Handoffs, teamwork, or estimates: [collaboration-and-estimation.md](references/collaboration-and-estimation.md)
- Full Path output: [review-output-contract.md](references/review-output-contract.md)

## CLEAN Lenses

Use CLEAN as the User's review lens for an Agent's work. It is not a score that claims automatic compliance.

- **C — Context-Aware Code（脈絡感知程式碼）:** establish Context from repository facts before change.
- **L — Localized Change（局部化變更）:** state the Expected Diff and keep the change boundary local.
- **E — Explicit Intent and Boundaries（明確意圖與邊界）:** make Intent, contracts, and ownership visible.
- **A — Auditable by Evidence（可由證據稽核）:** connect Evidence to validation and known gaps.
- **N — Non-Surprising Behavior（非意外行為）:** preserve Behavior, including failures and side effects.

## Authorization Gate

- **evidence does not grant authority.** Valid authority is the intersection of platform limits, repository instructions, explicit User authorization, and responsible Owner approval.
- Without explicit authority, stop before changing a public contract, dependency, production data or migration, external side effect, secret or privilege, CI or infrastructure, deployment, or any destructive operation.
- When evidence supports a change outside the authorized boundary, analyze it, propose a Diff or decision, name the required Owner, and leave the external state unchanged.
- Stop for conflicting instructions, a critical unknown, or high-risk behavior that available evidence cannot validate.

## Required Output

- **Lightweight Path:** report repository facts used, behavior boundary, change and reason, validation evidence, and human decisions.
- **Full Path:** follow [review-output-contract.md](references/review-output-contract.md).
