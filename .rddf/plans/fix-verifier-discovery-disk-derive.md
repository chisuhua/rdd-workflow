# fix-verifier-discovery-disk-derive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use skill_use("execute") to implement task-by-task.
> 详细 TDD 步骤见 `openspec/changes/fix-verifier-discovery-disk-derive/tasks.md`（**它是执行真相源**；
> 本文件给文件结构、代码形状与边界）。

**Goal:** `rddf rdd-verify` 的批量队列改为从 disk 推导（与 `rddf status` Mode A 同一实现），
空队列给出可诊断原因，写回侧不再创建半成品 `iteration.json`。

**Architecture:** 抽 `_lib/change_status.py` 作为 disk 状态推导的**唯一实现**；
`status_cmd` 与 `verifier.discovery` 都以 `derive_status as _derive` 导入（对象身份可断言）；
`discovery` 加 `discover_eligible_detailed`（原因/提示）而保留原签名；
`scan_queue.sh` 改为委派，删除第二份判据。

**Tech Stack:** Python 3.11 stdlib（`pathlib` / `dataclasses` / `json` / `subprocess`），bash 薄包装。

**Plan verification:** 每 task 红→绿 + 至少一个变异腿（T1 / T2）；收口 `./test.sh --gates` + `./test.sh --unit`
+ `openspec validate --strict`。

---

## File Structure

| File | 责任 |
|---|---|
| `_lib/change_status.py`（新） | `derive_status(project_root, name) -> str`：`in_worktree` / `committed` / `completed` / `planned`。内含 `_has_worktree` / `_has_committed` / `_plan_committed_changes` / `_tasks_complete`（自 `status_cmd` 迁出，逻辑不改）。 |
| `_lib/cli/status_cmd.py` | 删本地实现，改 `from _lib.change_status import derive_status as _derive`；`_disk_change_status` 保留为 `return _derive(...)` 薄包装。 |
| `_lib/verifier/discovery.py` | `discover_eligible_detailed()` + `DiscoveryResult` + `discover_eligible()` 包装；`_is_eligible(dict)` 语义保留。 |
| `_lib/cli/rdd_verify_cmd.py` | 空队列 reasons → stderr；`update_iteration_summary` 只在「文件存在且命中条目」时落盘。 |
| `skills/rdd-verifier/scripts/scan_queue.sh` | 改为调用 `discover_eligible`（`pkg_root` 解析同 `_lib/archive.sh`），删内联判据。 |
| `tests/unit/test_change_status_shared.py`（新） | derive_status 四形态 + **对象身份**断言。 |
| `tests/unit/test_verifier_discovery_disk.py`（新） | 无 iteration.json 可发现 / 空队列可达原因 / 陈旧提示。 |
| `tests/unit/test_rdd_verify_cmd.py` | 增 2 例：不创建 iteration.json / 无条目不落盘。 |
| `tests/unit/test_iteration_tasks_total.py` | `TestEligibilityParity` fixture 补 change 目录 + tasks.md。 |
| `tests/unit/test_verifier_branch_discovery.py` | `test_discover_from_iteration` → `test_discover_consistent_iteration_matches_disk`。 |
| `tests/integration/test_rdd_verify_dry_run_without_iteration.bats`（新） | 临时项目根（`git init`）端到端 dry-run。 |

## 代码形状（关键片段）

```python
# _lib/change_status.py
def derive_status(project_root: str, name: str) -> str:
    if _has_worktree(project_root, name):     return "in_worktree"
    if _has_committed(project_root, name):    return "committed"
    if _tasks_complete(project_root, name):   return "completed"
    return "planned"

# _lib/verifier/discovery.py
@dataclass(frozen=True)
class DiscoveryResult:
    eligible: list[str]
    reasons: list[str]
    notices: list[str]

_ELIGIBLE_STATUSES = {"in_worktree", "completed"}

def discover_eligible_detailed(project_root) -> DiscoveryResult:
    root = Path(project_root)
    changes_dir = root / "openspec" / "changes"
    if not changes_dir.is_dir():
        return DiscoveryResult([], ["no active change under openspec/changes/"], [])
    eligible, reasons, notices = [], [], []
    incomplete = 0
    for entry in sorted(changes_dir.iterdir()):
        tasks = entry / "tasks.md"
        if not entry.is_dir() or entry.name == "archive" or not tasks.is_file():
            continue
        done, total = count_tasks(tasks.read_text(encoding="utf-8"))
        status = _derive(str(root), entry.name)
        if total > 0 and done != total:
            incomplete += 1
        if total > 0 and done == total and status in _ELIGIBLE_STATUSES:
            eligible.append(entry.name)
    if not eligible:
        if incomplete:
            reasons.append(f"no change has all tasks checked ({incomplete} change(s) incomplete)")
        else:
            reasons.append("no change reached in_worktree/completed on disk")
    return DiscoveryResult(eligible, reasons, notices)
```

```python
# _lib/cli/rdd_verify_cmd.py::update_iteration_summary
def update_iteration_summary(project_root, change_name, verification):
    state_file = Path(project_root) / ".rddf" / "state" / "iteration.json"
    if not state_file.is_file():
        print(f"ℹ️  iteration.json 缺失 ⇒ 跳过 verification 回写（记账见 "
              f".rddf/state/verifier/）；change={change_name}", file=sys.stderr)
        return
    doc = _load_iteration_doc(project_root)
    for ch in doc.get("changes", []):
        if ch.get("name") == change_name:
            ch["verification"] = verification
            _save_iteration_doc(project_root, doc)
            return
    print(f"ℹ️  iteration.json 无 '{change_name}' 条目 ⇒ 跳过回写", file=sys.stderr)
```

## 边界（不做什么）

- 不改 `_is_eligible(dict)` 判据语义、不改 `rddf status` 文本、不改归档路径与 `archive_gate`；
- 不写 `iteration.json`（任何情形都不新建）、不建并行状态文件；
- 不把 verdict cache 的 freshness 逻辑并入 discovery（`run_one_change` 已有，重复即第二真源）。

## 执行顺序

T1（共享模块）→ T2（discovery）→ T3（诊断）→ T4（写回侧）→ T5（scan_queue + 既有用例）→ T6（端到端 + 门）。
T1 必须先于 T2（T2 依赖 `_derive`）；T4 与 T2/T3 无耦合，放其后以复用同一 worktree。
