## 1. Setup

- [x] 1.1 Read proposal.md, design.md and confirm scope
- [x] 1.2 Verify dependencies: P0 fix-rddf-session-owner-stability 实施 (强依赖)
- [x] 1.3 Check current branch + worktree strategy

## 2. Implementation (TDD 5 步)

- [x] 2.1 Write failing test (单元/集成测试, 按 improvements/fix-rddf-session-owner-stability.md 关键场景)
- [x] 2.2 Verify test fails (red)
- [x] 2.3 Implement change (按 improvements/fix-rddf-session-owner-stability.md 范围 + 技术约束)
- [x] 2.4 Verify test passes (green)
- [x] 2.5 Refactor + commit

## 3. Verification

- [x] 3.1 Run `openspec validate fix-rddf-session-owner-stability` (passes)
- [x] 3.2 Run `pytest tests/unit/test_rddf_*.py` (passes)
- [x] 3.3 Run `bats tests/integration/test_*.bats` (passes)
- [x] 3.4 Run `git show HEAD:openspec/changes/fix-rddf-session-owner-stability/design.md` (artifact committed)
- [x] 3.5 Run `git show HEAD:openspec/changes/fix-rddf-session-owner-stability/tasks.md` (artifact committed)
- [x] 3.6 Run `git show HEAD:openspec/changes/fix-rddf-session-owner-stability/.openspec.yaml` (metadata committed)

## 4. Documentation

- [x] 4.1 Update `skills/rddf-session/SKILL.md` if API surface changes
- [x] 4.2 Add entry to `CHANGELOG.md` (if present)
- [x] 4.3 Update ADR-0017 (rddf-session) if design decisions impact data model
