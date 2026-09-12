# React Framework Profile

## Use This Profile When

Use this profile only when the nearest package declares the `react` dependency and the Changed Module actually involves React behavior through relevant source, imports, repository policy, or a manifest change. `.tsx`, JSX syntax, `react-dom`, or `react-native` alone is not a sufficient React candidate.

This profile is renderer-neutral by default. Apply DOM-specific input, event, accessibility, and browser-testing guidance only when `react-dom` is present. With `react-native`, use the common component, Hooks, state, Effect, and lifecycle rules; platform APIs are out of scope for v0.5.0.

## Repository Facts to Inspect

Inspect the nearest `package.json` and lockfile for the React version and renderer. Identify `react-dom`, `react-native`, or another renderer; do not infer the platform from file extensions. Find Strict Mode configuration, root creation, routing and data libraries, state ownership, error boundaries, test library, test environment, compiler or transform configuration, and the project's actual build and typecheck gates.

Read the affected component tree, custom Hooks, Effect setup and cleanup, context providers, state transitions, asynchronous work, keys, loading and error states, and neighboring behavior tests. Confirm whether the Changed Module is React code rather than a non-React tool that happens to live in the same package.

## Version-Sensitive Facts

React APIs, renderer integration, development checks, concurrent behavior, and test utilities vary by version and setup. Strict Mode can intentionally repeat selected development-only work to expose unsafe effects; that observation is not proof of identical production execution. A dependency range does not prove the installed version without lock or install evidence.

When the React version, renderer, root mode, or test environment is Unknown, preserve APIs and lifecycle patterns already used in the nearest module and report the uncertainty. Do not assume the newest Hooks, rendering features, compiler behavior, or server/client boundary.

## Language or Framework Semantic Risks

- Hooks must be called in a stable order from React functions or valid custom Hooks. Moving a Hook behind a branch, early return, loop, callback, or exception path can associate state with the wrong call.
- A stale closure can retain props, state, or callbacks from an earlier render. Effect dependencies must describe the values used, but mechanically adding dependencies can create loops or change request frequency. Fix ownership and synchronization intent before editing the array.
- Effect cleanup must undo the setup owned by that Effect: subscriptions, timers, observers, or in-flight work where cancellation exists. Cleanup timing includes dependency changes and unmount; it must not dispose shared or caller-owned resources.
- State identity determines whether React can observe a change. Mutating an existing object and reusing its reference can hide updates; copying everything can also break identity-sensitive memoization or controlled integrations. Preserve the intended owner and update boundary.
- Derived state can drift from its source when duplicated and synchronized through Effects. Compute it during render when it is purely derived and affordable; store it only when it represents an independent user or workflow decision.
- A stable key represents item identity among siblings. Index or random keys can preserve the wrong state or remount work when order changes. Changing a key intentionally resets a subtree and is therefore a behavior change.
- Async results can arrive after newer input, cancellation, or unmount. Prevent stale success, error, or loading transitions from overwriting the current request state. Do not assume rendering occurs once or that render-phase code may cause side effects.
- Controlled and uncontrolled input contracts, DOM events, focus, and browser accessibility are `react-dom` concerns. Do not project DOM APIs onto another renderer.

## Clean Code Misapplications

Do not extract every expression into a custom Hook, wrap every callback in memoization, copy props into state, or add an Effect to synchronize values that can be derived during render. Fewer lines or fewer linter warnings do not justify changing lifecycle behavior.

Avoid broad context providers, generic component abstractions, and state libraries before ownership or reuse is demonstrated. Do not suppress Hook rules, add unstable objects to dependencies without examining identity, or use a changing key to hide a reset defect.

## Behavior and Boundary Contracts

Preserve rendered states, component and Hook inputs, state ownership, identity, key-based preservation or reset, Effect setup and cleanup, subscription counts, request ordering, loading and error transitions, focus and controlled input behavior where applicable, and renderer boundaries unless the task explicitly changes them.

Render must remain free of externally visible side effects. Every asynchronous path needs an owner for completion, stale-result prevention, and available cancellation. Error handling must preserve whether failures are rendered, thrown to a boundary, returned to a caller, logged, or retried.

## Repository-Native Gate Discovery

Use the repository's existing lint, typecheck, unit, component, accessibility, integration, visual, and end-to-end commands. Match the configured renderer and test environment; a DOM test cannot validate a native platform interaction, and a shallow assertion may not observe Effect cleanup or asynchronous races.

Do not install a renderer, state library, test library, linter plugin, or browser on this profile's authority. Run the smallest test that observes the lifecycle or user-visible behavior, then every mandatory repository gate. Report manual visual, device, or accessibility checks that remain unperformed.

## When Another Option Fits Better

Local state fits state owned by one subtree; lifting, context, an external store, or server state fits only when ownership and synchronization require it. Render-time derivation fits pure derived values; state or an Effect fits interaction with an external system or an independent persisted decision.

An inline callback can be clearer when identity is not part of a child or dependency contract. Memoization fits measured or contractually significant identity and computation. Controlled input fits when React owns the current value; uncontrolled input can fit native or third-party ownership when the surrounding contract supports it.

## Common Agent Failure Modes

- Selecting React from `.tsx`, `react-dom`, or a package name without the `react` dependency and relevant Changed Module.
- Calling Hooks conditionally or converting an ordinary function into a custom Hook without a lifecycle need.
- Fixing a stale closure by adding dependencies that create repeated requests or updates.
- Omitting Effect cleanup, or cleaning up a resource owned by another scope.
- Mutating state in place, or cloning so broadly that stable identity contracts break.
- Using index, timestamp, or random keys and silently resetting component state.
- Letting an old request clear loading or replace the latest result and error.
- Assuming development Strict Mode repetitions are duplicate production events.
- Applying DOM event, selector, or accessibility advice to a non-DOM renderer.

## Stop and Escalation Conditions

Stop when the React version, renderer, component ownership, Effect purpose, state owner, or async result policy cannot be established. Escalate before changing a public component or Hook contract, key or state identity, controlled input ownership, Effect frequency or cleanup, request cancellation, stale-result handling, loading or error behavior, or renderer-specific interaction.

Also stop when the relevant behavior requires an unavailable browser or device, a platform API outside this profile, a new runtime dependency, or a manual visual or accessibility decision that automated gates cannot establish.

## Output Additions

For each React Changed Module, report the applied framework profile, React version, renderer, Strict Mode, and test environment or mark them Unknown. Identify Hook order, stale closure, Effect dependency and Effect cleanup, state identity, derived state, key behavior, controlled inputs, async race, loading, and error impacts when applicable. Separate renderer-neutral evidence from `react-dom` or native-specific validation.

## Evidence Status

Current maturity is published in the generated [Runtime Profile Index](profile-selection.md#runtime-profile-index). Repository contract tests cover structure, selection, and required semantic topics. Versioned metadata records the v0.5.1 and v0.5.2 M2 pilots, including unfavorable outcomes; the latter tested the unchanged technical guidance from Skill v0.5.1. No M3 full run has been recorded. Pilot evidence does not establish general improvement across versions, runtimes, renderers, repositories, clients, or models.
