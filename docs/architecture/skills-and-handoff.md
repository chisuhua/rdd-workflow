# Skills and Handoff Protocol

A **skill** is a `SKILL.md` file with YAML frontmatter that an AI coding assistant can discover and invoke. rdd-workflow ships 17 user-invocable skills plus the shared `_lib/` runtime.

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

When the user types `skill_use("guide-arch")`, resolution runs in this order:

1. `${PROJECT_ROOT}/.opencode/skills/rdd-workflow/skills/guide-arch/SKILL.md`
2. `${PROJECT_ROOT}/skills/guide-arch/SKILL.md`
3. `~/.agents/skills/guide-arch/SKILL.md` (global install)
4. `~/.agents/skills/rdd-workflow/skills/guide-arch/SKILL.md` (global install, vendored)

Resolution code lives in `_lib/skill_root.sh::resolve_rdd_skill_dir`. If both PROJECT paths and global paths miss, the skill is reported as not-installed.

## Three Invocation Modes

| Mode | Mechanism | Use case |
|------|-----------|----------|
| `skill_use("name")` | Inline call from another skill or from the AI assistant's chat. | Most common — AI reads the SKILL.md and follows its instructions. |
| `rddf <subcommand>` | CLI call. | Scripting, dashboards, CI. |
| Direct `.md` read | `cat skills/<name>/SKILL.md` | Authoring, debugging. |

All three resolve to the same content; the mode is purely transport.

## Handoff Contracts

A **handoff file** is a versioned JSON file under `.rddf/state/` that one phase writes and the next phase reads.

### `.arch-handoff.json` (v1, ADR-0016)

Top-level fields:
```json
{
  "version": 1,
  "adr_dir": "docs/adr",
  "roadmap_path": "roadmap.md",
  "architecture_dir": "docs/architecture",
  "adr_pattern": "ADR-*.md",
  "discovered": true
}
```

**Versioning policy**: bump `version` whenever a field is added, removed, or its semantics change. Consumers **must reject `version: 0`** payloads (forces explicit migration). The `discovered: true` flag distinguishes "phase ran scan and found these paths" from "phase ran with all defaults" (`discovered: false`).

### `.design-handoff.json` (v2, ADR-0025)

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

**Path A contract**: `changes_pre_created` lists every change that `guide-design` approval directly wrote to `openspec/changes/<name>/{proposal.md, .openspec.yaml, roadmap-meta.yaml}`. `guide-plan` intake exports this as `CHANGES_PRE_CREATED` bash array and consumes it via:
- `is_design_pre_created <name>` — skip `propose --create` for pre-created changes (Phase 2).
- `get_design_pre_created_label <name>` — emit `🆕 design-pre-created` badge in the approved-list display.
- `get_fill_artifacts_for <name>` — narrow Phase 2.5 fill to `design tasks specs` for pre-created changes (NEVER overwrite the complete `proposal.md` that design wrote).

**Versioning policy** (v2.0.6+, `move-proposal-creation-to-design`): v2 schema requires `changes_pre_created` as a non-empty string array. v1 payloads are still accepted by `plan_intake.sh` as backward-compat (empty array), but new handoffs MUST be v2.

### `.plan-handoff.json` (v1, ADR-0024)

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

`execution_mode_decisions` is the field `guide-ship` reads to decide between worktree and lightweight mode (see [workflow-phases.md](workflow-phases.md)).

## Schema Files

The canonical schema for each handoff lives under `_lib/schemas/`:

| Schema | Version | JSON Schema file |
|--------|---------|------------------|
| arch-handoff | v1 | `_lib/schemas/arch_handoff_schema.json` |
| design-handoff | v2 (Path A contract) | `_lib/schemas/design_handoff_schema.json` |
| plan-handoff | v1 + `execution_mode_decisions` (ADR-0024) | `_lib/schemas/plan_handoff_schema.json` |
| state-vector | v1 | `_lib/schemas/state_vector_schema.json` |
| iteration | v1 | `_lib/schemas/iteration_schema.json` |
| sessions | v1 | `_lib/schemas/sessions_schema.json` |

**Any change to a schema requires bumping the `version` field in the handoff file and adding a migration entry.**

## Cross-references

- Phases that read/write handoffs: [workflow-phases.md](workflow-phases.md)
- State file mechanics: [state-and-events.md](state-and-events.md)
