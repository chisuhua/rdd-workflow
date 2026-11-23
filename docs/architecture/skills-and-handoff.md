# Skills and Handoff Protocol

A **skill** is a `SKILL.md` file with YAML frontmatter that an AI coding assistant can discover and invoke. rdd-workflow ships 26 skills (19 of them `user-invocable: true`) plus the shared `_lib/` runtime.

## SKILL.md Frontmatter Spec

Every skill's first line is `---` (YAML start); the frontmatter block closes with another `---`. The runtime reads **only** these fields.

### Required (top-level)

| Field | Type | Meaning |
|-------|------|---------|
| `name` | string | Unique skill identifier. Used for `skill_use("name")` and CLI lookup. **Immutable.** |
| `description` | string | One-paragraph purpose; surfaces in `/skills` lists and `rddf discover`. |
| `license` | string | SPDX identifier. |
| `compatibility` | string | Required runtime/CLI versions (e.g. `openspec CLI v1.3.1+, git 2.25+`). |

### Required (under `metadata:`)

| Field | Type | Meaning |
|-------|------|---------|
| `author` | string | Maintainer handle. |
| `version` | semver | `X.Y` style. Bump on any behavioural change. **Immutable at runtime.** |
| `evolved-from` | string | Previous skill name (if refactored). For history. |
| `user-invocable` | bool | If `false`, the skill is internal and should not appear in user menus. |

**Immutability rule** (per AGENTS.md / ADR convention): `name`, `version`, `evolved-from`, and `user-invocable` are **read-only at runtime**. Skill authors do not edit them to "rebrand"; they bump `version` semver.

## Discovery and Resolution

When the user types `skill_use("rdd-arch")`, resolution runs in this order:

1. `${PROJECT_ROOT}/.opencode/skills/rdd-workflow/skills/rdd-arch/SKILL.md`
2. `${PROJECT_ROOT}/skills/rdd-arch/SKILL.md`
3. `~/.agents/skills/rdd-arch/SKILL.md` (global install)
4. `~/.agents/skills/rdd-workflow/skills/rdd-arch/SKILL.md` (global install, vendored)

Resolution code lives in `_lib/skill_root.sh::resolve_rdd_skill_dir`. If both PROJECT paths and global paths miss, the skill is reported as not-installed.

## Three Invocation Modes

| Mode | Mechanism | Use case |
|------|-----------|----------|
| `skill_use("name")` | Inline call from another skill or from the AI assistant's chat. | Most common — AI reads the SKILL.md and follows its instructions. |
| `rddf <subcommand>` | CLI call. | Scripting, dashboards, CI. |
| Direct `.md` read | `cat skills/<name>/SKILL.md` | Authoring, debugging. |

All three resolve to the same content; the mode is purely transport.

## Handoff Contracts

A **handoff file** is a versioned JSON file under `.rddf/state/` that one stage writes and the next stage reads.

> **v4 命名说明**：v4 把 design 与 plan 合并为 `rdd-planner`，handoff 家族随之改名 ——
> `.design-handoff.json` / `.plan-handoff.json` 是 **v3 残留（v4 无写入方）**，
> v4 的活契约是 `.planner-handoff.json`（配套 `.planner-state.json` / `.planner-feedback.json`）。
> 读方对 v3 残留**只作兜底**：`_lib/recommender.py:133-162` 仅在 v4 handoff 缺失时回退到 v3，
> 并打印「legacy v3 handoff detected …; migrate to .planner-handoff.json」。

### `.arch-handoff.json` (v3, ADR-0016 + ADR-0042)

`rdd-arch` 阶段出口写（`skills/rdd-arch/scripts/write_arch_handoff.py:183` 写 `"version": 3`），
`rdd-planner` / `rdd-builder` 读。

Top-level fields（**v3 writer 的实际输出**，见 `skills/rdd-arch/scripts/write_arch_handoff.py:164-187`）:
```json
{
  "arch_complete_at": "2026-08-15T16:40:59+00:00",
  "adr_count": 31,
  "completed_adr_ids": ["0001", "0002"],
  "current_phase": "v2.0 (已完成)",
  "plan_started_at": null,
  "adr_dir": "docs/adr",
  "architecture_dir": "docs/architecture",
  "adr_pattern": "ADR-*.md",
  "discovered": {
    "adr_dir": {"found": true, "created": false, "candidates_tried": 1},
    "architecture_dir": {"found": true, "created": false, "candidates_tried": 1}
  },
  "version": 3
}
```
（可选 `adr_regex`：从 `.rddf/project.yaml` 透传的 Python regex，供 `populate_lib` 用 —— 与 `adr_pattern`（glob）是两回事。）

