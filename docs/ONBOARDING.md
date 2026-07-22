# rdd-workflow 新成员入职指南

> 生成时间: 2026-06-29
> 基于知识图谱分析

---

## 项目概览

| | |
|---|---|
| **项目名** | rdd-workflow |
| **版本** | v2.0.0-beta |
| **描述** | OpenSpec 工作流技能包，实现 propose→plan→execute→status→archive 变更管理生命周期 |
| **语言** | Python, Shell (Bash), Markdown, YAML, JSON |
| **框架** | pytest, Bats (Bash 测试), GitHub Actions |
| **复杂度** | ⚡ moderate（66 个文件，约 10K+ 行代码） |

### 这是什么项目？

rdd-workflow 是一个 **AI 助手工作流技能包**，提供给 Claude Code / OpenCode 等 AI 编程助手使用。它定义了从**变更提议**到**执行归档**的完整生命周期管理流程。

项目已演进到 **v2.0**，引入了三阶段架构（Arch → Plan → Ship）和闭环自动化引擎（Loop Engine）。

---

## 项目结构总览

```
rdd-workflow/
├── README.md                         # 项目入口（从这里开始）
├── USAGE.md                          # 完整使用指南（术语字典）
├── package.json                      # npm 包定义
├── install.sh                        # 安装脚本
├── requirements.txt                  # Python 依赖
├── .github/workflows/test.yml        # CI 流水线
├── skills/
│   ├── INSTALL.md                    # 安装程序（第一入口）
│   ├── guide.md                      # 推荐器入口
│   ├── guide-arch.md                 # Arch 阶段状态机
│   ├── guide-plan.md                 # Plan 阶段状态机
│   ├── guide-ship.md                 # Ship 阶段状态机
│   ├── propose.md                    # 变更提议
│   ├── execute.md                    # 变更执行
│   ├── status.md                     # 状态检查
│   ├── roadmap.md                    # 路线图管理
│   ├── deps.md                       # 依赖分析
│   ├── rdd-workflow-writing-plans.md # 实施计划生成
│   ├── loop_engine.py                # 闭环自动化核心引擎
│   └── _lib/                         # Python 辅助库（22 个模块）
│       ├── actions.py                # 核心操作定义
│       ├── state_vector.py           # 状态向量
│       ├── event_log.py              # 事件日志
│       ├── gate.py                   # 门控机制
│       ├── memory.py                 # 记忆系统
│       ├── tribunal.py               # 委员会裁决
│       └── ... (共 22 个模块)
```

---

## 架构层次

系统分为 **6 个架构层**，自顶向下：

### 1. 入口与展示层（14 个文件）
项目入口文档、配置元数据和安装程序，面向用户的第一界面。

**关键文件：**
| 文件 | 说明 |
|---|---|
| `README.md` | 项目入口文档，安装方式、使用流程、目录结构 |
| `USAGE.md` | 743 行的详尽使用指南，核心概念字典 |
| `CHANGELOG.md` | v2.0.0-beta 版本记录 |
| `package.json` | npm 包定义，依赖和引擎要求 |
| `install.sh` | 自动安装脚本，检测环境 → 复制文件 → 验证 |
| `.gitignore` | Git 忽略规则 |

### 2. 工作流状态机层（13 个文件）
定义三阶段（Arch→Plan→Ship）状态机和工作流推荐器。

**关键文件：**
| 文件 | 说明 |
|---|---|
| `skills/guide.md` | 推荐器入口 — 扫描状态、推荐下一步 |
| `skills/guide-arch.md` | Arch 端 — 5 阶段：setup → adr-create → architecture → roadmap → arch-done |
| `skills/guide-plan.md` | Plan 端 — 4 阶段：scan → propose → deps → plan-done |
| `skills/guide-ship.md` | Ship 端 — 5 阶段：plan → execute → archive → cleanup → ship-done |

**状态机调用链：**
```
guide.md (推荐器)
  ├── guide-arch.md → roadmap.md (Arch 阶段完成)
  │     └── [transitions_to]
  ├── guide-plan.md → propose.md, deps.md (Plan 阶段完成)
  │     └── [transitions_to]
  └── guide-ship.md → rdd-workflow-writing-plans.md, execute.md, status.md
```

