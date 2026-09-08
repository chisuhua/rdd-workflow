# rdd-workflow 端到端测试计划（v1）

> **日期**: 2026-09-08
> **作者**: sisyphus (brainstorming session)
> **状态**: 待用户审查
> **关联 ADR**: ADR-0028（role model per phase）、ADR-0034（rdd-verifier 5 阶段）、ADR-0045（inline-ac-verifier-into-rdd-verifier）、ADR-0047（rdd-quick bypass-path）
> **关联 skill**: `rdd-arch` / `rdd-planner` / `rdd-builder` / `rdd-verifier` / `rdd-quick`
> **关联 testbed**: `chisuhua/rdd-workflow-e2e`（外部仓库，4-5 stage 全流程）

## 1. 背景与问题

### 1.1 现状审计（2026-09-08）

rdd-workflow 当前共有 ~281 bats + ~2017 pytest 测试，但按流程分布严重不均：

| 流程 | 真实 e2e | 契约/结构 | 缺口 |
|------|----------|-----------|------|
| `rdd-quick` | 0 | 27 | P0-P4 状态机从未真跑 |
| `rdd-builder` | 0 | 26 | 6 phase 脚本仅"存在"被测，真路径靠 env-var shim 伪造 |
| `rdd-planner` | 0 | 12 unit + 0 bats | 横切命令从未集成测试 |
| `rdd-verifier` | 0 | 8 unit | verdict JSON 6 字段 + 失败回环路径未测 |
| `rdd-arch` | 0 | 10 | arch-done gate + arch-handoff contract 仅契约层 |
| 外部 testbed | ✓（独立仓库） | — | arch+planner+(quick\|builder)+verifier 全流程覆盖 |

**核心痛点**：
1. **Prose UX 漂移未捕获**：rdd-workflow skills 是 prose-driven（agent 读 SKILL.md 后行动），但没有任何测试验证 agent 真的能按 prose 走完状态机。SKILL.md 改一个字可能 silent break 整个 skill 行为。
2. **Phase 脚本空跑**：`test_full_workflow_e2e.bats` 的 `invoke_builder_phases` 用 `E2E_BUILDER_PHASE=phase-2` 等 env 变量注入**伪造状态**，从不调用 `skills/rdd-builder/scripts/phase*.sh` 真路径。spec §3.4 的 6-phase 状态机从未真跑过。
3. **Verifier 失败回环未测**：ADR-0034 + ADR-0045 核心机制（AC 验证 → 启发式分类 → P1/P2 回环 → max 3 retry）从未在测试中出现。
4. **零散状态文件污染**：5 个 skill 都写 `.rddf/state/*.json`，但没有统一隔离 + cleanup 验证。

### 1.2 外部 testbed 已覆盖什么

`chisuhua/rdd-workflow-e2e` 仓库（独立项目，nightly cron）已覆盖：
- 第三方项目视角的 `arch → planner → builder → archive` / `arch → planner → quick → verifier` 全流程
- 36 个 `rddf` CLI 子命令 smoke
- 安装路径 / 全局 vs 项目安装切换

外部仓库**不覆盖**本仓的：
- 单 skill 内部状态机 prose UX
- 失败回环 / 重试路由
- 隔离 / 零污染契约

## 2. 设计目标

| 目标 | 实现 |
|------|------|
| 5 skill 真 e2e 覆盖 | 本仓 5 个 skill（rdd-arch / rdd-planner / rdd-builder / rdd-verifier / rdd-quick）每 skill ≥8 scenario |
| Prose UX 验证 | C 层（AI agent 模拟）真读 SKILL.md 走状态机 |
| 状态机真实路径 | A 层（脚本调用）真调 6 phase 脚本 + 2 个 planner/arch 子脚本 |
| 零污染契约 | sha256 锁住 `$REPO_ROOT/.rddf/` / `openspec/` / 4 阶段 state 文件在测试后不变 |
| 失败回环验证 | verifier retry loop（spec §3.4 P3 → P1/P2, max 3）真跑 |
| 隔离 | BATS_TEST_TMPDIR + per-scenario `setup_fake_project` |
| 外部 testbed 协同 | 本仓 e2e 单 skill 粒度；外部 testbed 多 stage 集成 |

**非目标 (YAGNI)**:
- 不重写现有契约测试（27+26+12+8+10 维持）
- 不并发跑 agent 模拟（避免 token 峰值 + 输出交错难审计）
- 不做 LLM provider 切换（执行 agent 即 LLM，per ADR-0045）
- 不取代 `rdd-workflow-e2e` 外部仓库（边界明确划分，见 §6）
- 不为 .rddf-workflow 文档 / ADR 内容写 e2e（属 doc-contracts 已覆盖）

