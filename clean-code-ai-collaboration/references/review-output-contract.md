# Review Output Contract

## Standard Output Contract

Use this contract for a Standard Path. Report the following headings in order. The first five are required; include Stop or Human Decision only when a stop, unresolved authority, or Owner decision affects the result. Omit non-material fields instead of emitting empty placeholders, but never omit a known risk or required investigation.

### Outcome and Status

State the outcome first, using `planned`, `implemented`, `verified-within-scope`, `blocked`, or `not-investigated`. Name the behavior and Diff boundary covered by that status.

### Decision Basis

List only Repository facts that changed the decision. Add assumptions or unknowns only when they affect the conclusion, validation, authorization, or safe boundary.

### Selected Approach

State the selected approach and why it fits this Repository. When another viable approach exists, state the observable condition that would make it fit better.

### Development and Validation Strategy

State `Requested Development Rhythm`, `Development Rhythm Source`, `Effective Development Rhythm`, `Requested Validation Profile`, `Validation Profile Source`, and `Effective Validation Profile`. The source identifies where each requested value came from, not how the effective value was inferred; an explicit `auto` therefore remains sourced from the User prompt. Add `Feasibility or Escalation` when a requested rhythm or profile lacks an Oracle, feedback speed, isolation, tool, or authorization prerequisite. Do not imply that an automatically selected or substituted strategy was explicitly requested.

### Behavior, Diff, and Validation

State behavior that must not change, expected and actual Diff boundaries, executed validation, evidence limitations, and remaining blind spots.

### Stop or Human Decision

When applicable, state the stop condition, responsible Owner, external state left unchanged, and exact decision or evidence needed to resume.

## Full Audit Output Contract

Use this contract on the Full Audit Path. Return every heading below, including headings with no applicable item. Link conclusions with stable `F`, `A`, `U`, `O`, and `E` identifiers so a reviewer can trace evidence, uncertainty, options, and validation without inferring missing facts.

For every output heading with no item, write `None; Sources checked: ...` only after named sources establish that the section has no applicable item. Write `Not investigated` when the relevant sources or decision were not investigated. This rule applies to every output heading; do not use a bare `None` or let an empty section imply that investigation happened.

### Outcome and Status

State the outcome first and choose exactly one status: `planned`, `implemented`, `verified-within-scope`, `blocked`, or `not-investigated`. State the behavior and Diff boundary covered by that status. Do not use `done`, and do not imply that `verified-within-scope` covers behavior, environments, or authorization outside the recorded evidence.

### Applicable References

List only the decision references that changed this review, such as legibility, readability, testing, design, collaboration, or repository context. For each, state the decision it informed.

### Repository Facts Used

Record each `F1`, `F2`, and later fact with its active revision, path and line, command, endpoint, artifact, or other source. State what the fact establishes and its freshness or environment limitation. Repository facts are evidence for a decision, not authorization to broaden the change.

### Assumptions

Record each `A1`, its decision impact, why repository facts did not resolve it, and how it can be validated. An assumption must not be presented as a fact or used to claim behavior outside its stated condition.

### Unknowns

Record each `U1`, its criticality, responsible Owner, next action, and safe boundary while unresolved. Classify an unknown as critical when a different answer could change behavior, data, security, dependency, deployment, or a human decision.

### Options Considered

Record each `O1` with its fit conditions, protected behavior or boundary, cost, risk, checkable output, and rejection reason. Do not rank patterns generally; compare only options supported by the repository context.

### Selected Option and Reason

State the selected option and link the relevant `F`, `A`, `U`, `O`, and `E` identifiers. Explain why it fits the current repository facts, authorization boundary, and expected behavior rather than presenting it as a universal winner.

### Development and Validation Strategy

Record `Requested Development Rhythm`, `Development Rhythm Source`, `Effective Development Rhythm`, `Requested Validation Profile`, `Validation Profile Source`, and `Effective Validation Profile`. Name the Prompt, Repository Policy, or default that supplied each requested value. The source identifies where the requested value came from, not how the effective value was inferred; an explicit `auto` remains sourced from the User prompt. Record `Feasibility or Escalation` with linked facts, unknowns, and authorization when the effective strategy cannot match an explicit request. Never hide a substitution inside the implementation summary.

### When Other Options Fit Better

For every rejected viable option, state the condition that would make it fit better and the evidence required to reverse the selection. Keep this separate from the current selection so future reviewers can distinguish a contextual choice from a rule.

### Behavior That Must Not Change

List observable success and failure behavior, public contracts, data rules, side-effect order, retry or cancellation behavior, and compatibility constraints that the change must preserve. Link each claim to its `F`, `A`, or `U` identifier.

### Expected Diff Boundary

State the intended paths, modules, contracts, data, dependencies, configuration, and external state that are in scope. State explicit exclusions and the authorization required before crossing any excluded boundary.

### Actual Diff Boundary and Deviations

Record the actual changed paths and material generated or external artifacts. Compare them with the Expected Diff Boundary, explain every deviation, and record whether it was authorized, reverted, or still blocked.

### Validation Plan

State the behavior to validate, independent Oracle, command or repeatable procedure, revision, environment, inputs, expected result, and owner. Mark planned validation as planned until it produces an `E` record.

### Evidence Produced

Record each `E1`, `E2`, and later evidence item with command or artifact, revision, environment, exit code, observed result, and limitation. Separate executed evidence from planned work and preserve the actual output needed to repeat the check.

### Validation Blind Spots

List behavior, failure windows, environments, data states, consumers, side effects, or authorization boundaries that available evidence did not exercise. A passing result must not erase an untested blind spot.

### Stop or Escalation Conditions

State the exact condition that requires a stop, the Owner or authority needed, the external state left unchanged, and the evidence needed to resume. Evidence does not grant authority for a public contract, dependency, data, provider, CI, deployment, or destructive change.

### Human Decisions Required

List every unresolved scope, risk, compatibility, schedule, rollout, external commitment, or authorization decision that requires a responsible human.
