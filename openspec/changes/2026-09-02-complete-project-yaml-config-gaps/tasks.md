# complete-project-yaml-config-gaps — Implementation Tasks

> **目标**: 补齐 `rfc-rddf-project-yaml-config-i10` 8 项 checkbox-as-done 缺口
> **TDD 纪律**: 每个 task 遵循 Write failing test → Verify fail → Implement → Verify pass → Commit
> **修复对照**: `openspec/changes/archive/2026-09-02-rfc-rddf-project-yaml-config-i10/tasks.md` 23/25 done

## M1 — Schema + Defaults 加固 (补 i10 M1 Task 1.1, 1.5)

### Task 1.1 — config_schema.json 新增 4 节 (TDD, per design.md Decision 11)

- [x] **1.1.1** Write failing test: `tests/unit/test_config.py::test_project_yaml_schema_strict_raises` — 写 `.rddf/project.yaml` 含 `git: {openspec_tracked: "yes"}`(string 而非 bool),assert `ConfigError` raise
- [x] **1.1.2** Verify fail: `pytest tests/unit/test_config.py::test_project_yaml_schema_strict_raises -xvs` 确认 fail (当前 schema 无 git 节,字段静默通过)
- [x] **1.1.3** Implement: `_lib/schemas/config_schema.json` 在 `properties` 下新增 4 节(根级 `additionalProperties: true` 保留,新节内部 `additionalProperties: false`):
  - `project` (`type: object`, `additionalProperties: false`, 子字段 `name: string` / `version: string`)
  - `adr` (`type: object`, `additionalProperties: false`, 子字段 `pattern: string` / `glob: string` / `dir: string`)
  - `git` (`type: object`, `additionalProperties: false`, 子字段 `openspec_tracked: {type: boolean}`)
  - `verification` (`type: object`, `additionalProperties: false`, 子字段 `provider: {enum: [llm, hook]}`)
- [x] **1.1.4** Verify pass: 重跑测试确认 pass
- [x] **1.1.5** Commit: `feat(config-schema): add project/adr/git/verification sections for jsonschema validation` (commit `ce16f6f`)

### Task 1.1a — 根级 extras 零回归 (TDD, Metis 歧义 #4 防御)

- [x] **1.1a.1** Write failing test: `tests/unit/test_config.py::test_project_yaml_root_level_extras_allowed` — `.rddf/project.yaml` 含 `my_custom_tooling: {x: 1}` 根级 extras,assert `ConfigParser.parse()` 成功
- [x] **1.1a.2** Verify fail: 当前可能 fail(需实测);目标 pass — 根级 loose 须保持
- [x] **1.1a.3** Implement: N/A(根级 `additionalProperties` 已是默认 `true`,无需代码改动)
- [x] **1.1a.4** Verify pass: 确认 pass
- [x] **1.1a.5** Commit: `test(config): lock zero-regression for project.yaml root-level extras` (commit `e38df95`)

### Task 1.2 — defaults.py 新增 project 默认 (TDD)

- [x] **1.2.1** Write failing test: `tests/unit/test_config.py::test_project_defaults_present` — assert `get_defaults()['project']` 是 dict
- [x] **1.2.2** Verify fail: 当前 `DEFAULTS` 无 `project` 键,测试 fail
- [x] **1.2.3** Implement: `_lib/core/defaults.py::DEFAULTS` 新增 `"project": {}`(空 dict 占位;非 `None`,避免 `_set_dotted` 报错)
- [x] **1.2.4** Verify pass: 重跑确认 pass
- [x] **1.2.5** Commit: `feat(config): add project default empty dict to DEFAULTS` (commit `2eaaab7`)

### Task 1.3 — schema 严格性回归门 (TDD)

- [x] **1.3.1** Write failing test: `tests/unit/test_config.py::test_project_yaml_invalid_verification_provider_raises` — `verification: {provider: foo}` → `ConfigError`(enum 仅 llm/hook)
- [x] **1.3.2** Verify fail: 确认 fail (当前 schema 无 verification 节)
- [x] **1.3.3** Implement: 复用 Task 1.1.3 的 schema (无需新代码)
- [x] **1.3.4** Verify pass: 重跑确认 pass
- [x] **1.3.5** Commit: `test(config): add cross-section strict validation + positive control tests` (commit `8ae289a`)

### Task 1.4 — 向后兼容零回归 (TDD)

