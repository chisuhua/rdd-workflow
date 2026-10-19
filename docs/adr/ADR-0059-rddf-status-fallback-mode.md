# ADR-0059: `rddf status` 自动降级模式 (iteration.json 缺失/损坏 → openspec/changes/ fallback)

> **状态**: 待定
> **日期**: 2026-10-19
> **决策者**: rdd-workflow maintainer
> **关联 ADR**: ADR-0001 (propose-plan-execute 状态机), ADR-0025 (move-proposal-creation-to-design), ADR-0028 (role-model-per-phase)
> **关联 Improvement**: `.rddf/improvements/add-rddf-status-fallback-mode.md`
> **来源 issue**: 2026-10-19 由 CppTLM 项目使用反馈触发 (per `[角色: planner]` session `ses_eb3545ac9ffefOzGFYynmFN2Ub`)

## Context

`rddf status` 默认视图 (Mode A) 在 `.rddf/state/iteration.json` 缺失时输出友好提示 + initialize 提示, **exit code 0**, 但输出文本本身 ("📭 iteration.json not found / initialize via: skill_use(\"propose\", \"<change-name>\")") 看起来像**系统错误**, 用户感受模糊. 同时**完全空显示**, 浪费了 `openspec/changes/` 目录中已有的 ground-truth 信息 (e.g. CppTLM 项目有 3 active + 95 archive changes).

### 当前实现 (`_lib/cli/status_cmd.py`)

| Mode | 用途 | iteration.json 缺失行为 | exit code |
|------|------|-------------------------|-----------|
| **A** (默认) | 全局 change 概览表 | "not found" + initialize 提示 | **0** (友好) |
| **B** (`<name>`) | 单 change 详情 | "not found" + initialize 提示 | **1** (严格) |
| **D** (`--roadmap`) | 路线图状态 | (独立读 roadmap-state.json) | 0 |
| **E** (`--iteration`) | iteration 视图 | 友好提示 (delegated) | 0 |

### 触发场景

24 字段 iteration.json (per `_lib/schemas/iteration_schema.json` v7) 是 rdd-workflow procedural state。**未经过 propose / rdd-builder / rdd-arch 流程** 的项目**不会自动创建** iteration.json, 但项目**可能有 openspec changes**. CppTLM 是典型案例:

- 已重写 9 phase `.rddf/roadmap.md` + AUTO-INDEX 3 段 (per 真源 1 治理)
- 已 5 active + 95 archive `openspec/changes/` (procedural ground truth)
- **未走 propose 流程** → iteration.json 缺失 → `rddf status` 仅报"not found"

### 约束

- **兼容性**: 现有 Mode A/B/D/E 不能 break. 新增行为**仅在缺失/损坏时触发**.
- **数据真源优先级**: iteration.json > openspec/changes/ (前者更准确, 含 phase / category / blocker / plan_path 等元数据; 后者仅含生命周期信息).
- **降级语义**: fallback 不是 "代替", 是 "best-effort". 标注 `(inferred)` 或 `(no iteration data)` 区分.
- **退出码**: 缺失 + 降级显示 → 0; 显式 `--strict` 模式仍 1 (要求 iteration.json 存在).

## Decision

**新增 Mode F (`--autodetect` / `--fallback` 触发) + 4 个辅助 flag. iteration.json 缺失/损坏时, 自动降级扫描 `openspec/changes/` 目录, 给出 best-effort 视图.**

### 影响范围

- **In Scope**:
  - 新增 `cmd_status` Mode F 分发 (per `_lib/cli/status_cmd.py:108-168`)
  - 新增 `_mode_f_autodetect(project_root)` 实现: 优先 iteration.json, 失败降级 openspec 扫描
  - 新增 `_render_openspec_fallback(project_root)` 实现: 扫 `openspec/changes/*/`, 排除 `archive/`, 渲染降级视图
  - 新增 flag: `--autodetect` / `--fallback` (等价)
  - 新增 flag: `--source=openspec|iteration|both` (默认 `iteration`)
  - 新增 flag: `--no-initialize-hint` (抑制 initialize 提示)
  - 新增 flag: `--show-archive` (包含 archive changes, 默认仅 active)
  - 新增 flag: `--strict` (要求 iteration.json 存在, 缺失返 1)
  - 新增测试: `tests/cli/test_status_fallback.sh` (per rdd-workflow test 规范)
- **Out Scope**:
  - 不修改 `openspec list` (单独命令, 已工作)
  - 不修改 `rddf dashboard` / `rddf guide` 等其他命令 (各命令独立 Mode 体系)
  - 不实现 Mode F 的 `--roadmap` / `--iteration` 互操作 (Mode D/E 走各自数据源, 不降级)
  - 不引入新依赖 (复用 rdd-workflow 现有 `_lib/state_reader`)
  - 不修改 `iteration_schema.json` (降级视图不写回 iteration.json)

