# Testing and Change Safety

Use tests and other validation as evidence for the behavior they actually observe. A passing suite does not prove every requirement, failure window, deployment state, or external side effect.

## Use This Reference When

Use this reference for a feature, defect, refactor, acceptance outcome, side effect, or high-risk behavior. Start by identifying inputs, outputs, state transitions, boundary values, failure semantics, side-effect order, retries, cancellation, and concurrency windows.

Choose an observable behavior and an independent Oracle before selecting a development rhythm. Existing tests are evidence of covered behavior; they can also preserve an old misunderstanding.

## User-Selected Development Rhythm

Treat development rhythm and validation depth as separate decisions. TDD and TCR control the development rhythm. E2E and mutation testing control validation depth. A User can therefore request TDD while also requiring an acceptance-level check.

Resolve the values in this order:

1. An explicit value in the current User prompt.
2. A value in Repository Policy when the current prompt does not choose one.
3. `auto` when neither source chooses one.

The source records where the requested value came from. An explicit `auto` is sourced from the current User prompt; `default-auto` applies only when neither the Prompt nor Repository Policy supplies a value. Explain the evidence used to infer the effective value separately.

Use these fields when the Client supports structured settings, or accept the same names in ordinary Prompt or Repository Instruction text:

```yaml
development_rhythm: auto
validation_profile: auto
```

### `development_rhythm`

| Value | Meaning | Required conditions |
| --- | --- | --- |
| `auto` | Recommend and use the smallest safe rhythm supported by Repository evidence. | Report which rhythm became effective and why. |
| `direct` | Implement the bounded change, then run the selected validation without requiring an artificial RED step. | The behavior is understood, the change is reversible, and an existing Oracle gives fast feedback. Direct does not mean untested. |
| `tdd` | Establish a meaningful RED for the requested behavior, make the smallest GREEN change, then refactor and run regression gates. | The expected behavior can be stated independently, and the failing test fails for the intended reason before production code changes. |
| `tcr` | Work in tiny checkpoints; test each checkpoint, commit GREEN, and revert RED. | Tests are fast and reliable, the working tree can be isolated safely, and the User has granted explicit version-control authorization for commit and revert operations. |
| `characterization-first` | Capture current observable behavior before changing a legacy or poorly understood implementation. | The existing behavior is the critical unknown; label accidental or disputed behavior instead of silently treating it as the desired contract. |

### `validation_profile`

| Value | Meaning | Boundary |
| --- | --- | --- |
| `auto` | Select validation from the actual risk and available Repository gates. | Report the effective profile and uncovered risk. |
| `focused` | Run the smallest test, build, lint, static, or contract checks that observe the changed behavior. | It cannot waive broader gates required by Repository Policy or Production-Ready delivery. |
| `repository` | Run all Repository-required gates relevant to the Diff. | Passing does not prove deployment, external systems, or untested behavior. |
| `acceptance-e2e` | Add an acceptance or E2E path for a user-visible outcome that crosses boundaries. | Keep lower-level checks when they are needed for diagnosis or boundary cases. |
| `mutation-assisted` | Challenge an important established suite with scoped mutation testing. | Use only when the Oracle is reliable and the authorized toolchain can execute it. |

For `auto`, infer a recommendation from risk, Oracle reliability, feedback speed, working-tree state, and authorization. For an explicit choice, first check its required conditions. If a required condition is missing, report `blocked`, name the missing condition, recommend the nearest feasible option, and wait for the User when changing the requested rhythm would alter the workflow. The Agent must not silently substitute another development rhythm.

When the Client supports machine-readable prerequisite IDs, use `fast-test-feedback`, `reliable-test-oracle`, `isolated-working-tree`, `version-control-authorization`, and `mutation-tool-and-install-authorization`. Report every missing prerequisite; do not collapse test speed, Oracle reliability, workspace isolation, and version-control authority into one generic TCR failure.

An explicit `validation_profile` can add checks but cannot remove mandatory Repository gates. Do not install a testing, coverage, mutation, or E2E tool, change CI, commit, revert, or touch an external environment without the authority required for that action.

## Executable Gate Routing

Inventory existing repository gates before selecting validation. Use the smallest set that observes the actual risk; do not install a fashionable tool or change CI without authorization.

| Gate | Use it for | It does not prove |
| --- | --- | --- |
| Formatter and Linter | Repository-defined formatting and mechanical style | Behavior, data, or side-effect correctness |
| Static Analysis and Architecture Test | Type, dependency, complexity, nullability, security, or layer rules the analyzer actually implements | Requirements absent from the configured rules |
| Build | Compilation, packaging, and configured build checks | Runtime behavior or deployment success |
| Unit, Integration, Contract, and E2E Test | Observable behavior at the boundary each test executes | Untested failures, environments, or consumers |
| Dependency and Security Scan | Known issues in the scanned dependency and configuration scope | Unknown vulnerabilities or authorization to upgrade |
| Coverage and Mutation Test | Execution reach and whether selected code changes are detected | A reliable Oracle or correct business expectation |

A Prototype requires a repeatable Oracle for its experiment and a list of Production-Ready gates not run. Production-Ready work runs all repository-required gates relevant to the Diff. Record every executed command, environment, exit code, result, and limitation; record a required gate not run as a validation blind spot.

