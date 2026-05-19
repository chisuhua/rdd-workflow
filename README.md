# Spec Workflow

OpenSpec 工作流技能包 - manage changes via propose → plan → execute → status → archive lifecycle.

## 安装

### 通过 npx skills（推荐）

```bash
npx skills add sisyphus/spec-workflow -g -y
```

### 手动安装

```bash
git clone https://github.com/sisyphus/spec-workflow.git ~/.agents/skills/spec-workflow
```

## 使用流程

1. **安装到项目**：执行 `skill_use("INSTALL")` 将技能复制到项目目录
2. **使用子技能**：
   - `skill_use("guide")` - 交互式向导
   - `skill_use("propose")` - 生成提案
   - `skill_use("plan")` - 创建实施计划
   - `skill_use("execute")` - 执行实施
   - `skill_use("status")` - 查看状态

## 目录结构

```
spec-workflow/
├── package.json
├── README.md
├── install.sh           # 手动安装脚本
└── skills/
    ├── INSTALL.md       # 安装程序（第一入口）
    ├── guide.md         # 交互式向导
    ├── propose.md       # 提案生成
    ├── plan.md          # 实施计划
    ├── execute.md       # 执行实施
    └── status.md        # 状态查看
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