### 备选方案

| 备选 | 理由 |
|------|------|
| **A. 新增 Mode F + 4 flag (本 ADR)** | **YAGNI**; 复用现有 cmd_status 框架, 仅缺失/损坏触发降级; 完全向后兼容 |
| B. **强制创建 iteration.json** in `rddf status` 入口 | **副作用不可控**: 写入文件 = 引入副作用, 违反 `_lib/cli/__init__.py` "只读" 原则; 多个 CLI 实例并发会触发 `.lock` 冲突; iteration.json 应该是 procedural state, 不是 ad-hoc create |
| C. **把 "📭 not found" 改成纯友好文字** (例如 "尚未初始化 iteration.json") | **不解决核心问题**: 用户仍看不到 openspec/changes/ 内容; 失去判断 ground truth 的能力 |
| D. **删除 iteration.json 启动降级** (直接把 fallback 写成 Mode A 默认) | **破坏 iteration.json 权威性**: 现有项目以 iteration.json 为 ground truth, 切换为 openspec fallback 会丢失 phase / category / blocker / plan_path 字段, 破坏 dashboard / verifier / orchestrator 等多消费者 |
| E. **新增独立命令** `rddf status-fallback` | **冗余**: 与 `rddf status --autodetect` 等价; 用户记忆负担 |

## Consequences

### 正面

- **未初始化项目可用性**: CppTLM 类项目能直接用 `rddf status` 查看活跃 change, 不需要先走 propose
- **诊断降级保留**: iteration.json 损坏仍能看 best-effort 视图, 不需立即修复 schema
- **4 flag 灵活性**: `--source=both` 可显示双源; `--strict` 给严格 CI 用; `--no-initialize-hint` 给脚本用; `--show-archive` 给复盘用
- **0 改动 Mode A/B/D/E**: 现有调用全兼容, 现有测试不动
- **0 改动 iteration_schema.json**: schema 保持权威性, fallback 视图不污染主状态

### 负面 / 风险

- **Mode F 输出字段缺失**: 降级视图无 phase / category / blocker / plan_path 字段, 输出需标注 `(inferred)`. **缓解**: 表头明确写 "Source: openspec-fallback, no iteration.json"
- **Mode F 扫描 openspec/changes/ 慢**: 100 dir 估时 < 1s (per python pathlib glob). 大项目 (10000+ dir) 需后续 benchmark, 可考虑加缓存. **缓解**: 输出加进度提示
- **误用风险**: `--source=both` 可能让用户误以为 iteration.json + openspec/changes/ 总是一致. **缓解**: 双源不一致时打印 "iteration.json 与 openspec/changes/ 不一致 (差 N 项)"
- **Mode F 触发条件需保守**: 仅缺失/损坏触发降级; iteration.json 存在但 stale 不触发. **缓解**: stale 检测留给其他命令 (per `rddf iteration --strict` 已实现)
- **CI 行为**: 默认 Mode A 不变, CI 现有脚本不受影响; 新 flag 是**显式 opt-in**, 不会被意外触发

### 后续待办

- [ ] 起草 `openspec/changes/<name>/` proposal + design + tasks (per rdd-workflow OpenSpec workflow, ADR-0025)
- [ ] 实施 `cmd_status` Mode F 分发 (per `_lib/cli/status_cmd.py`)
- [ ] 实施 `_mode_f_autodetect` + `_render_openspec_fallback` helpers
- [ ] 加 4 个 flag parsing (per `_print_help` 同步更新)
- [ ] 加 `tests/cli/test_status_fallback.sh` (5 cases: 缺失/损坏/含 archive/empty/no openspec)
- [ ] 加 `tests/cli/test_status_flags.sh` (4 flag × 2 模式 = 8 assertions)
- [ ] 更新 `docs/architecture/overview.md` §rddf CLI 表 (line 113) 加 Mode F 行
- [ ] 更新 `docs/architecture/cli.md` (如果有) 加 Mode F 文档
- [ ] 更新 `CHANGELOG.md` (如果存在) 标记 v2.x 新 Mode

## References

- `_lib/cli/status_cmd.py:108-168` (Mode A/B/D/E 路由分发)
- `_lib/cli/status_cmd.py:200-203, 336-339` (iteration.json 缺失错误信息)
- `_lib/schemas/iteration_schema.json` (v7 schema)
- `_lib/state_reader.py::read_iteration_or_corrupt` (损坏检测)
- `docs/architecture/overview.md:113` (`rddf status` 文档行)
- `ADR-0001-propose-plan-execute-state-machine.md` (propose 流程)
- `ADR-0025-design-proposal-creation.md` (proposal 创建模式)
- `ADR-0028-role-model-per-phase.md` (planner 起草角色约束)
- CppTLM session `ses_eb3545ac9ffefOzGFYynmFN2Ub` (2026-10-19 planner 反馈触发)