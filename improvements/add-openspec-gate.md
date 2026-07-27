# add-openspec-gate

**优先级**: P0 | **来源**: UsrLinuxEmu backfill 事件复盘 2026-07-27
**阶段**: v2.1 | **分类**: planning
**类型**: feature

## 架构依据

- **ADR-0003 三阶段架构** (已采纳): arch → plan → ship 是 OpenSpec 工作流的标准路径。任何绕过 plan/ship 直接落地的代码违反此契约
- **ADR-0007 门控机制** (已采纳): `gate.py::register_gate_check()` 提供插件式 gate 注册接口,本提案的 workflow 层联动点
- **ADR-0017 rddf-session** (已采纳): session lifecycle 包含 `attached_changes`,但 plan_intake 未校验这些 change 是否仍"未实施"
- **add-full-regression-gate** (P0, 2026-07-27, proposal-approved): 已计划新增 `scripts/hooks/pre-commit`,本提案与其分工合作 —— 它管"build 文件 → ctest",本提案管"代码路径 → openspec change 联动"
- **add-config-validation** (P0, 2026-07-23, proposal-approved): 强化 `config.yaml` schema 校验,本提案的 glob 配置通过 `openspec_gate:` 节扩展 `config_schema.json`
- **事件复盘 2026-07-26/27**: UsrLinuxEmu 的 `stage4-1-bar-ioremap` 提案被批准但开发者直接 commit 3 个 TDD 实现 (571f9af / 556b647 / 116ca8c),proposal 滞留 `proposal-approved.md` 直到 `guide-plan` 触发才发现 → backfill 模式补追溯

### 反向论证 (为什么这是 workflow gap 而非流程问题)

- rdd-workflow 的 pre-commit hook (`scripts/hooks/pre-commit` 由 docs-audit 驱动) 只检查文档漂移
- 没有检查代码变更 ↔ `openspec/changes/` 关联的机制
- `plan_intake.sh` 不做 staleness 检测,`proposal-approved.md` 可长期滞留
- 因此 backfill-traceability mode 频繁发生,但缺少"阻止问题发生"的能力

## 范围

- **In Scope**:
  - `skills/openspec-gate/` 子技能创建 (SKILL.md + scripts/openspec-gate.sh + tests/test_openspec_gate.bats)
  - 默认 glob 集合:`include/`、`plugins/`、`src/`、`drivers/`、扩展名 `*.cpp` / `*.h` / `*.c` / `*.hpp` / `*.cu` / `*.S` / `*.py` / `*.ts`
  - `config.yaml` 增加 `openspec_gate:` 节 (`paths` / `extensions` / `exclude` / `mode`) + `config_schema.json` 同步
  - `scripts/hooks/pre-commit` 串联 openspec-gate + add-full-regression-gate 各自职责段
  - `plan_intake.sh` 调用 openspec-gate 检测 `proposal-approved.md` staleness (warning)
  - `skills/_lib/gate.py` 注册 `gate_check_openspec_change_active` (warning 级, `ship_done` gate)
  - 文档:`USAGE.md` 增加 "OpenSpec Gate" 节

- **Out Scope**:
  - 不实现硬拦截作为默认 (默认软警告,硬拦截作为 `OPENSPEC_GATE_MODE=block` 模式可选)
  - 不修改 OpenSpec CLI 本身 (仅在 rdd-workflow 层)
  - 不引入新配置文件 (复用 config.yaml,与 add-config-validation 提案同向)
  - 不覆盖 CI/Push gate (属于另一个改进议题)
  - 不替代 `guide-plan` Phase 2 propose / Phase 3 deps (仅检测,不创建)

## 关键场景

### 场景 A — TDD 直接落地拦截 (pre-commit 仓库层)

- **GIVEN** 项目配置默认 glob,staged 改动含 `plugins/gpu_driver/sim/bar_sim.cpp` 但 `openspec/changes/` 下无 active change
- **WHEN** 开发者运行 `git commit -m "feat(sim): add bar_sim"`
- **THEN** pre-commit hook 输出警告: "⚠️  staged code paths lack active OpenSpec change", 提示运行 `openspec new change <name>` 或输入 `w` 跳过

### 场景 B — proposal-approved 滞留检测 (workflow 层)

- **GIVEN** `proposal-approved.md` 含 `stage4-1-bar-ioremap`,git log 已含 commits 571f9af / 556b647 / 116ca8c
- **WHEN** 用户运行 `guide-plan`
- **THEN** `plan_intake.sh` 调用 openspec-gate 检测,输出 "⚠️  proposal 'stage4-1-bar-ioremap' 已被 commit 571f9af/556b647/116ca8c 实现,建议 backfill-traceability mode"

### 场景 C — 联动 add-full-regression-gate (pre-commit 串联)

- **GIVEN** `scripts/hooks/pre-commit` 同时包含 openspec-gate 与 regression-gate 两段
- **WHEN** staged 改动含 `src/CMakeLists.txt` (触发 regression) + `plugins/gpu_driver/sim/new.cpp` (触发 openspec-gate)
- **THEN** 两段按顺序执行:openspec-gate 先 (~50ms),regression-gate 后 (~30s)。任意失败阻塞 commit

