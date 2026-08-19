## Context

ADR-0032 §阶段 A 明确"提案生成含跨仓分析"作为 v2.2 第一阶段。当前 `add-improve` 是黑盒（仅生成 4 个 head 字段），开发者需手工识别跨仓。AI 辅助层是空缺。

e2e 测试 13 cases 验证 Hub 通信基础（RFC 上行/契约下行/状态轮询）已可用，但**提案生成层未自动化**。

## Goals / Non-Goals

**Goals**:

- `detect_cross_repo_impact.py` 独立脚本，可单独调用
- 集成到 `add-improve`（不改主流程，作为附加 step）
- 误报率 < 10%（人工标注 10 个测试用例验证）
- 单元/集成测试覆盖 4 个核心场景

**Non-Goals**:

- 替换 `add-improve` 主流程
- 自动填充 `proposal-approved.md`（由人工 approve 触发）
- 跨仓库 call graph 分析（依赖静态分析，超出 P0 范围）

## Technical Decisions

### TD-1: 检测方式 — grep vs AST

**选项 A**: grep 简单匹配（关键词、字段名）✅
- 优点: 实现简单，误报率低
- 缺点: 无法处理嵌套结构

**选项 B**: AST 解析 proposal.md
- 优点: 精确
- 缺点: 实现重，依赖 markdown parser

**选 A**: 提案文本是 markdown 散文，关键词/字段名匹配已够用。复杂解析留给后续 P1。

### TD-2: Hub 契约元数据存储

**选项 A**: 在 Hub `contracts/<name>.yaml` 头部加 `x-owners:` 注释
**选项 B**: 独立 `.rddf/state/hub-contracts-meta.json`

**选 A**: 契约文件自带 ownership 信息，符合 OpenAPI 扩展字段惯例。

### TD-3: 自动建议 category

**选项 A**: 检测到跨仓时仅输出建议，让人类确认
**选项 B**: 直接修改 `.rddf/improvements/<name>.md` head 字段

**选 A**: 保持人类决策权（符合 ADR-0031），AI 不自动写入 head。

## Implementation Notes

- `RDDF_HUB_REPO` env var 必填（继承）
- 检测结果输出到 stderr（不污染 stdout）
- 失败静默（不阻塞 `add-improve` 主流程）
- 检测完成后输出 markdown 报告 `.rddf/state/.cross-repo-detection-<name>.json`

## References

- ADR-0032 §阶段 A
- `2026-08-19-fix-federation-gh-cli-integration` (Hub 通信基础)
- `tests/integration/test_cross_repo_e2e_real.bats` (e2e baseline)
