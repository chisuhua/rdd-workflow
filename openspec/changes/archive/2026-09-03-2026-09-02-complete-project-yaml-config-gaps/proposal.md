# complete-project-yaml-config-gaps

## Why

`rfc-rddf-project-yaml-config-i10` 已于 2026-09-02 archive，但其 `tasks.md` 报告 **23/25 done** 与代码实际状态不符 — 经审计发现 **8 项 task 标记完成但代码未实际落地**（详见 `.rddf/improvements/complete-project-yaml-config-gaps.md` 调研证据）：

1. **`config_schema.json` 缺 `project` 节** — Task 1.1 标记 done，但 `_lib/schemas/config_schema.json` 仅 183 行，未包含 `project` / `adr` / `git` / `verification` schema 定义。`ConfigParser._validate_schema()` 跑 jsonschema 校验时完全不验证这些字段**，破坏 design.md Decision 6 "fail-closed" 承诺**。
2. **`core/defaults.py` 缺 `project` 默认值** — Task 1.5 标记 done，但 `_lib/core/defaults.py` `DEFAULTS` dict 不含 `project` 键。`_load_project_yaml` 返回 dict 后无默认值兜底，存在项目级字段空值时行为不一致。
3. **`hook_runner.py` 是孤儿代码** — Task 4.1 创建了 `_lib/verifier/hook_runner.py` (97 行, 含路径白名单 + 5min timeout)，但 Task 4.2 (`rdd_verify_cmd.py` `provider=hook` 分支) **未实现** — `grep -rn "hook_runner" _lib/ skills/` 整库仅 1 命中（hook_runner.py 自身）。ChipForge 配置 `verification.provider: hook` 后 `rddf rdd-verify` **实际不会调用 hook**，用户以为 LLM 验证被替代实际未替代。
4. **`guide-ship` Phase 1 不读 project.yaml** — Task 3.1 标记 done，但 `skills/guide-ship/SKILL.md` 中 `grep openspec_tracked` **0 命中**。用户配 `git.openspec_tracked: false` 后,worktree 创建仍按默认路径走，仅在 archive 阶段才会跳过 git merge/commit（Task 3.3 已实现）。**半实现状态** — 用户可能走到 archive 才发现行为不同。
5. **`ship_execution_mode.sh` 无 project.yaml 分支** — Task 3.2 标记 done，但 `_lib/ship_execution_mode.sh` 中 `grep openspec_tracked` **0 命中**。`parse_execution_mode` 不读 project.yaml，仅 CLI/env 决定。
6. **3 项集成测试缺失**：
   - Task 3.4 (`tests/integration/test_guide_ship_execution_mode.bats` 新增 `openspec_tracked=false` 场景) — **未实现**，12 个现有 case 无此场景。
   - Task 3.5 (`test_archive_with_openspec_tracked_false_skips_git_ops`) — **未实现**。
   - Task 4.4 (`tests/integration/test_rdd_verifier.bats` 新增 `provider=hook` 场景) — **未实现**。
7. **2 项 follow-up 测试缺失**（属 i10 已 deferred 项，本 change 升级）：
   - Task 2.3 (`populate_lib.py` / `roadmap_incremental_update.py` 透传 `adr_pattern`) — i10 标记 deferred，本 change 接收。
   - Task 2.6 (`test_discover_arch_artifacts_uses_project_yaml` 集成测试) — i10 标记 deferred，本 change 接收。
8. **cache 键未支持 hook 模式** — Task 4.3 (`_lib/verifier/cache.py` 缓存键支持 hook SHA + command-hash) — `hook_runner.cache_key()` 在 `_lib/verifier/hook_runner.py:81-97` 已实现，但 `_lib/verifier/cache.py::cache_key()` 未集成 — 即使 Task 4.2 实现后,hook 模式 verdict 仍无法按 SHA+command 缓存。

**Metis 评审补充 (2026-09-02)**: 提案初版完成后,Metis pre-planning consultant 审查发现 6 项 BLOCKER/HIGH 歧义 + 4 项额外缺口 (见 design.md Decision 8-11 + arch-handoff staleness Risk):

