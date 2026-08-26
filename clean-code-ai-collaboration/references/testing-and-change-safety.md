# Testing and Change Safety

Use this reference for features, defects, refactoring, acceptance tests, side effects, and high-risk changes.

## Start with Observable Behavior

Identify inputs, outputs, state transitions, boundary values, failure semantics, side-effect order, retry behavior, cancellation, and concurrency windows. Existing tests are evidence of covered behavior; they may also preserve an old misunderstanding.

## Choose the Development Rhythm

- Direct implementation fits low-risk, well-understood, easily reversible changes with fast feedback.
- TDD fits new rules, boundary values, defects, and state transitions that can first be expressed as a meaningful failing test.
- TCR fits high-risk work that can be divided into very small Green checkpoints with reliable, fast tests and safe version-control operations.
- Characterization tests fit legacy behavior that must be observed before restructuring.
- Acceptance or E2E tests fit cross-boundary user outcomes; keep lower-level tests for precise diagnosis.
- Mutation testing fits important test suites whose assertions may pass without detecting meaningful production changes.

## Keep Tests Readable

For a focused single-behavior test, Arrange only the state that matters, usually Act once, and Assert the observable contract. Keep multiple actions when their order is itself the workflow, state-machine, Saga, or interaction contract. A helper or Behavior DSL is useful when it reveals intent; it is harmful when readers must learn a second hidden program to understand the test.

## Validate the Path to Green

Record the initial failure, smallest implementation step, full regression result, formatting or static checks, and relevant smoke or boundary checks. A Green suite confirms only the exercised Oracle. Report blind spots and untested failure windows.

## High-Risk Signals

Payments, authorization, irreversible data changes, concurrency, external side effects, retry or idempotency, time boundaries, schema changes, security, and broad dependency migrations justify stronger checkpoints and independent validation.
