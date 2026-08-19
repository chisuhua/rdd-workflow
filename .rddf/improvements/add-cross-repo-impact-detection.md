# add-cross-repo-impact-detection

**阶段**: v2.2
**分类**: core-impl
**类型**: feature
**特性**: __ungrouped__

## Why

ADR-0030/0032 确立 Hub 联邦架构后，开发者经常在提案后期才意识到需要发起 Hub RFC。当前 `add-improve` 仅生成 head 字段（阶段/分类/类型/特性），不分析提案是否触碰 Hub `contracts/*.yaml`。导致：重复劳动（提案被 approve 后才发现要补 RFC）；跨仓契约变更遗漏（无 AI 提示）；stakeholders 列表需手工整理。

参考 e2e 测试 `tests/integration/test_cross_repo_e2e_real.bats` (13 cases)，基础设施已可用，需要 AI 辅助层补齐体验。

## What Changes

**In Scope**:

- 新增 `skills/add-improve/scripts/detect_cross_repo_impact.py`：扫描 `.rddf/improvements/<name>.md` 正文，匹配 Hub `contracts/*.yaml` 文件名/字段名/路径关键词
- 自动建议 `category=cross-repo-federation`（基于匹配结果）
- 自动建议 `stakeholders` 列表（解析 Hub 契约 ownership 注释/元数据）
- 集成到 `add-improve` 流程：检测到跨仓时提示人类 owner
- 新增 bats test `tests/integration/test_cross_repo_impact_detection.bats`：覆盖 4 个场景（无匹配/单契约匹配/多契约匹配/误报）
- 单元测试 `tests/unit/test_detect_cross_repo_impact.py`：≥ 6 个 case

**Out of Scope**:

- 契约内容 diff（由 `rddf contract-check` 已实现）
- Hub Projects V2 字段自动填写（依赖 `rdd-hub-bootstrap`）
- Stakeholder 端发现新 RFC（由 P2 `add-stakeholder-rfc-bootstrap` 在 v2.2+ 渐进）

## Impact

- **能力**: 提案生成阶段 AI 辅助识别跨仓变更
- **兼容**: 不破坏既有 `add-improve` 行为（仅新增 step，不替换）
- **风险**: 低. 检测逻辑隔离，可单独开关

## Acceptance

- AC-1: `add-improve <name>` 在提案正文含 `auth/` 时，输出 `⚠️ 检测到 Hub 契约: contracts/auth-v2.yaml，建议发起 RFC`
- AC-2: `add-improve <name>` 在多 Hub 契约匹配时输出 stakeholders 建议列表
- AC-3: 不匹配时不输出任何提示（不引入噪声）
- AC-4: `tests/integration/test_cross_repo_impact_detection.bats` ≥ 4 case 全绿
- AC-5: `tests/unit/test_detect_cross_repo_impact.py` ≥ 6 case 全绿
- AC-6: `./test.sh --full --regression` 不新增失败
