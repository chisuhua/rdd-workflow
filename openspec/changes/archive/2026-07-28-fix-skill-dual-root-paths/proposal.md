# fix-skill-dual-root-paths

**优先级**: P1 | **阶段**: v2.1 | **分类**: infrastructure
**类型**: fix

## Why

rdd-workflow skills (guide-arch, guide-plan, guide-ship, propose, deps, execute, status, feature, roadmap) 通过 `install.sh --global` 全局安装为 `~/.agents/skills/<name>` symlink。但所有 SKILL.md 和 shell scripts 使用 `$PROJECT_ROOT/skills/<name>/scripts/...` 路径引用脚本文件。当用户在其他项目（如 PTX-EMU）调用这些 skill 时：

- `PROJECT_ROOT` = 用户项目根目录（如 `/workspace/project/PTX-EMU`）
- `$PROJECT_ROOT/skills/guide-plan/scripts/plan_intake.sh` → 不存在
- `$PROJECT_ROOT/skills/_lib/state.sh` → 不存在

**结果**: 全局安装的 skill 只能在 rdd-workflow 项目自身内正常工作，在其他项目完全无法使用。这违背了全局安装的设计意图。

**事件**: 2026-07-28 PTX-EMU session 中 `/guide-plan` auto-slash-command 触发后，错误地展示了 rdd-workflow 项目的 changes 而非 PTX-EMU 的 changes，暴露出路径解析的根本缺陷。

## What Changes

引入 **Dual-Root 路径解析** 架构，将 skill 自身安装路径（`SKILL_DIR`）与项目数据路径（`PROJECT_ROOT`）分离：

1. **新增** `skills/_lib/skill_root.sh` — bootstrap 脚本，提供 `resolve_rdd_skill_dir()` 和 `resolve_rdd_lib_dir()` 函数
2. **修改** `install.sh` — 全局安装时增加 `_lib` symlink（`_lib` 是共享库，当前缺失）
3. **修改** 8 个 SKILL.md — 所有 bash 代码块中的 `$PROJECT_ROOT/skills/<name>/scripts/` 改为 resolved 路径
4. **修改** 5 个 shell scripts — 内部 `_lib` 和跨 skill 引用改为 resolved 路径

**BREAKING**: 无。项目安装模式（copy 到 `.opencode/skills/`）不受影响，resolution order 优先匹配项目本地路径。

## Capabilities

### New Capabilities
- `skill-path-resolution`: SKILL_DIR 解析机制 — 支持项目安装和全局安装两种模式，按优先级自动选择

### Modified Capabilities
- `three-phase-skills`: guide-arch/guide-plan/guide-ship 的脚本引用路径从 PROJECT_ROOT 相对改为 SKILL_DIR 相对
- `gate-mechanism`: `gate.py` 及相关 shell 脚本的 `_lib` 引用路径更新

## Impact

| 层面 | 影响 |
|------|------|
| **SKILL.md** | 8 个文件，39 处 `source` 语句 |
| **Shell scripts** | 5 个文件，5 处 `$PROJECT_ROOT/skills/` 引用 |
| **install.sh** | 全局安装新增 `_lib` symlink |
| **Python imports** | 不受影响（已通过 `.pth` 文件全局可导入） |
| **向后兼容** | 项目安装模式完全兼容（resolution order 优先项目本地） |

## Risks

- **R1**: `_lib` symlink 可能与其他项目的 `_lib` 冲突 — 缓解：resolution order 优先 `$PROJECT_ROOT/.opencode/skills/_lib`
- **R2**: SKILL.md 代码块被 AI 执行时 `$HOME/.agents/skills/_lib/skill_root.sh` 不存在（旧安装） — 缓解：resolution 函数内置 fallback 链，且 install.sh 更新后一次性解决
- **R3**: 某些 SKILL.md 代码块中 `$PROJECT_ROOT` 在 source 前未设置 — 缓解：`resolve_rdd_skill_dir()` 内部检查 `PROJECT_ROOT` 是否为空，安全处理

## 架构依据

- **ADR-0003 三阶段架构**: arch → plan → ship 三阶段 skill 的设计基础，本修复不改变阶段语义，仅修复路径解析
- **ADR-0017 rddf-session**: 跨 session 恢复依赖 skill 脚本的正确加载，路径解析是其前置条件
- **README 全局安装承诺**: "全局安装后 OpenCode 在任何项目下自动发现 rdd-workflow 技能" — 当前实现与此承诺不符，本修复使其兑现
