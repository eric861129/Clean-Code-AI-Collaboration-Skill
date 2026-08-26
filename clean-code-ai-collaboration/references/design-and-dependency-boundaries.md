# Design and Dependency Boundaries

Use this reference for abstractions, SOLID decisions, providers, components, concurrency, and architecture.

## Simple Design before Structure

Keep behavior correct, make intent visible, remove meaningful duplication, and add the fewest elements needed for the current change. A folder or interface is useful only when it protects a real boundary or change pressure.

## SOLID as Change Analysis

- SRP: identify actors and reasons to change.
- OCP: locate the stable policy and the extension point demanded by likely variants.
- LSP: verify substitutes preserve observable contracts, failure meaning, and supported operations.
- ISP: give consumers only the capabilities they need; split interfaces when consumers change for different reasons.
- DIP: keep policy independent from volatile mechanisms and choose abstractions owned by the policy side.

Apply these as questions, not scores. Extra interfaces, projects, mappers, or wrappers may increase cost without improving substitutability or change locality.

## Boundary Choices

- Isolate third-party APIs through a Port, Adapter, Wrapper, or Gateway when vendor types or failure semantics would otherwise spread through the core.
- Let repository context decide whether UI, persistence, messaging, and external services need separate boundaries.
- Keep dependency direction pointing toward stable policy. Project count does not prove the Dependency Rule.
- Use exploratory or contract tests to learn uncertain provider behavior before embedding it in business code.

## Concurrency and Failure Windows

Map the order of reads, writes, locks or leases, commits, external calls, acknowledgements, retries, and cancellation. Database success cannot undo an external side effect. Choose idempotency, outbox, lease, optimistic concurrency, or compensation according to the actual failure window.

## Compare Options

For each viable design, state the protected boundary, next likely change, added navigation or synchronization cost, operational risk, and the condition that would make it preferable. Stop before an unapproved public contract, schema, provider, dependency, or deployment change.