### 3. Loop 引擎层（1 个文件）
闭环自动化核心引擎。

| 文件 | 说明 |
|---|---|
| `skills/loop_engine.py` | **290 行** Python 引擎 — 扫描→计划→执行→验证→自适应调整 |

Loop 引擎是整个 v2.0 的核心创新。它实现了：
- **闭环自动化**：自动检测项目状态 → 生成执行计划 → 执行变更 → 验证结果
- **振荡检测**：检测和防止反复在相同状态之间切换
- **断路器机制**：当连续失败达到阈值时自动熔断

### 4. Python 辅助库层（26 个文件）
支撑 Loop 引擎和状态机的 Python 模块集合。

**核心模块：**
| 模块 | 行数 | 职责 |
|---|---|---|
| `actions.py` | 384 | 7 个核心操作：create_worktree, generate_plan, execute 等 |
| `detectors.py` | 384 | 项目状态检测器：worktree / changes / health / test 等 |
| `tribunal.py` | 327 | 委员会裁决系统，多智能体共识决策 |
| `session.py` | 266 | 会话协调器，多会话状态管理 |
| `gate.py` | 249 | 门控机制，阶段转换条件校验 |
| `memory.py` | 231 | 执行记录和记忆系统 |
| `state_vector.py` | 219 | 状态向量 — 整个系统的状态核心 |
| `event_log.py` | 148 | 事件日志系统 |
| `agents.py` | 175 | 多智能体协调框架 |
| `sanitizer.py` | 155 | 输入清洗和安全检查 |

**数据流示例：**
```
loop_engine.py → actions.py (执行操作)
  → state_vector.py (读取/更新状态)
  → event_log.py (记录事件)
  → gate.py (检查门控条件)
  → tribunal.py (需要时裁决)
```

### 5. Shell 辅助库层（3 个文件）
支撑 Git 操作和归档流程的 shell 脚本库。

| 脚本 | 行数 | 职责 |
|---|---|---|
| `worktree.sh` | 79 | Git worktree 管理 — 创建、清理、分支检测 |
| `archive.sh` | 228 | 归档操作 — 合并验证、分支删除、安全清理 |
| `state.sh` | 3 | 已存根的共享状态辅助函数 |

### 6. 数据与基础设施层（9 个文件）
Schema 定义、状态持久化文件、CI 流水线和 Issue 模板。

| 文件 | 说明 |
|---|---|
| `.github/workflows/test.yml` | GitHub Actions CI — push/PR 触发 pytest + bats |
| `skills/_lib/schemas/state_vector_schema.json` | 状态向量 JSON Schema（226 行） |
| `skills/_lib/phase_templates.yaml` | 路线图阶段模板（192 行） |
| `.rddf/state/index.md` | 状态文件目录索引 |

---

## 关键概念

### 三阶段架构（Arch → Plan → Ship）

| 阶段 | 技能 | 职责 | 人工介入 |
|---|---|---|---|
| **Arch** | `guide-arch` | 架构定义（ADR、roadmap、差距分析） | 高 |
| **Plan** | `guide-plan` | 变更生成（scan、propose、deps） | 中 |
| **Ship** | `guide-ship` | 变更执行（worktree、execute、archive） | 低 |

### Loop 引擎

v2.0 引入的核心自动化机制。`loop_engine.py` 实现了自适应的闭环工作流：

```
扫描状态 → 生成计划 → 执行计划 → 验证结果
                         ↕
                   自适应调整（含振荡检测 + 断路器）
```

### 推荐器系统

`guide.md` 作为入口推荐器，根据项目当前状态智能推荐下一步：

```
💡 Recommended: skill_use("guide-plan")
   Reason: 架构定义已完成 → 进入变更生成
```

### 门控机制

`gate.py` 控制阶段转换的门控条件，确保状态机按正确顺序推进。每个阶段完成前需要满足特定的前置条件。

### 计划生成

