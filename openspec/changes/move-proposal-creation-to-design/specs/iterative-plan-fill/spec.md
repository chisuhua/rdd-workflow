# iterative-plan-fill Specification (delta)

## ADDED Requirements

### Requirement: intake 消费 changes_pre_created

guide-plan SHALL read `changes_pre_created` from the design-handoff (v2) and skip change creation for those names, proceeding directly to roadmap-meta backfill and fill. Re-creation of a pre-created change MUST NOT occur (idempotent).

#### Scenario: 预建 change 跳过创建

- GIVEN design-handoff v2 contains `changes_pre_created: ["foo"]` and `openspec/changes/foo/` exists with a complete proposal.md
- WHEN guide-plan runs its propose phase
- THEN `foo` is marked as design-pre-created and no new change is created for it
- AND roadmap-meta backfill (`update_roadmap_meta`) still runs for `foo`

### Requirement: fill 范围收缩为 specs/design/tasks

The fill phase SHALL only create `specs/`, `design.md`, and `tasks.md` for changes whose `proposal.md` is already complete (as reported by `openspec status --change <name> --json` showing the proposal artifact as done). Fill MUST NOT rewrite an existing complete `proposal.md`.

#### Scenario: 完整 proposal 不被重写

- GIVEN a change pre-created in the design phase with a complete `proposal.md`
- WHEN the fill phase processes it
- THEN fill creates only `design.md` and `tasks.md` (and specs deltas where applicable)
- AND the existing `proposal.md` content is unchanged