- **歧义 #1** (BLOCKER): `cmd_rdd_verify` 显式 `runner` 参数与 provider 自动检测的优先级 → Decision 8: 显式 runner 永远胜出
- **歧义 #2** (HIGH): `RDDF_EXECUTION_MODE` env var 与 `ship_execution_mode.sh` 的关系 → Decision 9: env var 是 Phase 1 输出,不是 `parse_execution_mode` 输入
- **歧义 #4** (HIGH): schema strict 模式破坏现有 root-level extras 用户 → Decision 11: 根级 `additionalProperties: true` 保留,新节内部 strict
- **歧义 #6** (HIGH): ADR-0036 §Consequences append 缺先例 → Decision 10: 新增 `## Post-hoc Fix Record (2026-09-02)` 节
- **额外缺口 #1**: `_detect_verification_provider` 函数不存在 → Task 2.1 新增
- **额外缺口 #2**: `_hook_runner` 函数不存在 → Task 2.2 新增
- **额外缺口 #3**: `test_rdd_verifier_hook_provider.bats` 缺失 → Task 2.4 新增
- **额外缺口 #4**: arch-handoff 过期时无 fallback → 新增 Task 4.4 + Task 4.5 schema bump + Task 4.6 写方补字段
- **根因预防升级**: 原"可选" Task X.6 升级为 MANDATORY (per Decision 7),因本 change 根因即 checkbox-as-done,预防机制必须强制

**风险评估**（per rdd-doctor severity 映射）：

| 缺口 | 严重度 | 影响 |
|------|--------|------|
| Hook 是孤儿代码 | 🔴 P0 | ChipForge 用户配 `verification.provider: hook` 后无效果，**违反 ADR-0036 承诺** |
| `config_schema.json` 无 project 节 | 🟠 P1 | `project.yaml` 字段类型错误静默通过，破坏 fail-closed |
| guide-ship Phase 1 不读 | 🟠 P1 | 用户配 `openspec_tracked: false` 后行为不一致，archive 阶段才发现 |
| `ship_execution_mode.sh` 不读 | 🟡 P2 | wave 执行模式不受 project.yaml 控制 |
| 3 项集成测试缺失 | 🟡 P2 | 集成路径无回归门控 |
| defaults.py 无 project 默认 | 🟢 P3 | 缺失 project 默认值时行为依赖空 dict fallback |
| 2 项 deferred 测试 | 🟢 P3 | i10 已 deferred，接收 |

**根因分析**：`rfc-rddf-project-yaml-config-i10` 实施时由 4 个里程碑 (M1→M2/M3/M4→M5) 跨 PR 合并，可能在某个合并步骤 commit-level 误勾了 checkbox 而非 file-level 验证。AGENTS.md §"Archive 前全量回归门（MANDATORY）" 强制 `./test.sh --full --regression`，但 archive 流程未强制 file-level diff vs tasks.md 复核。

**影响范围**：

- **下游消费者**：所有 `.rddf/project.yaml` 实际用户（当前 ChipForge 为首）
- **CI / CI gate**：`openspec-gate` 不受影响（不涉及 staged source 文件与 active change 关联）
- **rdd-verifier**：M4 hook 未连接 → rdd-verifier 仍走 LLM 路径，与项目配置语义脱节

## What Changes

**In Scope（10 个修复 task，按依赖关系分 3 个里程碑）**：

### M1 — Schema + Defaults 加固（补 i10 M1 缺口，无依赖）

- **Task 1.1** `_lib/schemas/config_schema.json` 新增 `project` / `adr` / `git` / `verification` 4 个 schema 节（jsonschema Draft-07）
- **Task 1.2** `_lib/core/defaults.py::DEFAULTS` 新增 `project` 字段默认值（空 dict，仅为占位结构）
- **Task 1.3** 单测 `test_project_yaml_schema_validation_strict` (Task 1.8 originally) — 字段类型错误 raise `ConfigError`
- **Task 1.4** 单测 `test_project_defaults_present` — `get_defaults()['project']` 是 dict

### M2 — Hook Runner 接线（补 i10 M4 缺口，依赖 M1 schema 完成以支持字段验证）

- **Task 2.1** `_lib/cli/rdd_verify_cmd.py::cmd_rdd_verify()` 读 `verification.provider` 字段 → 选择 runner
- **Task 2.2** `_lib/cli/rdd_verify_cmd.py` 新增 `_hook_runner()` 函数（调用 `hook_runner.run_verification_hook`，转换 verdict → `_default_runner` 同格式 dict）
- **Task 2.3** `_lib/verifier/cache.py::cache_key()` 增加 `provider=hook` 分支（SHA + command-hash）
- **Task 2.4** 集成测试 `tests/integration/test_rdd_verifier_hook_provider.bats` 新建（provider=hook + 退出码映射 + 缓存复用 + 路径白名单）
- **Task 2.5** 单测 `test_rdd_verify_cmd_uses_hook_runner_when_provider_hook`

