# Design and Dependency Boundaries

Use architecture patterns to protect a demonstrated boundary, not to produce a pattern-shaped Diff. Repository behavior, ownership, and failure windows decide whether a boundary is valuable.

## Use This Reference When

Use this reference for abstractions, SOLID decisions, providers, components, concurrency, external effects, or architecture. Establish the current dependency direction, public contracts, next likely change, and operational failure window before adding a project, interface, mapper, Port, Adapter, or Gateway.

## Selection Rules

| Decision | Apply it when | Choose the alternative when | Checkable output |
| --- | --- | --- | --- |
| Simple Design | Behavior is correct, intent is visible, meaningful duplication is removed, and no further element protects a demonstrated change pressure. | Add structure only when a specific boundary, variant, or ownership concern remains exposed. | Behavior preserved, smallest Diff, and named protected boundary. |
| SRP and cohesion | Different actors, invariants, or reasons to change make a module's responsibilities compete. | Keep related work together when one workflow, invariant, and collaborator set change as one unit. | Actor and reason-to-change map with affected call paths. |
| OCP and extension point | A stable policy has demonstrated variants that need independent extension. | Keep a direct conditional when variants are hypothetical or the repository has one stable case. | Policy, variant evidence, extension contract, and fallback behavior. |
| LSP and ISP | A substitute must preserve observable contract and failure meaning, or consumers need different capabilities for different reasons. | Keep one interface when all current consumers need the same coherent capability. | Consumer list, supported operations, failure semantics, and substitute checks. |
| DIP and Dependency Rule | Stable policy must avoid owning volatile provider details, and the abstraction can be owned by the policy side. | Keep a direct dependency when the mechanism is local, stable, and does not leak into policy decisions. | Dependency path before and after, ownership, and volatility evidence. |
| Port, Adapter, Wrapper, or Gateway | Vendor types, provider failures, authentication, retries, or protocol details would otherwise spread through core behavior. | Use direct provider access at a local edge when the provider is already the boundary and no policy layer consumes its details. | Port contract, adapter behavior, provider failure map, and contract or exploratory test. |
| Concurrency and external effects | Reads, writes, commits, calls, acknowledgements, retries, and cancellation expose a real failure window. Choose idempotency for repeated delivery, Outbox for durable handoff after local commit, optimistic concurrency or lease for conflicting writers, and compensation for recoverable cross-system work. | Keep a local transaction or simple flow only when all effects share one atomic resource and the failure window is demonstrably absent. | Event/order map, idempotency key or conflict rule, recovery path, and validation evidence. |

Apply SOLID as change analysis, not as a score. Project count does not prove the Dependency Rule, and added layers have navigation, synchronization, test, and operational cost.

## When Another Option Fits Better

- Use a direct dependency when provider detail is contained at an existing edge and stable policy does not need to know it. Introduce a Port and Adapter when provider types or failure semantics would otherwise cross into policy code or require a second provider.
- Keep one component or module when its consumers, invariants, and lifecycle change together. Split it when separate actors need incompatible change cadence or one boundary must prevent an implementation detail from leaking.
- Use idempotency when the same command or message can arrive more than once. Use an Outbox when a durable local commit must lead to later delivery; use compensation only when a completed remote effect has a known, authorized reversal.
- Keep a simple direct flow when all effects can commit atomically in one resource. Add concurrency control or recovery logic when the observed order of operations leaves a write conflict, duplicate effect, lost acknowledgement, or partial completion window.

## Common Misjudgments

The following are source-bounded experiment records. Each Observation ID reuses an existing public evidence coordinate; it is not a newly generated Failure ID. They are review prompts, not a ranking of architecture patterns.

### Observation ID: `day-22/architecture-boundary#current-boundary`

Source: [Day 22 architecture boundary at commit e860838](https://github.com/eric861129/AI-CleanCode-API-Demo/blob/e860838ee9a353a55ae6ff0eb661220c49dbb16a/docs/evidence/day-22/architecture-boundary/experiment-results.md)

Supports: With only a replaceable Provider requirement, the experiment kept the existing Consumer Port and Composition Root and made no Production Diff. It did not add an independent package, team, process, or deployment boundary without the pressure that would require one.

Misjudgment to avoid: Add a Plugin, Package, Process, or extra project solely because a Provider exists, before identifying the contract, ownership, versioning, or operational boundary it must protect.

### Observation ID: `day-22/architecture-boundary#deferred-decision-pressure`

Source: [Day 22 architecture boundary at commit e860838](https://github.com/eric861129/AI-CleanCode-API-Demo/blob/e860838ee9a353a55ae6ff0eb661220c49dbb16a/docs/evidence/day-22/architecture-boundary/experiment-results.md)

Supports: When a new fact introduced an independently versioned Provider owned by another team, the experiment then added Contract and Provider Class Libraries. The record explicitly limits the result: it does not establish that deferring a boundary is always cheaper.

Misjudgment to avoid: Convert one boundary-timing result into a universal rule. Re-evaluate the direct dependency when a consumer contract, team, version, deployment, or failure-isolation requirement changes.

### Observation ID: `day-08/function-heuristics#cqs-exception`

Source: [Day 8 function heuristics at commit e860838](https://github.com/eric861129/AI-CleanCode-API-Demo/blob/e860838ee9a353a55ae6ff0eb661220c49dbb16a/docs/evidence/day-08/function-heuristics.md)

Supports: The accepted CQS candidate preserved explicit exceptions where a strict split would have changed expected failure semantics or hidden a meaningful result. The source presents CQS after observable behavior and side-effect order, not as a fixed priority.

Misjudgment to avoid: Apply an interface, split, or named Pattern before mapping the current failure meaning and side-effect order it must preserve.

## Stop Conditions

Stop and escalate when the boundary, consumer contract, provider behavior, concurrency window, or recovery action cannot be established from repository facts; when the design would change an unauthorized public contract, schema, provider, dependency, secret, CI, or deployment; or when a required failure path cannot be validated safely.

Evidence can support a bounded design proposal. It does not grant authority to introduce infrastructure, migrate data, call an external provider, or deploy a new dependency.
