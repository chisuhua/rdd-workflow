---
id: feat-fix-archive-gaps-v2
kind: feature
status: done
phase_refs: [phase-1, phase-2, phase-3, phase-4]
主题: 第二波归档治理改进（ADR 索引自动同步 / CHANGELOG-USAGE 同步 / verifier-archive-gate 边界明确化 / 第 3 波 doc drift 清理）
---

## 概述

2026-08-28 HANDOFF.md Phase D 评估 4 个 P2 deferred 提案后发现：3 个提案被本 session 工作直接命中（CHANGELOG v3.1 → USAGE.md 不同步、AGENTS.md 加 ADR 列表时 README 表格手写过时、`rddf rdd-verify --re-verify-archived` 是 print-only stub），1 个（bypass-audit-mechanism）维持 deferred 留作 v3.2 follow-up。

本 feature 跟踪 **4 个升级 P2→P1 提案** 的实施（phase-1/2/3 由 2026-08-28 升级，phase-4 由 2026-09-09 第 3 波审计新增）：

| 提案 | 来源 | 优先级 | 依赖 | ship 时间 |
|---|---|---|---|---|
| `adr-index-auto-sync` | 2026-08-26 audit | P2→P1 | 无（基础） | 2026-08-28 (commit `4900db4`) + 2026-09-11 (`73fdff4` 重新生成含 ADR-0049/0050) |
| `changelog-usage-sync` | 2026-08-26 audit | P2→P1 | 无（独立） | 2026-08-28 (commit `d887610`) |
| `verifier-archive-gate-clarification` | 2026-08-26 review | P2→P1 | 依赖 adr-index-auto-sync（ADR-0035 需 README 同步） | 2026-09-11 (commit `c5b45b4` + ADR-0035 文档) |
| `fix-doc-drift-followup-3` | 2026-09-09 第 3 波 audit | P1 | 依赖 `docs-v4-sync-followup-v2` 待归档 | 2026-09-09 (commits `0ba5ae4` + `2b39d6b`) |

bypass-audit-mechanism（统一 audit log）维持 deferred，价值清晰但当前 SKIP 使用频率低，留作 v3.2 跟 hub-federation governance 一起做。

> **2026-09-22 状态同步收尾**：4 个 phase 在物理层全部 ship（per `improvement-approved.md` "已实施"段 + 代码/测试/ADR/文档存在证据）；本 commit 仅做 frontmatter `status: proposed → done` 同步 + prose 段描述对齐，未引入新代码改动。`rddf roadmap validate-fragments` → ✅ All checks passed。

## 跨阶段拆分

### phase-1: adr-index-auto-sync ✅ shipped 2026-08-28

- ✅ 新建 `_lib/adr_index_generator.py`：扫描 `docs/adr/ADR-*.md`，提取 frontmatter（status, date, decider），自动生成 Markdown 表格（3514 bytes）
- ✅ `docs/adr/README.md` 表格改为生成产物（保留手写头注释 + `<!-- ADR_INDEX_START --> ... <!-- ADR_INDEX_END -->` 段）
- ✅ `tests/integration/test_adr_index.bats` 强制验证 README 表格 == 磁盘 ADR 列表（2002 bytes）
- ⏸ AGENTS.md line 148 "关键 ADR 列表" 接入：未实施（feature fragment 不在本 ship 范围，留作后续 follow-up）
- ⏸ pre-commit hook（新增/重命名 ADR 时自动重生成 README）：未实施（可选）

### phase-2: changelog-usage-sync ✅ shipped 2026-08-28

- ✅ USAGE.md 顶部加 `<!-- VERSION_BANNER_START --> ... <!-- VERSION_BANNER_END -->` 占位符（已确认存在）
- ✅ 新建 `_lib/sync_usage_banner.py`：从 `package.json` version + CHANGELOG latest tag 生成 banner（2660 bytes）
- ⏸ pre-commit hook（可选）：CHANGELOG.md 改动时强制 USAGE.md banner 更新：未实施（可选）
- ✅ `tests/integration/test_changelog_usage_sync.bats` 基础一致性测试（1183 bytes）

### phase-3: verifier-archive-gate-clarification ✅ shipped 2026-09-11

