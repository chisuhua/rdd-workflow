## Implementation Tasks

- [ ] Create `_lib/schemas/skill_role_schema.json` with 5 sub-fields defined (title, perspective, boundaries.owns, boundaries.not_owns, boundaries.human_involvement)
- [ ] Add `role:` field to `skills/guide-arch/SKILL.md` frontmatter with all 5 sub-fields populated
- [ ] Add `role:` field to `skills/guide-design/SKILL.md` frontmatter with all 5 sub-fields populated
- [ ] Add `role:` field to `skills/guide-plan/SKILL.md` frontmatter with all 5 sub-fields populated
- [ ] Add `role:` field to `skills/guide-ship/SKILL.md` frontmatter with all 5 sub-fields populated
- [ ] Update each SKILL.md's "职责边界" section to reference the frontmatter role field (avoid duplication)
- [ ] Create `tests/integration/test_skill_role_all.bats` — verifies all 4 SKILL.md files have all 5 sub-fields
- [ ] Update `rdd-workflow/AGENTS.md` "关键约定" section with reference to ADR-0028
- [ ] Verify backward compatibility: remove role field from one SKILL.md, confirm `skill_use()` still loads
- [ ] Run `./test.sh --full` and verify all tests pass (no new failures vs KNOWN_FAILURES.txt baseline)
- [ ] Create `docs/adr/ADR-0028-role-model-per-phase.md` with the decision context
