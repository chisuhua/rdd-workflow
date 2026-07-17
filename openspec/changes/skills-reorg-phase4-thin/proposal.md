---
SCOPE: shared
STATUS: PROPOSED
---

## Why

经过 Phase 1-3，目录结构已经清晰，但 SKILL.md 文件仍然很大（guide-ship.md ~650 行, guide-arch.md ~670 行等）。PKGM-Wiki 的 SKILL.md 平均 200-400 行，几乎不含内联代码。

本 change 将剩余的 inline bash/Python 代码从 SKILL.md 移入各 skill 的 `scripts/`，并为 key skill 添加 `references/` LLM 参考文档。

## What Changes

### 4A: 剩余内联代码提取

| SKILL.md | 提取目标 | 估计行数 |
|----------|---------|---------|
| guide-ship.md | Phase 5 loop check (L650+) → `scripts/ship_done.sh` | ~30 |
| guide-ship.md | Phase 2 分离执行 echo (L192-215, L339-356) → `scripts/ship_execute_echo.sh` | ~40 |
| guide-ship.md | Phase 4 清理 (L610+) → `scripts/ship_cleanup.sh` | ~30 |
| guide-arch.md | roadmap init/status/gate-report 交互模板 → `scripts/arch_roadmap_menu.sh` | ~50 |
| guide-plan.md | propose/create 交互 → `scripts/plan_propose_menu.sh` | ~40 |
| status.md | 归档交互 → `scripts/status_archive_menu.sh` | ~30 |

总计 ~220 行移出 SKILL.md → ~120 行新 helper。

### 4B: 创建 references/ LLM 参考文档

每个 skill 的 `references/` 从 `docs/` 中摘取相关上下文：

| Skill | references/ 内容 |
|-------|-----------------|
| guide-arch | `adr-format.md` (ADR-0000 模板约定), `arch-quality-gate.md` (gate 检查清单) |
| guide-ship | `worktree-guide.md` (worktree 操作指引), `archive-flow.md` (归档流程) |
| propose | `proposal-format.md` (proposal-suggestions JSON 格式) |
| deps | `deps-analysis-guide.md` (依赖分析规则) |
| execute | `tdd-5-steps.md` (TDD 5 步结构) |

### 4C: 清理

- 更新 `CHANGELOG.md` 记录 Phase 1-4 完成
- 更新 `AGENTS.md` 中的目录结构描述
- 确认 `_lib/state.sh` 的 STUB 状态（AGENTS.md 称"无 production 调用方"但 `plan_queue_overview.sh` 实际 source 它）

## Impact

- 所有 SKILL.md 目标 ≤ 300 行（当前平均 480 行）
- `references/` 让 LLM 执行技能时有结构化参考文档,减少 SKILL.md 内重复内容
- 无路径断链风险（提取遵循现有 Round A/B/C 模式）

## Dependencies

- **前置 change**: `skills-reorg-phase3-core`（目录结构必须稳定）
- **无后续 change**: 此为系列最后一个 change