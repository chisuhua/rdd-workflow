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

## 扫描逻辑（v1.1+：提取到独立脚本；v2.1+：synthesizer 增强输出）

v1.1 起，扫描逻辑不再写在 skill 文件里--它由 `scripts/scan-state.sh` 暴露的 `scan_state()` 函数提供，独立测试，bash 原生执行（不再每次由 AI 现场"翻译"）。v2.1 起增加 Python `workflow_synthesizer.py` 作为结构化输出层：先跑 `scan_state` 取得 baseline `RECOMMEND` + `REASON`，再尝试调用 synthesizer 覆盖输出（synthesizer 失败则保留 baseline，向后兼容）。**推荐器调一次即可**：

```bash
case "${1:-}" in
  --help|-h)
    cat <<'EOF'
guide 推荐器 - 用法:
  skill_use("guide")                  # 默认扫描并输出 RECOMMEND + REASON
  skill_use("guide --no-binding")     # 不输出 rddf-session binding block
  skill_use("guide --help")           # 打印此帮助
EOF
    return 0 2>/dev/null || exit 0
    ;;
  --no-binding)   NO_BINDING=1 ;;
  *)              NO_BINDING=0 ;;
esac

PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]:-$0}")")/scripts/scan-state.sh"
scan_state "$PROJECT_ROOT"

# v2.1: structured recommendation from workflow_synthesizer (read-only).
# Falls back gracefully to legacy scan_state result on Python/import errors.
# The synthesizer produces a WorkflowRecommendation dataclass with
# suggested_action/reason/confidence + unblocked_changes + active_session.
if command -v python3 >/dev/null 2>&1; then
  RECO_JSON=$(PY_PROJECT_ROOT="$PROJECT_ROOT" python3 -c '
import json, os, sys
sys.path.insert(0, os.environ["PY_PROJECT_ROOT"])
from skills._lib.workflow_synthesizer import synthesize
r = synthesize(os.environ["PY_PROJECT_ROOT"])
print(json.dumps({
    "suggested_action": r.suggested_action,
    "reason": r.reason,
    "confidence": r.confidence,
    "unblocked_changes": list(r.unblocked_changes),
    "active_session": r.active_session,
    "orphaned_sessions": list(r.orphaned_sessions),
}))
' 2>/dev/null) && [ -n "$RECO_JSON" ]
  then
    RECOMMEND=$(printf '%s' "$RECO_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["suggested_action"])')
    REASON=$(printf '%s' "$RECO_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["reason"])')
  fi
fi

echo "💡 Recommended: skill_use(\"$RECOMMEND\")"
echo "   Reason: $REASON"

# Binding discovery (spec 2026-07-14): read-only rddf-session binding scan
# 当 BINDING_LINES 为空（sessions.json 不存在或当前无绑定）时静默跳过，
# 不打印任何额外行。
if [ "${NO_BINDING:-0}" -eq 0 ]; then
  scan_session_binding "$PROJECT_ROOT"
  if [ ${#BINDING_LINES[@]} -gt 0 ]; then
    printf '%s\n' "${BINDING_LINES[@]}"
  fi
fi
```

设置 `$RECOMMEND` 和 `$REASON`（沿用旧版变量契约，向后兼容）。优先级 12 条 -> 见 `scripts/scan-state.sh` 函数体顶部注释。v2.1 synthesizer 复刻同样 13-path 决策树（路径 10-13 隐式被早期路径短路）并补充 `confidence` / `unblocked_changes` / `active_session` / `orphaned_sessions` 结构化字段。

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

## 过期状态检测（v2.0.3 提升为 runtime check）

> 该检测已下沉到 `scripts/scan-state.sh::check_stale_workflow_state()`，
> 在 `scan_state()` 末尾自动调用。AI 不再需要主动读取 `workflow-state.md`。
> 输出格式见辅助函数源码。

## Cross-Reference

- **`rddf-session`** (`skills/rddf-session.md`) — 当输出包含 `📍 No current binding` 时,可调 `skill_use("rddf-session current")` 查看完整绑定状态,或 `skill_use("rddf-session resume <rds_id>")` 接管推荐会话。详见 spec 2026-07-14。
- **ADR-0017** (`docs/adr/ADR-0017-rddf-session.md`) — rddf-session 数据模型、跨 OpenCode session 恢复语义、心跳机制的来源。
- **scan-state.sh** (`scripts/scan-state.sh`) — 推荐器底层扫描脚本;11-priority `scan_state` + v2.0.2 `scan_session_binding`。
