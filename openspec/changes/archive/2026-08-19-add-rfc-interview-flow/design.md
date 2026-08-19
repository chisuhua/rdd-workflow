## Context

当前 `approve_proposal.sh --manual --hub-issue <org/repo#N>` 强制人工先有 Hub Issue。但本应是：**审批流程 + RFC 起草合二为一**，人类在 approve 前看到"准备发什么"。

`rddf report-issue` 与 `approve_proposal.sh` 独立，需要引入"草稿层"作为中间产物。

## Goals / Non-Goals

**Goals**:

- `rfc_interview.sh` 引导式对话生成 `.rfc-draft-<name>.json`
- `rddf rfc-draft <name>` / `rddf rfc-create --from-draft <name>` 两阶段 CLI
- `rfc_draft_schema.json` v1 定义草稿必填字段
- `design_done_gate.py::check_rfc_draft` 新增门控
- 审计 trail 完整（草稿生成 / approve / Hub 创建各自留痕）

**Non-Goals**:

- 异步 Hub 创建（同步即可）
- Hub Issue 评论自动撰写（人类撰写）

## Technical Decisions

### TD-1: 草稿存储位置

**选项 A**: `.rddf/state/.rfc-draft-<name>.json` ✅
- 优点: 与现有 `.cross-repo-pending.json` 同目录，便于原子写
- 缺点: state 目录膨胀

**选项 B**: `.rddf/improvements/<name>/rfc-draft.json`
- 优点: 与 proposal 同目录
- 缺点: 跨目录原子写复杂

### TD-2: 草稿 schema

```json
{
  "version": 1,
  "proposal_name": "<name>",
  "title": "[RFC] ...",
  "stakeholders": ["org/repo-a", "org/repo-b"],
  "gate": "Design-Gate",
  "contract_impact": "Breaking-Change",
  "contract_draft_path": "<path>",
  "created_at": "2026-08-19T...",
  "created_by": "<actor>"
}
```

### TD-3: design-done 门控顺序

现有门控 → 新 `check_rfc_draft`（category=cross-repo-federation 时强制）。

门控失败时审计 trail 写 `decision=fail`（复用 ADR-0031 模式）。

## Implementation Notes

- `rfc_interview.sh` 使用 bash + read 交互（与 `approve_proposal.sh` 一致）
- 草稿 schema 校验用现有 `jsonschema` Python 库
- 草稿与 audit log 同 schema 校验路径

## References

- ADR-0032 §阶段 B
- 依赖 P0 #1 + P0 #2
