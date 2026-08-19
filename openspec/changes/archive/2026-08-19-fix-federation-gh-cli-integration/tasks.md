# fix-federation-gh-cli-integration — Tasks

> Schema: spec-driven
> See: `proposal.md` (动机/范围/AC) + `design.md` (技术决策).
> Source: e2e test `tests/integration/test_cross_repo_e2e_real.bats` (13 cases) 2026-08-19.

## Implementation

- [ ] 1. **TDD red**: 写 `tests/integration/test_cross_repo_e2e_real.bats` case #02 (RFC creation), 跑确认 fail (RuntimeError)
- [ ] 2. **修复 #1**: `skills/_lib/gh_hub_client.py::create_issue` 改 stdout URL 解析 + JSON fallback, 跑 case #02 确认 pass
- [ ] 3. **TDD red**: 写 case #11/12 (contract-check pass/breaking), case #13 (watch-hub), 跑确认 fail
- [ ] 4. **修复 #2**: `gh_hub_client.get_issue_status` `state_reason` → `stateReason`, 跑 #13 确认 pass
- [ ] 5. **修复 #3**: `gh_hub_client.batch_get_issues_status` 改为迭代 `get_issue_status`, 跑 #12 确认 pass
- [ ] 6. **修复 #4**: `watch_hub.py` 去除 broken subprocess, 跑 #13 确认 pass
- [ ] 7. **TDD green**: 跑全部 13 case 确认 13/13 通过, 单次 < 90s
- [ ] 8. **回归保护**: 跑 `python3 -m pytest tests/unit/test_gh_hub_client.py` 确认既有 3 个 case 全过
- [ ] 9. **回归保护**: 跑 `./test.sh --python --unit` 确认 133 个 unit test 全过
- [ ] 10. **回归保护**: 跑 `bats tests/integration/test_design_done_gate_hub.bats test_design_done_hub_gates.bats test_sync_hub.bats test_watch_hub.bats test_rddf_cross_repo_cli.bats test_rdd_hub_bootstrap.bats` 确认既有相关 test 全过
- [ ] 11. **AC-1 ~ AC-6 逐项 verify**: 跑 `./test.sh --full --regression` 确认全绿
- [ ] 12. **conventional commit**: `git commit -m "fix(federation): repair gh CLI integration for real cross-repo flow"` + 引用 AC
- [ ] 13. **archive**: `openspec archive fix-federation-gh-cli-integration --yes` 移动到 archive/

## Audit Trail

- 涉及 3 个文件改动: `skills/_lib/gh_hub_client.py`, `skills/watch-hub/scripts/watch_hub.py`, `tests/integration/test_cross_repo_e2e_real.bats` (new)
- 4 处 bug fix 全部由 e2e test 触发, 非推测性
- unit test mock 兼容性保留 (JSON fallback)
- 不引入新外部依赖