`rdd-workflow-writing-plans.md` 是 v2.0 自包含的计划生成器，fork 自 superpowers/writing-plans 并适配 OpenSpec change 上下文。

- **TDD 5 步结构**: Write failing test → Verify fail → Implement → Verify pass → Commit
- **零外部依赖**: 不依赖 oh-my-opencode/superpowers 等外部 skill
- **输出路径**: `.rddf/plans/<name>.md`

`guide-ship` Phase 1 自动调用本技能：
```
skill_use("rdd-workflow/writing-plans")
```

---

## 学习路径（10 步导览）

| 步骤 | 主题 | 涵盖文件 |
|---|---|---|
| **1** | 从 README 出发 — 项目全景认知 | `README.md` |
| **2** | USAGE.md — 完整使用指南与核心概念 | `USAGE.md` |
| **3** | INSTALL.md + install.sh — 技能如何进入项目 | `INSTALL.md`, `install.sh`, `package.json` |
| **4** | guide.md — 工作流推荐器 | `guide.md` |
| **5** | 三阶段状态机总览 | `guide-arch.md`, `guide-plan.md`, `guide-ship.md` |
| **6** | Arch 与 Plan 子技能 | `propose.md`, `roadmap.md`, `deps.md` |
| **7** | Ship 端子技能 + 计划生成 | `execute.md`, `status.md`, `rdd-workflow-writing-plans.md` |
| **8** | loop_engine.py — 闭环自动化核心引擎 | `loop_engine.py` |
| **9** | Python 辅助库核心 | `state_vector.py`, `event_log.py`, `event_types.py`, `gate.py`, `memory.py` |
| **10** | Shell 库、CI 与基础设施 | `state.sh`, `worktree.sh`, `archive.sh`, `test.yml`, `.rddf/state/index.md` |

> 完整导览详情见知识图谱的 `tour` 部分（10 步，每步含具体文件清单和描述）。

---

## 复杂度热点

所有文件复杂度均为 **moderate**（中等），以下为最值得关注的模块：

| 文件 | 行数 | 关注原因 |
|---|---|---|
| `skills/_lib/detectors.py` | 384 | 最复杂的检测逻辑，包含 10+ 检测函数 |
| `skills/_lib/actions.py` | 384 | 7 个核心操作，涉及 worktree/plan/execute/archive |
| `skills/_lib/tribunal.py` | 327 | 委员会裁决逻辑，多智能体共识 |
| `skills/loop_engine.py` | 290 | 自动化引擎主入口，振荡检测 + 断路器 |
| `skills/_lib/session.py` | 266 | 多会话状态管理和协调 |
| `skills/_lib/gate.py` | 249 | 门控条件校验逻辑 |
| `skills/_lib/memory.py` | 231 | 记忆系统，执行记录管理 |
| `skills/_lib/state_vector.py` | 219 | 状态向量核心，系统状态支柱 |
| `skills/_lib/archive.sh` | 228 | 归档操作 Shell 脚本 |
| `skills/roadmap.md` | 797 | 路线图管理技能文档 |
| `skills/guide-arch.md` | 805 | Arch 状态机文档 |
| `skills/propose.md` | 742 | 变更提议流程文档 |

> 💡 **建议**：新成员可以从 Step 1-4（入口和推荐器）开始，逐步深入到 Step 8-9（引擎和库）。

---

## 开发指南

### 环境要求

| 工具 | 版本要求 |
|---|---|
| openspec CLI | >= 1.3.1 |
| git | >= 2.25 |
| cmake | >= 3.16 |
| Python | >= 3.10 (用于测试) |
| Node.js | >= 18 (用于 npm) |

### 运行测试

```bash
# Python 测试（pytest）
pytest tests/

# Bash 测试（bats）
bats tests/
```

### 安装到项目

```bash
# 方式 1: npx skills (推荐)
npx skills add chisuhua/rdd-workflow -g -y

# 方式 2: 手动
bash install.sh /path/to/project
```

### 主要依赖

- **pytest** — Python 测试框架（18 个单元测试 + 3 个集成测试）
- **bats** — Bash 自动化测试框架
- **GitHub Actions** — CI 流水线（push/PR 时自动测试）

