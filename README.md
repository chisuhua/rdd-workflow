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
   - `skill_use("guide")` - 推荐器入口(扫描状态,建议调 spec 或 ship)
   - `skill_use("guide-spec")` - Spec 端状态机(setup → roadmap → propose → deps)
   - `skill_use("guide-ship")` - Ship 端状态机(plan → execute → archive → cleanup)
   - `skill_use("propose")` - 子技能(被 guide-spec 调用)
   - `skill_use("execute")` - 子技能(被 guide-ship 调用)
   - `skill_use("status")` - 子技能(被 guide-ship 调用或独立使用)
   - `skill_use("prometheus-planning")` - 实施计划生成器(被 guide-ship 调用,带三级回退链)

## v2.0 新特性

### 三阶段架构 (arch → plan → ship)

| 阶段 | 技能 | 职责 | 人工介入 |
|------|------|------|---------|
| **Arch** | `guide-arch` | 架构定义（ADR、roadmap、差距分析） | 高 |
| **Plan** | `guide-plan` | 变更生成（scan、propose、deps） | 中 |
| **Ship** | `guide-ship` | 变更执行（worktree、execute、archive） | 低 |

> **向后兼容**: `guide-spec` 保留为别名，自动调用 arch → plan。现有工作流完全不受影响。

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
    ├── guide-spec.md          # Spec 端状态机
    ├── guide-ship.md          # Ship 端状态机
    ├── propose.md             # 子技能(被 guide-spec 调用)
    ├── execute.md             # 子技能(被 guide-ship 调用)
    ├── roadmap.md             # 子技能(被 guide-spec 调用)
    ├── deps.md                # 子技能(被 guide-spec 调用)
    ├── status.md              # 子技能(被 guide-ship 调用或独立使用)
    └── prometheus-planning.md # 实施计划生成器(v1.1+,取代 prometheus-start-work)
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

### 实施计划生成器(`prometheus-planning` 的三级回退链)

`guide-ship` Phase 1 通过 `prometheus-planning` 技能生成 `.sisyphus/plans/<name>.md`。
`prometheus-planning` 按以下优先级自动选择可用源,**无需用户介入**:

| 优先级 | 来源 | 用途 | 安装 |
|---|---|---|---|
| 1️⃣ (推荐) | `oh-my-opencode` 内置 Prometheus (plan) 子代理 | 通过 `task(subagent_type="plan", ...)` 直接调用,零依赖,prompt 透明可审计 | `npm install -g oh-my-opencode` |
| 2️⃣ (回退) | `superpowers/writing-plans` 技能 | opencode 内置 superpowers 套件成员,plan 阶段专业技能 | 检查 `~/.config/opencode/opencode.json` 是否含 superpowers 插件 |
| 3️⃣ (最后回退,已弃用) | `prometheus-start-work` (外部 GitHub 技能) | 兼容 v1.0 用户,标记为 deprecated | `npx skills add chisuhua/prometheus-start-work -g -y` |
| ❌ | 全部不可用 | 报错并退出,提示安装 1️⃣ 或 2️⃣ | — |

**跳过后备** (不推荐,仅紧急时使用):
```bash
export SKIP_PROMETHEUS_PLANNING=yes  # 跳过计划生成,execute.md 阶段将无详细计划
```

**架构变更说明** (v1.0 → v1.1):
- 解决了 P0-6 缺陷(`docs/audit/2026-06-05-workflow-audit.md:568`):`prometheus-start-work` 不再是隐式黑盒依赖
- 新技能 `skills/prometheus-planning.md` 自带检测 + 三级回退 + 契约验证
- 配置文件探测 + 试调双重验证,避免假阳性
- 失败时给出可执行的修复命令,不再"请确认已安装"

## Skill 版本语义

所有 skill 文件的前置元数据使用：
- `version: X.Y` (X = 主版本, Y = 次版本, semver 风格)
- `evolved-from: "..."` (历史来源,用于重构追溯)

历史版本(2026-06-04 之前)使用 `generatedBy: X.Y`,现已重命名为 `evolved-from`。
