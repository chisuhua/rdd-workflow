# `proposal-suggestions.md` Format

> **Status**: canonical (P1-7, replaced the legacy mixed YAML+Markdown format).

This document is the single source of truth for how the
`proposal-suggestions.md` file is structured, read, and written by the
spec-workflow skills (`propose`, `guide-spec`, `guide`, `status`).

---

## Container format: pure JSON

The file **MUST** contain a single JSON array at the top level. Each
element of the array is a suggestion object.

### Schema

```json
[
  {
    "name": "fix-ns-pollution",
    "priority": "P0",
    "source": "ADR-033",
    "status": "待创建",
    "phase": "phase-1",
    "category": "arch-design",
    "description": "## 架构依据\n- ADR-033 §3.2: ...\n## 范围\n- In Scope: ...\n- Out Scope: ...",
    "effort": "2-3天"
  }
]
```

### Field reference

| Field         | Type   | Required | Description                                                                                       |
|---------------|--------|----------|---------------------------------------------------------------------------------------------------|
| `name`        | string | yes      | kebab-case identifier. Used as the `openspec/changes/<name>/` directory name.                     |
| `priority`    | string | yes      | One of `P0`, `P1`, `P2`. Drives display sort order.                                               |
| `source`      | string | yes      | Free-form reference (e.g. `ADR-033 §3.2`, `架构差距分析`, `TODO @ src/foo.cpp:42`).               |
| `status`      | string | yes      | One of `待创建`, `进行中`, `已完成`. Consumers filter on `待创建` to find pending work.            |
| `phase`       | string | yes      | Roadmap phase id (e.g. `phase-1`) or `default` in compat mode.                                     |
| `category`    | string | yes      | Task category id (e.g. `arch-design`, `infra-setup`, `core-test`, `core-impl`) or `general`.      |
| `description` | string | yes      | Multi-line Markdown with `##` headers (5 sections — see below). `\\n` separates lines in JSON.   |
| `effort`      | string | no       | Free-form effort estimate (e.g. `2-3天`, `1w`). Optional but recommended.                         |

### 5-section description contract

The `description` field embeds the same five Markdown sections that the
old format used as top-level `##` headers. Consumers and the
`openspec-propose` pipeline treat them as opaque Markdown — the only
requirement is that all five sections appear in this order:

1. `## 架构依据` — ADR / 文档引用
2. `## 范围` — `In Scope` / `Out Scope`
3. `## 关键场景` — `GIVEN` / `WHEN` / `THEN`
4. `## 技术约束` — `MUST` / `MUST NOT` / `SHOULD`
5. `## 验收标准` — 量化指标

When the value is written into JSON, embedded newlines are encoded as
`\n` (two characters) and embedded `"` are escaped as `\"`.

---

## Migration from the legacy YAML+Markdown format

The legacy format mixed top-level YAML entries with Markdown `## 架构依据`
sections. The new format keeps the same logical content (5-section
description) but moves the description into a single JSON string field.

### Detection

A file is treated as **legacy format** if, when parsed as JSON, it fails
OR its raw text contains the marker `## 架构依据` at column 0 (i.e. as a
top-level Markdown header, not as a substring of a JSON string value).

### Behavior

`write_suggestions` (in `skills/_lib/state.sh`) does the following when it
detects a legacy file before overwriting:

1. Print a warning to stderr: `⚠️ 旧格式 proposal-suggestions.md 检测到`
2. Print a hint: `   自动迁移需要手动确认`
3. Copy the file to `proposal-suggestions.md.bak` (preserves user data)
4. Print: `   已备份到 proposal-suggestions.md.bak`
5. Continue with the new write

> The skill **never** auto-migrates. The user must run a migration tool
> or hand-edit the file. This is per the audit's MUST NOT DO
> requirement: warn only, never rewrite user data silently.

`read_suggestions` does the same detection and prints the warning on
read, then continues with the (likely empty) parse. This is intentional:
the user sees the warning every time they touch the file until they
either delete it or migrate it.

---

## Consumers

All five skills that touch `proposal-suggestions.md` MUST read it as JSON:

| Skill           | Where the format matters                                       |
|-----------------|----------------------------------------------------------------|
| `propose.md`    | Phase 0 (load + filter), Phase 4d (lookup phase/category), Phase 5d (count remaining) |
| `guide-spec.md` | Phase 2 display (`cat proposal-suggestions.md`)                |
| `guide.md`      | Priority 6 (recommend `guide-spec` if any `待创建` exists)      |
| `status.md`     | Mode C post-archive loop check                                  |

The helpers in `skills/_lib/state.sh` (`read_suggestions`,
`write_suggestions`) centralize the read/write logic so consumers don't
re-implement JSON parsing.

### Why JSON, not YAML

- **Single source of truth** — no ambiguity about whether `##` is a
  top-level header or part of a description value
- **Built-in `json` module** in Python 3 (no PyYAML dependency for
  this file)
- **Trivially validated** — `python3 -c "import json; json.load(open(f))"`
- **Machine-parseable by all 5 consumers** with the same 1-line helper

---

## Example: writing a new entry

```python
import json

entry = {
    "name": "fix-ns-pollution",
    "priority": "P0",
    "source": "ADR-033",
    "status": "待创建",
    "phase": "phase-1",
    "category": "arch-design",
    "description": (
        "## 架构依据\n"
        "- ADR-033 §3.2: 命名空间污染修复决策\n"
        "\n"
        "## 范围\n"
        "- In Scope: 8 个核心头文件\n"
        "- Out Scope: archive/ 目录\n"
    ),
    "effort": "2-3天",
}

with open("proposal-suggestions.md", "w") as f:
    json.dump([entry], f, ensure_ascii=False, indent=2)
```

## Example: reading and filtering

```python
import json

with open("proposal-suggestions.md") as f:
    suggestions = json.load(f)

pending = [s for s in suggestions if s.get("status") == "待创建"]
print(f"{len(pending)} pending suggestions")
```

---

## See also

- `skills/propose.md` Phase 0 / 2 / 5 — primary producer
- `skills/_lib/state.sh::read_suggestions` and `::write_suggestions` — shared helpers
- `tests/integration/test_suggestions_format.bats` — format conformance test
