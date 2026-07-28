# fix-skill-dual-root-paths — Design

## Context

rdd-workflow 通过 `install.sh --global` 将 13 个子技能 symlink 到 `~/.agents/skills/`。OpenCode 在任何项目下自动发现这些技能。但所有 SKILL.md 中的 bash 代码块和 shell scripts 使用 `$PROJECT_ROOT/skills/<name>/scripts/...` 引用脚本文件，导致全局安装在其他项目下完全失效。

**当前状态**:
- `~/.agents/skills/guide-plan` → `/workspace/project/rdd-workflow/skills/guide-plan` (symlink)
- `~/.agents/skills/_lib` → **不存在**（install.sh 未 symlink `_lib`）
- Python imports (`from skills._lib`) 正常工作（`.pth` 文件指向 `skills/` 父目录）
- Bash scripts 全部失效（`$PROJECT_ROOT/skills/` 在其他项目不存在）

**约束**:
- 必须向后兼容项目安装模式（copy 到 `.opencode/skills/`）
- 不能修改 OpenCode 或 AI agent 的执行模型
- 不能修改 Python 导入机制（已工作）
- 不能改变 skill 的语义或行为，仅修复路径解析

## Goals / Non-Goals

**Goals**:
- 全局安装的 skill 在任何项目下正常工作
- 项目安装的 skill 不受影响
- `_lib` 共享库脚本可被所有 skill 正确引用
- 跨 skill 引用（如 guide-plan 调用 propose 的脚本）正确解析

**Non-Goals**:
- 不改变 skill 的功能或行为
- 不修改 OpenSpec CLI
- 不修改 Python 导入路径
- 不引入新的配置文件格式

## Decisions

### D1: 引入 SKILL_DIR 概念，与 PROJECT_ROOT 分离

**选择**: 每个 skill 通过 `resolve_rdd_skill_dir()` 函数解析自身安装路径，而非依赖 `$PROJECT_ROOT/skills/`。

**替代方案**:
- (a) 在 AI agent 层面设置环境变量 `RDD_SKILL_ROOT` — 不可行，AI 执行模型不保证 env var 设置
- (b) 修改 OpenCode 的 skill 加载机制注入路径 — 不可行，不修改 OpenCode
- (c) 每个 skill 的 SKILL.md 硬编码自身路径 — 不可维护，skill 名称变更需同步修改

**理由**: `resolve_rdd_skill_dir()` 函数在运行时解析，支持两种安装模式，无需 AI agent 或 OpenCode 配合。

### D2: Resolution Order — 项目本地优先

**选择**: 解析顺序为 `$PROJECT_ROOT/.opencode/skills/<name>` → `$HOME/.agents/skills/<name>` → `$RDD_WORKFLOW_SRC/skills/<name>`。

**替代方案**:
- (a) 全局优先 — 项目安装模式下会错误使用全局版本，违背项目隔离原则
- (b) 固定路径 — 无法支持两种安装模式

**理由**: 项目安装是显式行为，应优先于全局安装。这与 OpenCode 的 skill scope 优先级（project > user）一致。

### D3: `_lib` 也纳入 resolution 机制

**选择**: `_lib` 虽然不是 skill，但提供 `resolve_rdd_lib_dir()` 函数，与 skill 使用相同的 resolution order。

**替代方案**:
- (a) `_lib` 硬编码为 `$HOME/.agents/skills/_lib` — 项目安装模式下不存在
- (b) 每个 skill 内嵌 `_lib` 的 copy — 维护噩梦

**理由**: `_lib` 是共享基础设施，必须与 skill 使用相同的解析逻辑。

### D4: Bootstrap 脚本 `skill_root.sh` 作为唯一入口

**选择**: 所有 SKILL.md 代码块和 shell scripts 首先 `source "$HOME/.agents/skills/_lib/skill_root.sh"`，然后调用 resolution 函数。

**替代方案**:
- (a) 每个代码块内联 resolution 逻辑 — 重复代码，难以维护
- (b) 使用环境变量一次性设置 — AI 执行模型不保证跨代码块 env 持久

**理由**: 单一 bootstrap 文件，39 处 `source` 统一改为 `source "$HOME/.agents/skills/_lib/skill_root.sh"` 加函数调用。

### D5: install.sh 增加 `_lib` symlink

**选择**: `install_global_symlinks()` 中在子技能循环后，额外 symlink `_lib` 到 `~/.agents/skills/_lib`。

**替代方案**:
- (a) 不 symlink `_lib`，skill_root.sh 从 rdd-workflow 源码目录解析 — 如果用户删除源码目录，全局安装失效
- (b) 将 `_lib` copy 到全局目录而非 symlink — 无法即时同步源码变更

**理由**: symlink 保持与现有子技能相同的更新语义（源码变更即时生效）。

## 详细设计

### 路径解析架构

