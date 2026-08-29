# phase-2-general-20260829063814

## Why

`ADR-0025` (design proposal creation) + `ADR-0002` (goal-driven interaction modes) 已建模,但当前 guide-design审批只有 `y/n/d/s/a` 单键决策,无法处理模糊提案(范围不清/验收缺失)。`skills/guide-design/scripts/rfc_interview.sh` 已存在但未启用为默认流程。**Why now**: 多方对称(#9)场景需要结构化审批,纯单键决策不足。

## What Changes

**In Scope**:

- **Out Scope**: NLP 情感分析;自动改写提案

### 关键场景

- GIVEN 提案缺 ## Acceptance WHEN design_proposal_review 加载
  THEN rfc_interview.sh 触发,生成 acceptance checklist 草稿,用户确认后追加
- GIVEN 提案 In Scope 涉及 8 个文件 (超过阈值 5)
  WHEN 审查加载
  THEN 自动询问是否拆分 proposal,推荐拆分为2 子提案

**Out of Scope**:

- (no items specified)

## Capabilities

- MUST: 面试状态持久化 `.rddf/state/.rfc-interview-{name}.json` (断点续传)
- SHOULD: 与现有 `question` 工具协同 (模糊度高才用 question,否则直接 y/n)

## Impact

- MUST NOT: 强制修改提案内容 (仅生成建议,用户确认)

## Acceptance

- 5 个测试用例: 缺验收 / 范围超限 / 多 stakeholder / 内容矛盾 / 含糊措辞
- rfc-interview 中断恢复 (删除 .json 后重跑) 测试通过
- 至少 3 个现有 backlog 提案能用此流程从延迟 → 活跃