**版本**：schema `enum: [1, 2, 3]`（`_lib/schemas/arch_handoff_schema.json:133`）——
v2 加 `adr_regex`，v3 是当前写出版本；读者按 `version` 分支兼容
（`additionalProperties: true` ⇒ 老 payload 的额外字段不致命）。
⚠️ **`discovered` 的语义随版本变过**：v1 是布尔（`true` = 「phase 扫过并找到了这些路径」，
`false` = 「用了默认值」）；v2/v3 是**逐工件对象**（`{found, created, candidates_tried}`）——
读布尔值的消费者对 v3 payload 会拿到 truthy dict 而非布尔。

**Versioning policy**: bump `version` whenever a field is added, removed, or its semantics change. Consumers **must reject `version: 0`** payloads (forces explicit migration).

### `.planner-handoff.json` (schema `planner-handoff-v1`, ADR-0048) — **v4 活契约**

`rdd-planner` 阶段出口写（`_lib/planner_handoff.py:33,77`），`rdd-builder` 读
（`_lib/builder_deps.py:223,234` 读 `recommended_route`，供 P0 dispatch-quick 决策）。

Top-level fields:
```json
{
  "schema": "planner-handoff-v1",
  "version": 1,
  "owner": "rdd-planner",
  "planner_complete_at": "2026-11-18T20:47:00+00:00",
  "current_sprint": "2026-11-sprint-3",
  "proposals_ready": ["fix-foo"],
  "proposals_approved_count": 1,
  "features_active": ["feat-bar"],
  "awaiting_builder": ["fix-foo"],
  "recommended_route": "simple",
  "active_objectives": ["objective-baz"]
}
```

**必填**（`_lib/schemas/planner_handoff_schema.json`）：`schema` / `version` / `owner` /
`planner_complete_at` / `current_sprint` / `recommended_route`。

`recommended_route` 是 **advisory** 字段 —— 它被 `_lib/planner_state.py:56` 的
`_SEMANTIC_HASH_EXCLUDE` 排除在 `state_revision` 语义哈希之外（advisory 重算**不** bump revision）。

### `.planner-state.json` (v1)

`rdd-planner` 的**聚合状态**（当前 sprint / 同步状态 / roadmap 映射）：写方
`_lib/planner_state.py:149` `write_state`（由 `_lib/planner_sync.py` 调用，原子写 + FileLock），
`SCHEMA_VERSION = 1`（`:35`）。读方：`_lib/cli/planner_cmd.py:18`（`rddf planner`）
与 `_lib/planner_feedback.py:325`（只取 `state_revision`）。

必填：`version` / `current_sprint` / `last_sync_at` / `recommended_route`。

### `.planner-feedback.json` (schema `planner-feedback-v1`, ADR-0042)

`rdd-builder` 的**实施期发现回灌通道**：写方 `_lib/builder_feedback_router.py:30-48`
（builder → planner 反馈）与 `_lib/planner_feedback.py`（原子写 + FileLock），
读方 `rdd-planner` / `rdd-arch`。

### `.rddf/state/builder/<change>.json` (schema `builder-handoff-v1`)

**逐 change** 的 builder 状态：写方 `_lib/builder_handoff.py:14-30,85`，读方 `rdd-builder`
（阶段推进 / 重试计数）与 `rdd-verifier`（验收锚点）。

必填：`schema` / `version` / `owner` / `change_name` / `current_phase` / `retry_count` / `max_retries`。

### `.rddf/state/rdd-quick-context.json` (ADR-0048)

`rdd-quick` 旁路的**派发上下文**：`rdd-builder` P0 dispatch-quick 时写
（`skills/rdd-builder/scripts/phase0_approval.sh:321-345`），`rdd-quick` 消费，
用完由 `skills/rdd-quick/scripts/cleanup_context.sh:58`（`rm -f`；路径定义在 `:49`）删除。

必填：`change_name` / `proposal_path` / `from_builder` / `dispatched_at`。

