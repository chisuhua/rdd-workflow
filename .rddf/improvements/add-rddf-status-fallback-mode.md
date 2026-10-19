---
优先级: P1
来源: 2026-10-19 CppTLM 项目使用反馈 (session ses_eb3545ac9ffefOzGFYynmFN2Ub, 角色 planner) — `rddf status` 在 .rddf/state/iteration.json 缺失时输出模糊 "not found" 提示, 无法显示 openspec/changes/ 已有的 ground-truth 信息
阶段: phase-3
分类: cli-tooling
类型: improvement
主题: rddf status 自动降级模式 (iteration.json 缺失 → openspec fallback)
---
**优先级**: P1 | **来源**: 2026-10-19 CppTLM 项目使用反馈 | **阶段**: phase-3 | **分类**: cli-tooling | **类型**: improvement

**主题**: rddf status 自动降级模式 (iteration.json 缺失 → openspec fallback)

## 架构依据

`rddf status` 默认视图 (Mode A) 在 `.rddf/state/iteration.json` 缺失时:
- exit code = 0 (友好) ✅
- 但输出 "📭 iteration.json not found / initialize via: skill_use(\"propose\", \"<change-name>\")" 看起来像**系统错误**
- **完全空显示**, 浪费 `openspec/changes/` 目录中已有的 ground-truth 信息

**触发场景 (per CppTLM 真实案例)**:
- CppTLM 项目有 9 phase `.rddf/roadmap.md` (per 路线图治理, commit `84846cbb`)
- CppTLM 有 3 active + 95 archive `openspec/changes/` (procedural ground truth)
- CppTLM **未走 rdd-workflow propose 流程** → iteration.json 缺失 → `rddf status` 仅报"not found"
- CppTLM 用户 (planner 角色) 必须靠 `openspec list` 绕道才能看 active changes

**约束**:
- 现有 Mode A/B/D/E 不能 break (per `_lib/cli/status_cmd.py:108-168`)
- iteration.json > openspec/changes/ 数据优先级 (前者含 phase/category/blocker/plan_path)
- 降级仅在缺失/损坏触发, stale 不触发 (per `rddf iteration --strict` 已有 stale 检测)

**ADR**: 配套起草 `docs/adr/ADR-0059-rddf-status-fallback-mode.md`

## 范围

**In Scope**:

- 新增 `cmd_status` Mode F 分发 (per `_lib/cli/status_cmd.py`)
- 新增 `_mode_f_autodetect(project_root)` 实现: 优先 iteration.json, 失败降级 openspec 扫描
- 新增 `_render_openspec_fallback(project_root)` 实现: 扫 `openspec/changes/*/`, 排除 `archive/`, 渲染降级视图
- 新增 flag: `--autodetect` / `--fallback` (等价, 默认 `False`)
- 新增 flag: `--source=openspec|iteration|both` (默认 `iteration`)
- 新增 flag: `--no-initialize-hint` (抑制 initialize 提示, 默认 `False`)
- 新增 flag: `--show-archive` (包含 archive changes, 默认 `False`)
- 新增 flag: `--strict` (要求 iteration.json 存在, 缺失返 1, 默认 `False`)
- 加 `tests/cli/test_status_fallback.sh` (5 cases: 缺失/损坏/含 archive/empty/no openspec)
- 加 `tests/cli/test_status_flags.sh` (4 flag × 2 模式 = 8 assertions)
- 更新 `docs/architecture/overview.md:113` `rddf status` 文档行 (加 Mode F)
- 更新 `_print_help()` 帮助文本 (per `_lib/cli/status_cmd.py:398`)

**Out Scope**:

- 不修改 `openspec list` 命令 (已独立工作)
- 不修改 `rddf dashboard` / `rddf guide` 等其他命令 (各命令独立 Mode 体系)
- 不修改 `_lib/schemas/iteration_schema.json` (降级视图不写回 iteration.json)
- 不引入新依赖 (复用 rdd-workflow 现有 `_lib/state_reader`)
- 不实现 Mode F 的 `--roadmap` / `--iteration` 互操作 (Mode D/E 走各自数据源, 不降级)

