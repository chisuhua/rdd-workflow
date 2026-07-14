---
name: guide
description: 无状态推荐器——扫描项目当前状态（roadmap、arch-handoff、plan-handoff、active changes、worktrees、rddf-session binding），建议用户调 guide-arch、guide-plan 或 guide-ship。不持有任何状态，不调用 openspec CLI，不修改任何文件。
license: MIT
compatibility: Requires git 2.25+
metadata:
  version: "2.0"   # source-of-truth (latest semver)
  author: sisyphus
  evolved-from: "split from guide.md v3.0; v1.1 also added rddf-session binding scan (spec 2026-07-14)"
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
echo "💡 Recommended: skill_use(\"$RECOMMEND\")"
echo "   Reason: $REASON"

# Binding discovery (spec 2026-07-14): read-only rddf-session binding scan
scan_session_binding "$PROJECT_ROOT"
if [ ${#BINDING_LINES[@]} -gt 0 ]; then
  printf '%s\n' "${BINDING_LINES[@]}"
fi
```

设置 `$RECOMMEND` 和 `$REASON`（沿用旧版变量契约，向后兼容）。优先级 11 条 → 见 `skills/_lib/scan-state.sh` 函数体顶部注释。

`scan_session_binding` 是 v2.0.2 新增的只读函数，扫描 `.rddf/state/sessions.json` 的当前绑定状态，将结果存入 `BINDING_LINES` 数组。推荐器 AI 应在打印 RECOMMEND/REASON 之后、关闭输出之前输出这批行（见下方输出格式）。

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

输出追加（v2.0.2+，仅当 `.rddf/state/sessions.json` 存在时）：

```
📍 Current: rds_xxx (kind=stage_X, started=...)             # 当当前 OpenCode session 已绑定一个 active rddf-session
📍 No current binding                                          # 当无活跃绑定
💡 Recommended: rds_yyy ... → skill_use("rddf-session resume ...")  # 当存在 orphaned session
```

## 过期状态检测

如果 `$PROJECT_ROOT/workflow-state.md` 存在(旧版文件),打印一次警告:

```
⚠️  Stale workflow-state.md detected (pre-refactor format).
   This file is no longer used and will be ignored.
   Remove it manually if you want: rm workflow-state.md
```

不自动删除(尊重用户数据)。

## Cross-Reference

- **`rddf-session`** (`skills/rddf-session.md`) — 当输出包含 `📍 No current binding` 时,可调 `skill_use("rddf-session current")` 查看完整绑定状态,或 `skill_use("rddf-session resume <rds_id>")` 接管推荐会话。详见 spec 2026-07-14。
- **ADR-0017** (`docs/adr/ADR-0017-rddf-session.md`) — rddf-session 数据模型、跨 OpenCode session 恢复语义、心跳机制的来源。
- **scan-state.sh** (`skills/_lib/scan-state.sh`) — 推荐器底层扫描脚本;11-priority `scan_state` + v2.0.2 `scan_session_binding`。
