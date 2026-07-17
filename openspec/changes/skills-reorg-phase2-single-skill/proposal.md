---
SCOPE: shared
STATUS: PROPOSED
---

## Why

`skills-reorg-phase1-skeleton` 已完成（archive 2026-07-17）：每个 skill 有了独立的 `skills/<name>/{SKILL.md, scripts/, references/}` 骨架，但所有 90+ helper 文件仍平铺在 `skills/_lib/`，无法分辨谁属于哪个 skill。

本 change（Phase 2）将 **46 个**只被 1 个 skill 引用的 helper（含 `rddf-session` 的 hooks + .py 同移）从 `skills/_lib/` 移入各自 skill 的 `scripts/`。完成后 `skills/_lib/` 从 91 → ~44 文件，每个 skill 自包含其 helpers。

## What Changes

将 46 个文件移出 `skills/_lib/`，按 **ADR-0021 Decision 1+2** 分配到 per-skill `scripts/`：

| Skill | 移动文件数 | 文件 |
|-------|----------|------|
| guide | 1 | scan-state.sh |
| guide-arch | 7 | arch_env_check.sh, arch_gap_analysis.sh, arch_done_gate.sh, arch_quality_report.sh, write_arch_handoff.{sh,py,_env.py} |
| guide-plan | 9 | plan_intake.sh, plan_queue_overview.sh, plan_feature_progress.sh, plan_deps_candidates.{sh,py,_env.py}, plan_done_gate.{sh,py,_env.py} |
| guide-ship | 6 | ship_case_handler.sh, ship_plan.sh, ship_monitor.sh, ship_review.sh, ship_archive.sh, post_archive_fill.sh |
| propose | 3 | propose_change.{sh,py}, validate_baseline.py |
| execute | 8 | select_worktree.sh, update_roadmap_progress.{sh,py,_env.py}, execute_step7.{sh,py,_env.py}, tasks_writeback.sh |
| feature | 6 | feature_summary.sh, feature_graph.sh, feature_status.sh, feature_order.sh, feature_cli.py, feature_view.py |
| status | 1 | status_render_mode_a.sh |
| deps | 3 | deps_render_report.sh, deps_iteration_sync.sh, deps_output.py |
| **rddf-session** | **2** | **rddf_session.py, rddf_session_hooks.sh** *(ADR-0021 Decision 2: 同移解决 N3 自相矛盾)* |

### 路径更新（按 ADR-0021 Decision 1+3）

1. **Python imports**（74+ 处）：`from skills._lib.X import Y` → `from skills.<skill>.scripts.X import Y`
   - 给每个被迁移 skill 的 `scripts/` 加 `__init__.py`（11 个空文件）
2. **Bash source**（53+ 处）：`_lib/X.sh` → `scripts/X.sh`（或 `../_lib/` 对跨 skill 共享）
3. **测试文件 source**（~63 处）：`$REPO_ROOT/skills/_lib/X.sh` → `$REPO_ROOT/skills/<skill>/scripts/X.sh`
4. **Prose 引用**（仅 SKILL.md）：`skills/_lib/X.sh` → `scripts/X.sh`（**ADR/历史 plan 文档不变**）

### 不移动的文件（留在 `_lib/`）

跨 skill 共享：`state.sh`、`state_vector.py`、`worktree.sh`、`archive.sh`、`discover-arch-artifacts.sh`、`status_helpers.sh`、`iteration.py`、`gate.py`、`tribunal.py`、`sanitizer.py`、`memory.py`、`session_manager.py`、`agents.py`、`detectors.py`、`actions.py`、`event_log.py`、`event_types.py`、`lock.py`、`atomic_write.py`、`plugin_loader.py`、`defaults.py`、`roadmap_state.py`、`validate_delta_targets.py`、`rddf_session_binding.py`、`schemas/`

## Impact

- 47 文件移出 `_lib/`，`_lib/` 从 91 → ~44 文件
- 13 SKILL.md 的 source 行 + prose 更新
- **74+ Python imports 重写**（ADR-0021 Decision 1）
- **53+ bash source 重写**（含 4 类 sed 模式 + 1 处 readlink 手动）
- 115+ 测试文件路径更新
- INSTALL.md 推迟到 Task 7 改造（ADR-0021 Decision 4）
- ADR/历史 plan 文档**不变**（ADR-0021 Decision 3）
- `feature_*.sh` 4 处 PYTHONPATH 重算（ADR-0021 N2 fix）
- `tests/_lib/test_scan_state.bats` 7 处引用更新（Phase 1 N6 同款 lesson）
- `guide.md:41` readlink 模式手动处理（Phase 1 N1 同款 lesson）
- `feature.md` fallback 逻辑手动处理（Phase 1 N2 同款 lesson）

## Dependencies

- **前置 change**: `skills-reorg-phase1-skeleton` ✓（已完成）
- **设计依据**: `docs/adr/ADR-0021-phase2-per-skill-helper-migration.md`（本次新增）
- **后续 change**: `skills-reorg-phase3-core`（重组剩余 `_lib/` 共享文件结构）