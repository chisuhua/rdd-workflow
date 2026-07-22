# ADR-0023: v3.0.0 包名重命名 `spec-workflow` → `rdd-workflow`

> **状态**: 已采纳
> **日期**: 2026-07-22
> **决策者**: sisyphus

## Context

### 命名不一致

rdd-workflow 项目经过多次迭代后，内部使用的项目名与外部引用名严重不一致：

| 层级 | 当前名称 | 期望 |
|------|---------|------|
| GitHub repository | `chisuhua/rdd-workflow` | ✅ 已对齐 |
| npm package | `spec-workflow` | 需改为 `rdd-workflow` |
| Skill names | `spec-workflow/writing-plans` | 需改为 `rdd-workflow/writing-plans` |
| Install path | `~/.agents/skills/spec-workflow/` | 需改为 `~/.agents/skills/rdd-workflow/` |
| Project install path | `.opencode/skills/spec-workflow/` | 需改为 `.opencode/skills/rdd-workflow/` |
| Internal references | `spec-workflow` across docs, code, ADRs | 需改为 `rdd-workflow` |

### 命名冲突风险

选择 `rdd-workflow` 与现有命名存在格式差异：

| Content | Token | 说明 |
|---------|-------|------|
| CLI 命令 | `rddf` | `rdd` + `f` (flow?) |
| 目录前缀 | `.rddf/` | 与 CLI 同根 |
| Python 模块 | `rddf_session` | `rddf` + `_session` |
| 子技能 | `rdd-session` | `rdd` + `-session` (dash 分隔) |
| **新包名** | `rdd-workflow` | `rdd` + `-workflow` (dash 分隔) |

`rdd-workflow` 与 `rddf` / `rdd-session` / `rddf_session` 共享 `rdd` 前缀但格式不同，存在认知混淆风险。用户已接受此风险。

## Decision

1. **包名统一为 `rdd-workflow`**（用户选择，放弃 `rddf-workflow` 更一致的替代方案）。
2. **完全 breaking change**，不保留兼容性 shim：
   - Skill name: `spec-workflow/writing-plans` → `rdd-workflow/writing-plans`
   - Install path: `~/.agents/skills/spec-workflow/` → `~/.agents/skills/rdd-workflow/`
   - Project install: `.opencode/skills/spec-workflow/` → `.opencode/skills/rdd-workflow/`
   - npm package: `spec-workflow` → `rdd-workflow`
3. **版本号 bump 到 v3.0.0 (major)**，因为 skill name change 是公开 API 的 breaking change。
4. **不改 git repository URL**（已经是 `chisuhua/rdd-workflow`）。
5. **不改 CLI 命令名**（仍然是 `rddf`，与包名 `rdd-workflow` 不同）。

## Consequences

### 正面影响

- ✅ GitHub 仓库名与包名完全一致（`chisuhua/rdd-workflow`）
- ✅ 减少用户认知负担（不再需要在两种名字间切换）
- ✅ 内部引用、文档、代码风格统一

### 负面影响

- ❌ **完全 breaking**：所有现有安装失效，需要重装
- ❌ **命名不完美**：`rdd-workflow` 与 `rddf` CLI / `rdd-session` / `.rddf/` 有格式冲突
- ❌ **ADRs, specs, archive 等历史文档被批量 rename**（2026-07-22 runtime 执行）

### 迁移路径

用户需要：
1. 删除旧安装：`rm -rf ~/.agents/skills/spec-workflow .opencode/skills/spec-workflow`
2. 重装：`git clone https://github.com/chisuhua/rdd-workflow.git ~/.agents/skills/rdd-workflow && bash ~/.agents/skills/rdd-workflow/install.sh --global`
3. 更新脚本调用：`skill_use("spec-workflow/X")` → `skill_use("rdd-workflow/X")`
4. 数据无需迁移（`.rddf/state/` 不包含包名引用）

### 替代方案评估

| 方案 | 优点 | 缺点 | 是否采用 |
|------|------|------|---------|
| `rddf-workflow` | 与 CLI `rddf` / 目录 `.rddf/` 完全一致 | 比 `rdd-workflow` 多一个字符 | ❌ 用户选择 |
| 保留 `spec-workflow` | 零迁移成本 | 与 GitHub 名称不一致，持续混淆 | ❌ GitHub 已被重命名 |
| `rdd-flow` | 短名 | 不直观，没有表达 workflow 含义 | ❌ 太随意 |

## 实施记录

- **执行时间**：2026-07-22
- **执行者**：AI agent Sisyphus + human user
- **变更范围**：全部非 gitignored 的 source files（code, docs, ADRs, specs, archive, tests）
- **验证**：952 unit tests + bats smoke + full grep scan