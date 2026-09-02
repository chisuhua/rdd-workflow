# rfc-rddf-project-yaml-config-i10 — Implementation Tasks

> **里程碑拆分**：M1 → M2/M3/M4（并行）→ M5
> **TDD 纪律**：每个 task 遵循 Write failing test → Verify fail → Implement → Verify pass → Commit
> **状态**：0/25 (planned, awaiting execute 阶段)

## M1 — 配置基础设施 (基石)

- [ ] **Task 1.1** — 在 `_lib/schemas/config_schema.json` 增加 `project` 节 schema 定义（jsonschema）
- [ ] **Task 1.2** — `_lib/config.py` 新增 `_load_project_yaml()` helper（含 schema 校验）
- [ ] **Task 1.3** — `_lib/config.py::parse()` 插入 project.yaml 到 merge 顺序 `runtime > project.yaml > loop.yaml > env vars > .rddf.json > defaults`
- [ ] **Task 1.4** — `_lib/project_config.sh` 新建 sourced library（yq/python 双回退 + env-var 模式）
- [ ] **Task 1.5** — `_lib/core/defaults.py` 新增 `project` 字段默认值
- [ ] **Task 1.6** — 单测 `test_priority_project_yaml_over_loop_yaml`（TDD：先红后绿）
- [ ] **Task 1.7** — 单测 `test_project_yaml_missing_no_effect`（向后兼容）
- [ ] **Task 1.8** — 单测 `test_project_yaml_schema_validation_strict`（fail-closed）

## M2 — ADR 发现可配置 (依赖 M1)

- [ ] **Task 2.1** — `_lib/adr_catalog.py::scan_adr_catalog(..., adr_pattern=None)` 参数化
- [ ] **Task 2.2** — `_lib/discover-arch-artifacts.sh` Path 1.5 读 project.yaml（导出 `DISCOVERED_ADR_PATTERN`）
- [ ] **Task 2.3** — `populate_lib.py` / `roadmap_incremental_update.py` 透传 `adr_pattern` 参数
- [ ] **Task 2.4** — 单测 `test_three_digit_adr_pattern`（ChipForge 场景）
- [ ] **Task 2.5** — 单测 `test_adr_pattern_overrides_default`（向后兼容）
- [ ] **Task 2.6** — 集成测试 `test_discover_arch_artifacts_uses_project_yaml`

## M3 — openspec_tracked / 轻量模式 (依赖 M1)

- [ ] **Task 3.1** — `skills/guide-ship/SKILL.md` Phase 1 Step 1.5 读 `git.openspec_tracked` 并设置 `RDDF_EXECUTION_MODE=lightweight`
- [ ] **Task 3.2** — `_lib/ship_execution_mode.sh` 增加 project.yaml 检测分支
- [ ] **Task 3.3** — `_lib/archive.sh::archive_change()` 增加 `openspec_tracked=false` 分支（跳过 git merge/commit）
- [ ] **Task 3.4** — 集成测试 `tests/integration/test_guide_ship_execution_mode.bats` 新增 `openspec_tracked=false` 场景
- [ ] **Task 3.5** — 集成测试 `test_archive_with_openspec_tracked_false_skips_git_ops`

## M4 — verification hook (依赖 M1)

- [ ] **Task 4.1** — `_lib/verifier/hook_runner.py` 新建（含路径白名单 + 5 分钟 timeout）
- [ ] **Task 4.2** — `_lib/cli/rdd_verify_cmd.py` 增加 `provider=hook` 分支
- [ ] **Task 4.3** — `_lib/verifier/cache.py` 缓存键支持 hook 模式（SHA + command-hash）
- [ ] **Task 4.4** — 集成测试 `tests/integration/test_rdd_verifier.bats` 新增 `provider=hook` 场景
- [ ] **Task 4.5** — 单元测试 `test_hook_runner_path_whitelist`（安全检查）

## M5 — 文档 + 全量测试 (依赖 M2/M3/M4)

- [ ] **Task 5.1** — `README.md` 增加 `.rddf/project.yaml` 章节（含 ChipForge 示例）
- [ ] **Task 5.2** — `USAGE.md` 增加配置迁移指南（env var → project.yaml）
- [ ] **Task 5.3** — ChipForge 真实反馈采集（首个异构项目采用者）
- [ ] **Task 5.4** — `./test.sh --full --regression` 全绿后才允许 archive
- [ ] **Task 5.5** — 更新 ADR（如 `ADR-0036-project-level-config`）记录本次决策

## Cross-Milestone

- [ ] **Task X.1** — 里程碑 M1 完成后跑 `./test.sh --unit` 验证基础
- [ ] **Task X.2** — 里程碑 M2/M3/M4 完成后跑 `./test.sh --python --bats`
- [ ] **Task X.3** — 全部 task 完成后跑 `./test.sh --full --regression`（archive 前必须全绿）