### M3 — Guide-Ship Phase 1 + ship_execution_mode 加固（补 i10 M3 缺口，独立）

- **Task 3.1** `skills/guide-ship/SKILL.md` Phase 1 Step 1.5 新增：读 `git.openspec_tracked`，false → 设 `RDDF_EXECUTION_MODE=lightweight`
- **Task 3.2** `_lib/ship_execution_mode.sh::parse_execution_mode()` 增加 project.yaml 检测分支（CLI flag > project.yaml > env var > default）
- **Task 3.3** 集成测试 `tests/integration/test_guide_ship_execution_mode.bats` 新增 `openspec_tracked=false` 场景（3 个 case：worktree 跳过提示 / archive 不报 git 错误 / 单 PR 路径）
- **Task 3.4** 集成测试 `tests/integration/test_archive_with_openspec_tracked_false.bats` 新建（archive 阶段不触发 git merge/commit）
- **Task 3.5** 集成测试 `tests/integration/test_ship_execution_mode_reads_project_yaml.bats` 新建（CLI flag > project.yaml > env）

### M4 — ADR 发现透传（接收 i10 M2 deferred 项，独立）

- **Task 4.1** `populate_lib.py` / `roadmap_incremental_update.py` 透传 `adr_pattern` 参数（来自 `.rddf/state/.arch-handoff.json`）
- **Task 4.2** 集成测试 `test_discover_arch_artifacts_uses_project_yaml`（i10 M2 Task 2.6 deferred，本 change 实施）
- **Task 4.4** `populate_lib.py::catalog_sources` 增加 fallback（Metis 额外缺口 + Decision 9 Risk）— handoff 缺 `adr_pattern` 时直接读 `.rddf/project.yaml` 的 `adr.pattern`
- **Task 4.5** `_lib/schemas/arch_handoff_schema.json` v1→v2 bump，新增 `adr_pattern` optional 字段
- **Task 4.6** `guide-arch/scripts/write_arch_handoff` 写 handoff 时读 `.rddf/project.yaml` 的 `adr.pattern`（如有）写入 `adr_pattern` 字段

### M2 补充 — 显式 runner override（Metis 歧义 #1）

- **Task 2.6** `cmd_rdd_verify` 显式 `runner` 参数优先级测试（per design.md Decision 8）

### M1 补充 — 根级 extras 零回归（Metis 歧义 #4 防御）

- **Task 1.1a** 根级 `additionalProperties: true` 锁定测试（per design.md Decision 11）

### 跨里程碑

- **Task X.1** M1 完成后跑 `./test.sh --unit` 验证 schema 严格性
- **Task X.2** M2/M3 完成后跑 `./test.sh --python --bats` 验证 hook + guide-ship 接线
- **Task X.3** M4 完成后跑 `./test.sh --full --regression`（archive 前必须全绿）
- **Task X.4** 更新 ADR-0036 §Consequences 段,记录本次 fix（file-level diff vs report）

**Out of Scope**：

- ❌ 不重做 i10 已实施的 M1/M2/M3/M5 任务（archive.sh openspec_tracked 分支、project_config.sh、config.py merge、adr_catalog.py 参数化、discover-arch-artifacts.sh Path 1.5、ADR-0036、README 章节）
- ❌ 不改 i10 proposal.md / tasks.md / spec.md（保留归档原貌,作为修复对象对照）
- ❌ 不实现 `rdd-doctor --category project-config` / `rddf init-project-config`（属 future work per i10 §SHOULD）
- ❌ 不强制现有项目迁移到 project.yaml
- ❌ 不修改 roadmap 多路径聚合（`candidates` 字段预留）

## Capabilities

### Modified Capabilities

- `project-config-schema` (i10 新增,本期加固): jsonschema 强校验 `project` / `adr` / `git` / `verification` 4 节,**字段类型错误 raise ConfigError**(fail-closed)
- `project-config-hook-verifier` (i10 新增,本期接线): `rddf rdd-verify` 检测 `verification.provider: hook` → 调用 `_lib/verifier/hook_runner.py::run_verification_hook()`,exit code 映射 verdict
- `project-config-lightweight-mode` (i10 新增,本期加固): `guide-ship` Phase 1 在 worktree 创建**前**检测 `git.openspec_tracked: false` → 强制走 lightweight 路径(before archive)
- `project-config-execution-mode` (i10 新增,本期加固): `parse_execution_mode()` 读取 project.yaml,优先级 CLI flag > project.yaml > env var > default

### Capabilities Invariants (保留自 i10)

