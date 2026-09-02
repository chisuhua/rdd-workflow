---
issue_ref: ""
gh_repo: chisuhua/rdd-workflow
---
# complete-project-yaml-config-gaps

**优先级**: P1 | **来源**: rfc-rddf-project-yaml-config-i10 archive 审计 (2026-09-02)
**阶段**: v2.2+ | **分类**: arch-design | **类型**: fix
**主题**: 不适用（自由模式 — roadmap 新格式尚未启用主题约束）
**修复对象**: `openspec/changes/archive/2026-09-02-rfc-rddf-project-yaml-config-i10/tasks.md` 23/25 done

## 架构依据

`rfc-rddf-project-yaml-config-i10` (P1, 2026-09-02 archived) 是 rdd-workflow 引入 `.rddf/project.yaml` 项目级配置的奠基提案。其 5 优先级配置链扩展和 ChipForge 异构项目适配是核心价值。**但 archive 后审计发现 8 项 task 标记完成但代码未实际落地**:

| 缺口 | 严重度 | 影响 |
|------|--------|------|
| `_lib/schemas/config_schema.json` 缺 `project` 节 (Task 1.1) | 🟠 P1 | `project.yaml` 字段类型错误静默通过,破坏 fail-closed |
| `_lib/core/defaults.py` 缺 `project` 默认 (Task 1.5) | 🟢 P3 | 缺失默认值时行为依赖空 dict fallback |
| `_lib/cli/rdd_verify_cmd.py` 缺 `provider=hook` 分支 (Task 4.2) | 🔴 P0 | ChipForge `verification.provider: hook` 不生效 |
| `_lib/verifier/cache.py` 未支持 hook 缓存键 (Task 4.3) | 🔴 P0 | 即使接线完成,缓存键仍无法隔离 |
| `skills/guide-ship/SKILL.md` Phase 1 不读 project.yaml (Task 3.1) | 🟠 P1 | 用户配 `openspec_tracked: false` 后行为不一致 |
| `_lib/ship_execution_mode.sh` 不读 project.yaml (Task 3.2) | 🟡 P2 | wave 执行模式不受 project.yaml 控制 |
| `tests/integration/test_guide_ship_execution_mode.bats` 缺 openspec_tracked 场景 (Task 3.4) | 🟡 P2 | 集成路径无回归门控 |
| `tests/integration/test_rdd_verifier.bats` 缺 provider=hook 场景 (Task 4.4) | 🟡 P2 | 集成路径无回归门控 |

**调研证据** (file-level diff vs tasks.md):

```bash
# Hook runner 是孤儿代码 — Task 4.1 创建,Task 4.2 未实现
$ grep -rn "hook_runner" _lib/ skills/
_lib/verifier/hook_runner.py:1  # 仅 hook_runner.py 自身引用

# guide-ship 不读 project.yaml — Task 3.1 未实现
$ grep -n "openspec_tracked" skills/guide-ship/SKILL.md
(no output)

# ship_execution_mode 不读 project.yaml — Task 3.2 未实现
$ grep -n "openspec_tracked" _lib/ship_execution_mode.sh
(no output)

# config_schema 缺 project 节 — Task 1.1 未实现
$ grep -n '"project"\|"git"\|"verification"' _lib/schemas/config_schema.json
(no output)

# defaults.py 缺 project 默认 — Task 1.5 未实现
$ grep -n '"project"' _lib/core/defaults.py
(no output)

# 集成测试缺失 — Task 3.4/3.5/4.4 未实现
$ grep -rn "openspec_tracked\|provider=hook" tests/integration/
tests/integration/test_archive_l2_hook.py (无关)
```

**根因分析**: i10 实施时由 4 个里程碑 (M1→M2/M3/M4→M5) 跨 PR 合并,可能在某个合并步骤 commit-level 误勾了 checkbox 而非 file-level 验证。AGENTS.md §"Archive 前全量回归门 (MANDATORY)" 强制 `./test.sh --full --regression`,但 archive 流程未强制 file-level diff vs tasks.md 复核。

**Metis 评审补充 (2026-09-02)**: Metis pre-planning consultant 审查提案初版发现 6 项 BLOCKER/HIGH 歧义 + 4 项额外缺口,均已通过 design.md Decision 8-11 + tasks.md Task 1.1a/2.6/4.4/4.5/4.6 解决。详见 design.md "Decision 7-11" + "Risks / Trade-offs" 中的 arch-handoff staleness 项。

**影响项目**:
- **ChipForge** (CppTLM+CppHDL 硬件验证平台) — 配置 `verification.provider: hook` 后实际不会触发 hook,LLM 验证仍跑(用户误以为被替代)
- **未来异构项目** — `git.openspec_tracked: false` 用户需走到 archive 才发现行为不同,worktree 阶段仍按默认路径走

