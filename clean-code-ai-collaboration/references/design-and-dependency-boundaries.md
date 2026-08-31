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

These are failure modes observed in Agent-assisted changes. They are review prompts, not a ranking of architecture patterns.

- Adding an interface, project, or mapper because the pattern appears clean without identifying the owner, volatile mechanism, or protected policy boundary.
- Treating package or project count as evidence of Dependency Rule compliance while policy still imports provider detail.
- Splitting interfaces without checking whether callers rely on combined operation ordering or shared failure meaning.
- Treating database success as proof that an external notification, queue publish, or remote call also completed.
- Choosing Outbox, idempotency, lease, or compensation by name without mapping the actual read, write, commit, retry, and acknowledgement sequence.

## Stop Conditions

Stop and escalate when the boundary, consumer contract, provider behavior, concurrency window, or recovery action cannot be established from repository facts; when the design would change an unauthorized public contract, schema, provider, dependency, secret, CI, or deployment; or when a required failure path cannot be validated safely.

Evidence can support a bounded design proposal. It does not grant authority to introduce infrastructure, migrate data, call an external provider, or deploy a new dependency.
