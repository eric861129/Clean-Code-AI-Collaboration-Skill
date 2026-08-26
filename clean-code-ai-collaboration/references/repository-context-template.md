# Repository Context Template

Collect evidence before applying a design rule. Keep this context close to the repository because it changes with the codebase.

## Required Context

- Repository and active revision
- Task, change reason, and acceptance criteria
- Domain terms and current behavior
- Public API, event, file, and user-visible contracts
- Data model, persistence rules, migrations, and compatibility limits
- Side effects such as notifications, queues, outbox records, files, or remote calls
- Current architecture, dependency direction, and provider limitations
- Test commands, behavior Oracle, smoke checks, and known blind spots
- Allowed and forbidden change scope
- Owners, consumers, deployment path, and rollback expectations
- Known risks, assumptions, and unknowns

## Criticality Check

An unknown is critical when a different answer could change externally observable behavior, data integrity, security, dependency direction, deployment safety, or the User's decision. Stop and ask for that answer. Record non-critical unknowns and proceed with a reversible choice.

Repository facts override generic examples in this Skill. A familiar framework pattern is not project evidence.
