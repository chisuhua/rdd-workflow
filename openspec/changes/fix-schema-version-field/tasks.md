# fix-schema-version-field — Tasks

> Schema: spec-driven
> See: `proposal.md` (motivation/scope) + `design.md` (technical decisions).

## Implementation

- [x] 1.1 给 `skills/_lib/schemas/*.json` 下 17 个 schema 文件统一添加顶层 `"version": {"const": "v1"}` 字段
  - 17 个文件清单: `arch_handoff_schema.json`, `config_schema.json`, `contract_cache_schema.json`, `cross_repo_audit_schema.json`, `cross_repo_deps_cache_schema.json`, `cross_repo_pending_schema.json`, `deps_analysis_schema.json`, `design_handoff_schema.json`, `feature_view_schema.json`, `hub_metrics_schema.json`, `iteration_schema.json`, `mcp_trace_schema.json`, `plan_handoff_schema.json`, `sessions_schema.json`, `skill_role_schema.json`, `state_vector_schema.json`, `trigger_schema.json`
  - 插入位置: `$schema` 字段之后,`$id` 字段之前(保持 JSON Schema 标准字段顺序)
  - 字段内容: `"version": {"const": "v1", "description": "Schema metadata version per ADR-0016. Const v1 = initial baseline. Future bumps require version-migration flow."}`
  - **CRITICAL**: 不修改 `properties` 内已有 `version` 字段(如 `sessions_schema.json` 的 `properties.version` 是业务数据版本,语义不同)
- [x] 1.2 新增 `tests/unit/test_schema_version_field.py`(≥17 用例)
  - 用 `pytest.mark.parametrize("schema_path", [...])` 参数化 17 个 schema 文件
  - 每个用例: `json.load(open(schema_path))` → 断言顶层 `"version"` 字段存在 → 断言 `version["const"] == "v1"`
  - 额外测试: `test_version_field_distinct_from_properties_version` — 验证 `sessions_schema.json` 等含 `properties.version` 的 schema,顶层 const version 与 properties.version 不冲突
- [x] 1.3 给 `rdd-doctor` 新增 schema version self-check(`--category state`)
  - 在 `skills/rdd-doctor/scripts/doctor.sh` 的 state 检查路径中,新增 `check_schema_version_field` 函数
  - 扫描 `skills/_lib/schemas/*.json`,对缺失顶层 `version` 的 schema 报 CRITICAL
  - 错误消息格式: `"[CRITICAL] schema <name>.json: missing top-level 'version' field (ADR-0016 violation)"`
  - 修复后预期: `rdd-doctor --category state` 的 CRITICAL 数从 5 降至 ≤ 3(剩余可能为 `.mcp-trace.jsonl` 实际损坏等非 schema 问题)
- [x] 1.4 验证 `.rddf/state/` 下 state 文件通过新 schema 校验
  - 目标文件: `.arch-handoff.json`, `.design-handoff.json`, `.plan-handoff.json`, `.iteration.json`, `.sessions.json`, `.deps-analysis.json`, `.cross-repo-deps-cache.json`, `.mcp-trace.jsonl` 等(全部活跃 state)
  - 手工验证命令: `for f in .rddf/state/*.json; do python3 -c "import json, jsonschema; data=json.load(open('$f')); schema_name='...'; jsonschema.validate(data, json.load(open('skills/_lib/schemas/${schema_name}.json')))" || echo "FAIL: $f"; done`
  - 预期: 全部通过(因 schema 顶层 properties 未变,只新增根级 metadata)
- [x] 1.5 文档化 `docs/schemas/README.md` 新增"version 字段语义"章节
  - 第 1 节: 引用 ADR-0016 解释 schema 治理最小合规要求
  - 第 2 节: 说明 const 版本号 vs `properties.version` 业务字段的语义差异(顶层 metadata 是 schema 元数据版本,properties 内是数据业务版本)
  - 第 3 节: 列出 17 个 schema 的 version v1 状态基线
- [x] 1.6 同步更新 `tests/unit/test_cross_repo_schemas.py` 已有 schema 测试
  - 检查是否引用 schema 顶层 metadata 字段;如是则保持兼容(只读不写)
  - 不引入 regression: 现有测试用例保持 pass
- [x] 1.7 手工验证: 退出码 0 命令必须全部成功
  - `python3 -c "import json, glob; [json.load(open(f)) for f in glob.glob('skills/_lib/schemas/*.json')]"` (无 JSONDecodeError)
  - `python3 -c "for f in glob.glob('skills/_lib/schemas/*.json'): assert 'version' in json.load(open(f))"` (退出码 0)
  - `./test.sh --unit` (含 test_schema_version_field.py 全绿 + test_cross_repo_schemas.py 无 regression)