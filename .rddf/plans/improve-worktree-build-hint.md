# improve-worktree-build-hint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use skill_use("execute") to implement task-by-task.
> 详细 TDD 步骤见 `openspec/changes/improve-worktree-build-hint/tasks.md`（**执行真相源**）。

**Goal**：worktree 内无 `build/` 目录时，P2 输出一行固定文本的可机判提示（stderr）。

**Architecture**（一处改动 + 一个 bats 文件）：

1. `skills/rdd-builder/scripts/phase2_execute.sh`：worktree 建好之后、执行之前，若
   `[ ! -d "$EXEC_DIR/build" ]` ⇒ 向 stderr 打印固定提示行（含「后台任务」「勿 sleep 轮询」）；
2. `tests/integration/test_phase2_build_hint.bats`（新）：三种情形（无 build ⇒ 提示 / 有 build ⇒
   不提示 / lightweight ⇒ 不提示）+ 通道断言（stdout 不含）+ 判别力变异腿。

**Tech Stack**：bash + bats，无新依赖。

**Plan verification**：红→绿 + 变异腿；收口 `./test.sh --gates` + `./test.sh --bats` +
`openspec validate --strict`。

---

## File Structure

| File | 责任 |
|---|---|
| `skills/rdd-builder/scripts/phase2_execute.sh` | 一行提示（只读检测，走 stderr）。 |
| `tests/integration/test_phase2_build_hint.bats`（新） | AC1–AC4。 |

## 代码形状（关键片段）

```bash
# skills/rdd-builder/scripts/phase2_execute.sh —— worktree 建好之后、执行之前
if [ "$EXEC_MODE" = "worktree" ] && [ ! -d "$EXEC_DIR/build" ]; then
    echo "⚠️  worktree 内无 build/ 目录 ⇒ 首次构建可能较慢（建议后台任务 + 等完成通知，勿 sleep 轮询）" >&2
fi
```

## 边界（不做什么）

- 不实现任何构建缓存机制（ccache / 复用 build 目录属项目侧）；
- 不改执行模式判定；
- 不检测项目是否已用 ccache（不分支）；
- 提示**不阻断**、不改退出码。

## 执行顺序

T1（提示行 + 通道）→ T2（不产生噪音）→ T3（判别力 + 收口校验）→ T4（全量门）。