## 关键场景

- **GIVEN** `.rddf/state/iteration.json` 缺失 + `openspec/changes/` 有 3 active changes
  **WHEN** `rddf status` 跑 (默认 Mode A)
  **THEN** 当前: 输出 "📭 not found" 友好提示, exit 0
  **THEN** 期望: 仍输出友好提示 (默认 Mode A 不变), exit 0

- **GIVEN** `.rddf/state/iteration.json` 缺失 + `openspec/changes/` 有 3 active changes
  **WHEN** `rddf status --autodetect` 跑
  **THEN** 期望: Mode F 自动降级, 扫描 openspec, 输出 best-effort 表 (含 source = openspec-fallback 标注), exit 0

- **GIVEN** `.rddf/state/iteration.json` 缺失 + `openspec/changes/` 有 95 archive + 3 active changes
  **WHEN** `rddf status --autodetect --show-archive` 跑
  **THEN** 期望: Mode F 降级 + 包含 archive changes, 输出 98 行 (3 + 95)

- **GIVEN** `.rddf/state/iteration.json` 损坏 + `openspec/changes/` 有 3 active changes
  **WHEN** `rddf status --autodetect` 跑
  **THEN** 期望: Mode F 自动降级 (iteration.json 损坏视为缺失), 输出降级视图

- **GIVEN** `.rddf/state/iteration.json` 存在 (含 5 active changes)
  **WHEN** `rddf status` 跑 (默认 Mode A)
  **THEN** 期望: Mode A 不变, 读 iteration.json, 输出原 5 行, exit 0 (无变化)

- **GIVEN** `.rddf/state/iteration.json` 缺失 + `openspec/changes/` 存在
  **WHEN** `rddf status --strict` 跑
  **THEN** 期望: 严格模式返 1, 输出 "iteration.json required by --strict, but missing"

- **GIVEN** `.rddf/state/iteration.json` 缺失 + `--source=openspec` 显式
  **WHEN** `rddf status --source=openspec` 跑
  **THEN** 期望: 跳过 iteration.json, 直接走 openspec fallback, 输出降级视图

- **GIVEN** `.rddf/state/iteration.json` 存在 (含 5 active changes) + `openspec/changes/` 有 95 archive
  **WHEN** `rddf status --source=both` 跑
  **THEN** 期望: 双源合并显示, 不一致时打印 "iteration.json 与 openspec/changes/ 不一致 (差 N 项)"

## 验收标准

### 功能验收 (5 cases per `tests/cli/test_status_fallback.sh`)

1. Mode A (默认) 在 iteration.json 缺失时 exit 0, 输出友好提示
2. Mode F (`--autodetect`) 在 iteration.json 缺失 + openspec 存在时 exit 0, 输出降级视图
3. Mode F (`--fallback`) 等价于 `--autodetect`
4. `--show-archive` 包含 archive changes
5. iteration.json 损坏时 Mode F 触发降级

### Flag 验收 (8 assertions per `tests/cli/test_status_flags.sh`)

6. `--no-initialize-hint` 抑制 initialize 提示
7. `--strict` 在缺失时返 1
8. `--source=openspec` 跳过 iteration.json
10. `--source=both` 合并显示 + 不一致告警

### 兼容性验收

11. 现有 `rddf status` 调用 (无 flag) 行为不变 (Mode A 0 流失)
12. 现有 `rddf status <name>` 行为不变 (Mode B 0 流失)
13. 现有 `rddf status --roadmap` 行为不变 (Mode D 0 流失)
14. 现有 `rddf status --iteration` 行为不变 (Mode E 0 流失)

### 文档验收

15. `docs/architecture/overview.md:113` 表格行加 Mode F 描述
16. `_print_help()` 帮助文本列 4 新 flag
17. `tests/cli/test_status_fallback.sh` + `test_status_flags.sh` 加入 CI

### 性能验收

18. Mode F 扫描 `openspec/changes/` 100 dir 估时 < 1s (实测)
19. Mode F 大项目 (10000+ dir) 仍 < 10s (benchmark 决定是否需加缓存)

## Capabilities

### New Capabilities

