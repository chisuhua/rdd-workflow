---
name: guide
description: 无状态推荐器——扫描项目当前状态（roadmap、arch-handoff、plan-handoff、active changes、worktrees），建议用户调 guide-arch、guide-plan 或 guide-ship。不持有任何状态，不调用 openspec CLI，不修改任何文件。
license: MIT
compatibility: Requires git 2.25+
metadata:
  author: sisyphus
  version: "1.0"  # P0: 缩减为无状态推荐器
  evolved-from: "split from guide.md v3.0"
  user-invocable: true
---

# OpenSpec 工作流 — 推荐器入口

## 用途

`guide` 是一个**无状态推荐器**。它只读不写——扫描项目当前状态，给出一行建议，告诉用户应该调 `guide-arch`、`guide-plan` 还是 `guide-ship`（三阶段架构 ADR-0003：arch → plan → ship）。

不持久化任何状态,不调用 openspec CLI,不修改任何文件。

## 扫描逻辑(按优先级)

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

# 0. 三阶段交接状态检测 (arch → plan → ship) — 优先级最高
#    通过 .rddf/state/.arch-handoff.json / .rddf/state/.plan-handoff.json 软状态文件判断当前阶段。
#    arch-done 后但 plan 未开始 → 引导进入 plan
#    plan-done 后 → 引导进入 ship
ARCH_HANDOFF="$PROJECT_ROOT/.rddf/state/.arch-handoff.json"
PLAN_HANDOFF="$PROJECT_ROOT/.rddf/state/.plan-handoff.json"

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
# 4. 无 roadmap.md → arch 初始化
# 5. 无 committed change → plan 继续 propose
# 6. 默认 → plan

if [ -f "$ARCH_HANDOFF" ] && [ ! -f "$PLAN_HANDOFF" ]; then
    RECOMMEND="guide-plan"; REASON="架构定义已完成 → 进入变更生成"
elif [ -f "$PLAN_HANDOFF" ]; then
    RECOMMEND="guide-ship"; REASON="变更生成已完成 → 进入变更执行"
elif [ -n "$WORKTREE_IN_PROGRESS" ]; then
    RECOMMEND="guide-ship"; REASON="worktree 存在,任务未完成 → 继续执行"
# P1-3: phase gate report takes priority — must review before proceeding
# P1-3: detached worktrees (other sessions) may be running, surface them
elif [ -f "$PROJECT_ROOT/.rddf/state/.phase-gate-report.md" ]; then
    RECOMMEND="status --roadmap"; REASON="阶段门控报告待 review"
elif DETACHED=$(git worktree list 2>/dev/null | awk '$3 ~ /^openspec\//' | wc -l)
     [ "$DETACHED" -gt 0 ]; then
    RECOMMEND="guide-ship"; REASON="$DETACHED 个 worktree 在跑（可能在分离终端）"
elif git worktree list 2>/dev/null | awk '$3 ~ /^openspec\//' | grep -q .; then
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
    RECOMMEND="guide-arch"; REASON="无 roadmap.md → 进入架构定义"
elif [ -z "$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/)" ]; then
    RECOMMEND="guide-plan"; REASON="无 change → 进入变更生成"
else
    # 6. 读取 proposal-suggestions.md 判断
    # P1-7: 文件格式已规范化为 JSON 列表
    #       用 json.load 解析后判断是否有 status == "待创建" 的条目
    #       旧实现用 grep -q 'status: 待创建'，但 description 字段可能也含"待创建"字面量
    HAS_PENDING=$(python3 -c "
import json, sys
try:
    with open('proposal-suggestions.md') as f:
        entries = json.load(f)
    if not isinstance(entries, list):
        print('no')
        sys.exit(0)
    pending = any(isinstance(e, dict) and e.get('status') == '待创建' for e in entries)
    print('yes' if pending else 'no')
except (FileNotFoundError, json.JSONDecodeError):
    print('no')
" 2>/dev/null)
    if [ "$HAS_PENDING" = "yes" ]; then
      RECOMMEND="guide-plan"
      REASON="有 change 待创建 → 继续 propose"
    else
      RECOMMEND="guide-ship"
      REASON="无待创建 change → 准备 ship"
    fi
fi
```

## 输出格式

```
🔍 Project state scan:
   - roadmap.md: [✅ exists / ❌ missing]
- .rddf/state/.arch-handoff.json: [✅ exists / ❌ missing]
- .rddf/state/.plan-handoff.json: [✅ exists / ❌ missing]
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
