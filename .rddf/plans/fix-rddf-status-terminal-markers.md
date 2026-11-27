# fix-rddf-status-terminal-markers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use skill_use("execute") to implement task-by-task.
> 详细 TDD 步骤见 `openspec/changes/fix-rddf-status-terminal-markers/tasks.md`（**执行真相源**）；
> 本文件给文件结构、代码形状与边界。

**Goal:** `rddf status` 的 pending 数 = 真待办数；陈旧状态行**可见**；终态词表**单一真源**。

**Architecture:** 三处改动，互相独立但共享「单一真源」这条主线 ——

1. `_lib/dashboard/improvement_status.py`：终态词表提为公开常量 `TERMINAL_MARKERS`，
   补 `已落地` / `已拆分` / `已取代`；
2. `_lib/dashboard/__init__.py::collect_pending`：过滤顺序改为「先判状态 → 终态跳过 →
   archived/approved 跳过但记 stale → 否则进 pending」，stale 进 `snap.errors`；
3. `_lib/state_reader.py`：破损 front matter 的错误附「行号 + 原文」；
   `_lib/cli/status_cmd.py`：help 从常量渲染词表 + 错误段措辞覆盖两类问题。

**Tech Stack:** Python 3.11 stdlib（`dataclasses` / `pathlib` / `re`），无新依赖。

**Plan verification:** 每 task 红→绿；T3 Step 4 变异腿（过滤顺序回退 ⇒ AC3 红）；
收口 `./test.sh --gates` + `./test.sh --unit` + `openspec validate --strict`。

---

## File Structure

| File | 责任 |
|---|---|
| `_lib/dashboard/improvement_status.py` | `TERMINAL_MARKERS`（公开、唯一）+ 三个新 token + 登记册指针注释。 |
| `_lib/dashboard/__init__.py` | `collect_pending()` 的分类/过滤顺序；stale 诊断进 `snap.errors`。 |
| `_lib/state_reader.py` | `_parse_improvement_meta()` 的错误附行号 + 原文。 |
| `_lib/cli/status_cmd.py` | `_print_help()` 渲染词表；Mode A 错误段措辞。 |
| `tests/unit/test_improvement_status_markers.py`（新） | AC1 + AC2（三个新 token / 既有 token 零回归）。 |
| `tests/unit/test_collect_pending_stale.py`（新） | AC3 + AC4 + AC5（stale 可见 / 字段级定位 / 单一真源）。 |

## 代码形状（关键片段）

```python
# _lib/dashboard/improvement_status.py
#: Terminal markers ⇒ delivered. SINGLE definition point (AC5): the help
#: text renders this table, so a second copy would be a drift surface.
#: Registry whitelist (项目登记册 §6.8) uses 已落地 / 已拆分 / 已取代 — keep in sync.
TERMINAL_MARKERS: tuple[tuple[str, str], ...] = (
    ("已完成并归档", "已归档"),
    ("已实施并验收", "已完成"),
    ("已归档", "已归档"),
    ("已完成", "已完成"),
    ("已实施", "已实施"),
    ("已落地", "已落地"),      # 登记册完成态 token
    ("已拆分", "已作废"),
    ("已取代", "已作废"),
    ("implemented", "已实施"),
    ("completed", "已完成"),
    ("已作废", "已作废"),
    ("作废", "已作废"),
    ("superseded", "已作废"),
    ("archived", "已归档"),
)
```

```python
# _lib/dashboard/__init__.py::collect_pending
        try:
            terminal, label = classify_improvement_status(entry.get("status") or "")
        except Exception as exc:
            snap.errors.append(f"{name}: {exc}")
            continue
        if terminal:
            continue
        if name in approved or name in archived_names:
            snap.errors.append(
                f"{name}: stale status — 已归档/已批准，但状态行仍是"
                f"「{(entry.get('status') or '').strip()[:40]}」（非终态）"
            )
            continue
        snap.suggestions.append(SuggestionEntry(...))
```

```python
# _lib/state_reader.py — field-level location for a broken front matter
def _front_matter_error(content: str, exc: Exception) -> str:
    msg = " ".join(str(exc).split())
    mark = getattr(exc, "problem_mark", None)
    if mark is None:
        return "invalid YAML front matter: " + msg
    lines = content.split("\n")
    file_line = mark.line + 2          # block line 0 == file line 2 ("---" is line 1)
    src = lines[file_line - 1].strip() if 0 < file_line <= len(lines) else ""
    tail = f" (front-matter line {file_line}: {src[:80]})" if src else ""
    return "invalid YAML front matter: " + msg + tail
```

## 边界（不做什么）

- 不回填既有 improvement 的状态行（只读面）；
- 不引入词表可配置机制（review 判定过度设计）；
- 不改 pending 视图结构、不改 `improvement-approved.md` 生命周期；
- 不新增并行状态文件。

## 执行顺序

T1（词表）→ T2（过滤顺序）→ T3（端到端可见 + 变异腿）→ T4（字段级定位）→ T5（文档化 + 单一真源）→ T6（收口）。
