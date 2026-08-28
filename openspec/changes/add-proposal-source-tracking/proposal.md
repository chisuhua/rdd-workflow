# add-proposal-source-tracking

## Why

当前 `.rddf/improvements/*.md` 前置元数据只有 6 个字段:
- `**优先级**`
- `**来源**` (free text)
- `**阶段**`
- `**分类**`
- `**类型**`
- `**主题**`

但缺乏:
- `**session_id**` — 哪个 session/AI agent 创建
- `**audit_source**` — 触发场景的机器可读 ID (例如 `2026-08-27-ship-audit`)
- `**created_at_iso**` — ISO 8601 时间戳(当前日期只在 `**来源**:` 中文字描述)
- `**parent_session_id**` — 父 rddf-session (per ADR-0017)

后果:
- 178 个 unmapped legacy proposal 无法追溯创建上下文
- 无法按 session / audit 过滤 proposal 池
- rdd-doctor 巡检报告无法精确指出"哪些 proposal 由哪个 session 创建"
- 当需要重新评估或回滚某个 audit 的产出时,定位困难

期望行为: 每个 proposal 含结构化元数据,支持查询和审计追溯。

## What Changes

**In Scope**:

- `.rddf/improvements/*.md` schema 扩展,新增 4 个字段:
- `**session_id**` (string, format: `rds_<uuid>` or `manual-<timestamp>`)
- `**audit_source**` (string, format: `<date>-<event>` 例如 `2026-08-27-ship-audit`)
- `**created_at_iso**` (ISO 8601 timestamp)
- `**parent_session_id**` (optional, references rddf-session)
- `add-improve` 脚本自动填充这 4 个字段 (从环境变量 `RDDF_SESSION_ID`, `RDDF_AUDIT_SOURCE`, etc.)
- `propose_quality_check.py` 验证字段存在
- `_read_proposal_subjects` 在 `design_preflight.py` 扩展支持新字段(可选)

### 关键场景

- GIVEN 用户运行 `add-improve` 创建 proposal,环境变量 `RDDF_SESSION_ID=rds_abc123` 设置
  WHEN proposal 写入完成
  THEN 自动填充 `**session_id**: rds_abc123`, `**created_at_iso**: 2026-08-27T...`, `**audit_source**: manual`

- GIVEN 用户运行 `rddf rdd-verify --filter-session rds_abc123`
  WHEN 扫描 `.rddf/improvements/*.md`
  THEN 只列出该 session 创建的 proposal

- GIVEN `rdd-doctor --category proposal-quality --report-format json`
  WHEN 巡检所有 proposal
  THEN 输出包含 `session_id` 和 `created_at_iso`,支持按字段过滤

**Out of Scope**:

- 修改 178 个 legacy proposal(legacy exception,保留向后兼容)
- 改 rdd-session 创建流程(per ADR-0017 已存在)
- UI / dashboard 改造

## Capabilities

- MUST: 4 个新字段是 schema v2 的 mandatory 字段
- MUST: 178 legacy proposal 不强制补字段(legacy exception 注释)
- SHOULD: 提供 `_lib/improvements/migrate.py` 脚本,可选性批量给 legacy 补字段
- SHOULD: `add-improve` 接受 `--session-id <id>` 和 `--audit-source <src>` 参数覆盖默认值

## Impact

- MUST NOT: 改变已有 6 个字段的语义

## Acceptance

- [ ] `_lib/improvements/schema.md` v2 文档化 4 个新字段
- [ ] `add-improve/scripts/{free,from_roadmap,from_issue}.sh` 自动从 env 读取并填充 4 个字段
- [ ] `--session-id` 和 `--audit-source` CLI flag 实现
- [ ] `propose_quality_check.py` 验证 4 个新字段存在(对 v2 schema)
- [ ] 178 legacy proposal 保持原状 + 头部注释 `<!-- legacy: no v2 fields -->`
- [ ] `_lib/improvements/migrate.py` 提供 `migrate --dry-run` / `migrate --execute` 选项
- [ ] 新增 unit test 覆盖 scenarios: 自动填充 / 手动覆盖 / legacy exception
- [ ] `rdd-doctor --category proposal-quality` 输出 JSON 含 `session_id` 字段
- [ ] `rddf rdd-verify --filter-session <id>` CLI 参数支持

