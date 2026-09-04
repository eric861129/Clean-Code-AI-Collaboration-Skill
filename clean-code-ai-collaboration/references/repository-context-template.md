# Repository Context Template

Collect evidence before applying a design rule. Keep this context close to the repository because its revision, ownership, environment, and executable behavior can change. Repository facts override generic examples, and evidence does not grant authority for a broader change.

## Evidence Freshness

For every decision-changing fact, record when and where it was observed: revision or deployment identifier, path or endpoint, environment, command or source, and observation time when relevant. Label evidence as current for the active revision, historical, environment-specific, or stale/unknown. Refresh evidence when a later revision, migration, configuration change, or different environment could change the conclusion.

## Source Authority

Name the source and what it can establish rather than treating all sources as interchangeable. A versioned repository file may establish current code at a named revision; an executable Oracle may establish only the behavior it exercised; a contract or consumer may establish compatibility expectations; a responsible human establishes approved scope and external commitments.

When sources conflict, record the conflict, the revision and environment for each source, the Owner who can resolve it, and the safe stop boundary. Repository instructions and explicit authorization govern what may change independently from evidence quality.

## Current Revision

- Repository, branch or ref, commit, merge base when relevant, and active working-tree state
- Task, change reason, acceptance criteria, and expected Diff boundary
- Requested and effective `development_rhythm`; requested and effective `validation_profile`; source of each value and any unmet prerequisite
- Related source revisions, generated artifacts, configuration, migration state, or deployed version when they can change behavior
- Environment, dependency lock state, feature flags, test data assumptions, and access limits that affect the conclusion

## Required Context

- Domain terms, current behavior, and behavior that must not change
- Public API, event, file, database, and user-visible contracts
- Data model, persistence rules, migrations, retention, and compatibility limits
- Side effects such as notifications, queues, outbox records, files, or remote calls
- Current architecture, dependency direction, provider limitations, ownership, and consumers
- Allowed and forbidden change scope, deployment path, rollback expectations, and required human decisions
- Known risks, assumptions, unknowns, and the validation boundary

## Executable Oracle

For each validation claim, record the observable behavior, independent expected result, command or repeatable procedure, environment, inputs or fixtures, exit code or artifact, and limitation. A test, smoke check, log, query, or manual observation is an Oracle only for the behavior it actually observes.

When no executable Oracle exists, record the strongest available evidence, the behavior it cannot verify, and whether the gap makes the unknown critical. Do not convert a planned command, unrun test, or stale result into validation evidence.

## Context Budget

Load the smallest set of repository facts that can change the current decision. Prefer direct callers, contracts, tests, configuration, and ownership records over broad unrelated history. Record omitted sources and why they are not decision-changing, so another reviewer can see the boundary of the investigation.

The budget controls attention and review scope. It does not claim reduced Token use, establish completeness, or authorize skipping a critical source.

## Criticality Check

A Critical Unknown is one where a different answer could change externally observable behavior, data integrity, security, dependency direction, deployment safety, or a human decision. Stop and obtain or escalate that answer before an irreversible or boundary-crossing action.

Record a non-critical unknown with its decision impact and proceed only with a reversible choice inside the approved scope. A familiar framework pattern is not project evidence.