- [x] **1.4.1** Write test: `tests/unit/test_config.py::test_no_project_yaml_unchanged_behavior` — 无 `.rddf/project.yaml`,assert 现有 behavior 不变(全 `defaults` 字段相同)
- [x] **1.4.2** Verify pass: 当前已 pass (确认 schema strict 不破坏缺失 case)
- [x] **1.4.3** Implement: N/A (仅验证)
- [x] **1.4.4** Commit: `test(config): add backward compat zero-alignment regression locks` (commit `b0b2829`)

## M2 — Hook Runner 接线 (补 i10 M4 Task 4.2, 4.3, 4.4)

### Task 2.1 — rdd_verify_cmd 读 project.yaml verification.provider (TDD)

- [x] **2.1.1** Write failing test: `tests/unit/test_rdd_verify_cmd.py::test_detect_verification_provider_default_llm` — 无 project.yaml → 返回 "llm"
- [x] **2.1.2** Verify fail: 当前函数不存在,测试 fail (ImportError)
- [x] **2.1.3** Implement: `_lib/cli/rdd_verify_cmd.py` 新增 `_detect_verification_provider(project_root: Path) -> str` 函数
- [x] **2.1.4** Verify pass: 重跑确认 pass
- [x] **2.1.5** Commit: `feat(verifier): wire rdd_verify_cmd to hook_runner when verification.provider=hook` (commit `13ac217`, batched with 2.2/2.3/2.6)

### Task 2.2 — _hook_runner 函数 + cmd_rdd_verify 分支 (TDD)

- [x] **2.2.1** Write failing test: `tests/unit/test_rdd_verify_cmd.py::test_hook_runner_passed_returns_exit_0` — 临时 `tools/verify_change.sh` echo + exit 0 → `_hook_runner(change, project_root)` 返回 `{"exit_code": 0, "verdict": [{"ac_id": "hook-...", "status": "pass"}]}`
- [x] **2.2.2** Verify fail: 当前 `_hook_runner` 不存在,测试 fail
- [x] **2.2.3** Implement: `_lib/cli/rdd_verify_cmd.py` 新增 `_hook_runner(change_name, project_root, *, hook_path=None) -> dict`,内部调 `from _lib.verifier.hook_runner import run_verification_hook`,按 verdict 映射 exit code
- [x] **2.2.4** Verify pass: 重跑确认 pass
- [x] **2.2.5** Commit: `feat(verifier): wire rdd_verify_cmd to hook_runner when verification.provider=hook` (commit `13ac217`)

### Task 2.3 — cmd_rdd_verify 选择 runner (TDD)

- [x] **2.3.1** Write failing test: `tests/unit/test_rdd_verify_cmd.py::test_cmd_rdd_verify_uses_hook_runner_when_provider_hook` — 创建临时 project.yaml 设 `verification.provider: hook`,mock queue,验证 runner 是 `_hook_runner`
- [x] **2.3.2** Verify fail: 当前 `cmd_rdd_verify` 不读 provider,测试 fail
- [x] **2.3.3** Implement: `cmd_rdd_verify()` 在 `for change in queue:` 循环内增加 `provider = _detect_verification_provider(...)`, `active_runner = runner or (_hook_runner if provider == "hook" else _default_runner)`
- [x] **2.3.4** Verify pass: 重跑确认 pass
- [x] **2.3.5** Commit: `feat(verifier): wire rdd_verify_cmd to hook_runner when verification.provider=hook` (commit `13ac217`)

### Task 2.4 — cache.py cache_key hook 分支 (TDD)

- [x] **2.4.1** Write failing test: `tests/unit/test_verifier_cache_v2.py::test_cache_key_hook_differs_from_llm` — `cache_key("c", root, provider="hook", hook_path=...)` != `cache_key("c", root, provider="llm")`
- [x] **2.4.2** Verify fail: 当前 `cache_key()` 不存在,测试 fail
- [x] **2.4.3** Implement: `_lib/verifier/cache.py::cache_key()` 新增 `provider: str = "llm"` 和 `hook_path: Optional[Path] = None` 参数,provider="hook" 时 payload 含 hook path
- [x] **2.4.4** Verify pass: 重跑确认 pass
- [x] **2.4.5** Commit: `feat(verifier): cache.py cache_key supports provider=hook with SHA+command-hash` (commit `c0949fe`)

