## 1. Setup

- [ ] 1.1 Read proposal.md, design.md and confirm scope
- [ ] 1.2 Verify dependencies: P0 fix-rddf-session-owner-stability 实施 (强依赖)
- [ ] 1.3 Check current branch + worktree strategy

## 2. Implementation (TDD 5 步)

- [ ] 2.1 Write failing test (单元/集成测试, 按 improvements/add-rddf-session-workflow-group.md 关键场景)
- [ ] 2.2 Verify test fails (red)
- [ ] 2.3 Implement change (按 improvements/add-rddf-session-workflow-group.md 范围 + 技术约束)
- [ ] 2.4 Verify test passes (green)
- [ ] 2.5 Refactor + commit

## 3. Verification

- [ ] 3.1 Run `openspec validate add-rddf-session-workflow-group` (passes)
- [ ] 3.2 Run `pytest tests/unit/test_rddf_*.py` (passes)
- [ ] 3.3 Run `bats tests/integration/test_*.bats` (passes)
- [ ] 3.4 Run `git show HEAD:openspec/changes/add-rddf-session-workflow-group/design.md` (artifact committed)
- [ ] 3.5 Run `git show HEAD:openspec/changes/add-rddf-session-workflow-group/tasks.md` (artifact committed)
- [ ] 3.6 Run `git show HEAD:openspec/changes/add-rddf-session-workflow-group/.openspec.yaml` (metadata committed)

## 4. Documentation

- [ ] 4.1 Update `skills/rddf-session/SKILL.md` if API surface changes
- [ ] 4.2 Add entry to `CHANGELOG.md` (if present)
- [ ] 4.3 Update ADR-0017 (rddf-session) if design decisions impact data model
