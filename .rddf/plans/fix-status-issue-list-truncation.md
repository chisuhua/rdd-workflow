# fix-status-issue-list-truncation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use skill_use("execute") to implement task-by-task.
> 详细 TDD 步骤见 `openspec/changes/fix-status-issue-list-truncation/tasks.md`（**执行真相源**）。

**Goal:** `rddf status` 的 issue 列表逐条可见（未展开的部分必须**明示**）；状态摘要不切开
markdown 标记；摘要清洗与状态分类同源。

**Architecture:** 两处改动 + 一处新函数 ——

1. `_lib/cli/status_cmd.py`：issue 列表去掉 `[:5]` 硬截断；引入
   `STATUS_ISSUE_LIST_LIMIT = 20`，超过时列出前 20 + 明示「还有 N 条未展开（见 `rddf dashboard`）」，
   标题追加未展开数；
2. `_lib/dashboard/improvement_status.py`：新增公开 `clean_status_snippet(raw, limit=40)`
   （复用既有 `_strip_markup`；截断后清掉未闭合的 `「」`/`**` 再补 `…`）；
3. `_lib/dashboard/__init__.py`：stale 消息改用清洗后的摘要（不再 `raw[:40]` 硬切）。

**Tech Stack:** Python 3.11 stdlib，无新依赖。

**Plan verification:** 每 task 红→绿；T3 Step 4 变异腿（渲染退回 `[:5]` ⇒ AC1/AC2 红；
摘要退回硬切 ⇒ AC3 红）；收口 `./test.sh --gates` + `./test.sh --unit` + `openspec validate --strict`。

---

## File Structure

| File | 责任 |
|---|---|
| `_lib/cli/status_cmd.py` | issue 列表渲染（全量 / 阈值 + 明示未展开行）；`STATUS_ISSUE_LIST_LIMIT` 常量。 |
| `_lib/dashboard/improvement_status.py` | `clean_status_snippet()`（清洗 + 安全边界截断 + `…`）。 |
| `_lib/dashboard/__init__.py` | stale 消息使用清洗后的摘要；import 该函数（单一真源）。 |
| `tests/unit/test_status_issue_list_not_truncated.py`（新） | AC1–AC5。 |
| `openspec/specs/status-issue-visibility/spec.md` | 新 capability（1 requirement / 1 scenario），归档时合流。 |

## 代码形状（关键片段）

```python
# _lib/cli/status_cmd.py
#: How many improvement issues the status view lists before it switches to an
#: explicit remainder line. Pinned by tests (never silently reduced).
STATUS_ISSUE_LIST_LIMIT = 20

    if snapshot.errors:
        shown = snapshot.errors[:STATUS_ISSUE_LIST_LIMIT]
        rest = len(snapshot.errors) - len(shown)
        print()
        if rest:
            print(f"⚠️ {len(snapshot.errors)} improvement issue(s) "
                  f"(unreadable / invalid front matter / stale status lines) "
                  f"— 列出前 {len(shown)}，其余 {rest} 条见 `rddf dashboard`")
        else:
            print(f"⚠️ {len(snapshot.errors)} improvement issue(s) "
                  f"(unreadable / invalid front matter / stale status lines)")
        for err in shown:
            print(f"   - {err}")
        if rest:
            print(f"   … 还有 {rest} 条未展开（见 `rddf dashboard` 看全量）")
```

```python
# _lib/dashboard/improvement_status.py
def clean_status_snippet(raw: str, limit: int = 40) -> str:
    """Clean a status line for display and trim it at a SAFE boundary."""
    text = " ".join(_strip_markup(raw or "").split())
    if len(text) <= limit:
        return text
    clipped = text[:limit]
    # Drop a marker the cut left open (「 without 」, ** without its pair).
    for opening, closing in (("「", "」"), ("**", "**")):
        if clipped.count(opening) > clipped.count(closing):
            clipped = clipped.rsplit(opening, 1)[0]
    return clipped.rstrip() + "…"
```

## 边界（不做什么）

- 不改 issue 的产生侧判据（stale / metadata problem 分类）；
- 不改 dashboard 渲染（已全量列出）；
- 不改 pending 表渲染 / 排序 / 分级；
- 不回填任何仓的 improvement 状态行。

## 执行顺序

T1（全量）→ T2（阈值 + 明示）→ T3（摘要 + 变异腿）→ T4（单一真源）→ T5（收口）。