### Task 2.5 — 集成测试 provider=hook (TDD)

- [x] **2.5.1** Write failing test: `tests/integration/test_rdd_verifier_hook_provider.bats`:
  - Case 1: project.yaml 设 `verification.provider: hook`,`tools/verify_change.sh` exit 0 → `rddf rdd-verify <change>` exit 0
  - Case 2: exit 1 → exit 1 (failed)
  - Case 3: exit 2 → exit 3 (error)
  - Case 4: missing tools/verify_change.sh → rc 0 (skipped)
  - Case 5: hook_path 在 `tools/` 之外 → HookPathError
  - Case 6: cache_key isolation (provider=hook vs llm)
  - Case 7: default-provider routing (no project.yaml → LLM)
- [x] **2.5.2** Verify fail: bats 测试文件不存在,skip 或 fail
- [x] **2.5.3** Implement: 7 个 @test case + load `test_helper` + 临时 `$TEST_TMP` 创建 mock project.yaml + tools/verify_change.sh
- [x] **2.5.4** Verify pass: `bats tests/integration/test_rdd_verifier_hook_provider.bats` 全绿 (7/7)
- [x] **2.5.5** Commit: `test(verifier): integration tests for provider=hook with exit code mapping and cache` (commit `2495b71`)

## M3 — Guide-Ship Phase 1 + ship_execution_mode 加固 (补 i10 M3 Task 3.1, 3.2, 3.4, 3.5)

### Task 3.1 — guide-ship SKILL.md Phase 1 Step 1.5 (TDD)

- [x] **3.1.1** Write failing test: `tests/integration/test_guide_ship_phase1_project_yaml.bats` — grep SKILL.md 验证 Step 1.5 存在 + 含 "openspec_tracked" + 含 "RDDF_EXECUTION_MODE=lightweight"
- [x] **3.1.2** Verify fail: 当前 SKILL.md 无 Step 1.5,grep fail
- [x] **3.1.3** Implement: `skills/guide-ship/SKILL.md` Phase 1 在 Step 2 worktree 创建之前新增 Step 1.5 (per design.md Decision 4 bash 块)
- [x] **3.1.4** Verify pass: grep 测试 pass
- [x] **3.1.5** Commit: `feat(ship): guide-ship Phase 1 Step 1.5 reads project.yaml openspec_tracked` (commit `7be7ab6`)

### Task 3.2 — ship_execution_mode.sh project.yaml 分支 (TDD)

- [x] **3.2.1** Write failing test: `tests/integration/test_ship_execution_mode_reads_project_yaml.bats::test_openspec_tracked_false_forces_serial` — 创建 mock project.yaml 设 `git.openspec_tracked: false`,跑 `bash _lib/ship_execution_mode.sh parse_execution_mode`,assert 输出 "serial"
- [x] **3.2.2** Verify fail: 当前 `parse_execution_mode` 不读 project.yaml,测试 fail
- [x] **3.2.3** Implement: `_lib/ship_execution_mode.sh::parse_execution_mode()` 在 CLI flag 之后、env var 之前增加 project.yaml 检测 (per design.md Decision 5)
- [x] **3.2.4** Verify pass: 重跑确认 pass
- [x] **3.2.5** Commit: `feat(ship): parse_execution_mode reads project.yaml openspec_tracked` (commit `1b42454`)

### Task 3.3 — test_guide_ship_execution_mode.bats 新增 3 case (TDD)

- [x] **3.3.1** Write failing test: 3 个 @test case:
  - `openspec_tracked=false` 在 SKILL.md 中存在
  - `RDDF_EXECUTION_MODE=lightweight` 在 SKILL.md 中存在 (Step 1.5 检测的产物)
  - `project_yaml_get "git.openspec_tracked"` 调用在 SKILL.md 中存在
- [x] **3.3.2** Verify fail: 当前 12 个 case 无此场景
- [x] **3.3.3** Implement: 在 `tests/integration/test_guide_ship_phase1_project_yaml.bats` 新建 (4 cases 涵盖 Step 1.5 全部内容)
- [x] **3.3.4** Verify pass: `bats tests/integration/test_guide_ship_phase1_project_yaml.bats` 4 个 case 全绿 (与 Task 3.1 共享 commit `7be7ab6`)
- [x] **3.3.5** Commit: `feat(ship): guide-ship Phase 1 Step 1.5 reads project.yaml openspec_tracked` (commit `7be7ab6`)

