## Context

The rdd-workflow v2.1 has 4 phase skills (`guide-arch`, `guide-design`, `guide-plan`, `guide-ship`) but the "职责边界" (boundary of responsibility) section in each is informal prose. This makes it hard for new developers to understand role boundaries at a glance, and AI agents may inadvertently cross phase boundaries (e.g., `guide-arch` writing to `openspec/changes/<name>/`).

This change formalizes the role model via a `role:` field in frontmatter, single source of truth, and a schema for validation. The change is documentation-only at the AI behavior level — no enforcement hooks are added (per the proposal's MUST NOT).

## Goals / Non-Goals

**Goals:**
- Add `role:` field to all 4 phase SKILL.md frontmatter with 5 sub-fields.
- Create JSON schema (`_lib/schemas/skill_role_schema.json`) for the `role:` field.
- Update each SKILL.md's "职责边界" section to reference the frontmatter (avoid drift).
- Add 1 comprehensive bats test (`tests/integration/test_skill_role_all.bats`).
- Update `rdd-workflow/AGENTS.md` to reference ADR-0028.

**Non-Goals:**
- Modify AI prompt-injection mechanism (frontmatter only).
- Add pre-commit hooks for boundary enforcement.
- Modify `guide` recommender's free-discussion behavior.
- Add roles to sub-skills (propose/execute/status/etc).
- Modify existing ADRs (ADR-0003, ADR-0017, ADR-0025).
- Split into multiple PRs (single PR for all 4 SKILL.md files).

## Decisions

### 1. Single PR vs. 5-PR pilot+batch

Use a single PR for all 4 SKILL.md changes. The proposal originally proposed 5 PRs (1 pilot + 3 batch + 1 ADR), but the change is small enough (config-only without behavior change) to fit in 1 PR.

**Alternatives considered:**
- 5-PR approach (original proposal): Rejected — adds overhead for a 14-file change with no behavior shift.
- 2-PR approach (ADR + skill changes): Rejected — separates a tightly-coupled change unnecessarily.

### 2. Schema location: `_lib/schemas/` vs `skills/_lib/schemas/`

Place the new schema at `_lib/schemas/skill_role_schema.json` (project root), matching the existing 10 schema files (`arch_handoff_schema.json`, `iteration_schema.json`, etc.). The original proposal had `skills/_lib/schemas/` which is a path drift.

**Alternatives considered:**
- New `skills/_lib/schemas/` directory: Rejected — non-conforming with existing schema convention.
- Embed schema in each SKILL.md: Rejected — violates single-source-of-truth.

### 3. Role field structure: nested object vs flat fields

Use a nested `role:` object with 5 sub-fields (`title`, `perspective`, `boundaries.owns`, `boundaries.not_owns`, `boundaries.human_involvement`). Nested boundaries group related concepts.

**Alternatives considered:**
- Flat fields (`role_title`, `role_perspective`, etc.): Rejected — loses semantic grouping.
- Single `role` string with embedded Markdown: Rejected — not schema-validatable.

### 4. Single bats test vs 4 separate files

Use 1 comprehensive bats test (`test_skill_role_all.bats`) that iterates over all 4 SKILL.md files. The original proposal had 4 separate test files — over-engineered for a 4-file schema check.

**Alternatives considered:**
- 4 separate test files (original proposal): Rejected — adds maintenance overhead.
- Per-test bats parameterized: Rejected — bats doesn't support parameterization natively.

## Risks / Trade-offs

- **Risk**: YAML parser in `tests/_lib/skill.bash` only supports scalar top-level fields. The new `role:` field is a nested object, which the parser will return as a string. **Mitigation**: The bats test uses `yq` or `python3 -c yaml.safe_load` for nested validation, not the existing `skill_field` helper.
- **Trade-off**: Documentation-only change affects no behavior. The value is purely in onboarding clarity and review-checklist consistency. Future proposals can add enforcement hooks separately.
- **Risk**: Schema path drift between proposal text and actual code. **Mitigation**: Schema paths are verified in the bats test (loads `_lib/schemas/skill_role_schema.json`).
