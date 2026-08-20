## Implementation Tasks

- [x] T1: 创建 `_lib/cli/doctor_cmd.py` — 薄包装: 暴露 `rddf doctor [--json] [--category <name>] [--quiet] [--version]`, 转发到 `bash skills/rdd-doctor/scripts/doctor.sh "$@"`, 透传 exit code
- [x] T2: 创建 `_lib/cli/roadmap_cmd.py` — 薄包装: 暴露 `rddf roadmap <sub>`, 子命令分发表 (migrate → roadmap_migrate.sh, validate-fragments → roadmap_validate_fragments.sh), 透传 exit code
- [x] T3: 创建 `_lib/cli/rdd_hub_bootstrap_cmd.py` — 薄包装: 暴露 `rddf rdd-hub-bootstrap [init|status|...] [--dry-run|--yes|--org|--repo]`, 转发到 `bash skills/rdd-hub-bootstrap/scripts/*.sh`, 透传 exit code
- [x] T4: 在 `_lib/cli/__init__.py` 注册 3 行路由表: `"doctor": cmd_doctor, "roadmap": cmd_roadmap, "rdd-hub-bootstrap": cmd_rdd_hub_bootstrap`
- [x] T5: 新增 `tests/integration/test_cli_coverage.bats` (7-8 个测试: --help 完整性 / exit code 透传 / --version / subcommand 列表)
- [x] T6: 运行 `./test.sh --quick` 全绿 (零回归) + `lsp_diagnostics` 干净
- [x] T7: 验证 AC-1~AC-10 全部满足