### Task 3.4 — archive_with_openspec_tracked_false.bats (TDD,补 i10 Task 3.5)

- [x] **3.4.1** Write failing test: `tests/integration/test_archive_with_openspec_tracked_false.bats`:
  - Case 1: project.yaml 设 `git.openspec_tracked: false`,创建 worktree + commits,跑 `archive_change`,assert 无 `git merge` 调用 + 无 `commit_archive_moves` + 仅 `openspec archive` + `mark_iteration_archived`
  - Case 2: `git.openspec_tracked: true`(默认),跑同样 archive,assert 走 merge 路径
- [x] **3.4.2** Verify fail: bats 文件不存在
- [x] **3.4.3** Implement: 3 个 @test case + mock setup/teardown (含 YAML bool "False" → 字符串 "false" 兼容修复)
- [x] **3.4.4** Verify pass: bats 全绿 (3/3)
- [x] **3.4.5** Commit: `test(archive): integration tests for openspec_tracked=false skipping git operations` (commit `9098a73`)

### Task 3.5 — ship_execution_mode_reads_project_yaml.bats (TDD)

- [x] **3.5.1** Write failing test: `tests/integration/test_ship_execution_mode_reads_project_yaml.bats`:
  - Case 1: CLI flag `--parallel` > project.yaml `openspec_tracked: false` → 输出 "parallel"(CLI 优先级最高)
  - Case 2: project.yaml `openspec_tracked: false` > env `RDD_SHIP_PARALLEL=yes` → 输出 "serial"(project.yaml 第二优先级)
  - Case 3: 仅 env `RDD_SHIP_PARALLEL=yes` → 输出 "parallel"
  - Case 4: 无 project.yaml + 无 env → 输出 "serial"(默认)
- [x] **3.5.2** Verify fail: bats 文件不存在
- [x] **3.5.3** Implement: 5 个 @test case + mock $BATS_TMPDIR/.rddf/project.yaml + symlink _lib/project_config.sh
- [x] **3.5.4** Verify pass: bats 全绿 (5/5)
- [x] **3.5.5** Commit: `feat(ship): parse_execution_mode reads project.yaml openspec_tracked` (commit `1b42454`, batched with 3.2)

## M4 — populate_lib 透传 + i10 M2 deferred 项 (补 i10 M2 Task 2.3, 2.6)

### Task 4.1 — populate_lib.py 透传 adr_pattern (TDD, 接收 i10 deferred)

- [ ] **4.1.1** Write failing test: `tests/unit/test_populate_lib.py::test_catalog_sources_uses_adr_pattern_from_handoff` — mock `.rddf/state/.arch-handoff.json` 含 `adr_pattern: "^ADR-(\\d{3})-.*\\.md$"`,跑 `catalog_sources(project_root)`,assert `scan_adr_catalog` 接收此 pattern
- [ ] **4.1.2** Verify fail: 当前 `catalog_sources` 无 `adr_pattern` 参数
- [ ] **4.1.3** Implement: `populate_lib.py::catalog_sources` 新增 `adr_pattern=None` 参数,优先级: 入参 > arch-handoff > 默认 4 位
- [ ] **4.1.4** Verify pass: 重跑确认 pass
- [ ] **4.1.5** Commit: `feat(populate): catalog_sources accepts adr_pattern from arch-handoff`

### Task 4.2 — roadmap_incremental_update 透传 (TDD)

- [ ] **4.2.1** Write failing test: `tests/unit/test_roadmap_incremental_update.py::test_incremental_update_passes_adr_pattern` — mock handoff + ADR-040 文件,跑 `incremental_update`,assert 3 位 pattern 生效(识别 ADR-040)
- [ ] **4.2.2** Verify fail: 当前 `incremental_update` 硬编码 4 位
- [ ] **4.2.3** Implement: `_lib/roadmap_incremental_update.py::incremental_update()` 从 arch-handoff 读 adr_pattern,透传给 catalog_sources
- [ ] **4.2.4** Verify pass: 重跑确认 pass
- [ ] **4.2.5** Commit: `feat(roadmap): incremental_update passes adr_pattern from handoff`

### Task 4.4 — populate_lib project.yaml fallback (TDD, Metis 额外缺口 + Decision 9 fallback)

