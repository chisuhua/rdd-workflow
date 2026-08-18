# fix-cli-routing-cross-repo-commands — Tasks

> Schema: spec-driven
> See: `proposal.md` (动机/范围) + `design.md` (技术决策).
> Source: Oracle review of ADR-0030/ADR-0031 (ses_fecf9715affebqMTQnuYJMEEL7) 2026-08-18.

## Implementation

- [x] 1. `_lib/cli/__init__.py::_ROUTES` 新增 3 条 entry（sync-hub / watch-hub / deps.cross-repo）
- [x] 2. `tests/integration/test_rddf_cli_routing.bats` 新增, 3 个 case 全绿
- [x] 3. `tests/unit/test_deps_cmd.py` 新增 cross-repo 路由分发 3 个 case
- [x] 4. 实跑 `rddf sync-hub --help` 返回帮助（不再是 "unknown command"）
- [x] 5. 实跑 `rddf watch-hub --help` 返回帮助
- [x] 6. 实跑 `rddf deps cross-repo --help` 返回帮助
- [x] 7. **既有回归**: `tests/integration/test_cli_routing.bats` 既有 22 个命令 case 全绿
- [x] 8. **既有回归**: `tests/unit/test_deps_cmd.py` 全绿
- [x] 9. **既有回归**: `./test.sh --full --regression` 通过
- [x] 10. **README 同步**: README §跨项目协同 章节示例命令更新为 `rddf sync-hub` / `rddf watch-hub` / `rddf deps cross-repo`
- [x] 11. **GitHub Actions 同步**: `.github/workflows/contract-check.yml` 若引用旧命令路径需更新
