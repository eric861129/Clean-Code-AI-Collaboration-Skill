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

These are failure modes observed in Agent-assisted changes. They are review prompts, not a ranking of patterns.

- Copying a nearby name or abstraction without checking its callers, owner, or current contract can spread an old misunderstanding.
- Splitting methods or classes by line count can turn one readable workflow into a navigation chain with hidden shared state.
- Treating a comment as proof can preserve stale behavior when the executable code, tests, or contract disagrees.
- Extracting syntactic repetition can couple workflows that happened to look alike but have different failure meanings.
- Introducing a DTO or interface because it appears cleaner can add mapping and synchronization work without a protected boundary.

## Stop Conditions

Stop and escalate when the domain term, invariant, caller behavior, or public-name compatibility cannot be established from repository facts; when the change would cross an unauthorized contract, schema, dependency, or deployment boundary; or when the expected behavior cannot be checked through an available Oracle.

Evidence can justify a proposal and its validation plan. It does not authorize a broader rename, migration, or public-contract change.
