# add-cross-repo-state-schemas

## Why

**背景**

ADR-0030 + 7 个相关提案涉及 **6 个新 state 文件**（`.rddf/state/` 下）。当前 rdd-workflow 已通过 `_lib/schemas/` 集中管理 schema（参考 ADR-0016 arch_handoff_schema.json v1 模式）。如果 6 个新文件无 schema：

1. 各提案独立实现可能导致字段不一致
2. 跨提案读写同一文件时格式漂移
3. CI 校验缺失（参考 rdd-doctor 检查现有 schema 漂移）
4. 后续重构成本激增

**本提案填补**：在 `_lib/schemas/` 下新增 6 个 schema 文件，提供 SSOT（Single Source of Truth）。

**架构依据**（引用 ADR-0016）：
> 所有 handoff / state 文件必须在 `_lib/schemas/<name>_schema.json` 下定义 schema，版本字段标识 v1/v2，schema 变更必须 bump version。

**已有能力（集成而非替换）**：
- `_lib/schemas/arch_handoff_schema.json` v1 — 当前参考模板
- `_lib/schemas/iteration_schema.json` v6 — schema 演进模式
- `_lib/schemas/feature_view_schema.json` v1 — 视图类型 schema
- `_lib/rddf-doctor` — schema 漂移检测（rdd-doctor skill）

## What Changes

**In Scope**:

- 新增 6 个 schema 文件到 `_lib/schemas/`：
- `cross_repo_pending_schema.json` v1 — Hub Issue 挂起状态
- `cross_repo_audit_schema.json` v1 — 跨项目决策审计
- `mcp_trace_schema.json` v1 — MCP 调用追踪
- `contract_cache_schema.json` v1 — 契约版本缓存
- `cross_repo_deps_cache_schema.json` v1 — 跨仓库依赖缓存
- `hub_metrics_schema.json` v1 — Hub 运行时指标
- 升级 `_lib/schemas/README.md`（或新增）列出 6 个新 schema + 引用 ADR-0030
- 升级 `rdd-doctor` (如有 `--schema` 模式) 检查新文件
- 新增 `tests/unit/test_cross_repo_schemas.py` — 6 个 schema 的 jsonschema 验证单元测试
- 新增 `docs/schemas/cross-repo-schemas.md` — 6 个 schema 字段语义文档

### 关键场景

### 场景 1：Schema 校验（按提案写入时）

```python
# skills/cross-repo-protocol/mcp_client.py (示例, 属 Step 3 实施)
import json
from jsonschema import validate

# 写入 .rddf/state/.mcp-trace.jsonl 时
with open(".rddf/state/.mcp-trace.jsonl", "a") as f:
    record = {
        "timestamp": "2026-08-15T16:00:00Z",
        "direction": "spoke-to-hub",
        "tool_name": "hub_create_issue",
        "actor_repo": "org/repo-frontend",
        "args_hash": "abc123...",
        "result_status": "success"
    }
    validate(record, MCP_TRACE_SCHEMA_V1)  # 来自 _lib/schemas/
    f.write(json.dumps(record) + "\n")
```

### 场景 2：rdd-doctor 漂移检测

```bash
$ rddf doctor --category state
# 实际行为：
📋 Schema 校验报告

  现有 8 个 schema + 6 个新 schema = 14 个
  ✅ arch_handoff_schema.json v1 — 10 个 .rddf/state/*.json 验证通过
  ✅ ...
  ⚠️  cross_repo_audit_schema.json v1 — 0 个 .rddf/state/.cross-repo-audit.jsonl (新增)
  ⚠️  mcp_trace_schema.json v1 — 0 个 .rddf/state/.mcp-trace.jsonl (新增)
  
  决策: 6 个新 schema 已声明但无对应文件 → CRITICAL (实施未开始)
```

### 场景 3：Schema 版本演进

```bash
# 未来 v2 演进（v1 → v2）
# 1. 新增 _lib/schemas/cross_repo_audit_schema_v2.json
# 2. 旧 v1 文件保留 6 个月过渡期
# 3. rdd-doctor 警告 v1 文件仍在使用
# 4. 迁移完成后删除 v1
```

**Out of Scope**:

- **不实现** 各 state 文件的读写逻辑（属于各提案的实施步骤）
- **不修改** 现有 8 个 schema（arch_handoff / design_handoff / plan_handoff / iteration / sessions / deps_analysis / config / feature_view）
- **不集成** 6 个新 schema 到 `gate.py` 插件（属于后续 features）

## Capabilities

- **字段命名**：snake_case（与现有 schema 一致）
- **时间字段**：统一 `format: date-time`（ISO-8601）
- **Hub Issue 引用**：统一 pattern `^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+#[0-9]+$`
- **可扩展性**：使用 `additionalProperties: true` 允许后续字段添加
- **版本字段**：每个 schema 必须有 `version` 字段（const）
- **跨 schema 引用**：startship 格式（`hub_issue` pattern）统一

## Impact

- (no items specified)

## Acceptance

- [ ] 验证已有 6 个 schema 文件位于 `_lib/schemas/`，并输出与提案规格的 diff review；若缺失才创建，不得覆盖已有定义
- [ ] 每个 schema 含 `version` 字段（const）和 `$id` 唯一标识
- [ ] `tests/unit/test_cross_repo_schemas.py` 覆盖 6 个 schema × 3 个验证（valid / invalid / missing-field）
- [ ] `rdd-doctor --category state` 报告 6 个新 schema（无对应文件时警告）
- [ ] `docs/schemas/cross-repo-schemas.md` 含字段语义表
- [ ] 与现有 8 个 schema 的字段命名、格式风格一致
- [ ] Schema 文件 ≤ 200 行（保持可读）
- [ ] 集成到 `jsonschema` 库（与现有 schema 验证一致）

