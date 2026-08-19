# add-rfc-interview-flow

**阶段**: v2.2
**分类**: core-impl
**类型**: feature
**特性**: __ungrouped__

## Why

当前 `approve_proposal.sh --manual --hub-issue <org/repo#N>` 强制人工先创建 Hub Issue，再回填 URL。两步流程让人类在多个工具间跳转，且审批时**看不到**"准备发什么 RFC"。`rddf report-issue` 与 `approve_proposal.sh` 完全独立。

需要引导式对话，让人类在 approve 前看到"准备发什么"，可以编辑草稿后再实际发。

## What Changes

**In Scope**:

- 新增 `skills/guide-design/scripts/rfc_interview.sh`：引导式对话（title / stakeholders / gate / contract-impact / Hub Issue 占位），生成 `.rddf/state/.rfc-draft-<name>.json`
- 拆分 `rddf report-issue` 为两阶段：`rddf rfc-draft <name>` 生成草稿 → 人类编辑 → `rddf rfc-create --from-draft <name>` 实际创建
- 新增 `skills/_lib/schemas/rfc_draft_schema.json` v1（定义草稿必填字段）
- `design_done_gate.py::check_rfc_draft`：category=cross-repo-federation 必须存在 `.rfc-draft-<name>.json`，且 schema 校验通过
- bats + unit test

**Out of Scope**:

- Hub Issue 自动回复（保持人类撰写评论）
- 草稿版本控制（依赖 `.rddf/state/` 原子写）

## Impact

- **能力**: 审批流程与 RFC 起草合二为一
- **兼容**: 不破坏现有 `rddf report-issue` 命令（新增 `rfc-draft` / `rfc-create` 子命令）
- **风险**: 中. design-done 门控新增会阻断现有 approve 流程；需配套 fallback 路径

## Acceptance

- AC-1: `rddf rfc-draft <name>` 交互生成 `.rfc-draft-<name>.json`
- AC-2: `rddf rfc-create --from-draft <name>` 创建 Hub Issue 并回填 URL 到草稿
- AC-3: `design-done` 门控对 category=cross-repo-federation 检查草稿存在性 + schema 校验
- AC-4: 缺失草稿时 design-done 阻断 + 审计 trail 写 `decision=fail`
- AC-5: bats + unit test 全绿
- AC-6: `./test.sh --full --regression` 不新增失败