### 场景 D — config.yaml 配置覆盖

- **GIVEN** 项目根 `config.yaml` 含 `openspec_gate: { exclude: ["vendor/", "third_party/"], paths: ["src/"] }`
- **WHEN** staged 改动含 `third_party/libfoo/new.cpp`
- **THEN** 跳过 openspec-gate 检测 (被 exclude 命中),无警告

### 场景 E — ship_done gate 注册 (workflow 层)

- **GIVEN** `ship_done` gate 注册了 `gate_check_openspec_change_active`
- **WHEN** `guide-ship` 试图 archive change A,但 `git log -- openspec/changes/A/` 无相关实现 commit
- **THEN** 输出 warning: "change A 可能尚未实现,确认 archive?" (不阻断,提供 3 选项)

## 技术约束

- **MUST**:
  - 默认 soft warning (exit 0),仅打印警告 + 提示 y/N 确认;硬拦截通过 `OPENSPEC_GATE_MODE=block` 显式启用
  - `SKIP_OPENSPEC_GATE=1` 环境变量可跳过 hook
  - hook 检测执行时间 ≤ 200ms (不显著拖慢 commit)
  - 不修改 openspec CLI,仅在 rdd-workflow 层添加
  - 与 add-full-regression-gate 共享同一个 pre-commit 文件 (不要各自 cp 一份)
  - `config.yaml` schema 扩展同步更新 `config_schema.json` (与 add-config-validation 联动)

- **MUST NOT**:
  - 不创建新的配置文件 (不复用 config.yaml 之外的 yml/toml)
  - 不在 pre-commit hook 中嵌入硬编码项目特定路径
  - 不直接修改 `scripts/regression-test.sh` 或其它 `_lib` 现有脚本 (仅通过 gate 注册接口联动)
  - 不阻塞仓库自身的 docs / scripts / AGENTS.md 改动 (白名单)

- **SHOULD**:
  - 检测逻辑支持 dry-run 模式 (`OPENSPEC_GATE_DRY_RUN=1` 仅打印不交互)
  - 输出包含可点击链接或具体命令提示 (`openspec new change <suggested-name>`)
  - 与 code-review-graph MCP 联动 (如已安装),把检测结果纳入图谱

## 验收标准

### 自动化

- `tests/test_openspec_gate.bats` PASS,覆盖场景 A / B / C / D / E
- `openspec-gate.sh --self-test` exit 0
- `config_schema.json` 校验 `openspec_gate:` 节合法

### 集成

- `scripts/hooks/pre-commit` 安装后含 openspec-gate + regression-gate 两段,互不干扰
- `plan_intake.sh` 调用 openspec-gate 检测 `proposal-approved.md` staleness
- `gate.py::register_gate_check("ship_done", gate_check_openspec_change_active)` 注册成功

### 用户体验

- 在 UsrLinuxEmu 项目模拟事件复盘:commit 571f9af / 556b647 / 116ca8c 时若 hook 已安装 → 输出警告 + 提示创建 change
- 软警告默认行为:输入 `w` 跳过,commit 继续
- 硬拦截模式:`OPENSPEC_GATE_MODE=block` + 无 change 时 exit 1 阻塞

### 文档

- `USAGE.md` 增加 "OpenSpec Gate" 节,含安装、配置、跳过方法
- `SKILL.md` 描述完整,包含 5 个场景的 GIVEN / WHEN / THEN
- `CHANGELOG.md` 记录本改进为新功能

### 可验证场景

- 复现 2026-07-26 / 27 事件:手动 commit `plugins/gpu_driver/sim/bar_sim.cpp` (无 change) → hook 应警告
- 复现 add-full-regression-gate 协作:commit `src/CMakeLists.txt` (有 change) → openspec-gate 通过、regression-gate 触发

## 与现有提案的协同关系

| 提案 | 关系 |
|------|------|
| add-full-regression-gate (P0) | **串联协作** —— 同一 pre-commit 文件,openspec-gate 先 (cheap),regression-gate 后 (expensive) |
| add-config-validation (P0) | **配置联动** —— `openspec_gate:` 节由 config_schema.json 校验 |
| add-progressive-linting (P2) | **互不干扰** —— linting 是独立维度,本提案不触及 |
| add-full-regression-gate 优先落地 | **依赖建议** —— 先让 regression-gate 落地,本提案后接入其 pre-commit 串联点 |

## 风险与权衡

- **风险 1**: 软警告可能成为"噪音"被习惯性跳过
  - **缓解**: 默认 + suggestion 命令提示;建议团队约定 `OPENSPEC_GATE_MODE=block`
- **风险 2**: glob 误报 (例: 测试文件被误判为"需 change 关联")
  - **缓解**: `exclude` 节支持 + 默认排除 `tests/`、`archive/`、`build*/`
- **风险 3**: 与现有 `.git/hooks/pre-commit` (docs-audit) 冲突
  - **缓解**: 串联方式,docs-audit 先、openspec-gate 后,各自 `SKIP_*` 环境变量独立
- **风险 4**: plan_intake.sh 新增调用拖慢 guide-plan 启动
  - **缓解**: staleness 检测是 git log grep,单 proposal < 50ms,可接受