# extract-rdd-env-check-from-guide-arch

## Why

- **ADR-0003 §Decision 4 (三阶段 arch→plan→ship)**: arch 阶段是"高人工介入、
  低频执行的架构治理"，Phase 1 setup 当前承担两件异质任务——(a) 工件发现
  (ADR-0016 Layer 1) 和 (b) 环境健康检查 (openspec/git/build)。本提案分离
  (a) 保留在 guide-arch Phase 1，外置 (b) 到独立 skill，使 arch 阶段菜单首屏
  不再被静态环境信息淹没。
- **ADR-0016 Layer 1 (arch-artifact-discovery-contract)**: `discover_adr_dir` /
  `discover_roadmap` / `discover_architecture_dir` / `discover_adr_pattern`
  必须每次 phase 进入时运行 (branch 可能切换、ADR 目录可能重命名)，不能
  cache。**本提案不替换发现层，只外置环境健康检查**。
- **ADR-0017 (rddf-session)**: 当前 `stage_arch` 会话钩子 (entry/close) 仅
  追踪会话生命周期，无"会话级环境快照"概念。新增 `.rddf/state/.env-cache.json`
  作为 rddf-session 的伴随状态文件，自然落入 rddf-session 治理范围。
- **Token 经济学 (实测)**: 当前 guide-arch 入口输出 ~15 行静态环境信息。
  在 63 ADR / 6 活动 change 的项目上，用户每次进入 arch 阶段消耗 ~600 tokens
  噪音。本提案将噪音压缩到 ~50 tokens (单行状态 + 工件发现结果)。
- **2026-08-03 HydraForge 会话复盘**: 用户明确指出"希望引导创建
  adr-create / 架构差距分析 / 路线图定义等架构内容，而不是浪费很多会话上下文
  在环境检查上"——这是本提案的直接需求来源。

## What Changes

**In Scope**:

- **In Scope**:
- 新建独立 skill `skills/rdd-env-check/` (SKILL.md + scripts/env_check.sh)
- 新建伴随状态文件 `.rddf/state/.env-cache.json` (env 快照 + 失效时间戳)
- 重构 `skills/guide-arch/scripts/arch_env_check.sh` Phase 1 调用：
- 在 `skills/guide-design/scripts/` / `guide-plan/scripts/` / `guide-ship/scripts/`
- 添加 3 个 bats 单元测试：cache 命中 / cache 失效 (TTL) / cache 失效 (branch 变化)
- 更新 `skills/guide-arch.md` Phase 1 文档，移除"环境检查"步骤描述
- **Out Scope**:
- 不修改 `discover-arch-artifacts.sh` (ADR-0016 Layer 1 工件发现，
- 不修改 `arch_done_gate.sh` / `arch_quality_report.sh` / `write_arch_handoff.sh`
- 不修改 rddf-session 协议本身 (cache 文件是其伴随状态，
- 不引入 CI 自动化运行 env-check (留作 follow-up)
- 不修改 4 个 phase 技能的其他 phase (Phase 2-6 行为零变化)

### 关键场景

- **GIVEN** `.rddf/state/.env-cache.json` 存在且 mtime < 1h 且 cache.branch == 当前 branch
  **WHEN** `guide-arch` Phase 1 setup 执行
  **THEN** 跳过 `rdd-env-check` 全量检查，直接读 cache，菜单首屏输出
  `✅ Env OK (cached 23m ago) | ADR:63 | Roadmap:✓`
  (~50 tokens 而非 ~600 tokens)

- **GIVEN** `.rddf/state/.env-cache.json` 不存在 (首次运行)
  **WHEN** `guide-arch` Phase 1 setup 执行
  **THEN** 调用 `rdd-env-check` 全量检查，写 cache，再读 cache，菜单首屏同
  上 (后续进入直接命中 cache)

- **GIVEN** `.rddf/state/.env-cache.json` 存在但 mtime > 1h (TTL 过期)
  **WHEN** `guide-arch` Phase 1 setup 执行
  **THEN** 重新跑 `rdd-env-check` 全量检查，覆盖 cache

- **GIVEN** `.rddf/state/.env-cache.json` 存在但 cache.branch != `git rev-parse --abbrev-ref HEAD`
  (branch 切换)
  **WHEN** `guide-arch` Phase 1 setup 执行
  **THEN** 失效 cache，重新跑 `rdd-env-check`，覆盖 cache

- **GIVEN** `rdd-env-check` 检测到 openspec CLI 缺失或 git 工作区严重污染
  **WHEN** 任何 phase 子技能 Phase 1 setup 执行
  **THEN** 阻断 phase 进入，显示修复指引，退出码非 0
  (与现状一致，不削弱安全网)

- **GIVEN** 用户直接调用 `guide-arch` 而未先调用 `guide` 入口
  **WHEN** Phase 1 setup 执行
  **THEN** cache 不存在则现场跑全量检查，行为对用户透明
  (降级路径，与现状兼容)

**Out of Scope**:

- design 阶段不生成 tasks.md / design.md / specs (留在 plan fill)
- 不修改 ADR-0003 (另起 ADR 记录本次职责再分配)


## Capabilities

- `design-proposal-creation`: design 审批批准即创建完整 openspec change
- `design-content-review`: 两层内容审查 (improvements 5 段 + openspec validate), warning / strict 双模式


## Impact

- **受影响文件**: `skills/guide-design/SKILL.md` + 4 个 scripts, `skills/guide-plan/scripts/plan_intake.sh`, `docs/adr/ADR-0025-*.md` (新增)
- **兼容性**: `SKIP_DESIGN_HANDOFF=yes` 存量路径行为不变
- **硬约束**: 批准动作幂等; env-var 传参 (Oracle C1)


## Acceptance

| # | 标准 | 验证方式 |
|---|------|----------|
| 1 | `rdd-env-check` 输出 JSON 与现状 `arch_env_check.sh` 字段完全一致 | bats 测试：解析两脚本输出，diff 字段 |
| 2 | Phase 1 菜单首屏从 ~15 行压缩到 1 行 (含 ADR 计数 + roadmap 状态) | 手工对比脚本输出 line count |
| 3 | cache 命中时，Phase 1 setup 总耗时 < 100ms (不含 subprocess 启动) | `time` 命令对比 cache hit vs miss |
| 4 | TTL 过期或 branch 切换时自动重跑全量检查 | 3 个 bats 用例：mtime 修改 / 改 branch / cache 删除 |
| 5 | openspec 缺失场景下，phase 子技能正确阻断并给出修复指引 | bats：PATH 临时移除 openspec，断言 exit code ≠ 0 |
| 6 | 4 个 phase 技能 (arch/design/plan/ship) 行为兼容现状 | 现有 49 个测试 + 手动 walkthrough 全部通过 |
| 7 | 不引入新运行时依赖 (bash + git + openspec 三件套足够) | `command -v jq` / `command -v python3` 在测试中可缺席 |
| 8 | 关键函数 `_check_*` 在两个脚本间共享 (DRY) | grep `_lib/env_checks.sh` 引用计数 ≥ 4 |

