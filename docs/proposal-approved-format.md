# `proposal-approved.md` Format

> **Status**: canonical (proposal-approval-pipeline, replaces the legacy JSON-only flow).

This document is the single source of truth for how the
`proposal-approved.md` file is structured, read, and written by the
rdd-workflow skills (`guide-design`, `guide-plan`, `propose`, `archive`).

---

## Container format: Markdown with two table sections

The file **MUST** contain two Markdown table sections, each preceded by
a `## ` header:

1. `## 已批准提案` - proposals approved by `guide-design` (Path A: approval also writes complete `openspec/changes/<name>/proposal.md`); `guide-plan` consumes this index to fill remaining artifacts (`design.md`, `tasks.md`, specs/).
2. `## 已实施` - proposals whose corresponding OpenSpec changes have been archived.

### Example file

```markdown
# 已批准提案索引

> guide-design 批准的提案索引。guide-plan intake 从此文件读取链接，按 `.rddf/state/.design-handoff.json` v2 的 `changes_pre_created` 数组跳过已落盘的 change（Path A）。

## 已批准提案

| 提案 | 优先级 | 批准时间 | 批准者 |
|------|--------|----------|--------|
| [fix-silent-exception](.rddf/improvements/fix-silent-exception.md) | P0 | 2026-07-23 | guide-design |
| [add-config-validation](.rddf/improvements/add-config-validation.md) | P0 | 2026-07-23 | guide-arch |

## 已实施

| 提案 | 优先级 | 完成时间 |
|------|--------|----------|
| [remove-ci-redundant-bats](.rddf/improvements/remove-ci-redundant-bats.md) | P1 | 2026-07-20 |
```

### Section: `## 已批准提案`

Table columns:

| Column     | Format                              | Description                                                |
|------------|-------------------------------------|------------------------------------------------------------|
| 提案       | `[name](.rddf/improvements/name.md)`      | Markdown link to the improvement file. The link text is the proposal name (kebab-case). |
| 优先级     | `P0` / `P1` / `P2`                 | Priority level, copied from the improvement file metadata. |
| 批准时间   | `YYYY-MM-DD`                        | UTC date when `guide-design` approved the proposal.        |
| 批准者     | Free-form string (e.g. `guide-design`) | Who/what approved the proposal.                            |

### Section: `## 已实施`

Table columns:

| Column     | Format                              | Description                                                |
|------------|-------------------------------------|------------------------------------------------------------|
| 提案       | `[name](.rddf/improvements/name.md)`      | Same link format as the approved section.                  |
| 优先级     | `P0` / `P1` / `P2`                 | Priority level (preserved from approved section).          |
| 完成时间   | `YYYY-MM-DD`                        | UTC date when the change was archived.                     |
| 状态       | `已实施` (literal)                  | Fixed completion status. Originally 3 columns, expanded to 4 in v2.2 to align with the `## 已批准提案` schema (consistent 4-col layout) and to silence `rdd-doctor` `proposal-table` false positives. |

---

## Lifecycle

### Approval flow (`guide-design` Phase 3 — Path A)

1. `guide-design` reviews each file in `.rddf/improvements/` directory.
2. For each approved proposal, `approve_proposal.sh`:
   - Appends a row to the `## 已批准提案` table via `append_approved()`.
   - **Directly creates** `openspec/changes/<name>/{proposal.md, .openspec.yaml, roadmap-meta.yaml}` with the complete 5-section content.
   - Adds the change name to `.rddf/state/.design-handoff.json` v2's `changes_pre_created` array.
3. Rejected proposals are simply not added - they remain in `.rddf/improvements/`
   but never appear in `proposal-approved.md`.

### Consumption flow (`guide-plan` propose)

1. `guide-plan` reads `proposal-approved.md` via `list_approved()` or
   `read_improvement_entries()`.
2. For each approved entry, it follows the link to `.rddf/improvements/<name>.md`
   to read the full 5-section content.
3. It creates an OpenSpec change using that content.

### Completion flow (`archive`)

1. After a change is archived, `mark_approved_completed()` (in
   `skills/_lib/state.sh`) moves the row from `## 已批准提案` to
   `## 已实施`.
2. The priority is preserved; the timestamp column is updated to the
   archive date.

---

## Relationship to `.rddf/improvements/` directory

The `.rddf/improvements/` directory contains one `.md` file per proposal with
the full 5-section content:

```
.rddf/improvements/
├── fix-silent-exception.md      # Full proposal content
├── add-config-validation.md
├── ...
```

Each improvement file has this structure:

```markdown
# <name>

**优先级**: <priority> | **来源**: <source>
**阶段**: <phase> | **分类**: <category>
**类型**: <type>

## 架构依据
...

## 范围
...

## 关键场景
...

## 技术约束
...

## 验收标准
...
```

The `proposal-approved.md` file **only** contains links to these files -
it never duplicates the proposal content. This keeps the index file small
and ensures a single source of truth for each proposal's details.

---

## Relationship to `proposal-suggestions.md`

| File                        | Role                                      | Format              |
|-----------------------------|-------------------------------------------|---------------------|
| `proposal-suggestions.md`   | Index of ALL proposals (pre-approval)     | Markdown table      |
| `proposal-approved.md`      | Index of APPROVED proposals (post-arch)   | Markdown table      |
| `.rddf/improvements/*.md`         | Full proposal content (one file each)     | Structured Markdown |

`proposal-suggestions.md` lists every proposal for `guide-design` to review.
`proposal-approved.md` lists only those that have been approved and is the
input for `guide-plan` intake (combined with `.design-handoff.json`
`changes_pre_created` array to identify pre-created changes that need fill only).

---

## API reference

### Shell (`skills/_lib/state.sh`)

| Function                          | Description                                                |
|-----------------------------------|------------------------------------------------------------|
| `list_improvements <project_root>` | List all improvement files. Returns `name\|priority\|source` lines. |
| `list_approved <project_root>`    | Parse approved table. Returns `name\|priority\|time\|approver` lines. |
| `append_approved <root> <name> <priority>` | Add a row to the approved table. Idempotent. |
| `mark_approved_completed <root> <name>` | Move entry from approved to completed table. |

### Python (`skills/_lib/state_reader.py`)

| Function                                  | Returns                          | Description                          |
|-------------------------------------------|----------------------------------|--------------------------------------|
| `read_improvement_entries(project_root)`  | `list[dict]`                    | Read all improvement files with parsed metadata (name, priority, source, phase, category, type). |

---

## See also

- `docs/proposal-suggestions-format.md` - format for the pending proposals index
- `skills/_lib/state.sh` - shell helpers for reading/writing the index files
- `skills/_lib/state_reader.py` - Python read-only data layer
- `.rddf/improvements/proposal-approval-pipeline.md` - the proposal that designed this format
