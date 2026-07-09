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

`guide` 是一个**无状态推荐器**。它只读不写——扫描项目当前状态，给出一行建议，告诉用户应该调 `guide-arch`、`guide-plan`、`guide-ship` 或子技能如 `feature`（三阶段架构 ADR-0003：arch → plan → ship）。

不持久化任何状态,不调用 openspec CLI,不修改任何文件。

## 扫描逻辑（v1.1+：提取到独立脚本）

v1.1 起，扫描逻辑不再写在 skill 文件里——它由 `skills/_lib/scan-state.sh` 暴露的 `scan_state()` 函数提供，独立测试，bash 原生执行（不再每次由 AI 现场"翻译"）。**推荐器调一次即可**：

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
# shellcheck source=/dev/null
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]:-$0}")")/_lib/scan-state.sh"
scan_state "$PROJECT_ROOT"
```

设置 `$RECOMMEND` 和 `$REASON`（沿用旧版变量契约，向后兼容）。优先级 11 条 → 见 `skills/_lib/scan-state.sh` 函数体顶部注释。

P0/P1 bug 历史（`$3` 列、`[openspec/` 前缀、`json.load` 非 grep、cwd 安全）作为注释保留在新脚本里，作为 regression guards。

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