## 3. 分层执行模型

### 3.1 C 层（AI agent 模拟）— 主力

**核心思想**：rdd-workflow skills 是 prose-driven，真 e2e = 真测 agent 能否按 SKILL.md 行动。

| 属性 | 实施 |
|------|------|
| 入口 | 启动本地 agent，喂入 prompt：`请按 skill_use("<skill>") 走完状态机，输入：<fixture>，捕获产出：<产出清单>` |
| 输出 | agent 写出 plan / handoff / verdict / history 等真实文件 |
| 断言 | 文件存在 + 关键字段比对 + golden output sha256 锁 |
| 触发 | nightly cron + 本地 `RDDF_AGENT_E2E=1 bats tests/e2e/agent/` |
| 凭据 | 复用本地 agent 配置（`~/.config/opencode/agent.yaml` 等），CI 环境无凭据自动 skip |
| 失败分类 | 失败时 stderr 标 "prose drift"（issue 给 SKILL.md 作者）vs "script bug"（issue 给脚本作者）vs "env error"（skip） |

**适用场景**：
- Prose 漂移检测（SKILL.md 改字 → C 层 fail）
- 复杂状态机决策（重试、升级、模式分流）
- Agent 能否从 SKILL.md 提取正确入口命令

**不适用**：CI 必跑（成本/凭据）、纯文件 I/O 验证（用 A 层更快更准）。

### 3.2 A 层（脚本调用 smoke）— CI 必跑

**核心思想**：跳过 prose 解释层，直接调 `phase*.sh` 验证脚本本身能跑、有产出、退出码对。

| 属性 | 实施 |
|------|------|
| 入口 | `bash skills/<skill>/scripts/phase*.sh <args> --auto-approve --no-confirm`（需 phase 脚本支持非交互 flag） |
| 输出 | 脚本产生的 state 文件 + git 提交 |
| 断言 | exit code + 文件存在 + 关键字段存在 |
| 触发 | `./test.sh --e2e-smoke` + CI PR/push |
| 凭据 | 无（纯 bash + Python） |
| 速度 | < 60s 整个 A 层 |

**适用场景**：
- Phase 脚本语法 / 依赖 / exit code 回归
- D3 spec-delta 等机械产物落盘
- worktree 模式 vs lightweight 模式机械分流
- 零污染契约（sha256 锁）

**不适用**：prose UX（用 C）、verdict JSON 6 字段构造（用 C）。

### 3.3 现有契约测试（不动）

`test_rdd_quick.bats`（14）、`test_rdd_builder_phases.bats`（19）、`test_full_workflow_e2e.bats`（7）等保持现状，作为快速结构 / 契约 smoke 继续跑。

## 4. 目录结构

```
tests/e2e/
├── _lib/
│   ├── isolation.bash          # BATS_TEST_TMPDIR 包装 + 状态快照/比对
│   ├── agent_runner.bash       # AI agent spawn 框架（prompt 喂入 + output 捕获 + retry）
│   ├── golden_compare.bash     # golden output sha256 + 关键字段 diff
│   └── script_smoke.bash       # A 层 phase 脚本非交互入口封装
├── script/                     # A 层：CI 必跑（10 cases）
│   ├── test_rdd_quick_smoke.bats        # 4 cases: scaffold + append_history + AC 来源 + 隔离
│   └── test_rdd_builder_smoke.bats      # 6 cases: 6 phase 脚本 --no-confirm
├── agent/                      # C 层：nightly + 手动（5 × 8 = 40 cases）
│   ├── test_rdd_arch_e2e.bats           # 8 scenarios A-E1..A-E8
│   ├── test_rdd_planner_e2e.bats        # 8 scenarios P-E1..P-E8
│   ├── test_rdd_builder_e2e.bats        # 12 scenarios B-E1..B-E12
│   ├── test_rdd_verifier_e2e.bats       # 8 scenarios V-E1..V-E8
│   ├── test_rdd_quick_e2e.bats          # 8 scenarios Q-E1..Q-E8
│   └── scenarios/              # 每 case 一个 JSON：input + golden_output + expected_AC
│       ├── a_e1.json ... a_e8.json
│       ├── p_e1.json ... p_e8.json
│       ├── b_e1.json ... b_e12.json
│       ├── v_e1.json ... v_e8.json
│       └── q_e1.json ... q_e8.json
└── fixtures/                   # 共享 fake project 模板 + sample proposal
    ├── fake_project_template/
    ├── sample_proposal_minimal.md
    ├── sample_proposal_complex.md
    └── sample_proposal_broken.md
```

