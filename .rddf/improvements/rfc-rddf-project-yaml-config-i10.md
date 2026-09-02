---
issue_ref: 10
gh_repo: chisuhua/rdd-workflow
---
# rfc-rddf-project-yaml-config-i10

**优先级**: P1 | **来源**: GitHub RFC #10 (2026-09-01, ChipForge 异构项目适配)
**阶段**: v2.2+ | **分类**: arch-design | **类型**: feature
**主题**: 不适用（自由模式 — roadmap 新格式尚未启用主题约束）
**上游**: https://github.com/chisuhua/rdd-workflow/issues/10

## 架构依据

rdd-workflow 缺项目级配置层，硬编码假设阻碍异构项目（硬件验证、嵌入式、文档驱动）接入。4 个具体证据：

1. **ADR 强制 4 位编号** — `_lib/adr_catalog.py:13` 硬编码 `ADR_PATTERN = re.compile(r"^ADR-(\d{4})-.*\.md$")`，3 位编号（如 `ADR-040`）会被静默跳过，导致 ADR 扫描、populate-roadmap 全部失效。
2. **openspec/ 强制 git-tracked** — guide-ship worktree 模式与 archive 的 git merge/commit 流程假定 `openspec/` 进版本控制；但部分项目（如 ChipForge，commit 3e8fdbf 显式 untrack）将其视为本地工作区，导致 worktree/archive 链路断裂。
3. **AC 验证强制 LLM** — ac-verifier / rdd-verifier 固定走 LLM 语义检查；无 API key 的项目（或已有 CTest + 脚本门禁的硬件项目）无法复用其验收体系。
4. **配置只支持 env var** — `_lib/config.py` 当前 5 优先级链 `runtime > loop.yaml > .rddf.json > env vars > defaults` 无项目级 yaml 持久化、无 schema 校验、无团队共享能力。

**影响项目**：ChipForge（CppTLM+CppHDL 硬件验证平台）为首个非软件项目采用者。

**调研证据**（issue #10 引用 + 当前 codebase 核对）：
- `_lib/adr_catalog.py:13` — 4 位硬编码 regex
- `_lib/discover-arch-artifacts.sh:43-56` — 默认候选 `docs/adr` 等，仅支持 env var 覆盖
- `_lib/config.py::ConfigParser` — 仅支持 loop.yaml / .rddf.json / env var / defaults，无 project.yaml
- `skills/guide-ship/SKILL.md:88-89` — 轻量模式（branch）仅为 worktree 的 alternate
- `skills/ac-verifier/SKILL.md` + `skills/rdd-verifier/SKILL.md` — 固定 LLM 语义验证

## 范围

**In Scope**（5 项能力 + 实施里程碑）：

| 里程碑 | 内容 | 依赖 | 风险 |
|--------|------|------|------|
| **M1** | 配置基础设施（`project_config.sh` + `config.py` merge + schema + defaults） | 无 | 🔴 高（merge 顺序全局影响） |
| **M2** | ADR 发现可配置（`adr_catalog.py` pattern/glob 参数化 + `discover-arch-artifacts.sh` Path 1.5） | M1 | 🟡 中 |
| **M3** | openspec_tracked / 轻量模式（`guide-ship` Phase 1 + `_lib/archive.sh` 分支） | M1 | 🔴 高（archive 核心路径） |
| **M4** | verification hook（`hook_runner.py` + `rdd_verify_cmd` provider=hook 分支） | M1 | 🟢 低 |
| **M5** | 文档 + 全量测试 | M2/M3/M4 | 🟢 低 |

**实施策略**：单提案跟踪，但实施时按 M1 → M2/M3/M4（并行）→ M5 拆为 4 个子 PR，降低单次回归风险。

**M1 详细 In Scope**：
- `_lib/project_config.sh`（新建 sourced library，yq/python 双回退）
- `_lib/config.py`：新增 `.rddf/project.yaml` 解析 + merge 顺序插入
- `_lib/schemas/config_schema.json`：新增 `project` 节
- `_lib/core/defaults.py`：新增 project 默认值

**M2 详细 In Scope**：
- `_lib/adr_catalog.py::scan_adr_catalog(..., adr_pattern=None)` 参数化
- `_lib/discover-arch-artifacts.sh` Path 1.5 读 project.yaml（优先于默认候选）
- `populate_lib.py` / `roadmap_incremental_update.py`：透传 pattern

**M3 详细 In Scope**：
- `skills/guide-ship/SKILL.md` Phase 1：检测 `git.openspec_tracked=false` → 强制轻量模式
- `_lib/ship_execution_mode.sh`：分支
- `_lib/archive.sh`：`openspec_tracked=false` 时跳过 git merge/commit，仅 `openspec archive` + mark_iteration

**M4 详细 In Scope**：
- `_lib/verifier/hook_runner.py`（新建）：外部命令调用，exit code → verdict
- `_lib/cli/rdd_verify_cmd.py`：`provider=hook` 分支
- 复用 `_lib/verifier/classify_failure.sh` 输出格式

**M5 详细 In Scope**：
- README/USAGE 增加 project.yaml 章节
- 4 个里程碑的集成测试全绿

