# C# / .NET Language Profile

## Use This Profile When

Use this profile when the Changed Module contains C# source or a nearby C# project manifest and the change depends on .NET type, async, resource, enumeration, equality, or dependency-lifetime semantics. A solution file is supporting evidence only; it does not make unrelated frontend, Python, generated, or build-output changes C# work.

Do not use this profile as an ASP.NET Core, Entity Framework Core, test-framework, container, or architecture-pattern guide. Those facts must come from the repository or a separately available framework profile.

## Repository Facts to Inspect

Before recommending a change, inspect the nearest `.csproj` and any imported `Directory.Build.props` or `Directory.Build.targets`. Record `TargetFramework` or `TargetFrameworks`, `Nullable`, `LangVersion`, implicit usings, warning policy, analyzer packages, generated-code settings, and package versions that affect the changed code. Check `global.json` when it pins an SDK, but do not treat the installed SDK as proof of the project's language contract.

Read neighboring production code and tests for public signatures, exception mapping, serialization, null behavior, async conventions, cancellation, equality, and resource ownership. If the repository uses a DI container, inspect the existing registration and scope boundaries before discussing DI lifetime. If it constructs objects directly, do not introduce a container merely to follow this profile.

## Version-Sensitive Facts

Separate runtime or BCL availability from compiler-language availability. `TargetFramework`, `LangVersion`, SDK selection, package versions, and per-file nullable directives can describe different constraints. A multi-targeted project may require one implementation to work under several targets.

When any relevant version or setting is unknown, report it as Unknown and use syntax and APIs already demonstrated by the nearest project. Do not assume the newest C# version, the newest .NET runtime, nullable warnings enabled everywhere, or identical behavior across target frameworks.

## Language or Framework Semantic Risks

- Nullable annotations improve compile-time analysis; they are not runtime validation. Adding `string` instead of `string?` does not reject null input, and adding `!` only suppresses analysis. Preserve the observed null contract or add validation at the real boundary with explicit approval.
- Pass `CancellationToken` through an existing cancellable call chain and preserve the repository's cancellation exception or result semantics. Do not add a token to a public API, convert timeout into cancellation, or swallow `OperationCanceledException` without treating that as a contract change.
- Determine who owns each `IDisposable` or `IAsyncDisposable`. Use `using` only when the current scope owns disposal; use `await using` when owned async cleanup is required. Disposing injected, cached, returned, or caller-owned instances can shorten their lifetime incorrectly.
- Avoid sync-over-async such as blocking on a `Task` unless existing constraints make it unavoidable and the deadlock, scheduling, and exception behavior are understood. Adding `async` can also alter stack traces, timing, and public return types.
- LINQ deferred execution can move I/O, exceptions, and side effects to enumeration time. Multiple enumeration can repeat a database query, network read, iterator mutation, or expensive computation. Materialize only when a stable snapshot or single execution is part of the intended behavior.
- Class, record, entity, and value-object equality are different domain contracts. Changing equality or hash behavior can affect sets, dictionaries, caches, tracking, serialization, and tests; a record is not automatically the right model for every data carrier.
- DI lifetime matters only when the repository already uses dependency injection. Verify singleton, scoped, and transient ownership before capturing a shorter-lived service, introducing mutable shared state, or moving disposal responsibility.

## Clean Code Misapplications

Do not silence nullable warnings with `!`, broad pragmas, or arbitrary defaults when the real boundary remains uncertain. Do not append `Async` and convert an entire public call chain merely for naming consistency. Do not materialize every enumerable to avoid reasoning about deferred execution.

Avoid extracting interfaces, repositories, base classes, or service layers solely to make a small method look abstract. Do not convert classes to records for terseness, replace explicit failure types with a generic exception, or move construction into DI unless the repository's ownership and substitution needs support that change.

## Behavior and Boundary Contracts

Preserve public method signatures, null acceptance, exception types, result mapping, ordering, enumeration count, side-effect timing, serialization names and shapes, equality and hashing, thread-safety, cancellation, and disposal ownership unless the task explicitly changes them.

At I/O boundaries, distinguish failure, cancellation, timeout, empty result, and invalid input. At resource boundaries, state who creates, lends, returns, and disposes the object. At async boundaries, state whether work starts immediately, whether calls may overlap, and where cancellation is observed.

## Repository-Native Gate Discovery

Use the repository's existing build scripts, solution or project selection, test filters, analyzer configuration, formatter, and CI commands. Typical clues include `dotnet` commands in CI, `.editorconfig`, analyzer package references, architecture tests, and project-specific test runners. Run only tools already available or authorized; this profile does not authorize SDK, workload, analyzer, formatter, or package installation.

Choose the smallest gate that observes the changed behavior, then retain every mandatory repository gate. A compile-only check cannot establish runtime null validation, cancellation propagation, disposal timing, repeated enumeration, equality behavior, or external side effects.

## When Another Option Fits Better

A synchronous method can remain clearer for short CPU-only work with no asynchronous dependency. An `IEnumerable<T>` can remain deferred when lazy streaming is intentional and the source is safe to enumerate at the documented time. Materialization fits when one execution or snapshot semantics are required.

A class can retain reference or custom equality; a record fits only when value-like equality matches the domain and serialization contract. Direct construction fits code without a container or lifetime graph. Repository- or framework-specific guidance should control web pipelines, database tracking, hosted services, or container registration.

## Common Agent Failure Modes

- Treating nullable warnings as proof that runtime nulls are impossible.
- Adding a `CancellationToken` parameter but not forwarding it to cancellable dependencies.
- Disposing an injected dependency or returning an already-disposed stream.
- Enumerating a query for logging and then enumerating it again for the result.
- Replacing a class with a record without checking equality, hashing, or serializers.
- Capturing scoped mutable state inside a longer-lived registration.
- Assuming a root `.sln`, an SDK on `PATH`, or a familiar architecture describes the Changed Module.
- Reporting `dotnet test` as sufficient when the relevant project, target framework, or behavioral path was not exercised.

## Stop and Escalation Conditions

Stop when the relevant target framework or language version cannot be established and the proposed syntax or API may be unsupported. Escalate before changing a public signature, cancellation or exception mapping, serialized contract, equality or hash semantics, resource ownership, concurrency behavior, or DI lifetime.

Also stop when a LINQ source may perform external I/O but execution count is unknown, when a disposable object's owner cannot be identified, when generated code would be edited directly, or when required repository gates need an unavailable SDK, service, credential, database, or explicit installation approval.

## Output Additions

For each affected C# Changed Module, report the applied profile and the observed `TargetFramework`, `Nullable`, and `LangVersion` facts or mark them Unknown. Call out cancellation and resource ownership, deferred execution or multiple enumeration, equality and serialization effects, and DI lifetime only when applicable. Name the exact project and repository-native gates run, plus targets or behavioral paths not exercised.

## Evidence Status

Current maturity is published in the generated [Runtime Profile Index](profile-selection.md#runtime-profile-index). Repository contract tests cover structure, selection, and required semantic topics. Versioned metadata records the v0.5.1 and v0.5.2 M2 pilots, including unfavorable outcomes; the latter tested the unchanged technical guidance from Skill v0.5.1. No M3 full run has been recorded. Pilot evidence does not establish general improvement across versions, runtimes, renderers, repositories, clients, or models.
