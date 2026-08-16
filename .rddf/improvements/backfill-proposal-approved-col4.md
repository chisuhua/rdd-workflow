# backfill-proposal-approved-col4

**优先级**: P2 | **来源**: rdd-doctor 诊断 2026-08-16 — proposal-table 类别 150 WARNING
**阶段**: v2.2 | **分类**: quality
**类型**: debt

## 架构依据

- **rdd-doctor proposal-table 类别**(已实施): 检测 `proposal-approved.md` 表格行 column count 与预期(4 列)的一致性
- **rdd-workflow proposal-suggestions.md format 文档**(已采纳): 表格格式必须严格 4 列(提案 | 优先级 | 来源 | 添加时间)
- **现状缺陷**: `proposal-approved.md` 存在 column drift(150 处 WARNING),可能是早期限表格格式不严格,后续追加行格式漂移导致 rdd-doctor 无法精确解析
- **类比 anchor**: 与 `fix-doc-truth-sync` (P0 修复 INSTALL.md / package.json skills count 不一致) 同类问题 — 文档/索引 drift

## 范围

- **In Scope**:
 - 检查 `proposal-approved.md` 中所有 4-列格式行,确认 column drift 的真实位置
 - 修复任何确实存在的 3-列或 5-列行(添加缺失列或合并多余列)
 - 增强 `rdd-doctor` 的 `proposal-table` check,输出 `severity: CRITICAL` 当列数 != 4(从 WARNING 升级)
 - 在 CI `.github/workflows/test.yml` 的"断言质量门控"步骤调用 `rddf doctor --category proposal-table --quiet`,失败时 exit 1
- **Out Scope**:
 - NOT backfill `.rddf/plans/*` 中的老 plans(63 个 plan-tdd WARNING 属 noise)— 这是另一个独立 issue
 - NOT 修改 `proposal-suggestions.md`(结构正确,刚被 sync-approved-to-suggestions 重构过)
 - NOT 修改 docs/adr/(无相关 ADR 涉及)

## 关键场景

- GIVEN proposal-approved.md 中某行有 3 列(缺优先级/来源/添加时间之一)
- WHEN `rddf doctor --category proposal-table` 运行
- THEN 输出 `CRITICAL: row N has 3 columns, expected 4` 并 exit 非零

- GIVEN CI pipeline 在 plan 完成后跑质量门控
- WHEN 检测到 proposal-table CRITICAL
- THEN workflow 在 archive 前阻断,要求手动修复

## 技术约束

- MUST 保留所有现有行的内容,只调整 column 结构(不修改提案名称/优先级/日期)
- MUST 保持 Markdown 表格 header 与 row separator 对齐
- MUST NOT 引入新的列(始终 4 列:`提案 | 优先级 | 来源 | 添加时间`)
- SHOULD 在 rdd-doctor 升级后跑一次全量回归,确认无其他检查误报

## 验收标准

- `rddf doctor --category proposal-table --quiet` 退出 0(proposal-approved.md 零 drift)
- `rddf doctor --json` 的 `findings[].severity` 中 `proposal-table` 类别无 WARNING/CRITICAL
- `.github/workflows/test.yml` 包含 `rddf doctor --category proposal-table` 步骤
- `tests/integration/test_proposal_approved_format.bats`(新增)覆盖 column drift 检测