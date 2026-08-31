---
name: clean-code-ai-collaboration
description: Use when repository changes require contextual trade-offs about behavior preservation, test adequacy, change locality, dependency boundaries, side effects, or review evidence.
license: MIT
compatibility: Agent Skills-compatible coding agents.
metadata:
  author: eric861129
  version: "0.3.0"
---

# Clean Code AI Collaboration

## Core Principle

The repository provides facts; Clean Code provides quality judgment. CLEAN controls collaboration responsibilities between the User and Agent. Repository facts override examples in this Skill. Evidence supports a decision but does not enlarge authorization.

## Path Selection

Evaluate Full Audit first, then Standard, then Lightweight. New evidence may upgrade a path; it must not downgrade one to shorten the report.

- **Full Audit Path:** use for a public contract, production data or migration, external side effect, third-party dependency change, concurrency, security, privilege, CI, infrastructure, deployment, destructive action, unclear authority, formal audit, material trade-off, or critical unknown. Read [repository-context-template.md](references/repository-context-template.md).
- **Standard Path:** use for a repository feature, test, defect, refactor, or internal design change with known ownership, authorization, behavior boundary, and executable gates.
- **Lightweight Path:** use only for a local, reversible readability change with no behavior, contract, data, side effect, dependency, ownership, or deployment impact and one obvious option.

## Reference Routing

Read [clean-code-for-agent-legibility.md](references/clean-code-for-agent-legibility.md) first when judging whether code lets an Agent find, change, validate, and explain the relevant behavior. Load only references that change the current decision:

- Code structure or naming: [code-readability.md](references/code-readability.md)
- Tests, defects, refactoring, or risky behavior: [testing-and-change-safety.md](references/testing-and-change-safety.md)
- Abstractions, providers, components, concurrency, or architecture: [design-and-dependency-boundaries.md](references/design-and-dependency-boundaries.md)
- Handoffs, teamwork, or estimates: [collaboration-and-estimation.md](references/collaboration-and-estimation.md)
- Standard or Full Audit output: [review-output-contract.md](references/review-output-contract.md)

## CLEAN Lenses

Use CLEAN as the User's review lens for an Agent's work. It is not a score that claims automatic compliance.

- **C — Context-Aware Code（情境感知）:** establish Context from repository facts before change.
- **L — Localized Change（局部變更）:** state the Expected Diff and keep the change boundary local.
- **E — Explicit Intent and Boundaries（意圖明確）:** make Intent, contracts, and ownership visible.
- **A — Auditable by Evidence（實據可審）:** connect Evidence to validation and known gaps.
- **N — Non-Surprising Behavior（符合預期）:** preserve Behavior, including failures and side effects.

## Authorization Gate

- **evidence does not grant authority.** Valid authority is the intersection of platform limits, repository instructions, explicit User authorization, and responsible Owner approval.
- Without explicit authority, stop before changing a public contract, dependency, production data or migration, external side effect, secret or privilege, CI or infrastructure, deployment, or any destructive operation.
- When evidence supports a change outside the authorized boundary, analyze it, propose a Diff or decision, name the required Owner, and leave the external state unchanged.
- Stop for conflicting instructions, a critical unknown, or high-risk behavior that available evidence cannot validate.

## Required Output

- **Lightweight Path:** report the facts used, behavior boundary, change, validation, and only applicable human decisions.
- **Standard Path:** follow the Standard Output Contract and omit non-material sections.
- **Full Audit Path:** follow every Full Audit heading and traceability rule in [review-output-contract.md](references/review-output-contract.md).