```
用户项目 (PTX-EMU)                    全局安装目录 (~/.agents/skills/)
├── openspec/                         ├── guide-plan/ → rdd-workflow/skills/guide-plan/
│   └── changes/                      │   ├── SKILL.md
│       └── ...                       │   └── scripts/
└── ...                               ├── _lib/ → rdd-workflow/skills/_lib/  [新增]
                                      │   ├── skill_root.sh                 [新增]
                                      │   ├── state.sh
                                      │   └── gate.py
                                      └── ...

SKILL_DIR 解析结果:
  项目安装模式: $PROJECT_ROOT/.opencode/skills/guide-plan
  全局安装模式: $HOME/.agents/skills/guide-plan
  开发模式:     $RDD_WORKFLOW_SRC/skills/guide-plan

PROJECT_ROOT: $git rev-parse --show-toplevel (不变，始终指向用户项目)
```

### skill_root.sh 接口

```bash
# resolve_rdd_skill_dir <skill-name>
#   输出: skill 安装目录的绝对路径
#   返回: 0 = 成功, 1 = 未找到
#
# resolve_rdd_lib_dir
#   输出: _lib 目录的绝对路径
#   返回: 0 = 成功, 1 = 未找到
```

### SKILL.md 代码块替换模式

**Before** (39 处):
```bash
source "$PROJECT_ROOT/skills/guide-plan/scripts/plan_intake.sh"
```

**After**:
```bash
source "$HOME/.agents/skills/_lib/skill_root.sh"
GUIDE_PLAN_DIR="$(resolve_rdd_skill_dir guide-plan)"
source "$GUIDE_PLAN_DIR/scripts/plan_intake.sh"
```

### 跨 skill 引用替换

**Before** (`plan_done_gate.sh`):
```bash
if [ -f "$PROJECT_ROOT/skills/propose/scripts/validate_baseline.py" ]; then
```

**After**:
```bash
source "$HOME/.agents/skills/_lib/skill_root.sh"
PROPOSE_DIR="$(resolve_rdd_skill_dir propose)"
if [ -f "$PROPOSE_DIR/scripts/validate_baseline.py" ]; then
```

### `_lib` 内部引用替换

**Before** (`plan_intake.sh` L114):
```bash
local STATE_SH="$PROJECT_ROOT/skills/_lib/state.sh"
```

**After**:
```bash
source "$HOME/.agents/skills/_lib/skill_root.sh"
local STATE_SH="$(resolve_rdd_lib_dir)/state.sh"
```

## Migration Plan

### Phase 1: 基础设施（新增文件 + install.sh）
1. 创建 `skills/_lib/skill_root.sh`
2. 修改 `install.sh` 增加 `_lib` symlink
3. 运行 `install.sh --global` 更新全局安装

### Phase 2: SKILL.md 更新（8 个文件）
按文件逐个修改，每个文件独立 commit：
4. `guide-plan/SKILL.md` — 10 处
5. `guide-ship/SKILL.md` — 21 处
6. `deps/SKILL.md` — 2 处
7. `execute/SKILL.md` — 1 处
8. `feature/SKILL.md` — 1 处
9. `propose/SKILL.md` — 2 处
10. `roadmap/SKILL.md` — 1 处
11. `status/SKILL.md` — 2 处

### Phase 3: Shell scripts 更新（5 个文件）
12. `guide-arch/scripts/arch_done_gate.sh` — 1 处 `_lib` 引用
13. `guide-arch/scripts/arch_env_check.sh` — 1 处 `_lib` 引用
14. `guide-arch/scripts/write_arch_handoff.sh` — 1 处 `_lib` 引用
15. `guide-plan/scripts/plan_done_gate.sh` — 2 处跨 skill 引用
16. `guide-plan/scripts/plan_intake.sh` — 1 处 `_lib` 引用

### Phase 4: 验证
17. rdd-workflow 项目内验证（项目安装模式）
18. PTX-EMU 项目验证（全局安装模式）

### 回退策略
- Phase 1 失败: 删除 `skill_root.sh`，恢复 `install.sh`
- Phase 2 失败: revert 对应 SKILL.md 的 commit
- Phase 3 失败: revert 对应 shell script 的 commit
- 每个 Phase 独立 commit，可独立 revert

## Risks / Trade-offs

| 风险 | 影响 | 缓解 |
|------|------|------|
| 旧安装缺少 `_lib` symlink | 全局安装在其他项目仍失效 | install.sh 更新后一次性解决；`resolve_rdd_lib_dir()` 有 fallback 到 `$RDD_WORKFLOW_SRC` |
| AI 执行代码块时 `$HOME` 未设置 | resolution 失败 | 检查 `$HOME` 为空时 fallback 到 `~` 展开 |
| 39 处替换遗漏 | 部分 skill 仍失效 | Phase 2 每个文件独立 commit，可用 grep 验证 `PROJECT_ROOT/skills/` 清零 |
| 项目安装模式 regression | 现有项目无法使用 | resolution order 优先项目本地，理论无影响；Phase 4 验证 |

## Open Questions

- **Q1**: 是否需要支持 Windows 路径？当前设计假设 Unix 路径分隔符。rdd-workflow 目前仅支持 Linux/macOS，暂不考虑。
- **Q2**: `RDD_WORKFLOW_SRC` 环境变量是否应该由 install.sh 自动设置？当前设计为可选 fallback，不强制要求。