## 范围

**In Scope** (4 个里程碑,共 28 个 task,含 Metis 评审补充的 6 项):

| 里程碑 | 内容 | 依赖 | 风险 |
|--------|------|------|------|
| **M1** | Schema + Defaults 加固 (Task 1.1, 1.5, 1.1a 根级 extras 零回归) | 无 | 🟢 低 (additive) |
| **M2** | Hook Runner 接线 (Task 4.2, 4.3, 4.4, 2.6 显式 runner override) | M1 | 🟡 中 (cache 双路径 + 优先级语义) |
| **M3** | Guide-Ship Phase 1 + ship_execution_mode 加固 (Task 3.1, 3.2, 3.4, 3.5) | 独立 | 🟡 中 (Phase 1 时机变更) |
| **M4** | populate_lib 透传 + arch-handoff fallback (Task 2.3, 2.6, 4.4 fallback, 4.5 schema bump, 4.6 写方补字段) | M1 | 🟢 低 |
| **X** | Cross-Milestone (Task X.1-X.6 含 X.6 MANDATORY 根治机制) | 各 M | 🟢 低 |

**Out of Scope**:
- ❌ 不重做 i10 已实施的 M1/M2/M3/M5 (archive.sh openspec_tracked 分支、project_config.sh、config.py merge、adr_catalog.py 参数化、discover-arch-artifacts.sh Path 1.5、ADR-0036、README 章节)
- ❌ 不修改 i10 archive 文件 (proposal.md / tasks.md / spec.md 保留归档原貌作为修复对象对照)
- ❌ 不实现 `rdd-doctor --category project-config` / `rddf init-project-config` (属 future work)
- ❌ 不强制现有项目迁移到 project.yaml
- ❌ 不修改 roadmap 多路径聚合 (`candidates` 字段预留)

## 关键场景

- **场景 1 — ChipForge Hook 真生效**: GIVEN `project.yaml` 设 `verification.provider: hook`, WHEN `rddf rdd-verify <change>` 执行, THEN 调 `_lib/verifier/hook_runner.py::run_verification_hook()`, exit 0/1/2+ → passed/failed/error, SHA 缓存键独立。
- **场景 2 — 强 schema 校验**: GIVEN `project.yaml` 含 `git: {openspec_tracked: "yes"}` (string 而非 bool), WHEN `ConfigParser.parse()` 跑, THEN raise `ConfigError` 提及 `git.openspec_tracked`, 而非静默通过。
- **场景 3 — Phase 1 早检测**: GIVEN `project.yaml` 设 `git.openspec_tracked: false`, WHEN `guide-ship` Phase 1 执行, THEN **在 Step 2 worktree 创建前**打印 "⚡ 强制轻量模式" 并设 `RDDF_EXECUTION_MODE=lightweight`, worktree 创建跳过。
- **场景 4 — execute mode 优先级**: GIVEN `--parallel` CLI flag + `project.yaml` openspec_tracked=false + `RDD_SHIP_PARALLEL=yes`, WHEN `parse_execution_mode`, THEN 输出 "parallel" (CLI flag 优先级最高)。

## 技术约束

**MUST**:
- 100% 向后兼容 (无 `project.yaml` = 现状, 现有 2421 pytest + 现有 bats 保持全绿)
- env-var 传递模式 (参照 add-improve 已有 env.py 模式, 禁止内联 `python3 -c "...$VAR..."`)
- TDD 5 步结构 (每个 task: Write failing test → Verify fail → Implement → Verify pass → Commit)
- file-level diff vs tasks.md 验证 (PR description 列出 task ↔ commit hash 对应)
- `./test.sh --full --regression` 全绿后才 archive (per AGENTS.md MANDATORY)

**MUST NOT**:
- 不重做 i10 已实施的代码 (M1/M2/M3/M5 的 17 项已 done)
- 不破坏 `test_priority_loop_yaml_over_rddf_json` 等锁定旧顺序的单测
- 不删除 env var 覆盖能力 (CI 临时注入仍需支持)
- 不修改 i10 archive 文件

**SHOULD**:
- 任务 M1/M2/M3/M4 拆为 4 个独立 PR, 降低单次回归风险
- 可选 Task X.6: 新增 `tests/integration/test_archive_gate_tasks_checklist_match.bats`, 防止后续 change 再现 checkbox-as-done (本 change 根因)

## 验收标准