**Out of Scope**：
- ❌ 不改现有默认行为（project.yaml 缺失 = 现状）
- ❌ 不实现 roadmap 多路径聚合（`candidates` 字段预留，本期仅单路径）
- ❌ 不改 `RDDF_REPORT_GH_REPO` 等既有 env 语义
- ❌ 不强制现有项目迁移到 project.yaml

## 关键场景

- **场景 1 — ChipForge 3 位 ADR 扫描**：GIVEN `project.yaml` 设 `adr.pattern: "ADR-\\d{3}"`，WHEN `scan_adr_catalog` 执行，THEN 识别 ADR-040/041/042，guide-arch 列出 3 个 ADR。
- **场景 2 — 强制轻量模式**：GIVEN `project.yaml` 设 `git.openspec_tracked: false`，WHEN guide-ship Phase 1 检测，THEN 显示 "⚡ 强制轻量模式 (branch only, no worktree)"，archive 不报 worktree 错误。
- **场景 3 — 外部验证 hook**：GIVEN `project.yaml` 设 `verification.provider: hook`，WHEN `rddf rdd-verify <change>` 执行，THEN 调用 `tools/verify_change.sh <change>`，exit 0 → passed，exit 1 → failed；SHA 缓存仍生效。
- **场景 4 — 向后兼容**：GIVEN 无 `project.yaml`，WHEN 任一 skill 执行，THEN merge 顺序退化为现状（runtime > loop.yaml > .rddf.json > env vars > defaults），现有单测 `test_priority_loop_yaml_over_rddf_json` 仍通过。

## 技术约束

**MUST**：
- 配置优先级（严格单向覆盖）：`runtime_overrides > project.yaml > loop.yaml > env vars > .rddf.json > defaults`
- project.yaml 缺失时**完全不插入**（零影响）
- `adr.pattern`（Python re）与 `adr.glob`（Shell glob）语义等价，文档强制配对
- env-var 传递模式（参照 add-improve 已有 env.py 模式，禁止内联 `python3 -c "...$VAR..."`）
- archive 跳过 git 操作后，`openspec archive` CLI 自身必须能处理文件移动

**MUST NOT**：
- 不破坏现有 `test_priority_loop_yaml_over_rddf_json` 等锁定旧顺序的单测
- 不删除 env var 覆盖能力（CI 临时注入仍需支持）
- 不强制现有项目迁移到 project.yaml

**SHOULD**：
- `rdd-doctor --category project-config` 检测可迁移项（可选增强）
- `rddf init-project-config` CLI 生成骨架（可选增强）

## 验收标准

**功能验收**：
- [ ] `project.yaml` 设 `adr.pattern: "ADR-\\d{3}"` 后，ChipForge 的 ADR-040/041/042 可被 `scan_adr_catalog` 识别
- [ ] `project.yaml` `adr.dir` 被 `discover-arch-artifacts.sh` 读取，`DISCOVERED_ADR_DIR_FOUND=true`
- [ ] `git.openspec_tracked: false` 时 guide-ship 强制轻量模式，archive 无 git merge/commit 错误
- [ ] `verification.provider: hook` 时 `rddf rdd-verify` 调用外部 hook，verdict 写入缓存
- [ ] 无 `project.yaml` 时所有现有行为不变（零回归）

**测试验收**：
- [ ] `test_priority_project_yaml_over_loop_yaml` 单测通过（project.yaml > loop.yaml > env）
- [ ] `test_three_digit_adr_pattern` 单测通过
- [ ] `tests/integration/test_guide_ship_execution_mode.bats` 新增 openspec_tracked=false 场景全绿
- [ ] `tests/integration/test_rdd_verifier.bats` 新增 provider=hook 场景全绿
- [ ] `./test.sh --full --regression` 全绿后才允许 archive

**ADR 验收**：
- [ ] 新建 ADR（如 `ADR-0xxx-project-level-config`）记录本次决策
- [ ] 引用相关 ADR（配置优先级、AC 验证、ship 执行模式）

**里程碑拆分验收**（实施时）：
- [ ] M1 单独立 PR 提交 + 合并，merge 顺序测试通过后再启 M2/M3/M4
- [ ] M2/M3/M4 可并行，但合入前需 M1 已合入 master
- [ ] M5 在所有里程碑合入后合并

## 依赖与后续

**前置依赖**：
- 无（绿地）

**后续工作**（不在本提案范围）：
- 异构项目 ChipForge 在 M1-M5 落地后，作为首个采用者提供真实反馈与适配验收
- 第三方项目 fork 维护者（若存在）按 M5 文档自行迁移
- `rdd-doctor` 检测 + `rddf init-project-config` CLI 作为 follow-up 提案独立处理

## 上游 Issue 引用

**title**: RFC: 引入 .rddf/project.yaml 项目级配置，支持异构项目（ChipForge 硬件验证平台）原生接入

**issue_ref**: 10
**gh_repo**: chisuhua/rdd-workflow

<!-- 引用自 https://github.com/chisuhua/rdd-workflow/issues/10 (2026-09-01) -->
