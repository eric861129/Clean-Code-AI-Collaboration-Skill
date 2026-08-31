# Code Readability Decisions

Use repository language and observed change pressure before applying a readability rule. A familiar name, extraction, or class pattern is not evidence that it fits this repository.

## Use This Reference When

Use this reference when a change requires a decision about naming, comments, function shape, duplication, model roles, or class cohesion. It is especially relevant when an Agent must make the behavior easy to find and explain without widening the approved Diff.

Read the affected callers, contracts, tests, and repository instructions first. Record the current name or boundary, the behavior that must remain stable, and the evidence that makes the proposed local change meaningful.

## Selection Rules

| Decision | Apply it when | Choose the alternative when | Checkable output |
| --- | --- | --- | --- |
| Naming policy | A repository domain term describes the responsibility at the current abstraction level and does not hide a side effect or temporary mechanism. | Preserve an externally serialized, database, or public-contract name; document the local mapping when changing it needs compatibility work. | Name-to-domain evidence with affected paths, callers, or contract fields. |
| Comment evidence | A contract, reason, hazard, unit, or constraint cannot be made clear by code alone. | Rename, extract, or simplify when the comment only repeats the implementation. Resolve a code-comment conflict from repository evidence before retaining either claim. | The comment's source or invariant and the validation that keeps it current. |
| Stepdown | Readers need policy before mechanism and each delegated step has a coherent, nearby responsibility. | Keep a small cohesive calculation together when extraction makes its inputs, ordering, or invariant harder to see. | Main-flow scan plus the extracted or retained behavior boundary. |
| Command-Query Separation | A caller can reasonably expect a read to be side-effect free or a command to have explicit effects and failure meaning. | Keep an atomic operation together when separating read and write would create a race, duplicate a transaction, or obscure the outcome. | Inputs, observable result, side effects, exceptions, and concurrency constraint. |
| DRY | Repeated code has the same business meaning and the same likely reason to change. | Keep similar syntax separate when the domain meaning, owner, failure rule, or future variation differs. | Shared reason-to-change evidence and affected callers. |
| DTO, persistence, and domain roles | A real boundary protects public shape, storage concerns, invariants, or independently changing consumers. | Use a direct model when the repository has one stable role and a second mapping adds no demonstrated protection. | Role map, dependency direction, and mapping or no-mapping rationale. |
| Class cohesion | Different actors, invariants, or reasons to change can be isolated without hiding a single workflow behind extra navigation. | Keep a cohesive class when the same collaborators and invariant change together. | Responsibility list, likely-change examples, and navigation cost. |

Prefer the smallest option that makes the current behavior and boundary explicit. The choice is contextual; line count and file count do not decide cohesion by themselves.

## When Another Option Fits Better

- Keep an existing public or serialized name when compatibility is the governing constraint. Introduce a precise local domain name only when the mapping boundary can be validated and is inside the authorized Diff.
- Keep duplicated-looking code when two workflows have different owners, invariants, or failure semantics. Extract a shared helper when repository callers demonstrate one stable policy and one change would otherwise require synchronized edits.
- Keep a short calculation inline when its state and ordering are its explanation. Use Stepdown when the top-level method must expose policy, and each extracted step can be understood from its name and local inputs.
- Use one model when the repository establishes one stable responsibility. Separate DTO, persistence, and domain models when a boundary must prevent storage or transport detail from redefining domain behavior.

For each rejected option, state the condition that would reverse the choice and the repository observation needed to verify it.

## Common Misjudgments

The following are source-bounded experiment records. Each Observation ID reuses an existing public evidence coordinate; it is not a newly generated Failure ID. They are review prompts, not a pattern ranking.

### Observation ID: `day-05/naming-comparison#human-review`

Source: [Day 5 naming comparison at commit e860838](https://github.com/eric861129/AI-CleanCode-API-Demo/blob/e860838ee9a353a55ae6ff0eb661220c49dbb16a/docs/evidence/day-05/naming-comparison.md)

Supports: The Human Review accepted a short local `outcome` and rejected `overdueResult` for that scope because the nearby helper and tuple already supplied context. It also accepted a more explicit helper name where the caller could not see the implementation.

Misjudgment to avoid: Choose a name from its length or copy a reviewer-preferred string without checking scope, caller context, and the behavior the name must expose.

### Observation ID: `day-06/comments-formatting#stale-comment-agent-impact`

Source: [Day 6 comments and formatting at commit e860838](https://github.com/eric861129/AI-CleanCode-API-Demo/blob/e860838ee9a353a55ae6ff0eb661220c49dbb16a/docs/evidence/day-06/comments-formatting.md)

Supports: The controlled stale-comment mutation left executable Gates green while the comment contradicted repeated-notification behavior. The follow-up Agent path stopped at the evidence conflict and did not produce a harmful Code Diff.

Misjudgment to avoid: Treat a comment as behavior proof when executable code, tests, smoke evidence, or repository instructions conflict. Stop to resolve the conflict instead of silently preserving the text.

### Observation ID: `day-07/function-levels#over-split-run-01`

Source: [Day 7 function levels at commit e860838](https://github.com/eric861129/AI-CleanCode-API-Demo/blob/e860838ee9a353a55ae6ff0eb661220c49dbb16a/docs/evidence/day-07/function-levels.md)

Supports: The over-split candidate lowered entry complexity by distributing it across more symbols, requiring readers to rebuild the call relationship. The accepted Stepdown candidate kept side-effect order and HTTP response visible at the entry point.

Misjudgment to avoid: Split methods by line count or entry complexity alone when the extraction only relocates a cohesive calculation and adds navigation.

### Observation ID: `day-08/function-heuristics#parameter-dry-run-02`

Source: [Day 8 function heuristics at commit e860838](https://github.com/eric861129/AI-CleanCode-API-Demo/blob/e860838ee9a353a55ae6ff0eb661220c49dbb16a/docs/evidence/day-08/function-heuristics.md)

Supports: The parameter and DRY candidate moved dependencies into a private processor, added three private types, and required extra navigation. The source records no second use case that justified making that structure the default.

Misjudgment to avoid: Extract a shared result type, DTO-like mapping, or private processor solely because data shapes repeat when no independently changing boundary has been established.

## Stop Conditions

Stop and escalate when the domain term, invariant, caller behavior, or public-name compatibility cannot be established from repository facts; when the change would cross an unauthorized contract, schema, dependency, or deployment boundary; or when the expected behavior cannot be checked through an available Oracle.

Evidence can justify a proposal and its validation plan. It does not authorize a broader rename, migration, or public-contract change.
