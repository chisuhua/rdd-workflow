# RDD Workflow

> ⚠️ **v2.1+: 工作流从三阶段扩展为四阶段 (arch → design → plan → ship)**
>
> 提案管理（创建、审查、批准/拒绝/延迟）已从 `guide-arch` Phase 5.5 迁移到独立的 `guide-design` 阶段。
> 存量项目请先运行 `skill_use("guide-design")` 审查提案，或设置 `SKIP_ARCH_HANDOFF=yes` 临时跳过两个门控。

[![npm version](https://img.shields.io/npm/v/rdd-workflow.svg)](https://www.npmjs.com/package/rdd-workflow)

## Install

```bash
# Latest stable (v1.x)
npm install rdd-workflow

# v2.0 beta
npm install rdd-workflow@2.0.0-beta
```

OpenSpec 工作流技能包 - manage changes via propose → plan → execute → status → archive lifecycle.

## 安装

### 全局安装（跨项目可用，推荐）

```bash
git clone https://github.com/chisuhua/rdd-workflow.git ~/.agents/skills/rdd-workflow
bash ~/.agents/skills/rdd-workflow/install.sh --global
```

安装后：
- **12 个子技能** symlink 到 `~/.agents/skills/` → OpenCode 在任何项目下自动发现
- **Python 依赖** 自动安装（`pip install --user -r requirements.txt`）
- **`_lib` Python 路径** 写入 `.pth` 文件 → 任何项目 `from skills._lib.xxx import yyy`
- **`rddf` CLI** 创建到 `~/.local/bin/rddf` → 终端直接 `rddf status`

> 全局安装后**不需要**在每个项目执行 `skill_use("INSTALL")`。技能即时生效。

### 项目安装（单项目隔离）

#### 通过 npx skills

```bash
npx skills add chisuhua/rdd-workflow -g -y
```

安装后只显示 `INSTALL` 技能。执行 `INSTALL` 后，子技能才会出现在项目中。

#### 手动安装

```bash
git clone https://github.com/chisuhua/rdd-workflow.git
bash install.sh /path/to/project
```

## 使用流程

1. **安装到项目**：执行 `skill_use("INSTALL")` 将技能复制到项目目录
2. **使用子技能**：
   - `skill_use("guide")` - 推荐器入口(扫描状态,建议调 arch、plan 或 ship)
   - `skill_use("guide-arch")` - Arch 端状态机(setup → roadmap → arch-done)
   - `skill_use("guide-plan")` - Plan 端状态机(scan → propose → deps → plan-done)
   - `skill_use("guide-ship")` - Ship 端状态机(plan → execute → archive → cleanup)
   - `skill_use("feature")` - feature 管理(summary/graph/status/order)
   - `skill_use("propose")` - 子技能(被 guide-plan 调用)
   - `skill_use("execute")` - 子技能(被 guide-ship 调用)
   - `skill_use("status")` - 子技能(被 guide-ship 调用或独立使用)
   - `skill_use("rdd-workflow-writing-plans")` - 实施计划生成器(被 guide-ship 调用,v2.0 自包含 TDD 5 步结构)

## v2.1 新特性

### 四阶段架构 (arch → design → plan → ship)

| 阶段 | 技能 | 职责 | 人工介入 |
|------|------|------|---------|
| **Arch** | `guide-arch` | 架构定义（ADR、roadmap、差距分析） | 高 |
| **Design** | `guide-design` | 设计管理 + 内容审查（提案创建、审查、批准/拒绝/延迟；approve 即落盘 + 两层内容审查） | 中 |
| **Plan** | `guide-plan` | 变更生成（scan、propose、deps） | 中 |
| **Ship** | `guide-ship` | 变更执行（worktree、execute、archive） | 低 |

> **v2.1+ 变更**: 从三阶段扩展为四阶段架构。提案管理（创建、审查、批准/拒绝/延迟）从 `guide-arch` Phase 5.5 迁移到独立的 `guide-design` 阶段。
> `guide-spec` 别名已在 v2.0 移除。请直接使用 `guide-arch` → `guide-design` → `guide-plan` → `guide-ship`。

### 推荐器升级

`guide` 推荐器现在支持四阶段扫描：

```
💡 Recommended: skill_use("guide-plan")
   Reason: 架构定义已完成 → 进入变更生成
```

### Feature 管理

- `skill_use("feature")` - 查看和管理 feature groups（summary、dependency graph、per-feature status、execution order）

### 测试基础设施

- **57 个 Python 单元测试**：覆盖状态向量、事件日志、门控机制、Loop 引擎等
- **10 个 Python 集成测试**：覆盖 Loop 流程、门控切换、阶段切换
- **测试框架**：pytest (Python) + bats (shell)

## 目录结构

```
rdd-workflow/
├── package.json
├── README.md
├── USAGE.md
├── install.sh           # 手动安装脚本
└── skills/
    ├── INSTALL.md             # 安装程序（第一入口）
    ├── guide/SKILL.md         # 推荐器入口
    ├── guide-arch/SKILL.md    # Arch 阶段状态机(v2.0+)
    ├── guide-plan/SKILL.md    # Plan 阶段状态机(v2.0+)
    ├── guide-ship/SKILL.md    # Ship 端状态机
    ├── feature/SKILL.md       # feature 管理 (v2.0+)
    ├── rddf-session/SKILL.md  # 跨 OpenCode session 恢复 (ADR-0017)
    ├── propose/SKILL.md       # 子技能(被 guide-plan 调用)
    ├── execute/SKILL.md       # 子技能(被 guide-ship 调用)
    ├── roadmap/SKILL.md       # 子技能(被 guide-arch 调用)
    ├── deps/SKILL.md          # 子技能(被 guide-plan 调用)
    ├── status/SKILL.md        # 子技能(被 guide-ship 调用或独立使用)
    ├── rdd-workflow-writing-plans/SKILL.md  # 实施计划生成器(v2.0 自包含)
    ├── loop_engine.py         # v2.0 Loop 引擎(向后兼容 shim)
    ├── <skill>/scripts/       # per-skill 辅助脚本
    └── _lib/                  # 共享辅助函数库(46 .py + 8 schema)
```

## 工作原理

### 全局安装模式（`--global`）

1. 每个子技能 symlink 到 `~/.agents/skills/<name>/` 
2. OpenCode 自动发现所有子技能（无需 `INSTALL` 步骤）
3. 技能代码即时同步源码变更
4. `_lib/` Python 模块通过 `.pth` 文件全局可导入
5. `rddf` CLI 通过 `~/.local/bin/rddf` 在任何目录可用

### 项目安装模式（`skill_use("INSTALL")`）

1. 全局安装后，只显示 `INSTALL` 技能
2. 执行 `INSTALL` 将子技能复制到项目的 `.opencode/skills/rdd-workflow/`
3. 子技能通过 `PROJECT_ROOT=$(git rev-parse --show-toplevel)` 自动检测项目根目录

## 其他 AI 助手安装

其他 AI 编程助手可以使用：

```bash
# 全局安装（所有项目可用，推荐）
bash ~/.agents/skills/rdd-workflow/install.sh --global

# 项目安装
bash ~/.agents/skills/rdd-workflow/install.sh /path/to/project

# 或直接复制
cp -r ~/.agents/skills/rdd-workflow/skills /path/to/project/.opencode/skills/rdd-workflow/
```

## 前置条件

### 必需

- `openspec` CLI v1.3.1+
- `git` 2.25+
- `cmake` 3.16+
- **bats-core 1.10+** (测试基础设施,可选用 `bats tests/`)

### 实施计划生成器(v2.0 自包含)

v2.0 重构后,实施计划生成器**完全自包含**于 rdd-workflow,**无任何外部 skill 依赖**:

- ✅ `rdd-workflow-writing-plans` — 内置 TDD 5 步结构 plan 生成器(fork 自 superpowers/writing-plans,适配 OpenSpec change 上下文)
- ✅ `execute` — 内置 plan 执行器,强制 TDD 5 步纪律(整合原 rdd-workflow/executing-plans)

**调用流程**(`guide-ship` Phase 1):

```bash
cd "$WT_PATH"
skill_use("rdd-workflow-writing-plans")  # 直接调用内置 skill
# 生成 .rddf/plans/<CHANGE_NAME>.md
# 含 TDD 5 步结构: Write failing test → Verify fail → Implement → Verify pass → Commit
```

**架构简化**:
- **删除**: `prometheus-planning.md` (481 行间接层 + 检测链 + 路径桥接 + 混合 TDD)
    *(README 仅作为变更说明保留提及,代码本身已删除)*
- **替换**: `rdd-workflow-writing-plans.md` (~250 行,自包含)
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
