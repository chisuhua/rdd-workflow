---
SCOPE: shared
STATUS: PROPOSED
---

## Why

经过 Phase 1-3，目录结构已经清晰，但 SKILL.md 文件线数仍然偏高（前 7 个文件平均 ~601 行）。Phase 3 遗留了 3 个断裂路径，需要在 Phase 4 修复。剩余的内联 bash 代码块可以进一步提取，减少 SKILL.md 体积。

## What Changes

### 4A: 修复 Phase 3 遗留断裂路径（P0）

| 文件 | 问题 | 修复 |
|------|------|------|
| `guide-plan/scripts/plan_queue_overview.sh:15` | `source ./state.sh` 路径断裂 | → `../../_lib/state.sh` |
| `propose/SKILL.md:507` | `../_lib/validate_baseline.py` 文件已移走 | → `scripts/validate_baseline.py` |
| `guide-ship/SKILL.md` L122/426/482 | `$REPO_ROOT` 未定义变量 | → `$(dirname "${BASH_SOURCE[0]:-$0}")` 统一模式 |

### 4B: 提取剩余内联代码

| SKILL.md | 提取目标 | 节省 |
|----------|---------|------|
| guide-ship.md | Phase 5 loop check (L650+) → `scripts/ship_done.sh` | ~30 |
| guide-ship.md | Phase 4 清理 (L610+) → `scripts/ship_cleanup.sh` | ~30 |
| guide-arch.md | roadmap init/status/gate-report 交互 → `scripts/arch_roadmap_menu.sh` | ~50 |
| guide-plan.md | propose/create 菜单 → `scripts/plan_propose_menu.sh` | ~40 |
| status.md | 归档交互 → `scripts/status_archive_menu.sh` | ~30 |
| **共享提取** | 各文件重复的 case handler → `scripts/_case_handler.sh` | ~80 |
| **共享提取** | ACTIVE_CHANGES 表渲染 → `scripts/render_active_changes.sh` | ~60 |

总计 ~320 行移出 SKILL.md。

### 4C: 修正 state.sh STUB 标签

AGENTS.md 称 `state.sh` 为 "STUB (无 production 调用方)"，但实际有 6 个活跃函数（`safe_python_json`, `read_suggestions`, `write_suggestions`, `count_pending_suggestions` 等），被 propose、roadmap、status、plan_queue_overview 等 4+ 消费者调用。修正此标签。

### 4D: 清理

- 更新 `AGENTS.md` 中目录结构描述 + state.sh 标签修正
- 扫描并修复 `_lib/` 旧路径残留引用
- 更新 `CHANGELOG.md` 为 v2.0.8

## Impact

- 所有 SKILL.md 目标 ≤ 450 行（当前平均 ~601 行，降低 ~25%）
- 共享 case handler 消除 6-8 处重复
- 3 个断裂路径修复确保 Phase 3 完成后运行时完整
- 无路径断链风险（提取遵循 Round A/B/C 成熟模式）

## Dependencies

- **前置 change**: `skills-reorg-phase3-core`（目录结构必须稳定）
- **无后续 change**: 此为系列最后一个 change