- ✅ 新建 `docs/adr/ADR-0035-verifier-archive-gate-boundary.md`：明确双轨（normal path vs fallback）边界（3693 bytes）
- ✅ `_lib/archive.sh::archive_gate_check` 顶部注释引用 ADR-0035 §1
- ✅ `STRICT_AC_GATE=yes` 行为写进 README.md "紧急跳过" 章节
- ✅ 修 `rddf rdd-verify --re-verify-archived` 真实调用 ac-verifier（消除 print-only stub）
- ✅ 修 `skills/ac-verifier/scripts/ac_verifier.sh:71`：支持 archive 目录 proposal.md 路径

### phase-4: fix-doc-drift-followup-3 ✅ shipped 2026-09-09（第 3 波审计新增）

> 来源：2026-09-09 rdd-doctor + 3 agent 并行审计。前两批（`fix-doc-drift-v4-architecture` 已 archived，`docs-v4-sync-followup-v2` 已归档）覆盖后仍有 12 文件、35 处 active skill_use 或 stage list 漂移未处理。
> **优先级**: P1

- ✅ **`skills/guide/SKILL.md`** 30+ 处 stale `guide-*` invocations（推荐器坏掉，**CRITICAL**）
- ✅ 创建 **`docs/migration/v3-to-v4.md`**（被 `docs/ONBOARDING.md:375` 显式引用但文件缺失，8793 bytes）
- ✅ 9 个子技能 SKILL.md：`execute`/`status`/`rddf-session`/`rdd-verifier`/`rdd-env-check`/`add-improve`/`feature`/`deps`/`sync-hub`/`openspec-gate` 的描述漂移
- ✅ `README.md` L13-19 npm install v1.x/v2.0-beta → v4.0.0
- ✅ Test：扩展 `tests/integration/test_v4_doc_drift_contracts.bats` 新增 Test 16-19
- ✅ 验收：8 项 AC（含 doctor CRITICAL ≤ 6 regression gate）

## 验收标准

- [x] phase-1 全部 AC：见 `.rddf/improvements/adr-index-auto-sync.md` §验收（8 项）— 已 ship (commits `4900db4` + `73fdff4`)
- [x] phase-2 全部 AC：见 `.rddf/improvements/changelog-usage-sync.md` §验收（5 项）— 已 ship (commit `d887610`)
- [x] phase-3 全部 AC：见 `.rddf/improvements/verifier-archive-gate-clarification.md` §验收（5 项）— 已 ship (commit `c5b45b4`)
- [x] phase-4 全部 AC：见 `.rddf/improvements/fix-doc-drift-followup-3.md` §验收（8 项）— 已 ship (commits `0ba5ae4` + `2b39d6b`)
- [x] `rddf roadmap validate-fragments` → ✅ All checks passed (R1-R8 全合规)
- [x] `rddf rdd-verify --re-verify-archived` 对所有 archived changes 真实验证（不再 print-only）

## 与其他 feature 的关系

- **feat-fix-audit-findings**（proposed，phase-1..4，TBD 占位）：本 feature 是其后的第二波归档治理改进。两者合并形成"2026-08-26 audit 全套 follow-up"覆盖。**关系更新**：本 feature 已 done；feat-fix-audit-findings 的 4 phase TBD 是更早一批的占位（其中 4 项子提案 `fix-parametrize-planner-feedback-id-date` / `fix-rebuild-adr-index-for-0049-0050` / `fix-update-doctor-main-category-count` / `fix-remove-stale-filled-at-regression-test` 已于 2026-09-10 ship，归入 `improvement-approved.md` "已实施" 段）
- **fix-doc-drift-v4-architecture**（f4d675b，已 archived）+ **docs-v4-sync-followup-v2**（已归档）：phase-4 的依赖前置；本提案不与前两批重叠
- **bypass-audit-mechanism**：维持 deferred（v3.2 follow-up），与 hub-federation governance 一起做

## 备注

- 4 个提案已在 `.rddf/improvements/` 中存在（phase-1/2/3 升级 P2→P1；phase-4 新增 P1）
- 用户在 HANDOFF.md Phase D 评估后批准 phase-1/2/3 升级（2026-08-28）
- phase-4（fix-doc-drift-followup-3）由 2026-09-09 第 3 波 audit 新增
- **实际 ship 时序**（与 fragment 拆分一致）：phase-1 (08-28) → phase-2 (08-28) → phase-3 (09-11) → phase-4 (09-09)
- **2026-09-22 收尾动作**：frontmatter `status: proposed → done` + 4 个子提案 frontmatter 状态字段同步 + prose 段描述对齐 + `rddf roadmap validate-fragments` 校验通过