---
id: feat-fix-archive-gaps-v2
kind: feature
status: proposed
phase_refs: [phase-1, phase-2, phase-3]
主题: 第二波归档治理改进（ADR 索引自动同步 / CHANGELOG-USAGE 同步 / verifier-archive-gate 边界明确化）
---

## 概述

2026-08-28 HANDOFF.md Phase D 评估 4 个 P2 deferred 提案后发现：3 个提案被本 session 工作直接命中（CHANGELOG v3.1 → USAGE.md 不同步、AGENTS.md 加 ADR 列表时 README 表格手写过时、`rddf rdd-verify --re-verify-archived` 是 print-only stub），1 个（bypass-audit-mechanism）维持 deferred 留作 v3.2 follow-up。

本 feature 跟踪 3 个升级 P2→P1 提案的实施：

| 提案 | 来源 | 优先级 | 依赖 |
|---|---|---|---|
| `adr-index-auto-sync` | 2026-08-26 audit | P2→P1 | 无（基础） |
| `changelog-usage-sync` | 2026-08-26 audit | P2→P1 | 无（独立） |
| `verifier-archive-gate-clarification` | 2026-08-26 review | P2→P1 | 依赖 adr-index-auto-sync（ADR-0035 需 README 同步） |

bypass-audit-mechanism（统一 audit log）维持 deferred，价值清晰但当前 SKIP 使用频率低，留作 v3.2 跟 hub-federation governance 一起做。

## 跨阶段拆分

### phase-1: adr-index-auto-sync

- 新建 `_lib/adr_index_generator.py`：扫描 `docs/adr/ADR-*.md`，提取 frontmatter（status, date, decider），自动生成 Markdown 表格
- `docs/adr/README.md` 表格改为生成产物（保留手写头注释 + `<!-- ADR_INDEX_START --> ... <!-- ADR_INDEX_END -->` 段）
- `tests/integration/test_adr_index.bats` 强制验证 README 表格 == 磁盘 ADR 列表（pre-existing baseline 失败转 PASS）
- AGENTS.md line 148 "关键 ADR 列表" 也接入（限定"已采纳"+"已实施"）
- 可选：pre-commit hook（新增/重命名 ADR 时自动重生成 README）

### phase-2: changelog-usage-sync

- USAGE.md 顶部加 `<!-- VERSION_BANNER_START --> ... <!-- VERSION_BANNER_END -->` 占位符
- 新建 `_lib/sync_usage_banner.py`：从 `package.json` version + CHANGELOG latest tag 生成 banner
- pre-commit hook（可选）：CHANGELOG.md 改动时强制 USAGE.md banner 更新
- `tests/integration/test_changelog_usage_sync.bats` 基础一致性测试

### phase-3: verifier-archive-gate-clarification

- 新建 `docs/adr/ADR-0035-verifier-archive-gate-boundary.md`：明确双轨（normal path vs fallback）边界
- `_lib/archive.sh::archive_gate_check` 顶部注释引用 ADR-0035 §1
- `STRICT_AC_GATE=yes` 行为写进 README.md "紧急跳过" 章节
- 修 `rddf rdd-verify --re-verify-archived` 真实调用 ac-verifier（当前 line 245-249 是 print-only stub）
- 修 `skills/ac-verifier/scripts/ac_verifier.sh:71`：支持 archive 目录 proposal.md 路径
- docs/adr/README.md ADR 列表更新（依赖 phase-1 的 adr-index-auto-sync）

## 验收标准

- [ ] phase-1 全部 AC：见 `.rddf/improvements/adr-index-auto-sync.md` §验收（8 项）
- [ ] phase-2 全部 AC：见 `.rddf/improvements/changelog-usage-sync.md` §验收（5 项）
- [ ] phase-3 全部 AC：见 `.rddf/improvements/verifier-archive-gate-clarification.md` §验收（5 项）
- [ ] `./test.sh --full --regression` 通过（bypass-audit-mechanism 仍为 deferred 不影响本 feature）
- [ ] `rddf rdd-verify --re-verify-archived` 对所有 archived changes 真实验证（不再 print-only）

## 与其他 feature 的关系

- **feat-fix-audit-findings**（active，phase-1..4）：本 feature 是其后的第二波归档治理改进。两者合并形成"2026-08-26 audit 全套 follow-up"覆盖
- **bypass-audit-mechanism**：维持 deferred（v3.2 follow-up），与 hub-federation governance 一起做

## 备注

- 3 个提案已在 `.rddf/improvements/` 中存在（升级 P2→P1）
- 用户在 HANDOFF.md Phase D 评估后批准升级（2026-08-28）
- 预计 ship 时序：phase-1 → phase-2 → phase-3（顺序由依赖关系决定）