# Implementation ideas

Version-controlled handoffs for future repository work. Each document should
give a later AI or human enough context to inspect the code, resolve remaining
questions, implement the change, and verify the outcome.

These are proposals, not implemented features or authorization to execute them.
Start with [TEMPLATE.md](TEMPLATE.md), choose a descriptive kebab-case filename,
and add it to this index. Update existing ideas when planning continues.

| Idea | Status | Last reviewed | Goal |
| --- | --- | --- | --- |
| [Automatic catalog refresh](automatic-catalog-refresh.md) | proposed | 2026-09-15 | Refresh the model catalog after successful archive operations. |
| [Model storage capacity checks](model-storage-capacity-check.md) | proposed | 2026-09-15 | Estimate required disk space before writing model artifacts. |

Status meanings:

* `proposed`: an idea with recommendations or questions still to resolve.
* `ready`: enough decisions and acceptance criteria exist to implement when assigned.
* `implemented`: implementation and validation are complete; record the outcome.
* `superseded`: another linked plan replaces this one.

Keep status and review dates synchronized here and in each document. Retain
completed documents as context, with links to the resulting code or replacement
plan. Before implementing, check current source and instructions: plans can age.
Use portable paths and configuration names; keep private host details and secrets
outside the repository.
