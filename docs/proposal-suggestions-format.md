# `proposal-suggestions.md` Format

> **Status**: canonical (proposal-approval-pipeline, replaced the legacy JSON-only format).
> 
> **Updated**: 2026-07-24 — Changed from JSON array to Markdown table (index-only).

This document is the single source of truth for how the
`proposal-suggestions.md` file is structured, read, and written by the
rdd-workflow skills (`guide-arch`, `guide-plan`, `propose`, `dashboard`).

---

## Container format: Markdown table (index only)

The file **MUST** contain a Markdown table that **only stores links** to
individual proposal files in the `.rddf/improvements/` directory. It never contains
the full proposal content — that lives in `.rddf/improvements/<name>.md`.

### Example file

```markdown
# 提案池（待架构讨论）

> arch 阶段输入。guide-arch Phase 5.5 逐个审查，批准后添加到 `proposal-approved.md`。

| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
|------|--------|------|----------|------|
| [fix-silent-exception](.rddf/.rddf/improvements/fix-silent-exception.md) | P0 | Oracle 审查 2026-07-19 | 2026-07-19 | 待讨论 |
| [add-config-validation](.rddf/.rddf/improvements/add-config-validation.md) | P0 | Oracle 审查 2026-07-19 | 2026-07-19 | 待讨论 |
```

### Table columns

| Column     | Format                              | Description                                                |
|------------|-------------------------------------|------------------------------------------------------------|
| 提案       | `[name](.rddf/.rddf/improvements/name.md)`      | Markdown link to the improvement file. The link text is the proposal name (kebab-case). |
| 优先级     | `P0` / `P1` / `P2`                 | Priority level, copied from the improvement file metadata. |
| 来源       | Free-form string                    | Where the proposal came from (e.g. `Oracle 审查`, `复盘改进`). |
| 添加时间   | `YYYY-MM-DD`                        | UTC date when the proposal was added to the pool.          |
| 状态       | `待讨论` / `已批准` / `已拒绝` / `延迟` | Proposal lifecycle status, read from the improvement file's `**状态**` metadata line. Defaults to `待讨论` if absent. |

---

## Relationship to `.rddf/improvements/` directory

The `.rddf/improvements/` directory contains one `.md` file per proposal with
the full 5-section content:

```
.rddf/improvements/
├── fix-silent-exception.md      # Full proposal content
├── add-config-validation.md
└── ...
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

The `proposal-suggestions.md` file **only** contains links to these files —
it never duplicates the proposal content. This keeps the index file small
and ensures a single source of truth for each proposal's details.

---

## Lifecycle

### 1. Proposal creation

Proposals are created as individual `.rddf/improvements/<name>.md` files (manually
or by `guide-arch` gap analysis). Each file contains the full 5-section
proposal content.

### 2. Index update

When a new proposal is added to the pool, `proposal-suggestions.md` is updated
with a new table row linking to the improvement file.

### 3. Review flow (`guide-arch` Phase 5.5)

1. `guide-arch` reads `proposal-suggestions.md` via `list_improvements()`.
2. For each entry, it follows the link to `.rddf/improvements/<name>.md` to display
   the full content for review.
3. Approved proposals are added to `proposal-approved.md`.
4. Rejected proposals remain in `.rddf/improvements/` but never appear in the
   approved index.

### 4. Consumption flow (`guide-plan` propose)

1. `guide-plan` reads `proposal-approved.md` via `list_approved()`.
2. For each approved entry, it follows the link to `.rddf/improvements/<name>.md`.
3. It creates an OpenSpec change using the 5-section content.

---

## API reference

### Shell (`skills/_lib/state.sh`)

| Function                          | Description                                                |
|-----------------------------------|------------------------------------------------------------|
| `list_improvements <project_root>` | Parse suggestions table. Returns `name\|priority\|source` lines. |

### Python (`skills/_lib/state_reader.py`)

| Function                                  | Returns                          | Description                          |
|-------------------------------------------|----------------------------------|--------------------------------------|
| `read_improvement_entries(project_root)`  | `list[dict]`                    | Read all improvement files with parsed metadata (name, priority, source, phase, category, type). |
| `read_proposal_suggestions(project_root)` | `list[dict]` or `None`          | **DEPRECATED** — reads legacy JSON format. Use `read_improvement_entries()` instead. |

---

## Why Markdown table, not JSON

| Aspect               | Markdown table (current)        | JSON array (legacy)                |
|----------------------|---------------------------------|------------------------------------|
| **Human readability** | ✅ Excellent — view in any editor | ❌ Needs formatting tools          |
| **Git diff**          | ✅ Line-level, easy to review     | ⚠️ Single-line JSON hard to diff   |
| **Manual editing**    | ✅ Intuitive, no special tools    | ❌ Requires JSON editor            |
| **Content separation**| ✅ Index + content in separate files | ❌ All content in one file       |
| **File size**         | ✅ Index stays < 100 lines        | ❌ Can grow to 500+ lines          |

The legacy JSON format stored the full proposal content (5 sections) inside
each JSON object. This caused:
- Single-file bloat (500+ lines)
- All-or-nothing diffs (changing one proposal touched the entire file)
- Poor readability (JSON strings with escaped newlines)

The new Markdown table format solves these by keeping the index lightweight
and storing content in individual files.

---

## Consumers

All skills that touch `proposal-suggestions.md` MUST read it as a Markdown
table and follow the links to `.rddf/improvements/*.md`:

| Skill           | Where the format matters                                       |
|-----------------|----------------------------------------------------------------|
| `guide-arch.md` | Phase 5.5 (review proposals, approve/reject)                  |
| `guide-plan.md` | Propose phase (read `proposal-approved.md` instead)           |
| `propose.md`    | Phase 4d (lookup phase/category from improvement file)        |
| `dashboard`     | Pending section (count unapproved proposals)                   |

The helper in `skills/_lib/state.sh::list_improvements()` centralizes the
parsing logic so consumers don't re-implement regex extraction.

---

## See also

- `docs/proposal-approved-format.md` — format for the approved proposals index
- `skills/_lib/state.sh::list_improvements()` — shell helper for reading the table
- `skills/_lib/state_reader.py::read_improvement_entries()` — Python helper for reading all improvement files
- `skills/_lib/migrate_proposals.py` — migration script from JSON to individual files
- `.rddf/improvements/proposal-approval-pipeline.md` — the proposal that designed this format
