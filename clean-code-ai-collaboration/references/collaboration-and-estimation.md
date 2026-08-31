# Collaboration and Estimation

Use explicit ownership, contracts, and evidence to coordinate people and Agents. Execution observations can inform a plan, but they do not create a delivery commitment or expand authority.

## Use This Reference When

Use this reference for team boundaries, multi-Agent execution, handoffs, estimates, integration plans, or external commitments. Establish who owns each behavior and file boundary, which contract is shared, which revision is current, and who validates the integrated result before parallel work begins.

## Selection Rules

| Decision | Apply it when | Choose the alternative when | Checkable output |
| --- | --- | --- | --- |
| Ownership | More than one contributor can change related behavior or files. Assign an owner by responsibility and file boundary. | Use one owner for a local, reversible change with no shared contract or integration point. | Owner-to-responsibility and owner-to-file map. |
| Shared contract | Independent work meets at an API, event, schema, component, or review boundary. Define inputs, outputs, failure meaning, compatibility, and validation owner. | Use a short local decision record when no other contributor consumes the change. | Contract revision, consumers, compatibility claim, and test or review command. |
| Integration order | Work has dependencies or a shared seam. Integrate producers, contracts, consumers, and validation in an explicit order. | Work in parallel only when file ownership and behavior boundaries do not overlap and integration has a named checkpoint. | Dependency order, current revision, and integration result. |
| Handoff | Another person or Agent must continue, review, or merge the work. | Keep the update short for a contained task with one owner and no unresolved decision. | Revision, Diff boundary, decisions, assumptions, unknowns, commands, results, and remaining risks. |
| Small cycle | A change can be implemented and validated in a contained vertical slice. | Pause or narrow the slice when validation needs an unavailable environment, another owner, or an unapproved boundary. | Slice behavior, expected Diff, validation output, and next integration point. |
| Estimate range and confidence | Unknowns can materially affect behavior, data, integration, validation, deployment, or recovery. Use optimistic, most-likely, and pessimistic cases with evidence and confidence. | Use a single bounded effort only when scope, dependency state, validation path, and owner availability are already established. | Range, assumptions, confidence, evidence that narrows it, and excluded work. |
| Human commitment | Scope, risk, schedule, staffing, external promise, or rollout decision needs an accountable owner. | An Agent may make a local reversible implementation choice within explicit authority. | Named responsible human, decision requested, deadline if supplied, and unchanged external state until approved. |

Token usage, tool calls, generated lines, and elapsed Agent time are execution observations. They are not business estimates by themselves. Include human review, environment access, integration, rollout, and recovery work in any delivery range.

## When Another Option Fits Better

- Use a single owner and short status update for a local reversible change with no shared contract. Use explicit file ownership and a handoff contract when multiple contributors can edit the same behavior or need to merge their results.
- Work sequentially when a producer, contract, migration, or shared component must settle first. Work in parallel only when overlap has been checked, tasks own disjoint boundaries, and an integration checkpoint has an owner.
- Use a narrow estimate range when current revision, acceptance behavior, dependencies, validation, and owner availability are evidenced. Use a wider range or stop when any of those inputs can change the delivery path.
- Let the responsible human commit scope, risk, schedule, and external communication. Let an Agent propose options, evidence, and a bounded reversible implementation inside granted authority.

## Common Misjudgments

The following are source-bounded experiment records. Each Observation ID reuses an existing public evidence coordinate; it is not a newly generated Failure ID. They are review prompts, not a ranking of collaboration methods.

### Observation ID: `day-27/small-cycles-improvement#cycle-choice`

Source: [Day 27 small-cycles improvement at commit e860838](https://github.com/eric861129/AI-CleanCode-API-Demo/blob/e860838ee9a353a55ae6ff0eb661220c49dbb16a/docs/evidence/day-27/small-cycles-improvement/experiment-results.md)

Supports: The one-shot batch passed its first complete Gate, so the experiment does not treat a batch as inherently unsafe. It accepted small cycles for the specific high-risk combination of Provider effects, persistence state, failure paths, and gradual enablement because the checkpoints narrowed investigation and rollback scope.

Misjudgment to avoid: Treat the number of commits, Agents, or cycles as a universal quality signal. Choose sequential or parallel integration from ownership overlap, behavior risk, validation seams, and rollback needs.

### Observation ID: `day-29/honest-estimation#independent-review`

Source: [Day 29 honest estimation at commit e860838](https://github.com/eric861129/AI-CleanCode-API-Demo/blob/e860838ee9a353a55ae6ff0eb661220c49dbb16a/docs/evidence/day-29/honest-estimation/experiment-results.md)

Supports: Three identical-session inputs produced 156, 84, and 48-hour single-point estimates. The independent review records that Token and execution time describe session activity, not delivery speed, and that a User-selected exploration budget is a decision rather than a calibrated prediction.

Misjudgment to avoid: Convert generated lines, Token use, Agent elapsed time, or one point estimate into a delivery commitment without evidence for scope, access, integration, validation, rollout, and human decisions.

## Stop Conditions

Stop and escalate when ownership, integration order, contract compatibility, current revision, validation owner, or required human commitment is unknown and a different answer could change behavior, data, security, dependency, deployment, or a human decision. Stop before an unauthorized external promise, data mutation, provider call, CI change, deployment, or destructive action.

Record the decision, responsible Owner, evidence, and next action. Evidence supports coordination and review; it does not create authority or a schedule commitment.