---

## 文件地图（按层组织）

### 入口与展示层
```
.claude-plugin/marketplace.json     — Claude 市场插件元数据
.claude-plugin/plugin.json          — Claude 插件定义
README.md                           — 项目入口文档
USAGE.md                            — 使用指南（743行）
CHANGELOG.md                        — 版本变更记录
package.json                        — npm 包定义
requirements.txt                    — Python 依赖
install.sh                          — 安装脚本
.gitignore                          — Git 忽略规则
.rdd-workflow/flow.yaml.example    — 流程 YAML 配置示例
project-organization-plan.md        — 项目整理计划
project-organization.md             — 执行计划（847行）
proposal-suggestions.md             — 改进建议占位
roadmap.md                          — 版本路线图
```

### 工作流状态机层
```
skills/guide.md                     — 推荐器入口
skills/guide-arch.md                — Arch 端状态机（805行）
skills/guide-plan.md                — Plan 端状态机（622行）
skills/guide-ship.md                — Ship 端状态机（722行）
skills/INSTALL.md                   — 安装程序文档
skills/propose.md                   — 变更提议（742行）
skills/roadmap.md                   — 路线图管理
skills/deps.md                      — 依赖分析（719行）
skills/execute.md                   — 变更执行（457行）
skills/status.md                    — 状态检查（470行）
skills/rdd-workflow-writing-plans.md — 计划生成（自包含，TDD 5 步结构）
```

### Python 辅助库层
```
skills/loop_engine.py               — Loop 引擎主入口
skills/_lib/actions.py              — 7 个核心操作
skills/_lib/agents.py               — 多智能体协调
skills/_lib/config.py               — 配置解析
skills/_lib/defaults.py             — 默认配置
skills/_lib/dependency_scheduler.py — 依赖调度
skills/_lib/design_phase.py         — 设计阶段
skills/_lib/detectors.py            — 项目状态检测
skills/_lib/event_context.py        — 事件上下文
skills/_lib/event_log.py            — 事件日志
skills/_lib/event_types.py          — 事件类型定义
skills/_lib/flow_customizer.py      — 流程定制
skills/_lib/flowchart.py            — 流程图生成
skills/_lib/gate.py                 — 门控机制
skills/_lib/human_nodes.py          — 人工介入节点
skills/_lib/interaction_modes.py    — 交互模式
skills/_lib/lock.py                 — 文件锁
skills/_lib/loop_state.py           — 循环状态
skills/_lib/memory.py               — 记忆系统
skills/_lib/sanitizer.py            — 输入清洗
skills/_lib/session.py              — 会话协调
skills/_lib/session_manager.py      — 会话管理
skills/_lib/state_vector.py         — 状态向量
skills/_lib/step_pipeline.py        — 步骤管道
skills/_lib/sync_state.py           — 状态同步
skills/_lib/tribunal.py             — 委员会裁决
skills/_lib/trigger_engine.py       — 触发引擎
```

---

## 常见问题

### Q: 如何为项目添加新的子技能？
新增 `.md` 文件到 `skills/` 目录，然后在 `package.json` 的 `skills` 数组中注册。如果新技能需要被状态机调用，更新对应的 `guide-*.md` 文件添加引用。

### Q: 如何处理 v1.x 到 v2.0 的迁移？
v2.0 使用三阶段架构 arch → plan → ship。原来的 `guide-spec` 已被 `guide-arch` + `guide-plan` 替代（`guide-spec` 是 60 行别名，v2.0 已删除）。详细迁移指南见 `docs/migration/v1-to-v2.md`。

### Q: 测试策略是什么？
- **Python 测试**（pytest）：覆盖状态向量、事件日志、门控机制、Loop 引擎
- **Bash 测试**（bats）：覆盖安装、worktree、归档、合并验证等
- **CI**（GitHub Actions）：push/PR 时自动运行全部测试

---

> 📍 知识图谱位于 `.understand-anything/knowledge-graph.json`（107KB，130 节点 / 110 边 / 6 层）