- **`status-fallback`**: 在 iteration.json 缺失/损坏时自动降级显示 openspec/changes/ 内容
- **`status-source-flexible`**: `--source=openspec|iteration|both` 显式选择数据源
- **`status-strict-mode`**: `--strict` 给 CI 用, 严格要求 iteration.json 存在
- **`status-archive-visible`**: `--show-archive` 给复盘用, 包含 archive changes

### Affected Capabilities (no break)

- `status-overview` (Mode A): 默认行为不变, 仍优先 iteration.json
- `status-detail` (Mode B): `<name>` 仍走 iteration.json, 缺失返 1 (严格)
- `status-roadmap` (Mode D): `--roadmap` 仍走 roadmap-state.json, 不降级
- `status-iteration` (Mode E): `--iteration` 仍走 iteration.json (delegated to render)

## Impact

### 正面影响

- **未初始化项目可用性**: CppTLM 类项目能直接用 `rddf status --autodetect` 查看活跃 change, 不需要先走 propose
- **诊断降级保留**: iteration.json 损坏仍能看 best-effort 视图, 不需立即修复 schema
- **4 flag 灵活性**: `--source=both` 双源对比; `--strict` 给严格 CI; `--no-initialize-hint` 给脚本; `--show-archive` 给复盘
- **0 改动 Mode A/B/D/E**: 现有调用全兼容, 现有测试不动
- **0 改动 iteration_schema.json**: schema 保持权威性, fallback 视图不污染主状态
- **跨项目 dogfooding**: CppTLM, UsrLinuxEmu, ArchForge 等多项目可受益

### 负面影响 / 风险

- **Mode F 输出字段缺失**: 降级视图无 phase / category / blocker / plan_path 字段. 缓解: 表头明确写 "Source: openspec-fallback, no iteration.json"
- **Mode F 扫描慢**: 100 dir < 1s, 大项目需 benchmark. 缓解: 输出加进度提示, 后续考虑缓存
- **误用风险**: `--source=both` 可能让用户误以为 iteration.json + openspec/changes/ 总是一致. 缓解: 双源不一致时打印告警
- **CI 行为**: 现有脚本默认 Mode A 不变, 新 flag 是显式 opt-in, 不会被意外触发

### 估时

| 任务 | 估时 |
|------|------|
| 实施 Mode F + 4 flag (per `cmd_status` + helpers) | 0.5d |
| 加 `test_status_fallback.sh` (5 cases) | 0.2d |
| 加 `test_status_flags.sh` (8 assertions) | 0.2d |
| 更新 `docs/architecture/overview.md:113` | 0.1d |
| 更新 `_print_help()` | 0.1d |
| 跨 CI 验证 (per `tests/integration/`) | 0.2d |
| **总估时** | **1.3d** |

### 依赖

- 无新依赖
- 无新 schema 改动
- 无 frozen headers 改动 (rdd-workflow 自身的 _lib/ 全部可改)

### 文档

- `docs/adr/ADR-0059-rddf-status-fallback-mode.md` (决策真源)
- `docs/architecture/overview.md:113` (CLI 表格更新)
- `_print_help()` 帮助文本 (per `_lib/cli/status_cmd.py:398`)

## References

- `_lib/cli/status_cmd.py:108-168` (Mode A/B/D/E 路由分发)
- `_lib/cli/status_cmd.py:200-203, 336-339` (iteration.json 缺失错误信息)
- `_lib/schemas/iteration_schema.json` (v7 schema)
- `_lib/state_reader.py::read_iteration_or_corrupt` (损坏检测)
- `docs/architecture/overview.md:113` (`rddf status` 文档行)
- `ADR-0001-propose-plan-execute-state-machine.md` (propose 流程)
- `ADR-0025-design-proposal-creation.md` (proposal 创建模式)
- `ADR-0028-role-model-per-phase.md` (planner 起草角色约束)
- `.rddf/improvements/add-brainstorm-hardgate-enforcement.md` (improvement 格式参考)
- CppTLM session `ses_eb3545ac9ffefOzGFYynmFN2Ub` (2026-10-19 planner 反馈触发)