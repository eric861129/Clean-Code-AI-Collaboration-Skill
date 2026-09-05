---
name: clean-code-ai-collaboration
description: Use when repository changes require contextual trade-offs about behavior preservation, test adequacy, change locality, dependency boundaries, side effects, or review evidence.
license: MIT
compatibility: Agent Skills-compatible coding agents.
metadata:
  author: eric861129
  version: "0.5.2"
---

# Clean Code AI Collaboration

## Core Principle

Repository facts control Context; Clean Code supplies quality judgment; CLEAN defines User-Agent responsibilities. Evidence supports decisions, not authorization.

## Do Not Use

Skip syntax-only questions, repository-free conceptual explanations, standalone examples, formatter-owned layout, and work fully covered by a more specialized Skill. When that Skill leaves a behavior, boundary, side-effect, or Clean Code trade-off unresolved, use this Skill only for the remaining judgment.

## Path Selection

Evaluate Full Audit, then Standard, then Lightweight. Evidence may upgrade; it must not downgrade a path.

- **Full Audit Path:** public contract, production data or migration, external effect, dependency, concurrency, security, privilege, CI, infrastructure, deployment, destruction, unclear authority, audit, material trade-off, or critical unknown. Read [repository-context-template.md](references/repository-context-template.md).
- **Standard Path:** repository feature, test, defect, refactor, or internal design change with known ownership, authorization, behavior boundary, and executable gates.
- **Lightweight Path:** local, reversible readability change with one obvious option and no behavior, contract, data, side-effect, dependency, ownership, or deployment impact.

## Delivery Readiness

- **Prototype:** answer one isolated, disposable question with a repeatable Oracle; list remaining gates.
- **Production-Ready:** satisfy repository policy and executable gates; report deployment, UAT, and validation blind spots.

Readiness never lowers risk or authorization. A Prototype touching production data, public contracts, providers, security, or external effects still uses Full Audit.

## Development and Validation Preferences

Before changing production code, resolve two independent preferences:

- `development_rhythm`: `auto`, `direct`, `tdd`, `tcr`, or `characterization-first`.
- `validation_profile`: `auto`, `focused`, `repository`, `acceptance-e2e`, or `mutation-assisted`.

Priority: User prompt, Repository Policy, then `auto`. Preferences cannot waive gates, safety, or authorization. Read [testing-and-change-safety.md](references/testing-and-change-safety.md); report requested and effective values plus feasibility blocks. Never silently replace an infeasible explicit choice.

## Reference Routing

Read only relevant references:

- Profile selection for repository code changes: [profile-selection.md](references/profile-selection.md)
- Agent legibility: [clean-code-for-agent-legibility.md](references/clean-code-for-agent-legibility.md)
- Code structure or naming: [code-readability.md](references/code-readability.md)
- Tests, defects, refactoring, or risky behavior: [testing-and-change-safety.md](references/testing-and-change-safety.md)
- Abstractions, providers, components, concurrency, or architecture: [design-and-dependency-boundaries.md](references/design-and-dependency-boundaries.md)
- Handoffs, teamwork, or estimates: [collaboration-and-estimation.md](references/collaboration-and-estimation.md)
- Standard or Full Audit output: [review-output-contract.md](references/review-output-contract.md)

## CLEAN Lenses

Use CLEAN as the User's review lens, not an automatic-compliance score.

- **C — Context-Aware Code（情境感知）:** establish Context from repository facts.
- **L — Localized Change（局部變更）:** state the Expected Diff and keep it local.
- **E — Explicit Intent and Boundaries（意圖明確）:** expose Intent, contracts, and ownership.
- **A — Auditable by Evidence（實據可審）:** connect Evidence to validation gaps.
- **N — Non-Surprising Behavior（符合預期）:** preserve Behavior, failures, and side effects.

## Authorization Gate

- **evidence does not grant authority.** Authority requires platform permission, repository instructions, User authorization, and Owner approval.
- Without explicit authority, stop before changing a public contract, dependency, production data or migration, external side effect, secret or privilege, CI or infrastructure, deployment, or any destructive operation.
- For out-of-scope changes, analyze, propose a Diff, name the Owner, and leave state unchanged.
- Stop for instruction conflicts, critical unknowns, or high-risk behavior without adequate validation.

## Required Output

- **Lightweight Path:** report the facts used, behavior boundary, change, validation, and only applicable human decisions.
- **Standard Path:** follow the Standard Output Contract and omit non-material sections.
- **Full Audit Path:** follow every Full Audit heading and traceability rule in [review-output-contract.md](references/review-output-contract.md).
