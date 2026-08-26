# Collaboration and Estimation

Use this reference for team boundaries, multi-agent execution, handoffs, estimates, and commitments.

## Team and Agent Collaboration

- Assign ownership by responsibility and files before parallel work begins.
- Define shared contracts, integration order, validation owner, and stop conditions.
- Preserve other contributors' changes and surface overlap before editing the same boundary.
- Make handoffs inspectable: revision, Diff, decisions, assumptions, remaining risks, commands, and results.
- Integrate in small cycles so a failed branch can be understood or discarded without losing unrelated work.

## Estimation

Break work into behavior, data, integration, validation, deployment, and unknowns. Use a range or optimistic, most-likely, and pessimistic cases when uncertainty matters. State confidence and the evidence that would narrow the range.

Token usage, tool calls, generated lines, and elapsed Agent time are execution observations, not business estimates by themselves. Include human review, environment access, integration, rollout, and recovery work.

## Human Responsibility

The Agent may propose a range, identify uncertainty, and compare delivery options. The responsible human accepts scope, risk, schedule, and external commitments. Escalate when ownership is missing or the requested promise exceeds the available evidence.
