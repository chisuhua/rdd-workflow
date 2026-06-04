---
name: guide
description: 无状态推荐器——扫描项目当前状态（roadmap、changes、worktrees、tasks），建议用户调 guide-spec 或 guide-ship。不持有任何状态，不调用 openspec CLI，不修改任何文件。
license: MIT
compatibility: Requires git 2.25+
metadata:
  author: sisyphus
  version: "4.0"  # P0: 缩减为无状态推荐器
  generatedBy: "3.0"
  user-invocable: true
---

# OpenSpec 工作流 — 推荐器入口

## 用途

`guide` 是一个**无状态推荐器**。它只读不写——扫描项目当前状态，给出一行建议，告诉用户应该调 `guide-spec` 还是 `guide-ship`。

不持久化任何状态,不调用 openspec CLI,不修改任何文件。

## 扫描逻辑(按优先级)

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

# 1. 有 worktree 且 tasks 未全部 [x] → 继续 ship
# 注意:awk 的 system() 只返回状态码,不输出字符串,所以不能用 awk + system() 收集结果。
# 改用 bash 循环,直接检查每个 worktree 的 tasks.md 是否有未勾选任务。
WORKTREE_IN_PROGRESS=""
# git worktree list 的输出格式: <path> <commit> [<branch>]
# branch 在第 3 个字段($3),不是 $2。原代码用 $2 永远匹配不上。
for wt in $(git worktree list 2>/dev/null | awk '$3 ~ /openspec\// {print $1}'); do
    for tf in "$wt"/openspec/changes/*/tasks.md; do
        [ -f "$tf" ] || continue
        if grep -q '^- \[ \]' "$tf" 2>/dev/null; then
            WORKTREE_IN_PROGRESS="yes"
            break 2
        fi
    done
done

# 2. 有 worktree 且 tasks 全 [x] → ship 进入 archive
# 3. 有 committed change 但无 worktree → ship 开始新 change
# 4. 无 roadmap.md → spec 初始化
# 5. 无 committed change → spec 继续 propose
# 6. 默认 → spec

if [ -n "$WORKTREE_IN_PROGRESS" ]; then
    RECOMMEND="guide-ship"; REASON="worktree 存在,任务未完成 → 继续执行"
elif git worktree list 2>/dev/null | grep -q "openspec/"; then
    RECOMMEND="guide-ship"; REASON="worktree 存在,任务已完成 → 进入 archive"
# git show HEAD:<path> 要求相对于 repo root 的相对路径。
# 所以先 cd 进 PROJECT_ROOT,再用相对 globs 枚举 changes。
elif (cd "$PROJECT_ROOT" 2>/dev/null && for d in openspec/changes/*/; do
    [ -d "$d" ] || continue
    case "$d" in */archive/) continue ;; esac
    if git show HEAD:"$d.openspec.yaml" > /dev/null 2>&1; then
        exit 0
    fi
done; exit 1); then
    RECOMMEND="guide-ship"; REASON="有已 commit 的 change 待建 worktree"
elif [ ! -f "$PROJECT_ROOT/roadmap.md" ]; then
    RECOMMEND="guide-spec"; REASON="无 roadmap.md → 初始化"
elif [ -z "$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/)" ]; then
    RECOMMEND="guide-spec"; REASON="无 change → 进入 propose 阶段"
else
    RECOMMEND="guide-spec"; REASON="有 change 待 commit → 继续 propose"
fi
```

## 输出格式

```
🔍 Project state scan:
   - roadmap.md: [✅ exists / ❌ missing]
   - committed changes: [N]
   - worktrees: [N, with status]

💡 Recommended: skill_use("$RECOMMEND")
   Reason: $REASON
```

## 过期状态检测

如果 `$PROJECT_ROOT/workflow-state.md` 存在(旧版文件),打印一次警告:

```
⚠️  Stale workflow-state.md detected (pre-refactor format).
   This file is no longer used and will be ignored.
   Remove it manually if you want: rm workflow-state.md
```

不自动删除(尊重用户数据)。