**功能验收**:
- [ ] `config_schema.json` 含 `project` / `adr` / `git` / `verification` 4 节, `project.yaml` 字段类型错误 raise `ConfigError`
- [ ] `core/defaults.py::DEFAULTS` 含 `project` 键 (空 dict 或带默认子字段)
- [ ] `rddf rdd-verify` 在 `verification.provider: hook` 时调 `_lib/verifier/hook_runner.py::run_verification_hook()`, exit 0/1/2+ → passed/failed/error
- [ ] `_lib/verifier/cache.py::cache_key()` 在 provider=hook 时返回 SHA+command-hash 复合键
- [ ] `guide-ship` Phase 1 Step 1.5 读 `git.openspec_tracked`, false 时显示 "⚡ 强制轻量模式" 并设 `RDDF_EXECUTION_MODE=lightweight`
- [ ] `_lib/ship_execution_mode.sh::parse_execution_mode()` 按 CLI flag > project.yaml > env var > default 优先级解析

**测试验收**:
- [ ] 单测 `test_project_yaml_schema_strict_raises` 通过
- [ ] 单测 `test_project_defaults_present` 通过
- [ ] 单测 `test_rdd_verify_cmd_uses_hook_runner_when_provider_hook` 通过
- [ ] 集成测试 `tests/integration/test_rdd_verifier_hook_provider.bats` 全绿 (5 case)
- [ ] 集成测试 `tests/integration/test_guide_ship_execution_mode.bats` 新增 openspec_tracked 场景 3 case 全绿
- [ ] 集成测试 `tests/integration/test_archive_with_openspec_tracked_false.bats` 新建并全绿
- [ ] 集成测试 `tests/integration/test_ship_execution_mode_reads_project_yaml.bats` 新建并全绿
- [ ] 集成测试 `tests/integration/test_discover_arch_artifacts_uses_project_yaml.bats` 新建并全绿
- [ ] `./test.sh --full --regression` 全绿后才允许 archive
- [ ] `./test.sh --quick` 2421 pytest + 现有 bats 仍全绿 (零回归)

**ADR / 文档验收**:
- [ ] ADR-0036 在原 Consequences 节**后**新增 `## Post-hoc Fix Record (2026-09-02)` 节(per design.md Decision 10),**不追加到 Consequences**。内容指向本 change + commit hash + 8 项缺口对照表
- [ ] 引用 i10 archived change 作为修复对象对照

**Metis 评审补充验收**:
- [ ] `cmd_rdd_verify(args, runner=mock_runner)` 显式 runner 永远胜出(Decision 8 + Task 2.6)
- [ ] `RDDF_EXECUTION_MODE` env var 仅作 Phase 1 输出,不被 `parse_execution_mode` 读取(Decision 9)
- [ ] `.rddf/project.yaml` 含根级 extras `ConfigParser.parse()` 仍成功(Decision 11 + Task 1.1a)
- [ ] `_lib/schemas/arch_handoff_schema.json` bump v1→v2,新增 `adr_pattern` optional 字段(Task 4.5)
- [ ] `populate_lib.py::catalog_sources` arch-handoff 无 `adr_pattern` 时 fallback 读 `.rddf/project.yaml`(Task 4.4)

**里程碑拆分验收**:
- [ ] M1 单独立 PR, merge 后跑 `./test.sh --unit` 全绿再启 M2/M3
- [ ] M2/M3 可并行, 但合入前需 M1 已合入 master
- [ ] M4 在 M1 之后, 可与 M2/M3 并行
- [ ] archive 前跑 `./test.sh --full --regression` (per AGENTS.md MANDATORY)

## 依赖与后续

**前置依赖**:
- 无 (依赖 i10 已实施的代码: project_config.sh / hook_runner.py / archive.sh openspec_tracked 分支)

**后续工作** (不在本提案范围):
- 异构项目 ChipForge 在 M1-M4 落地后, 真实反馈与适配验收
- 第三方项目 fork 维护者按 M5 文档自行迁移
- `rdd-doctor --category project-config` 检测 + `rddf init-project-config` CLI 作为 follow-up 提案独立处理
- 预防性 tasks-diff-check (Task X.6 可选) 后续增强

## 修复对象引用

**title**: 补齐 rfc-rddf-project-yaml-config-i10 archive 后审计发现的 8 项 checkbox-as-done 缺口

**修复对象**: `openspec/changes/archive/2026-09-02-rfc-rddf-project-yaml-config-i10/tasks.md`

**关联 ADR**: ADR-0036 (项目级配置) — §Consequences 段追加 fix 记录

<!-- 本 change 由 rfc-rddf-project-yaml-config-i10 archive 后审计触发, 不引用上游 issue (内部 follow-up fix) -->