## 5. CI 集成

| Trigger | Command | 跑什么 | 必须绿？ |
|---------|---------|--------|----------|
| PR / push | `./test.sh --full --regression` | 全量 + 现有 KNOWN_FAILURES 检查 | ✅ 必 |
| PR / push | `./test.sh --e2e-smoke` | A 层 `tests/e2e/script/` | ✅ 必 |
| Nightly cron | `./test.sh --e2e-agent` | C 层 `tests/e2e/agent/` | ⚠️ 必（无 LLM 凭据时 skip，不 fail） |
| 手动（开发者） | `RDDF_AGENT_E2E=1 bats tests/e2e/agent/` | C 层（本地） | 开发者选 |
| 手动（hotfix） | `SKIP_AGENT_E2E=1` | 跳过 C 层 | 仅 hotfix 留 audit trail |

**GitHub Actions 工作流**：
- `.github/workflows/e2e-nightly.yml`：nightly 02:00 UTC 跑 C 层
- `.github/workflows/test.yml`：扩展 PR/push 跑 A 层
- 工作流需 `continue-on-error: true` 容错 agent 凭据缺失

## 6. 外部 Testbed 职责边界

| 职责 | 本仓 e2e/ | `chisuhua/rdd-workflow-e2e` |
|------|-----------|------------------------------|
| 单 skill 真 e2e（prose UX） | ✅ C 层 5 skill | — |
| Phase 脚本非交互 smoke | ✅ A 层 | — |
| 4-5 stage 全流程 e2e | — | ✅ arch+planner+quick+verifier / arch+planner+builder+verifier |
| 36 rddf CLI 子命令 smoke | — | ✅ |
| 第三方项目视角安装测试 | — | ✅ |
| 跨 stage 状态机集成 | — | ✅ |
| Prose 漂移检测 | ✅ C 层（per skill） | — |
| 零污染契约 | ✅ A 层 | — |

**协同契约**：
- 本仓 A 层 + 外部 testbed 共同覆盖"机械正确性"
- 本仓 C 层独占 prose UX 覆盖
- 任何一方的"全流程"失败都触发另一方的"单 skill"重测以定位故障域

## 7. 质量门 / 验收标准

本计划完成（v1 release）定义：

| # | 验收项 | 测量方式 |
|---|--------|----------|
| 1 | A 层 `tests/e2e/script/` 10 cases 全绿 | `./test.sh --e2e-smoke` exit 0 |
| 2 | C 层 `tests/e2e/agent/` 44 cases 全绿或 golden lock 报 drift | `RDDF_AGENT_E2E=1 bats tests/e2e/agent/` |
| 3 | 现有 `./test.sh --full --regression` 维持 | 仅 KNOWN_FAILURES.txt 5 个 baseline 失败 |
| 4 | 0 flaky test | C 层首跑后 7 天窗口内无 spurious fail |
| 5 | 覆盖矩阵 | rdd-quick 8/8 P0-P4、rdd-builder 12/12 6 phases + retry、rdd-arch 8/8、rdd-planner 8/8、rdd-verifier 8/8 |
| 6 | 隔离 | 每 case 运行后 `$REPO_ROOT/.rddf/` / `openspec/` sha256 与 baseline 一致 |
| 7 | 文档 | 1 主策略 + 5 场景 spec 落盘并 commit |
| 8 | CI | `.github/workflows/e2e-nightly.yml` + `test.sh` 扩展已合并 |
| 9 | 外部 testbed 联动 | 本仓 README "测试" 段加外部 testbed 引用 + 协同契约说明 |

## 8. 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| C 层 non-deterministic | 高 | flaky | golden output sha256 + 关键字段断言；prose drift 单独报警 |
| C 层成本（CI 跑 LLM） | 高 | CI 慢 / 贵 | 默认 skip；nightly 才跑；本地 `RDDF_AGENT_E2E=1` 选跑 |
| Phase 脚本非交互改造 | 中 | 改动 phase 脚本 | 保留默认行为；非交互 flag 通过 `--auto-approve` 显式触发 |
| Golden output 过期 | 中 | prose 改即 fail | 提供 `UPDATE_GOLDEN=1` 一键重锁 + 显式 audit trail |
| 5 skill 同步推进 | 中 | 工作量大 | P0 顺序：rdd-quick (8) → rdd-builder (12) → rdd-verifier (8) → rdd-arch (8) → rdd-planner (8) |
| Agent 凭据不一致 | 低 | 本地可跑 CI 不行 | CI `continue-on-error: true` + 显式 skip 报告 |