- [ ] **4.4.1** Write failing test: `tests/unit/test_populate_lib.py::test_catalog_sources_fallback_to_project_yaml_when_handoff_missing_adr_pattern` — arch-handoff 存在但无 `adr_pattern` 字段,且 `.rddf/project.yaml` 含 `adr.pattern`,assert `catalog_sources` 使用 project.yaml 的 pattern
- [ ] **4.4.2** Verify fail: 当前 `catalog_sources` 仅读 handoff,fallback 不存在
- [ ] **4.4.3** Implement: `populate_lib.py::catalog_sources()` 在 arch-handoff 无 adr_pattern 时,直接读 `.rddf/project.yaml` 的 `adr.pattern` (Priority 2)
- [ ] **4.4.4** Verify pass: 重跑确认 pass
- [ ] **4.4.5** Commit: `feat(populate): catalog_sources falls back to project.yaml when handoff missing adr_pattern`

### Task 4.5 — arch_handoff_schema.json v1→v2 bump (TDD, Task 4.4 副作用)

- [ ] **4.5.1** Write failing test: `tests/unit/test_arch_handoff_schema.py::test_v2_includes_adr_pattern` — `adr_handoff_schema["properties"]["adr_pattern"]` 存在
- [ ] **4.5.2** Verify fail: 当前 schema v1 无 `adr_pattern` 字段
- [ ] **4.5.3** Implement: `_lib/schemas/arch_handoff_schema.json` bump `version: 1` → `version: 2`,在 `properties` 下新增 `adr_pattern: {type: string}` optional 字段
- [ ] **4.5.4** Verify pass: 重跑确认 pass
- [ ] **4.5.5** Commit: `feat(schema): arch_handoff_schema v1→v2 adds adr_pattern optional field`

### Task 4.6 — arch-handoff 写方补 adr_pattern (TDD,Task 4.5 配套)

- [ ] **4.6.1** Write failing test: `tests/unit/test_write_arch_handoff.py::test_write_arch_handoff_includes_adr_pattern` — `write_arch_handoff()` 读 `.rddf/project.yaml` 的 `adr.pattern`,写入 handoff
- [ ] **4.6.2** Verify fail: 当前 `write_arch_handoff()` 不读 project.yaml
- [ ] **4.6.3** Implement: `guide-arch/scripts/write_arch_handoff.{sh,py}` 在写 handoff 前读 project.yaml `adr.pattern`,如有则写入 `adr_pattern` 字段
- [ ] **4.6.4** Verify pass: 重跑确认 pass
- [ ] **4.6.5** Commit: `feat(arch): write_arch_handoff reads project.yaml adr_pattern`

### Task 2.6 — 显式 runner override 测试 (TDD, Metis 歧义 #1)

- [x] **2.6.1** Write failing test: `tests/unit/test_rdd_verify_cmd.py::test_explicit_runner_overrides_provider_hook` — `cmd_rdd_verify(args, runner=mock_runner)`,project.yaml 设 `verification.provider: hook`,assert mock_runner 被调用而 `_hook_runner` 未被调用
- [x] **2.6.2** Verify fail: 当前 `cmd_rdd_verify` 无 provider 检测,测试可能因不同原因 fail
- [x] **2.6.3** Implement: `cmd_rdd_verify` 按 Decision 8 实现显式 runner 优先级 (`if runner is not None: active_runner = runner else: ...`)
- [x] **2.6.4** Verify pass: 重跑确认 pass
- [x] **2.6.5** Commit: `feat(verifier): wire rdd_verify_cmd to hook_runner when verification.provider=hook` (commit `13ac217`, batched with 2.1/2.2/2.3)

### Task 4.3 — discover_arch_artifacts 集成测试 (TDD, 接收 i10 Task 2.6 deferred)

- [ ] **4.3.1** Write failing test: `tests/integration/test_discover_arch_artifacts_uses_project_yaml.bats`:
  - Case 1: project.yaml 设 `adr.pattern: "ADR-\\d{3}"`,mock ADR-040/041/042 文件 + ADR-0001(4 位),跑 `discover_adr_pattern`,assert 输出 3 位 pattern
  - Case 2: env `SPEC_WORKFLOW_ADR_PATTERN="ADR-*.md"` > project.yaml → 输出 env 值(env 优先级最高)
  - Case 3: 无 project.yaml + 无 env → 输出 "ADR-*.md"(默认)
