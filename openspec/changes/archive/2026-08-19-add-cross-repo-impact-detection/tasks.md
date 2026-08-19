# add-cross-repo-impact-detection — Tasks

> Schema: spec-driven
> See: `proposal.md` (动机/范围/AC) + `design.md` (技术决策).
> Source: ADR-0032 (Hub 联邦深化), 2026-08-19.

## Implementation

- [ ] 1. TDD red: 写新增测试, 跑确认 fail (red)
- [ ] 2. 实现核心代码 + 辅助脚本
- [ ] 3. TDD green: 跑全部相关测试确认 pass
- [ ] 4. AC-1 ~ AC-N 逐项 verify
- [ ] 5. 既有回归: `./test.sh --python --unit` 133+ unit test 全过
- [ ] 6. 既有回归: `bats tests/integration/test_*.bats` 相关 test 全绿
- [ ] 7. e2e 测试 `tests/integration/test_cross_repo_e2e_real.bats` 全绿 (新增 case 视 change 而定)
- [ ] 8. `./test.sh --full --regression` 不新增失败
- [ ] 9. conventional commit: `<type>(add-cross-repo-impact-detection): <description>`
- [ ] 10. archive: `openspec archive add-cross-repo-impact-detection --yes`
- [ ] 11. cross-repo-federation spec delta 已合并 (`openspec/specs/`)
- [ ] 12. audit trail: `git log --grep='add-cross-repo-impact-detection'` 含清晰 commit
- [ ] 13. proposal-approved.md 含本 change 条目 (走 approve_proposal.sh)

## Dependencies

依赖见 `proposal.md` § Manual Deps (roadmap-meta.yaml manual_deps 字段).
