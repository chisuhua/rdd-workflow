# fix-schema-version-field

## Why

- ADR-0016 规定所有 handoff / state 文件必须在 `_lib/schemas/<name>_schema.json` 下定义 schema，且 schema 变更必须 bump version 字段。
- `add-cross-repo-state-schemas` change 提案验收标准（AC #1）明确要求"每个 schema 含 `version` 字段（const）和 `$id` 唯一标识"。
- 当前 `_lib/schemas/` 下 **17 个 schema 文件全部缺失 `version` 字段**（审计覆盖：`arch_handoff`、`config`、`contract_cache`、`cross_repo_audit`、`cross_repo_deps_cache`、`cross_repo_pending`、`deps_analysis`、`design_handoff`、`feature_view`、`hub_metrics`、`iteration`、`mcp_trace`、`plan_handoff`、`sessions`、`skill_role`、`state_vector`、`trigger`）。
- `rdd-doctor --category state` 当前报 **5 个 CRITICAL**（包含 `.cross-repo-deps-cache.json` schema version 缺失），根因之一即 schema 本身不符合 ADR-0016 + 提案 AC。

## What Changes

**In Scope**:

- 给 `skills/_lib/schemas/` 下 **全部 17 个 schema 文件** 添加 `"version"` 字段，模式为 JSON Schema `"const"`（即 `"version": {"const": "v1"}`）。
- 同步更新 `tests/unit/test_cross_repo_schemas.py` 等已有 schema 测试，覆盖 `version` 字段的存在性。
- 给 `rdd-doctor --category state` 增加 schema self-check（version 缺失 → CRITICAL）。
- 验证 `.rddf/state/` 下 5 个被 doctor 报的 state 文件（`.mcp-trace.jsonl`、`.cross-repo-deps-cache.json`）符合新 schema。

### 关键场景

- GIVEN doctor 当前报 `.cross-repo-deps-cache.json` schema missing `version`, WHEN 给该 schema 添加 `"version": {"const": "v1"}`, THEN doctor CRITICAL 计数从 5 降到 ≤ 3，且 schema 自身被新加的 self-check 通过。
- GIVEN 17 个 schema 添加 `version` 字段后, WHEN `tests/unit/test_cross_repo_schemas.py` 跑 valid/invalid/missing-field 三类用例, THEN 所有用例通过，且新增 `test_version_field_required` 类别验证。
- GIVEN schema 加上 `version: v1`, WHEN 现有 doctor 校验 `.rddf/state/iteration.json`, THEN 校验通过（doctor 已能识别 schema；只是 schema 自身不合法才报 CRITICAL）。
- GIVEN `_lib/schemas/iteration_schema.json` 加上 `version: v1`, WHEN `state_vector.py::load` 调 `jsonschema.validate(data, schema)`, THEN 校验行为不变（因为 schema 顶层 properties 未变，只加 metadata 字段）。

**Out of Scope**:

- 不修改 schema 的 properties / required / 业务字段（只加 version 元数据）。
- 不实现 ADR-0016 中的 schema 治理流程（migration、version bump 协议等），仅满足"v1 const"最小合规。
- 不修改 doctor 的其他 5 类检查（state/plan-tdd/roadmap-meta/proposal-table/tasks-checkbox），只补 schema self-check。
- 不重写 add-cross-repo-state-schemas 已通过的 AC（其他 AC 已通过 — 测试 47/47 pass）。

## Capabilities

- MUST 给全部 17 个 schema 添加 `"version": {"const": "v1"}` 字段（JSON Schema 标准 const 模式，DRY）。
- MUST 保留每个 schema 现有所有 properties、required、$id、$schema 字段不动。
- SHOULD 给 schema 测试加 1 个 `test_version_field_present` 用例覆盖新增字段（17 schema × 1 = 17 测试新增）。
- SHOULD 同步在 `docs/schemas/` 下添加 README 章节解释 version 字段语义（引用 ADR-0016）。

## Impact

- MUST NOT 给已有字段改名或调整类型（避免破坏现有 jsonschema 验证）。
- MUST NOT 修改 iteration.json / 其他 state 文件的实际内容（只补 schema 自身）。

## Acceptance

- `skills/_lib/schemas/*.json` 下所有 17 个 schema 都含 `"version": {"const": "v1"}` 字段（机器可校验：`python3 -c "for f in glob('skills/_lib/schemas/*.json'): assert 'version' in json.load(open(f))"` 退出码 0）。
- `rdd-doctor --category state` 报告 schema 相关 CRITICAL 数从 5 降至 ≤ 3（剩余可能是 `.mcp-trace.jsonl` 实际损坏等非 schema 问题）。
- 新增 `tests/unit/test_schema_version_field.py` 覆盖 17 个 schema × 1 验证 = 17 个测试用例，全绿。
- 现有 `tests/unit/test_cross_repo_schemas.py`、`tests/unit/test_iteration_planned_entry.py` 等 schema 验证测试保持 pass（不引入 regression）。
- `docs/schemas/README.md`（或同等文档）新增"version 字段语义"章节，引用 ADR-0016 解释 schema 治理最小合规要求。
- 手工验证：执行 `python3 -c "import json,glob; [json.load(open(f)) for f in glob.glob('skills/_lib/schemas/*.json')]"` 无 JSONDecodeError。