- [ ] **4.3.2** Verify fail: bats 文件不存在
- [ ] **4.3.3** Implement: 3 个 @test case + load `test_helper` + mock $PROJECT_ROOT/.rddf/project.yaml
- [ ] **4.3.4** Verify pass: bats 全绿
- [ ] **4.3.5** Commit: `test(arch): integration tests for discover_adr_pattern reads project.yaml`

## Cross-Milestone

- [x] **X.1** M1 完成后跑 `./test.sh --unit` 验证 schema 严格性(预期 2421 + 6 新 = 2427 passed) — **实际 2431 passed** (含 10 新测试,超预期 +4)
- [x] **X.2** M2 完成后跑 `./test.sh --quick` 验证 hook 接线(预期新 ~17 case 全绿) — **实际 2448 passed + 7/7 bats 全绿**
- [ ] **X.3** M3/M4 完成后跑 `./test.sh --full --regression`(archive 前必须全绿,per AGENTS.md §"Archive 前全量回归门 MANDATORY")
- [ ] **X.4** 更新 ADR-0036 — 在原 Consequences 节 **后**新增 `## Post-hoc Fix Record (2026-09-02)` 节(per design.md Decision 10),**不追加到 Consequences**。内容指向本 change + commit hash + 8 项缺口对照表
- [ ] **X.5** 更新 `proposal-approved.md` 表格登记本 change 为 P1 已批准
- [ ] **X.6 (MANDATORY)** 新增 `tests/integration/test_archive_gate_tasks_checklist_match.bats`:archive 前 file-level diff vs tasks.md 复核,**预防 checkbox-as-done 复发**(本 change 根因预防)。per design.md Decision 7 — 此 task 由原"可选"可升级为 MANDATORY,作为根治机制

## 状态追踪

- **M1 完成进度**: 5/5 done ✅ (2026-09-02 实施)
  - Task 1.1: schema 4 节 + 3 测试 (commit `ce16f6f`)
  - Task 1.1a: 根级 extras 锁 (commit `e38df95`)
  - Task 1.2: defaults `project: {}` + 2 测试 (commit `2eaaab7`)
  - Task 1.3: 跨章节严格性锁 (commit `8ae289a`)
  - Task 1.4: 向后兼容锁 (commit `b0b2829`)
- **M2 完成进度**: 6/6 done ✅ (2026-09-02 实施)
  - Task 2.1/2.2/2.3/2.6: _detect_verification_provider + _hook_runner + cmd_rdd_verify 接线 (commit `13ac217`, batched 12 tests)
  - Task 2.4: cache.py cache_key hook 分支 (commit `c0949fe`, 5 tests)
  - Task 2.5: 集成测试 (commit `2495b71`, 7 bats cases)
- **M3 完成进度**: 5/5 done ✅ (2026-09-02 实施)
  - Task 3.1 + 3.3: guide-ship SKILL.md Phase 1 Step 1.5 (commit `7be7ab6`, 4 bats cases)
  - Task 3.2 + 3.5: ship_execution_mode.sh reads project.yaml (commit `1b42454`, 5 bats cases)
  - Task 3.4: archive.sh openspec_tracked=false + YAML bool 修复 (commit `9098a73`, 3 bats cases)
- **总进度**: 14/28 done (M1+M2+M3 完成;M4 待实施)
- **风险 task**: Task 4.5 (schema bump 跨版本兼容)

## 状态追踪

- **Total tasks**: 22 个 (M1: 4 + M2: 5 + M3: 5 + M4: 3 + X: 6,可选 X.6)
- **完成进度**: 0/22 done (待实施)
- **风险 task**: Task 2.3 (cache 键变更) + Task 3.1 (SKILL.md 修改影响范围广)

## 防 checkbox-as-done 原则

> **AGENTS.md §"Archive 前全量回归门 (MANDATORY)"** 要求 `./test.sh --full --regression` 全绿。
> 但 archive 流程未强制 file-level diff vs tasks.md 复核,导致 i10 出现 8 项 checkbox-as-done。

**本 change 实施纪律**:

1. 每个 task 实施后,run `git diff main..HEAD --stat` 验证 task 引用的文件实际出现在 diff 中
2. PR description 必须列出每个 task 对应 commit hash
3. review 时 review-changes skill 检查"task done ↔ file 变更"对应关系
4. 可选 Task X.6: archive 时自动跑 `test_archive_gate_tasks_checklist_match.bats`,任何不对应 → fail