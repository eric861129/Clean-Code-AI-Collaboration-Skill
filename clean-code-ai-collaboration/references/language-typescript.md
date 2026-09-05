# TypeScript Language Profile

## Use This Profile When

Use this profile when a Changed Module contains `.ts`, `.tsx`, `.mts`, or `.cts` files, or when a TypeScript project configuration changes and nearby source establishes the language boundary. Prefer the nearest `tsconfig.json` or `tsconfig.*.json` project boundary, then the enclosing package manifest. JavaScript, JSX syntax, or a root workspace file alone does not establish TypeScript behavior.

Keep framework and tool-specific rules separate. React, Vue, a runtime schema library, a linter, and a bundler apply only when repository evidence makes them relevant.

## Repository Facts to Inspect

Inspect the installed or locked TypeScript version and the complete effective `tsconfig` chain, including `extends` and Project References. Record `strict` and its overrides, `exactOptionalPropertyTypes`, `noUncheckedIndexedAccess`, `moduleResolution`, `module`, `target`, `lib`, declaration settings, path mappings, JSX mode, and emit or no-emit behavior.

Read the nearest `package.json` for package `type`, `exports`, `imports`, public type entry points, scripts, package manager, and dependency versions. Inspect neighboring implementation and tests for runtime validation, error mapping, Promise behavior, module interop, generated declarations, and compatibility expectations. Find the actual typecheck, test, build, lint, and package gates without assuming any one tool is mandatory.

## Version-Sensitive Facts

Compiler behavior comes from the repository's TypeScript version and effective configuration, while runtime syntax and APIs depend on `target`, runtime versions, libraries, transforms, and bundling. A newer local compiler or Node runtime does not prove that the package supports it. Project References may deliberately use different effective settings.

When version, configuration inheritance, package mode, or runtime target is Unknown, preserve syntax and type patterns already compiled by the affected project and report the uncertainty. Do not assume the latest narrowing, module-resolution, decorator, JSX, or standard-library behavior.

## Language or Framework Semantic Risks

- Structural typing can accept values from unrelated domains when their shapes happen to match. Excess-property checks do not apply uniformly after assignment, assertion, or generic flow. Add nominal signals only when domain identity is a real contract, not as decoration.
- A union becomes safe through evidence-based narrowing. Preserve discriminants, exhaustive handling, and the runtime path for unexpected values. A `never` assertion can expose a missing compile-time case, but it is not runtime validation for untrusted input.
- Optional properties, explicit `undefined`, missing keys, and `null` can serialize and compare differently. `exactOptionalPropertyTypes` changes assignment rules but does not change runtime objects. Avoid fixing an error by silently deleting, defaulting, or inventing a value.
- `noUncheckedIndexedAccess` exposes possible missing lookups at compile time. A non-null assertion or unchecked cast suppresses the signal without proving the key exists.
- `readonly` and immutable-looking types do not guarantee runtime immutability or remove aliasing. Mutation through another reference can still affect shared arrays, objects, maps, or class instances.
- A Promise represents eventual settlement, not built-in cancellation. Preserve rejection types, observation, ordering, and cleanup. Introducing parallelism with aggregation methods can alter start time, failure timing, partial side effects, and result ordering.
- Module interop depends on package mode, `moduleResolution`, emitted syntax, exports, and the consuming runtime. Changing value imports to type-only imports can remove side effects; changing import style can break CommonJS or ESM consumers.
- Public types and declaration output are compatibility surfaces. Compile-time acceptance does not prove runtime shape, and a locally assignable change can still break downstream source or generated declarations.

## Clean Code Misapplications

Do not replace `unknown` with `any`, add broad assertions, append `!`, or weaken strict settings merely to make diagnostics disappear. Do not add runtime validation to every internal object, or assume a static type validates network, storage, environment, or user input.

Avoid extracting generic wrappers, utility types, conditional types, or shared base interfaces before there are multiple stable uses. Do not convert every sequential Promise flow into parallel work, rewrite module style for consistency, or expose an internal type solely to reduce duplication.

## Behavior and Boundary Contracts

Preserve runtime input validation, missing versus undefined versus null, serialization shape, error and rejection behavior, Promise ordering, side-effect timing, object identity and mutation, module initialization, package exports, emitted declarations, and downstream type compatibility unless the task explicitly changes them.

At trust boundaries, name the runtime evidence that establishes the value's shape. At module boundaries, separate type-only dependencies from imports required for execution. At async boundaries, state who observes rejection, whether work overlaps, and whether an external cancellation mechanism exists.

## Repository-Native Gate Discovery

Use the typecheck, build, tests, lint, API compatibility checks, declaration generation, package tests, and runtime matrix already defined in scripts, CI, workspace tooling, or contributor docs. Check the affected TypeScript project rather than assuming a root command covers every referenced project.

Do not install a compiler, runtime validator, linter, test runner, transpiler, or bundler on this profile's authority. A successful typecheck does not prove runtime validation, module loading, emitted package compatibility, Promise failure handling, or user-visible behavior.

## When Another Option Fits Better

Structural typing is useful for capability-oriented local boundaries; a branded or wrapped value fits when two identical shapes carry different domain meaning. A union fits a closed set with reliable narrowing; an extensible interface or registry may fit an open plugin boundary.

Sequential Promise execution fits dependent work, rate limits, deterministic side effects, or fail-fast requirements. Parallel execution fits independent work when ordering, cancellation, and partial failure are explicitly handled. Runtime validation belongs at untrusted boundaries, while internal values already constructed under verified invariants may only need static types.

## Common Agent Failure Modes

- Treating a passing typecheck as proof that JSON or external input is valid.
- Silencing optional or indexed access with assertions while preserving the defect.
- Losing a discriminant and replacing safe narrowing with casts.
- Mutating a value through an alias despite a readonly-facing API.
- Starting Promises in parallel and changing error timing or side effects.
- Removing an import as “type-only” even though the module performs required initialization.
- Changing package `type`, exports, or module settings without testing actual consumers.
- Editing generated declaration files instead of their source or generator.
- Applying UI-framework rules to TypeScript files that do not use that framework.

## Stop and Escalation Conditions

Stop when the TypeScript version, effective configuration, runtime target, or package module mode cannot be established and the proposed change depends on it. Escalate before changing a public type or declaration, package export, runtime validation, serialization, error or rejection contract, Promise concurrency, import side effect, or module format.

Also stop when the relevant config is generated, a referenced project or downstream consumer cannot be checked, required gates need unavailable tooling, or resolving a diagnostic would require weakening repository-wide compiler policy.

## Output Additions

For each TypeScript Changed Module, report the applied profile, TypeScript version, effective project config, package mode, and runtime target or mark them Unknown. Identify structural typing, optional or indexed access, union narrowing, runtime validation, Promise, module interop, declaration, and public-type impacts when applicable. Name the exact project gates and consumer paths exercised.

## Evidence Status

Current maturity is published in the generated [Runtime Profile Index](profile-selection.md#runtime-profile-index). Repository contract tests cover structure, selection, and required semantic topics. Versioned metadata records the v0.5.1 and v0.5.2 M2 pilots, including unfavorable outcomes; the latter tested the unchanged technical guidance from Skill v0.5.1. No M3 full run has been recorded. Pilot evidence does not establish general improvement across versions, runtimes, renderers, repositories, clients, or models.
