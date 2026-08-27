# fix-design-preflight-roadmap-format — Design

## Context

`skills/guide-design/scripts/design_preflight.py:19` 的 `_PHASE_HEADER_RE = re.compile(r"^### Phase \d+:[^\n]*?\(phase-[a-z0-9-]+\)")` 期望 `.rddf/roadmap.md` 用 `### Phase N: <name> (phase-X)` 标题 + 5 列分类表格式。
但实际 `.rddf/roadmap.md` 是简化表格格式 (`## Phase Skeleton` + 5 列 Phase/Theme/Status/Started/Done)。
后果:

- `compute_theme_coverage()` 永远返回 0 themes,即使主表含 10 个 theme 行。

## Goals / Non-Goals

**Goals:**
- `_read_roadmap_themes` 重构,同时支持两种格式:
- 新格式: `## Phase Skeleton` + `| Phase | Theme | ... |` 表格
- 老格式: `### Phase N: ... (phase-X)` + 分类表
- `_PHASE_HEADER_RE` 改为可选(仅在老格式中需要)
- 新增 unit test 覆盖两种格式

**Non-Goals:**
- 强制迁移 `.rddf/roadmap.md` 格式(向后兼容)
- 修复历史 178 个 unmapped legacy proposals(单独的 sync 提案)

## Decisions

### 1. MUST: 两种格式都能解析(向后兼容,不要 break 老文档)

Implementation MUST satisfy this constraint.

### 2. MUST: Phase ID 必须能被识别为 `phase-X` 格式

Implementation MUST satisfy this constraint.


## Risks / Trade-offs

- No identified risks beyond standard implementation discipline.

- **SHOULD**: SHOULD: 提供格式化帮助信息告诉用户哪种格式被检测