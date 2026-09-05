# Python Language Profile

## Use This Profile When

Use this profile when a Changed Module contains `.py` or `.pyi` files, or when a Python project manifest changes and nearby repository facts establish Python behavior. The nearest `pyproject.toml`, `setup.py`, or `setup.cfg` defines the project boundary; requirements files and lockfiles are supporting evidence only. A notebook does not automatically opt into source-code analysis.

Keep framework behavior outside this language profile. FastAPI, Django, Pydantic, a dependency-injection library, and a particular type checker apply only when the repository demonstrates and configures them.

## Repository Facts to Inspect

Inspect the nearest project manifest for `requires-python`, build backend, package layout, optional dependency groups, and tool configuration. Check `.python-version`, runtime files, CI matrices, container images, and lockfiles for corroborating Python version facts. A local interpreter on `PATH` is not proof of the supported version range.

Find the repository's formatter, linter, type checker, test runner, coverage settings, and task commands. Read neighboring tests and code for dynamic typing conventions, runtime validation boundaries, import behavior, exception translation, sync and async APIs, generator cleanup, context manager ownership, and mutable state. Treat `.pyi` stubs and public annotations as contracts only to the extent the repository publishes or checks them.

## Version-Sensitive Facts

Separate the minimum supported Python version from the interpreter used in one environment. Syntax, standard-library APIs, typing behavior, packaging metadata, `asyncio` features, and exception details may differ by version. Multiple CI interpreters can be a stronger compatibility contract than a developer's current runtime.

When the Python version or configured tools are Unknown, use syntax and APIs already exercised in the nearest module, preserve compatibility claims, and report the uncertainty. Do not assume the latest language, typing, packaging, or event-loop behavior.

## Language or Framework Semantic Risks

- Dynamic typing means type hints do not enforce runtime inputs or outputs by themselves. Add runtime checks only at a real trust boundary and preserve the existing failure contract; annotations can otherwise document and statically constrain code without changing runtime behavior.
- A mutable default is created once at function definition time. Use a per-call value when calls must not share state. Also inspect aliasing: assigning, slicing, shallow copying, or storing the same list, dictionary, model, or object can let one path mutate another path's state.
- Iterators and generators may be single-use, lazy, stateful, or tied to an open resource. Counting, logging, or testing membership can consume them before the real operation. Re-iteration can repeat I/O or side effects; eager materialization changes memory use, timing, and cleanup.
- At an `asyncio` boundary, preserve whether the caller may cancel, whether child tasks outlive the call, and how cleanup runs. Do not catch or translate cancellation as an ordinary business failure, and do not add background tasks without an owner that awaits, cancels, or observes their exceptions.
- A context manager expresses acquisition and cleanup, not ownership in every case. Use `with` or `async with` when the scope owns the managed lifetime. Do not close injected, cached, yielded, or caller-owned resources merely because they implement a context manager protocol.
- Preserve each exception boundary. Catch only failures the current layer can handle or translate. When translation is part of the contract, retain causal evidence with `raise NewError(message) from original_error`; broad catching can hide cancellation, programmer defects, and partial side effects.
- Imports execute module-level code and can expose circular dependencies or import-time side effects. Moving imports, registrations, mutable singletons, or package exports can change startup order and observable state.

## Clean Code Misapplications

Do not add annotations everywhere merely to make the file look typed, or replace useful runtime checks with hints. Do not hide uncertain values behind `Any`, unchecked casts, or blanket ignores. A type checker is valuable when the repository already runs it and the boundary benefits from its model; it is not a runtime oracle.

Avoid replacing every loop with a comprehension, materializing every iterator, copying every mutable object, wrapping every resource in a new context manager, or converting sync code to async for stylistic consistency. Do not create protocols, abstract bases, service layers, or dependency injection when direct behavior and ownership are already clear.

## Behavior and Boundary Contracts

Preserve accepted runtime types, return shapes, mutation and aliasing, ordering, iterator consumption, exception types and causes, warning behavior, import side effects, sync or async calling conventions, cancellation, task ownership, and cleanup timing unless the task explicitly changes them.

At external input boundaries, distinguish static hints from actual parsing or validation. At exception boundaries, distinguish expected domain failure, dependency failure, cancellation, timeout, and programmer error. At resource boundaries, identify who opens, yields, closes, and may reuse the object.

## Repository-Native Gate Discovery

Use commands and configuration already present in CI, `pyproject.toml`, task runners, scripts, or contributor docs. The effective gates may include tests, lint, format checks, static typing, packaging, import checks, or supported-version matrices. Run the narrowest check that observes the changed risk, followed by every mandatory repository gate.

Do not install or select a formatter, linter, test runner, type checker, package manager, or framework on this profile's authority. A green static check does not prove runtime validation, mutation isolation, cancellation, cleanup, exception translation, or import behavior.

## When Another Option Fits Better

A mutable object can be intentionally shared when that ownership is explicit and tested. A generator fits streaming, large data, or lazy pipelines when single consumption and resource lifetime are part of the contract; a list fits when callers require a reusable snapshot.

Synchronous code can remain simpler when dependencies are synchronous and blocking is acceptable. Async fits an established asynchronous call chain with explicit task and cancellation ownership. Structural duck typing may be clearer than a new protocol in local code; a protocol fits a checked public boundary or multiple meaningful implementations.

## Common Agent Failure Modes

- Treating annotations as runtime validation or claiming `Any` makes a value safe.
- Fixing a mutable default while leaving shared nested aliasing unchanged.
- Consuming a generator for inspection and returning the exhausted iterator.
- Catching `Exception` around an async operation and turning cancellation into success or a domain error.
- Closing a caller-owned stream, session, client, or iterator during local cleanup.
- Translating an exception without `from`, or leaking a lower-layer error across a public boundary.
- Moving imports to satisfy style while changing registration order or triggering a circular import.
- Running one interpreter and reporting compatibility with every declared Python version.
- Inventing a framework, validation library, or typing policy that the repository does not use.

## Stop and Escalation Conditions

Stop when the supported Python version is unknown and the proposed syntax or library API may be incompatible. Escalate before changing a public annotation or runtime validation contract, mutation or aliasing behavior, iterator consumption, exception mapping, import-time registration, sync or async boundary, cancellation, task lifetime, or resource cleanup.

Also stop when tests require an unavailable service or interpreter, a generated or vendored file appears to be the real target, the resource owner cannot be identified, or a new tool or dependency would be required without authorization.

## Output Additions

For each Python Changed Module, report the applied profile, the Python version evidence or Unknown, and the repository's relevant tool configuration. Identify runtime validation, mutable default or aliasing, iterator or generator consumption, `asyncio` cancellation, context manager cleanup, exception boundary, and import-side-effect impacts when applicable. Name the exact gates and supported versions exercised, plus remaining gaps.

## Evidence Status

Current maturity is published in the generated [Runtime Profile Index](profile-selection.md#runtime-profile-index). Repository contract tests cover structure, selection, and required semantic topics. Versioned metadata records the v0.5.1 and v0.5.2 M2 pilots, including unfavorable outcomes; the latter tested the unchanged technical guidance from Skill v0.5.1. No M3 full run has been recorded. Pilot evidence does not establish general improvement across versions, runtimes, renderers, repositories, clients, or models.