- 配置优先级（严格单向覆盖）：`runtime_overrides > project.yaml > loop.yaml > env vars > .rddf.json > defaults`
- project.yaml 缺失时**完全不插入**(零影响)
- `adr.pattern` (Python re) 与 `adr.glob` (Shell glob) 语义等价
- env-var 传递模式(参照 add-improve 已有 env.py 模式,禁止内联 `python3 -c "...$VAR..."`)
- 不破坏现有 `test_priority_loop_yaml_over_rddf_json` 等锁定旧顺序的单测
- 不删除 env var 覆盖能力(CI 临时注入仍需支持)
- 不强制现有项目迁移到 project.yaml

## Impact

### Affected Files

| File | 变更类型 | Task |
|------|----------|------|
| `_lib/schemas/config_schema.json` | modify | Task 1.1 |
| `_lib/core/defaults.py` | modify | Task 1.2 |
| `_lib/schemas/arch_handoff_schema.json` | modify | Task 4.5 (v1→v2 bump) |
| `_lib/cli/rdd_verify_cmd.py` | modify | Task 2.1, 2.2, 2.3 |
| `_lib/verifier/cache.py` | modify | Task 2.3 |
| `skills/guide-ship/SKILL.md` | modify | Task 3.1 |
| `_lib/ship_execution_mode.sh` | modify | Task 3.2 |
| `populate_lib.py` / `roadmap_incremental_update.py` | modify | Task 4.1, 4.4 |
| `guide-arch/scripts/write_arch_handoff.{sh,py}` | modify | Task 4.6 |
| `tests/unit/test_config.py` | modify | Task 1.3, 1.4, 1.1a |
| `tests/unit/test_rdd_verify_cmd.py` (new) | create | Task 2.5, 2.6 |
| `tests/unit/test_populate_lib.py` | modify | Task 4.1, 4.4 |
| `tests/unit/test_arch_handoff_schema.py` | modify | Task 4.5 |
| `tests/integration/test_rdd_verifier_hook_provider.bats` | create | Task 2.4 |
| `tests/integration/test_guide_ship_execution_mode.bats` | modify | Task 3.3 |
| `tests/integration/test_archive_with_openspec_tracked_false.bats` | create | Task 3.4 |
| `tests/integration/test_ship_execution_mode_reads_project_yaml.bats` | create | Task 3.5 |
| `tests/integration/test_discover_arch_artifacts_uses_project_yaml.bats` | create | Task 4.2 |
| `tests/integration/test_archive_gate_tasks_checklist_match.bats` | create | Task X.6 (MANDATORY) |
| `docs/adr/ADR-0036-rddf-project-yaml-config.md` | modify | Task X.4 (新增 `Post-hoc Fix Record` 节,非追加到 Consequences) |

### Lines of Code

- Schema + defaults: ~50 LOC
- rdd_verify_cmd.py hook 接线: ~30 LOC
- cache.py hook 分支: ~15 LOC
- guide-ship.md: ~20 LOC
- ship_execution_mode.sh: ~25 LOC
- populate_lib.py / roadmap_incremental_update.py: ~10 LOC
- 测试: ~400 LOC (8 新建 + 5 modify)
- ADR-0036 §Consequences 段: ~30 LOC

**总 ~580 LOC**

### Dependencies

- **无新增外部依赖**（jsonschema / pyyaml 已存在）
- **复用 i10 已实施**:
  - `_lib/project_config.sh::project_yaml_get()` — 读取 project.yaml
  - `_lib/verifier/hook_runner.py::run_verification_hook()` — hook 调用入口
  - `_lib/archive.sh::archive_change()` — openspec_tracked=false 分支已存在
  - `_lib/adr_catalog.py::scan_adr_catalog(adr_pattern=...)` — 参数化已存在

### Compatibility

- **100% 向后兼容**(无 project.yaml = 现状, per i10 §Capabilities Invariants)
- 现有 2421 个 pytest + 12 个 test_guide_ship_execution_mode case 全部保持绿色
- `_lib/cli/rdd_verify_cmd.py::cmd_rdd_verify()` 默认 runner 不变 (project.yaml 无 `verification.provider` 或 `verification.provider: llm` 走原 `_default_runner`)

### Risk

- 🟡 **中** — `rdd_verify_cmd.py` 接线 hook runner 涉及 cache + verdict 双重路径,需保证 SHA 缓存键不变性
- 🟢 **低** — schema / defaults 加固属 additive,字段缺失 = 缺失(非破坏)
- 🟡 **中** — `guide-ship` Phase 1 早检测可能改变现有项目的 worktree 创建行为(默认 `openspec_tracked: true`,行为不变;ChipForge 项目才受影响)

