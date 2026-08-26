# Code Readability Decisions

Use this reference for names, comments, formatting, functions, models, and classes.

## Names and Comments

- Choose names from repository domain language and the responsibility at the current abstraction level.
- Preserve established casing and serialization conventions; format consistency and semantic clarity serve different purposes.
- Prefer stable intent over temporary implementation detail.
- Write comments for contracts, reasons, hazards, units, or constraints that code cannot express clearly. A comment that disagrees with code is a defect and must be resolved from evidence.

## Functions

- Keep one abstraction level in the main flow when it makes the operation easier to scan.
- Use Stepdown when readers or Agents benefit from seeing policy before mechanism. Keep related detail nearby when jumping would hide a small, cohesive calculation.
- Evaluate parameters, Command-Query Separation, exception meaning, duplication, and side effects together. Improving one may increase the cost of another.
- Extract duplication only after identifying the shared reason to change. Similar syntax with different business meaning may need to remain separate.

## Models and Classes

- Measure size by responsibilities, actors, invariants, and reasons to change rather than line count alone.
- Keep DTO, persistence, and domain roles distinct when the repository has a real boundary to protect. Avoid extra models when no second use case or change pressure justifies mapping cost.
- Prefer cohesion that lowers the next likely change cost. In an AI-heavy codebase, a direct structure may be better when additional indirection only increases navigation and context loading.

## Selection Questions

1. What repository evidence gives this name, extraction, or class boundary meaning?
2. Which next likely change becomes local?
3. What navigation, mapping, or synchronization cost is added?
4. Under which different project condition would the rejected option become better?
