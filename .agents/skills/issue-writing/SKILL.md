---
name: issue-writing
description: Drafts a GitHub issue or epic without putting the design in the issue. Use when a human asks to write, draft, generate, or create an issue, epic, or child issue.
---

# Issue writing

Write the outcome, the boundary, and the checks. Leave the design for the specification. Do this even when the prompt supplies formulas, grains, column lists, file layouts, or implementation steps. Do not copy that material into the issue. After the draft, list anything withheld under `Held for the specification`, outside the issue body.

Read the template and replace its guidance. Do not add sections.

- One task uses `agent-platform/templates/issue.md`.
- A group of related tasks uses `agent-platform/templates/parent_issue.md` for the epic and `issue.md` for each child. A single task is not an epic.
- A child id is `DATA-<parent>-001`, then `DATA-<parent>-002`. Do not use `000` for the first child.
- Leave **Agent:** blank unless the human names the owner.
- **Depends On:** uses a full id, such as `DATA-007-001`.

## What stays out of the issue

- Grains, formulas, column lists, and file layouts.
- Which field feeds which measure, and how a number is calculated.
- Execution steps, reading order, and instructions to write the specification.
- An acceptance criterion that restates the design. A criterion is a check someone can fail.
- A parent that specifies a child. The parent lists one outcome per child.

## What may stay

- One outcome.
- What the result must include, and what it must not change.
- One locked business rule, as a single sentence, and only when the agent must not invent it. Delete that section when there is no such rule. A formula is not a locked decision.

## Creating the issue

Print the draft. Do not open a GitHub issue unless the human asks for that. When asked, create the issue with the drafted body. Do not set a `status:` label, write `specs/DATA-*.md`, or implement the task.