## Acceptance

**功能验收**：

- [ ] `config_schema.json` 含 `project` / `adr` / `git` / `verification` 4 节,`project.yaml` 字段类型错误时 `ConfigParser.parse()` raise `ConfigError`
- [ ] `core/defaults.py::DEFAULTS` 含 `project` 键(空 dict 或带默认子字段)
- [ ] `rddf rdd-verify` 在 `verification.provider: hook` 时调用 `_lib/verifier/hook_runner.py::run_verification_hook()`,exit 0/1/2+ → passed/failed/error
- [ ] `_lib/verifier/cache.py::cache_key()` 在 provider=hook 时返回 SHA+command-hash 复合键
- [ ] `guide-ship` Phase 1 Step 1.5 读 `git.openspec_tracked`,false 时显示 "⚡ 强制轻量模式 (branch only, no worktree)" 并设 `RDDF_EXECUTION_MODE=lightweight`
- [ ] `_lib/ship_execution_mode.sh::parse_execution_mode()` 按 CLI flag > project.yaml > env var > default 优先级解析

**测试验收**：

- [ ] 单测 `test_project_yaml_schema_validation_strict` 通过(类型错误 raise ConfigError)
- [ ] 单测 `test_project_defaults_present` 通过(`get_defaults()['project']` 是 dict)
- [ ] 单测 `test_rdd_verify_cmd_uses_hook_runner_when_provider_hook` 通过
- [ ] 集成测试 `tests/integration/test_rdd_verifier_hook_provider.bats` 全绿(exit code 映射 + cache 复用 + 路径白名单)
- [ ] 集成测试 `tests/integration/test_guide_ship_execution_mode.bats` 新增 `openspec_tracked=false` 场景 3 个 case 全绿
- [ ] 集成测试 `tests/integration/test_archive_with_openspec_tracked_false.bats` 新建并全绿
- [ ] 集成测试 `tests/integration/test_ship_execution_mode_reads_project_yaml.bats` 新建并全绿
- [ ] 集成测试 `tests/integration/test_discover_arch_artifacts_uses_project_yaml.bats` 新建并全绿
- [ ] `./test.sh --full --regression` 全绿后才允许 archive
- [ ] `./test.sh --quick` 2421 pytest + 现有 bats 仍全绿(零回归)

**ADR / 文档验收**：

- [ ] ADR-0036 在原 Consequences 节**后**新增 `## Post-hoc Fix Record (2026-09-02)` 节(per design.md Decision 10),**不追加到 Consequences**。内容指向本 change + commit hash + 8 项缺口对照表
- [ ] 引用 i10 archived change `openspec/changes/archive/2026-09-02-rfc-rddf-project-yaml-config-i10/tasks.md` 作为修复对象对照

**Metis 评审补充验收**(6 项歧义已解决):

- [ ] `cmd_rdd_verify(args, runner=mock_runner)` 显式 runner 永远胜出 provider 自动检测(Decision 8 + Task 2.6 测试通过)
- [ ] `RDDF_EXECUTION_MODE` env var 仅作 Phase 1 输出,不被 `parse_execution_mode` 读取(Decision 9)
- [ ] `.rddf/project.yaml` 含根级 extras(如 `my_custom_tooling: {...}`)`ConfigParser.parse()` 仍成功(Decision 11 + Task 1.1a 测试通过)
- [ ] `_lib/schemas/arch_handoff_schema.json` bump v1→v2,新增 `adr_pattern` optional 字段(Task 4.5)
- [ ] `populate_lib.py::catalog_sources` arch-handoff 无 `adr_pattern` 时 fallback 读 `.rddf/project.yaml`(Task 4.4)

**里程碑拆分验收**:

- [ ] M1 单独立 PR,merge 后跑 `./test.sh --unit` 全绿再启 M2/M3
- [ ] M2/M3 可并行,但合入前需 M1 已合入 master
- [ ] M4 在 M1 之后(依赖 schema),可与 M2/M3 并行
- [ ] archive 前跑 `./test.sh --full --regression`(per AGENTS.md §"Archive 前全量回归门 MANDATORY")

**预防性验收(MANDATORY,源自本 change 根因)**:

- [ ] 新增 `tests/integration/test_archive_gate_tasks_checklist_match.bats`(MANDATORY,非可选):archive 前 file-level diff vs tasks.md 复核,**任何 task 标记 done 但 file-level 未变更 → fail**。此为修复根因(避免后续 change 再出现 checkbox-as-done)。