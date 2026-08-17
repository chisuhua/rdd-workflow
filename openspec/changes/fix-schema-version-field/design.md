# fix-schema-version-field — Design

> Schema: spec-driven
> See: `proposal.md` for motivation, scope and acceptance criteria.

## Context

ADR-0016 规定所有 handoff / state 文件 schema 必须在 `skills/_lib/schemas/<name>_schema.json` 下定义,且 schema 变更必须 bump version 字段。`add-cross-repo-state-schemas` 提案验收标准 (AC #1) 明确要求"每个 schema 含 `version` 字段(const)和 `$id` 唯一标识"。当前 `skills/_lib/schemas/` 下 **17 个 schema 文件全部缺失顶层 `version` 字段**(审计覆盖: `arch_handoff`, `config`, `contract_cache`, `cross_repo_audit`, `cross_repo_deps_cache`, `cross_repo_pending`, `deps_analysis`, `design_handoff`, `feature_view`, `hub_metrics`, `iteration`, `mcp_trace`, `plan_handoff`, `sessions`, `skill_role`, `state_vector`, `trigger`)。`rdd-doctor --category state` 当前报 **5 个 CRITICAL**(包含 `.cross-repo-deps-cache.json` schema version 缺失),根因之一即 schema 本身不符合 ADR-0016 + 提案 AC。本提案为 17 个 schema 统一补齐顶层 `version` 元数据,达成 ADR-0016 最小合规。

## Goals / Non-Goals

**Goals:**

- 给 `skills/_lib/schemas/` 下全部 17 个 schema 文件添加顶层 `"version": {"const": "v1"}` 字段
- 新增 `tests/unit/test_schema_version_field.py` 覆盖 17 个 schema 的 version 字段存在性
- 给 `rdd-doctor --category state` 增加 schema self-check(顶层 version 缺失 → CRITICAL)
- 验证 `.rddf/state/` 下被 doctor 报的所有 state 文件仍能通过新 schema 校验

**Non-Goals:**

- 不修改 schema 的 `properties` / `required` / 业务字段(只加顶层 version 元数据)
- 不实现 ADR-0016 中的 schema 治理流程(migration、version bump 协议、consumer-side negotiation),仅满足"v1 const"最小合规
- 不修改 doctor 的其他 4 类检查(`plan-tdd` / `roadmap-meta` / `proposal-table` / `tasks-checkbox`),只补 schema self-check
- 不重写 `add-cross-repo-state-schemas` 已通过的 AC(其他 AC 已通过 — 测试 47/47 pass)

## Decisions

### 1. 使用 JSON Schema `const` 模式而非 `enum`

选择 `"version": {"const": "v1"}` 而非 `"type": "string", "enum": ["v1"]`。

**Alternatives considered:**

- `enum` 列表(允许 v1, v2 共存):便于多版本过渡,但本期是首次添加,无历史包袱;统一 const 单一版本更显式 — 后续 bump 时升级为 enum 即可。被否。
- `pattern` 正则 `^v[0-9]+$`:灵活但需后续治理逻辑配套;本期仅最小合规,被否。

### 2. 顶层位置放置(不放入 `properties`)

放在 schema 文件根级别(`$schema` / `$id` / `title` 旁边),不放入 `properties` 内。

**Alternatives considered:**

- 放入 `properties.version`:与已有业务字段冲突(如 `sessions_schema.json` 的 `properties.version` 是业务数据版本号,语义完全不同);混淆 schema 元数据与数据版本 — 被否。
- 放入 `$defs`:增加 schema 复杂度,需 `definitions` indirection;标准 JSON Schema 不强制 — 被否。

### 3. 所有 schema const 固定为 v1

不区分 schema 类型或创建时间,统一 const v1。

**Alternatives considered:**

- 按 schema 创建时间分版本(早期 v0.5):无历史包袱(本次是首次添加);后续 bump 升级到 v2 时同样一刀切 — 被否。
- 按 schema 复杂度分版本(multi-cap v2, single-cap v1):增加管理负担且无明确边界 — 被否。

### 4. rdd-doctor 自检复用 `json.load` 加载路径

新增 doctor check 通过 `json.load(open(schema_path))` 检测顶层 `"version"` 字段,与现有 `rdd-doctor --category state` 中 `jsonschema.validate(state_file, schema)` 的 schema 加载方式一致。

**Alternatives considered:**

- 用 `jsonschema.Draft202012Validator.check_schema()`:校验 schema 自身合法性,但标准 JSON Schema 不强制 `version` 字段,无法检测本提案针对的缺失 — 被否。
- 新增 `pyyaml` 解析 schema:多此一举,schema 是 JSON 格式 — 被否。

### 5. 测试膨胀控制

`test_schema_version_field.py` 用 `pytest.mark.parametrize("schema_file", [...])` 一次性参数化 17 个 schema × 1 个断言,而不是 17 个独立 test 函数。减少 pytest 收集开销(< 50ms 总耗时)。

**Alternatives considered:**

- 17 个独立 test 函数(`test_<schema>_has_version_field`):更细粒度,但 pytest 收集/报告开销高 — 被否。
- 1 个 test 函数扫描整个目录并循环断言:失去 per-schema 失败定位能力 — 被否。

## Risks / Trade-offs

- **业务 schema 已有 `properties.version` 的兼容性**:`sessions_schema.json` 等在 `properties` 内有 `version` 字段(业务数据版本),顶层 `version` 是 schema 元数据,语义不同。需在 const 字段加 `description` 明确区分两者语义("Schema metadata version" vs "Schema business data version")。
- **回归风险**:现有 `.rddf/state/*.json` 文件中保存的 version 字段(如 `sessions.json` 的 `version: 2`)是业务数据版本,**不是** schema 元数据。新 schema 校验不会失败,因 schema 顶层 properties 未变,只新增根级 metadata。
- **测试膨胀**:新增 17 个参数化用例对 pytest 总耗时影响 < 50ms,在 .rddf CI 容忍范围内。
- **未触达 `.rddf/state/.mcp-trace.jsonl` 等真正的损坏 state 文件**:本提案只补 schema 元数据,实际损坏 state 数据修复属其他提案。