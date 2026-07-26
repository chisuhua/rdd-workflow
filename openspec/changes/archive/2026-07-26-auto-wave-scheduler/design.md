## Context

当前 rdd-workflow 的 Wave 执行顺序完全依赖人工判断。`iteration.json` 存储所有 change 的状态，`manual_deps` 字段（ADR-0022）记录了 change 之间的依赖关系，但缺少消费方来自动检测：

1. 当 change-a 归档后，change-b（依赖 change-a）的 blocker 应自动标记为已解除
2. 各入口 hook（guide-arch/guide-plan/guide-ship）应自动推进 iteration 状态
3. 归档后应输出可执行的下一个 change 建议

现有基础设施：
- `iteration.json` schema v4 已支持 `manual_deps` 和 `manual_blocks` 字段
- `roadmap-meta.yaml` 已支持 `manual_deps: [change_name]` 声明
- `archive.sh` 已有归档完成后的回调位置
- 各 `guide-*` skill 入口已有 session 绑定 hook

## Goals / Non-Goals

**Goals:**
- guide-arch/guide-plan/guide-ship 入口 hook 自动迭代状态转换（planned→proposed→in_worktree→archived）
- archived hook 扫描 iteration.json 中 blocker 已解除的 planned change
- 输出建议信息 "bloker 已解除: change-x, change-y 可以执行"
- 测试覆盖 archived→unblocked→suggest 链路

**Non-Goals:**
- 不自动调用 guide-ship（仅建议，用户确认）
- 不修改 DependencyScheduler（ADR-0010 v2.1 完整版留待后续）
- 不修改现有 hook 行为

## Decisions

### Decision 1: Entry hook 状态推进（guide-arch/guide-plan/guide-ship）

- **Why**: 当前入口 hook 仅绑定 session，不推进 iteration 状态。同一 session 中用户可能手动切换阶段，状态应自动同步。
- **How**: 在 `skills/_lib/iteration/` 中新增 `auto_advance.py` 模块，暴露 `auto_advance_status()` 函数。各入口 hook 调用此函数，按 `planned→proposed→in_worktree→archived` 顺序推进。
- **State machine 规则**:
  - `planned` → `proposed`: 当 guide-plan 入口检测到当前 session 是 plan 阶段
  - `proposed` → `in_worktree`: 当 guide-ship 入口检测到 session 是 ship 阶段
  - `in_worktree` → `archived`: archive.sh 完成时由 archive hook 触发
- **Alternative**: 在 propose.md Phase 4 中手动推进
- **Rejected**: 手动推进容易遗漏，自动化更可靠

### Decision 2: archive hook blocker 检测

- **Why**: 归档后是最自然的检查点 — 此时一个 change 完成，可能有多个 blocker 解除。
- **How**: 在 `skills/_lib/archive.sh` 的 `archive_change` 函数末尾（auto-commit 之后）添加非阻塞的 blocker 检测调用：
  ```bash
  detect_unblocked_changes "$ARCHIVED_CHANGE" "$PROJECT_ROOT" || true
  ```
- **检测逻辑**:
  1. 读取 `iteration.json` 中所有 `status=planned` 的 change
  2. 检查每个 change 的 `manual_deps` 字段
  3. 如果 `manual_deps` 包含刚归档的 change，且所有 deps 都已归档 → 输出建议
- **输出格式**: `"📋 bloker 已解除: change-x, change-y 可以执行"`
- **Alternative**: 定时扫描
- **Rejected**: 定时扫描增加复杂度，归档后立即检测最及时

### Decision 3: 建议仅输出，不自动执行

- **Why**: 用户应确认 Wave 切换，自动化执行可能导致意外行为。
- **How**: 检测到可执行 change 后仅输出建议信息，不调用 guide-ship。用户确认后手动执行。
- **Alternative**: 自动调用 guide-ship
- **Rejected**: 不符合"仅建议，用户确认"的设计目标

## API

### `auto_advance_status()` (Python)

```python
def auto_advance_status(iteration_path: str, current_stage: str) -> dict:
    """
    Auto-advance iteration.json statuses based on current workflow stage.
    
    Args:
        iteration_path: Path to iteration.json
        current_stage: One of "arch", "plan", "ship"
    
    Returns:
        dict with keys:
            - updated: int (number of entries updated)
            - changes: list[str] (names of updated entries)
    """
```

### `detect_unblocked_changes()` (bash)

```bash
detect_unblocked_changes <archived_name> <project_root>
# Output: Prints suggestion lines to stdout
#   "📋 bloker 已解除: change-x, change-y 可以执行"
# Returns: 0 (always, non-blocking)
```

## Test Plan

### Unit tests (3 cases, in `tests/unit/test_iteration.py`)

| Test | Input | Expected |
|------|-------|----------|
| `auto_advance_status` with plan stage | iteration.json with planned changes | `planned`→`proposed` for relevant entries |
| `auto_advance_status` with ship stage | iteration.json with proposed changes | `proposed`→`in_worktree` for relevant entries |
| No-op when status already advanced | iteration.json with all `archived` | 0 updates |

### Integration tests (2 cases, in `tests/integration/test_archive_hook.bats`)

| Test | Input | Expected |
|------|-------|----------|
| Archive change-b, change-a has `manual_deps=[change-b]` | Archive change-b | Output contains "bloker 已解除: change-a" |
| Archive isolated change | Archive change with no dependents | No suggestion output |