## Selection Rules

| Decision | Apply it when | Choose the alternative when | Checkable output |
| --- | --- | --- | --- |
| Direct implementation | The change is low risk, well understood, reversible, and has fast feedback from an existing executable Oracle. | Use TDD when a new rule, defect, boundary value, or state transition can first be expressed as a meaningful failing test. | Named Oracle, behavior boundary, command, and result. |
| TDD | A failing test can state the intended observable behavior before production code changes. Work RED, make the smallest GREEN change, then run full regression. | Use characterization tests when current legacy behavior is unknown and must be observed before restructuring. | RED failure, smallest GREEN Diff, expected and actual output, regression result. |
| TCR | High-risk work can be divided into very small GREEN checkpoints with fast reliable tests and safe version-control operations. | Use TDD without a commit-per-cycle constraint when the feedback loop is reliable but the version-control workflow is not safe or practical. | Checkpoint command, exit code, revision, and behavior covered. |
| Characterization tests | Existing behavior must be observed before a legacy refactor or migration, including surprising outputs and failure semantics. | Use acceptance tests when the repository's main risk is a cross-boundary user outcome rather than internal legacy uncertainty. | Captured inputs, outputs, side effects, known ambiguity, and test result. |
| Acceptance or E2E tests | A user-visible, cross-boundary outcome needs proof across UI, API, persistence, messaging, or provider seams. | Keep focused lower-level tests when precise failure diagnosis or many boundary cases matter. | Scenario, environment, observed outcome, and lower-level diagnostic coverage. |
| Mutation testing | An important suite has assertions that may pass while meaningful production changes go undetected. | Use focused behavior tests first when the current Oracle is absent, unstable, or too slow for a useful mutation run. | Mutation scope, surviving mutations, and follow-up decision. |
| 3A test shape | A focused test has one behavior whose setup, action, and observable assertion remain easy to scan. | Keep multiple actions when their order is the workflow, state-machine, Saga, or interaction contract. | Arrange, Act, Assert evidence or explicit workflow-order rationale. |

Oracle reliability comes before test count. Derive expected values from a contract, known-good example, independent implementation, or externally observed behavior. Do not recompute the assertion with the same logic under test.

For authorization, payments, irreversible data changes, concurrency, external side effects, retry or idempotency, time boundaries, schema changes, security, or broad dependency migrations, map failure windows and add stronger checkpoints or independent validation.

## When Another Option Fits Better

- Use characterization tests before a legacy refactor when the current behavior is the critical unknown. Use TDD for a new rule once the desired behavior can be stated independently of the old implementation.
- Use acceptance or E2E coverage when the risk crosses application boundaries and a user outcome is the Oracle. Use focused unit or contract coverage when failures need fast diagnosis or the E2E environment cannot isolate the rule.
- Use TCR only when tests are fast and reliable and every checkpoint can be safely versioned. Use short TDD cycles with recorded RED and GREEN evidence when those preconditions do not hold.
- Use mutation testing to challenge an established, important test suite. Repair an unreliable or tautological Oracle first; mutation results cannot compensate for an undefined behavior contract.

## Common Misjudgments

The following are source-bounded experiment records. Each Observation ID reuses an existing public evidence coordinate; it is not a newly generated Failure ID. They are review prompts, not a ranking of test styles.

### Observation ID: `day-27/small-cycles-improvement#host-oracle`

Source: [Day 27 small-cycles improvement at commit e860838](https://github.com/eric861129/AI-CleanCode-API-Demo/blob/e860838ee9a353a55ae6ff0eb661220c49dbb16a/docs/evidence/day-27/small-cycles-improvement/experiment-results.md)

Supports: The experiment required three independently fixed Host Oracles because candidate tests written by the Agent could not be the sole decision source. It compared the same Oracle, Coverage, Mutation, and protected boundary rather than raw test counts.

Misjudgment to avoid: Treat an Agent-authored suite or a larger test count as the only proof of a cross-boundary behavior. Name an independent Oracle and the behavior it exercises.

### Observation ID: `day-27/small-cycles-improvement#coverage-and-mutation`

Source: [Day 27 small-cycles improvement at commit e860838](https://github.com/eric861129/AI-CleanCode-API-Demo/blob/e860838ee9a353a55ae6ff0eb661220c49dbb16a/docs/evidence/day-27/small-cycles-improvement/experiment-results.md)

Supports: The candidate components reached 100% Line and Branch Coverage, while the experiment records that Coverage alone cannot determine whether Assertions are correct. It therefore used mutation probes and semantic-stability checks as additional evidence.

Misjudgment to avoid: Present a GREEN suite or coverage percentage as proof of every failure window, side effect, or assertion quality when the Oracle did not exercise those claims.

## Stop Conditions

Stop and escalate when no independent Oracle can validate a high-risk behavior; when the required test crosses an unauthorized data, provider, security, CI, or deployment boundary; when existing behavior and requested behavior conflict without an authorized decision; or when an unobserved failure window could change data integrity or an external side effect.

Record the covered behavior, command, environment, exit code, result, and blind spots. Evidence supports the tested claim only and does not authorize a broader change.
