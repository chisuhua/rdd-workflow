# fix-builder-handoff-p2-lifecycle-truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use skill_use("execute") to implement task-by-task.
> 详细 TDD 步骤见 `openspec/changes/fix-builder-handoff-p2-lifecycle-truth/tasks.md`（**执行真相源**）。

**Goal**：handoff 的 `execution_status` 不再骗人，且有真实消费方；P2 之前能检出主仓分叉。

**Architecture**（4 处改动 + 1 个新助手）：

1. `_lib/builder_handoff.py`：新增 `ImplementationState` + `implementation_state()`
   （真相 = disk 的 `tasks.md`，handoff 只是「声明」）；
2. `skills/rdd-builder/scripts/phase2_execute.sh`：setup 写 `running`（不再 `completed`）
   + **建 worktree 之前的只读前置检查**（脏 tracked 改动 / HEAD 领先 `branch_base_sha`）；
3. `skills/rdd-builder/scripts/phase2_5_review.sh`（**唯一消费方**）：4 选项之前显示实现真实进度
   + 不一致告警；
4. `skills/rdd-builder/scripts/phase3_archive.sh`：归档成功写 `execution_status="completed"`；
   `skills/rdd-builder/SKILL.md`：P2 前置清单三条。

**Tech Stack**：Python 3.11 stdlib + bash；无新依赖。

**Plan verification**：每 task 红→绿；T2 Step 4 变异腿（写回 `completed` ⇒ AC1 红）；
收口 `./test.sh --gates` + `./test.sh --unit` + `openspec validate --strict`。

---

## File Structure

| File | 责任 |
|---|---|
| `_lib/builder_handoff.py` | `ImplementationState` dataclass + `implementation_state()`（唯一真相计算点）。 |
| `skills/rdd-builder/scripts/phase2_execute.sh` | setup 写 `running`；P2 前置检查（只读）。 |
| `skills/rdd-builder/scripts/phase2_5_review.sh` | 消费方：显示 tasks 真实进度 + 不一致告警。 |
| `skills/rdd-builder/scripts/phase3_archive.sh` | 归档成功写 `completed`。 |
| `skills/rdd-builder/SKILL.md` | P2 前置清单（carry 覆盖 / 授权产物先 commit / 分叉不可见）。 |
| `tests/unit/test_builder_handoff_lifecycle.py`（新） | AC1–AC4（+ AC6 变异腿）。 |
| `tests/unit/test_builder_handoff.py` | 连带修改：`in-progress` → `running`（AC3）。 |
| `tests/integration/test_phase2_prereq_check.bats`（新） | AC5。 |

## 代码形状（关键片段）

```python
# _lib/builder_handoff.py
@dataclass(frozen=True)
class ImplementationState:
    tasks_done: int
    tasks_total: int
    handoff_status: str
    claimed_complete: bool
    actually_complete: bool
    inconsistent: bool


def implementation_state(project_root: str, change_name: str) -> ImplementationState:
    """The implementation's TRUE state (disk) vs what the handoff CLAIMS.

    The truth is the task counter on disk; the handoff is only a claim. A
    legacy handoff (written by the old setup step) says `completed` while
    nothing is implemented — that is reported as `inconsistent`, never as
    "done".
    """
    from _lib.tasks_count import count_tasks

    tasks_path = Path(project_root) / "openspec" / "changes" / change_name / "tasks.md"
    done = total = 0
    try:
        done, total = count_tasks(tasks_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        pass
    handoff = read_builder_handoff(project_root, change_name)
    status = str(handoff.get("execution_status") or "")
    claimed = status == "completed"
    actually = total > 0 and done == total
    return ImplementationState(done, total, status, claimed, actually,
                               claimed and not actually)
```

```bash
# skills/rdd-builder/scripts/phase2_5_review.sh —— 消费方
python3 - <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["PKG_ROOT"])
from _lib.builder_handoff import implementation_state
state = implementation_state(os.environ["PROJECT_ROOT"], os.environ["CHANGE_NAME"])
done, total = state.tasks_done, state.tasks_total
mark = "已完成" if state.actually_complete else "未完成"
print(f"实现状态：tasks {done}/{total}（{mark}）   handoff execution_status={state.handoff_status or '-'}")
if state.inconsistent:
    print("⚠️  不一致：handoff 声称 completed，但 tasks 未全勾"
          "（存量 setup 语义或写入方未修）⇒ 以 tasks 为准", file=sys.stderr)
PYEOF
```

## 边界（不做什么）

- 不改 `_is_eligible` / 归档门语义；
- 不自动 commit / merge 主仓内容到 worktree（只检出 + 提示）；
- 不批量迁移存量 handoff（只提示不一致）；
- 不改 `_carry_artifacts` 的搬运实现。

## 执行顺序

T1（计算点）→ T2（写侧）→ T3（枚举收敛）→ T4（消费方）→ T5（前置检查 + SKILL）→ T6（收口）。
