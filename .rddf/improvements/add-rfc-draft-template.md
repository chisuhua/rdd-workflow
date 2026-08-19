# add-rfc-draft-template

**阶段**: v2.2
**分类**: core-impl
**类型**: feature
**特性**: __ungrouped__

## Why

当前 `.rddf/improvements/<name>.md` 模板 head 字段（阶段/分类/类型/特性）不强制跨仓 5 段正文结构（动机/契约草案/利益相关方/兼容策略/回滚）。开发者常省略"回滚方案"和"兼容策略"，Hub 端 Stakeholder 评估 RFC 时缺乏关键信息。

参考 `2026-08-19-fix-federation-gh-cli-integration` proposal.md 的"Acceptance" 节，发现 5 段结构清晰度远高于仅"动机"。

## What Changes

**In Scope**:

- `skills/add-improve/scripts/detect_cross_repo_impact.py` 在检测到跨仓后自动生成 5 段模板（插入到 `.rddf/improvements/<name>.md` 末尾）
- `report_issue_rfc.py` 接受 `--contract-draft <path>` 参数，将契约草案 base64 内联到 Hub Issue body
- 自动填充模板字段：`stakeholders` 来自检测结果、`gate=Design-Gate`、`contract-impact=Breaking-Change` 默认
- 单元测试 + bats test

**Out of Scope**:

- 模板内容的人工编辑（用户自行修改）
- Hub Issue 模板（GitHub Issue template 是 GitHub 端配置）

## Impact

- **能力**: 跨仓提案结构标准化，Hub 端评估时信息完整
- **兼容**: 不影响非跨仓提案
- **风险**: 极低. 模板生成是附加 step

## Acceptance

- AC-1: 检测到跨仓后 `.rddf/improvements/<name>.md` 末尾自动含 5 段占位（动机/契约草案/利益相关方/兼容策略/回滚）
- AC-2: `rddf report-issue --contract-draft <path>` 创建的 Hub Issue body 含 base64 编码契约草案
- AC-3: 模板字段自动填充正确（stakeholders 来自检测结果）
- AC-4: bats + unit test 全绿
- AC-5: `./test.sh --full --regression` 不新增失败
