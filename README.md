# Spec Workflow

[![npm version](https://img.shields.io/npm/v/spec-workflow.svg)](https://www.npmjs.com/package/spec-workflow)

## Install

```bash
# Latest stable (v1.x)
npm install spec-workflow

# v2.0 beta
npm install spec-workflow@2.0.0-beta
```

OpenSpec 工作流技能包 - manage changes via propose → plan → execute → status → archive lifecycle.

## 安装

### 通过 npx skills（推荐）

```bash
npx skills add chisuhua/spec-workflow -g -y
```

安装后只显示 `INSTALL` 技能。执行 `INSTALL` 后，子技能才会出现在项目中。

### 手动安装

```bash
git clone https://github.com/chisuhua/spec-workflow.git ~/.agents/skills/spec-workflow
```

## 使用流程

1. **安装到项目**：执行 `skill_use("INSTALL")` 将技能复制到项目目录
2. **使用子技能**：
   - `skill_use("guide")` - 推荐器入口(扫描状态,建议调 arch、plan 或 ship)
   - `skill_use("guide-arch")` - Arch 端状态机(setup → roadmap → arch-done)
   - `skill_use("guide-plan")` - Plan 端状态机(scan → propose → deps → plan-done)
   - `skill_use("guide-ship")` - Ship 端状态机(plan → execute → archive → cleanup)
   - `skill_use("propose")` - 子技能(被 guide-plan 调用)
   - `skill_use("execute")` - 子技能(被 guide-ship 调用)
   - `skill_use("status")` - 子技能(被 guide-ship 调用或独立使用)
   - `skill_use("spec-workflow/writing-plans")` - 实施计划生成器(被 guide-ship 调用,v2.0 自包含 TDD 5 步结构)

## v2.0 新特性

### 三阶段架构 (arch → plan → ship)

| 阶段 | 技能 | 职责 | 人工介入 |
|------|------|------|---------|
| **Arch** | `guide-arch` | 架构定义（ADR、roadmap、差距分析） | 高 |
| **Plan** | `guide-plan` | 变更生成（scan、propose、deps） | 中 |
| **Ship** | `guide-ship` | 变更执行（worktree、execute、archive） | 低 |

> **v2.0+ 变更**: `guide-spec` 别名已在 v2.0 移除（原为 60 行别名，自动调用 arch → plan）。请直接使用 `guide-arch` 和 `guide-plan`。

### 推荐器升级

`guide` 推荐器现在支持三阶段扫描：

```
💡 Recommended: skill_use("guide-plan")
   Reason: 架构定义已完成 → 进入变更生成
```

### 测试基础设施

- **18 个 Python 单元测试**：覆盖状态向量、事件日志、门控机制、Loop 引擎等
- **3 个 Python 集成测试**：覆盖 Loop 流程、门控切换、阶段切换
- **测试框架**：pytest (Python) + bats (shell)

## 目录结构

```
spec-workflow/
├── package.json
├── README.md
├── USAGE.md
├── install.sh           # 手动安装脚本
└── skills/
    ├── INSTALL.md             # 安装程序（第一入口）
    ├── guide.md               # 推荐器入口
    ├── guide-arch.md          # Arch 阶段状态机(v2.0+)
    ├── guide-plan.md          # Plan 阶段状态机(v2.0+)
    ├── guide-ship.md          # Ship 端状态机
    ├── propose.md             # 子技能(被 guide-plan 调用)
    ├── execute.md             # 子技能(被 guide-ship 调用)
    ├── roadmap.md             # 子技能(被 guide-arch 调用)
    ├── deps.md                # 子技能(被 guide-plan 调用)
    ├── status.md              # 子技能(被 guide-ship 调用或独立使用)
    ├── spec-workflow-writing-plans.md # 实施计划生成器(v2.0 自包含, fork 自 superpowers)
    ├── execute.md             # 实施计划执行(含 TDD 5 步纪律,v2.0 整合)
    ├── loop_engine.py         # v2.0 Loop 引擎(state vector + event log)
    └── _lib/                  # v2.0 共享辅助函数库(state.sh, worktree.sh, archive.sh, deps.sh)
```

## 工作原理

1. 全局安装后，只显示 `INSTALL` 技能
2. 执行 `INSTALL` 将子技能复制到项目的 `.opencode/skills/spec-workflow/`
3. 子技能通过 `PROJECT_ROOT=$(git rev-parse --show-toplevel)` 自动检测项目根目录

## 其他 AI 助手安装

其他 AI 编程助手可以使用：

```bash
# 方式 1: 使用 install.sh
bash ~/.agents/skills/spec-workflow/install.sh /path/to/project

# 方式 2: 直接复制
cp -r ~/.agents/skills/spec-workflow/skills /path/to/project/.opencode/skills/spec-workflow/
```

## 前置条件

### 必需

- `openspec` CLI v1.3.1+
- `git` 2.25+
- `cmake` 3.16+
- **bats-core 1.10+** (测试基础设施,可选用 `bats tests/`)

### 实施计划生成器(v2.0 自包含)

v2.0 重构后,实施计划生成器**完全自包含**于 spec-workflow,**无任何外部 skill 依赖**:

- ✅ `spec-workflow/writing-plans` — 内置 TDD 5 步结构 plan 生成器(fork 自 superpowers/writing-plans,适配 OpenSpec change 上下文)
- ✅ `execute` — 内置 plan 执行器,强制 TDD 5 步纪律(整合原 spec-workflow/executing-plans)

**调用流程**(`guide-ship` Phase 1):

```bash
cd "$WT_PATH"
skill_use("spec-workflow/writing-plans")  # 直接调用内置 skill
# 生成 .rddf/plans/<CHANGE_NAME>.md
# 含 TDD 5 步结构: Write failing test → Verify fail → Implement → Verify pass → Commit
```

**架构简化**:
- **删除**: `prometheus-planning.md` (481 行间接层 + 检测链 + 路径桥接 + 混合 TDD)
    *(README 仅作为变更说明保留提及,代码本身已删除)*
- **替换**: `spec-workflow/writing-plans.md` (~250 行,自包含)
- **零外部依赖**: 不需要 oh-my-opencode、不需要 superpowers 套件
    *(同上,变更说明保留提及)*
- **零路径桥接**: 单一路径 `.rddf/plans/<name>.md`(执行契约)
- **零运行时检测**: 任何 AI 编程助手(opencode / Claude Code / Cursor / Aider 等)都能用

**跳过后备** (不推荐,仅紧急时使用):
```bash
export SKIP_PROMETHEUS_PLANNING=yes  # 跳过计划生成,execute.md 阶段将无详细计划
```

**架构变更说明** (v1.0 → v2.0):
- **v1.1 (已废弃)**: 解决了 P0-6 缺陷:`prometheus-start-work` 不再是隐式黑盒依赖
- **v1.2 (已废弃)**: skills 隔离 + 路径独占 + 混合 TDD
- **v1.3 (已废弃)**: standalone 模式 + 跨 7 个 AI 工具路径探测
- **v2.0 (当前)**: 完全自包含 — 删除所有间接层,直接调用内置 skill

## Skill 版本语义

所有 skill 文件的前置元数据使用：
- `version: X.Y` (X = 主版本, Y = 次版本, semver 风格)
- `evolved-from: "..."` (历史来源,用于重构追溯)

历史版本(2026-06-04 之前)使用 `generatedBy: X.Y`,现已重命名为 `evolved-from`。