## 9. 实施阶段（writing-plans 阶段细化）

1. **Phase 1 — A 层基础设施** (P0)
   - `tests/e2e/_lib/{isolation,script_smoke,golden_compare}.bash` 抽取
   - phase 脚本加 `--auto-approve --no-confirm` flag（如缺失）
   - `tests/e2e/script/test_rdd_quick_smoke.bats` (4 cases)
   - `tests/e2e/script/test_rdd_builder_smoke.bats` (6 cases)

2. **Phase 2 — C 层基础设施 + 1 skill 试点** (P0)
   - `tests/e2e/_lib/agent_runner.bash` 实现
   - `tests/e2e/agent/scenarios/q_e*.json` 8 个 golden output
   - `tests/e2e/agent/test_rdd_quick_e2e.bats` 8 cases
   - 验证 prose UX 真跑通 1 个 skill 后，再推广

3. **Phase 3 — C 层余 4 skill** (P1)
   - rdd-builder / rdd-verifier / rdd-arch / rdd-planner 各 e2e.bats + scenarios/*.json

4. **Phase 4 — CI 集成** (P1)
   - `.github/workflows/e2e-nightly.yml`
   - `test.sh` 扩展 `--e2e-smoke` / `--e2e-agent` / `--e2e-all`
   - README "测试" 段扩展

5. **Phase 5 — 外部 testbed 联动文档** (P2)
   - 本仓 README 加外部 testbed 引用
   - 双向 issue 模板（如有）

## 10. 决策记录

| 决策 | 选项 | 选择 | 理由 |
|------|------|------|------|
| 执行模型 | A 脚本调用 / B 抽 Python runner / C AI agent 模拟 | **C 为主 + A smoke** | rdd-workflow skills 是 prose-driven；C 唯一能验证 prose UX；A 保 CI 必跑 |
| 分层触发 | 仅 CI / 仅本地 / nightly | **A CI 必 + C nightly 选** | 平衡成本/真实性 |
| 文档结构 | 1 综合 / 1+2 / 1+5 | **1 主策略 + 5 场景 spec** | 5 skill 每 spec 一份，单独 review 方便 |
| 隔离机制 | shared state / BATS_TEST_TMPDIR / docker | **BATS_TEST_TMPDIR + sha256 锁** | 现有约定（`test_full_workflow_e2e.bats`） |
| Golden output | 不锁 / 全文 sha256 / 关键字段 | **关键字段断言 + sha256 辅助** | 全文 sha256 过度敏感，关键字段更稳 |
| 零污染验证 | 不验证 / 散落断言 / 统一 hash 锁 | **统一 hash 锁**（`isolation.bash::verify_zero_pollution`） | 单一入口，覆盖全 5 skill |
| 与外部 testbed 关系 | 取代 / 重复 / 互补 | **互补**（边界明确） | 外部 cover 多 stage 集成，本仓 cover 单 skill + prose UX |

## 11. 关联文件清单

### 设计阶段（本 spec）
- `docs/superpowers/specs/2026-09-08-e2e-test-plan-design.md`（本文档）
- `docs/superpowers/specs/2026-09-08-rdd-quick-e2e-scenarios.md`
- `docs/superpowers/specs/2026-09-08-rdd-builder-e2e-scenarios.md`
- `docs/superpowers/specs/2026-09-08-rdd-arch-e2e-scenarios.md`
- `docs/superpowers/specs/2026-09-08-rdd-planner-e2e-scenarios.md`
- `docs/superpowers/specs/2026-09-08-rdd-verifier-e2e-scenarios.md`

### 实施阶段（writing-plans 阶段产出，本 spec 不展开）
- `tests/e2e/_lib/*.bash`（4 个 helper）
- `tests/e2e/script/*.bats`（2 个文件，10 cases）
- `tests/e2e/agent/*.bats`（5 个文件，44 cases）
- `tests/e2e/agent/scenarios/*.json`（44 个 golden output）
- `tests/e2e/fixtures/`（共享模板）
- `.github/workflows/e2e-nightly.yml`
- `test.sh` 扩展
- README "测试" 段更新
