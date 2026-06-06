# Spec Workflow

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

## 目录结构

```
spec-workflow/
├── package.json
├── README.md
├── USAGE.md
├── install.sh           # 手动安装脚本
└── skills/
    ├── INSTALL.md       # 安装程序（第一入口）
    ├── guide.md         # 推荐器入口
    ├── guide-spec.md    # Spec 端状态机
    ├── guide-ship.md    # Ship 端状态机
    ├── propose.md       # 子技能(被 guide-spec 调用)
    ├── execute.md       # 子技能(被 guide-ship 调用)
    ├── roadmap.md       # 子技能(被 guide-spec 调用)
    ├── deps.md          # 子技能(被 guide-spec 调用)
    └── status.md        # 子技能(被 guide-ship 调用)
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

- `openspec` CLI v1.3.1+
- `git` 2.25+
- `cmake` 3.16+
- **`prometheus-start-work` skill** (必需,ship 端唯一实施计划生成器)
  - 安装: `npx skills add chisuhua/prometheus-start-work -g -y`
- **bats-core 1.10+** (测试基础设施,可选用 `bats tests/`)

## Skill 版本语义

所有 skill 文件的前置元数据使用：
- `version: X.Y` (X = 主版本, Y = 次版本, semver 风格)
- `evolved-from: "..."` (历史来源,用于重构追溯)

历史版本(2026-06-04 之前)使用 `generatedBy: X.Y`,现已重命名为 `evolved-from`。