### `.design-handoff.json` (v2, ADR-0025) — **v3 残留，v4 无写入方**

Top-level fields:
```json
{
  "design_complete_at": "2026-08-13T01:55:18+00:00",
  "proposals_reviewed": 1,
  "all_proposals_have_decision": true,
  "version": 2,
  "changes_pre_created": ["fix-foo", "add-bar"]
}
```

**Path A contract (retired 2026-11-20)**: `changes_pre_created` used to list every change that `guide-design` approval directly wrote to `openspec/changes/<name>/{proposal.md, .openspec.yaml, roadmap-meta.yaml}`, with `guide-plan` intake exporting it as a `CHANGES_PRE_CREATED` bash array and consuming it via `is_design_pre_created` / `get_design_pre_created_label` / `get_fill_artifacts_for`. All three consumer functions and `plan_intake.sh` were removed with ADR-0043 / ADR-0044; the field survives only as a historical schema contract (`_lib/schemas/design_handoff_schema.json`), with **no live consumer**.

**Versioning policy** (v2.0.6+, `move-proposal-creation-to-design`): v2 schema requires `changes_pre_created` as a non-empty string array; v1 payloads remain valid input (empty array) for any v1 reader still in the field.

### `.plan-handoff.json` (v1, ADR-0024) — **v3 残留，v4 无写入方**

Top-level fields:
```json
{
  "version": 1,
  "change_name": "fix-foo",
  "execution_mode_decisions": {
    "mode": "lightweight" | "worktree",
    "rationale": "files_changed=2, tasks=3, no risk keywords, no conflicts"
  }
}
```

⚠️ **`execution_mode_decisions` 在 v4 已无写入方** —— `skills/rdd-builder/scripts/phase1_5_deps.sh:24`
明写「Legacy plan-handoff execution_mode (v3 residue). It has no writer in v4」。
该字段**只被读来打警告、永不覆盖**计算结果（最低优先级，`:115-120`）：

```
⚠️  legacy .plan-handoff.json execution_mode='worktree' 已忽略（v4 残留，无写入方）—— 保留计算得到的判定: lightweight
```

其余读者（`_lib/state_reader.py:103`、`_lib/discover_ship_changes.py:95`、`_lib/parallel_executor.py:16`）
也只作**兜底读取**；`skills/rddf-session/SKILL.md:129` 同理。

## Schema Files

The canonical schema for each handoff lives under `_lib/schemas/`（共 **34** 个 json）:

| Schema | Version | JSON Schema file |
|--------|---------|------------------|
| arch-handoff | v3（schema `enum: [1,2,3]`） | `_lib/schemas/arch_handoff_schema.json` |
| planner-handoff | `planner-handoff-v1`（`version: 1`） | `_lib/schemas/planner_handoff_schema.json` |
| builder-handoff | `builder-handoff-v1`（`version: 1`） | `_lib/schemas/builder_handoff_schema.json` |
| planner-state | v1（`SCHEMA_VERSION = 1`） | `_lib/schemas/planner_state_schema.json` |
| rdd-quick-context | ADR-0048 | `_lib/schemas/rdd_quick_context_schema.json` |
| design-handoff（v3 残留） | v2（Path A contract） | `_lib/schemas/design_handoff_schema.json` |
| plan-handoff（v3 残留） | v1 + `execution_mode_decisions` (ADR-0024) | `_lib/schemas/plan_handoff_schema.json` |
| state-vector | v1 | `_lib/schemas/state_vector_schema.json` |
| iteration | `enum: [3,4,5,6,7]` | `_lib/schemas/iteration_schema.json` |
| sessions | v1 | `_lib/schemas/sessions_schema.json` |

> ⚠️ `.planner-feedback.json` 的 schema 名 `planner-feedback-v1` 由 `_lib/planner_feedback.py:8`
> 定义，但**对应的 `planner_feedback_schema.json` 文件不存在**（`_lib/schemas/` 下只有
> `feedback_entry_schema.json`）⇒ 该 docstring 引用是悬空的（已知小债）。

**Any change to a schema requires bumping the `version` field in the handoff file and adding a migration entry.**

## Cross-references

- Phases that read/write handoffs: [workflow-phases.md](workflow-phases.md)
- State file mechanics: [state-and-events.md](state-and-events.md)
