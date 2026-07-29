# Prompt worktree cleanup before stage commands — 技术设计

## 设计目标

在 `guide` 入口中，用户选择阶段命令（`guide-arch` / `guide-plan` / `guide-ship`）后、AI 执行 `skill_use()` 前，增加一步工作树清理检查。当 `WT_ISSUES_JSON` 非空且包含非 `info` 级别问题时，提示用户先清理再继续，避免脏工作树导致后续流程异常。

## 现状分析

当前 `guide` 流程：

```
用户选择 stage 命令 → AI 直接 skill_use("guide-arch/plan/ship")
```

`guide/SKILL.md` 第 69-87 行已有"工作树清理分析"提示，但该提示在**展示菜单前**执行，且仅要求 AI "分析并展示建议"——用户选择阶段命令后不被拦截。

## 实现方案

### 方案 A（首选）：在 `guide/SKILL.md` 中增加阶段命令执行前门控

在 `guide/SKILL.md` 的"交互菜单"阶段后、AI 执行 `skill_use()` 前，增加硬性检查步骤：

```
用户选择阶段命令 → AI 检查 WT_ISSUES_JSON → 有问题？→ 提示清理 → 用户选择
                                                   ↓ 无问题     ↓ 跳过
                                             直接 skill_use() ←——┘
```

**修改 `skills/guide/SKILL.md`**：
- 在"交互菜单"步骤后新增"阶段命令门控"步骤
- 该步骤描述：当用户选择 `guide-arch` / `guide-plan` / `guide-ship` 时，检查 `WT_ISSUES_JSON`
- 如果非空且有非 `info` 级别问题，展示提示弹窗（2 选项）
- 如果用户选择"跳过"，正常执行 `skill_use()`
- 如果用户选择"清理"，引导用户进入清理流程（`🧹 清理 (N issues)` 菜单项）

### 方案 B（备选）：在 `workflow_synthesizer.py` 中修改 `all_options` 增加门控

将阶段命令的 `action` 改为 `"check_worktree_before:<stage_name>"`，AI 在解析时先检查再执行。但此方案需要修改 Python 代码，且 `action` 字段的语义从 `skill_use` 参数变为复合命令，增加复杂度。

### 选择：方案 A

方案 A 更合适，因为：
1. 不修改 Python 代码——`workflow_synthesizer.py` 保持只读契约
2. 不修改 bash 脚本——`guide_entry.sh` 和 `scan-state.sh` 不受影响
3. 纯 AI 行为变更——`WT_ISSUES_JSON` 已经导出，AI 只需在正确时机使用
4. 易于回滚——只需修改 SKILL.md 的指令文本

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `skills/guide/SKILL.md` | 修改 | 在"交互菜单"步骤后新增"阶段命令门控"步骤，约 30 行 |

## 技术约束

- MUST 不阻塞流程——用户应能选择跳过
- MUST 不自动执行任何清理命令（AI 仍不自动执行）
- MUST 仅检查 `WT_ISSUES_JSON`，不读取文件系统
- MUST 与现有 `🧹 清理 (N issues)` 选项的实现一致
- MUST 不影响 `WT_ISSUES_JSON` 为空时的正常流程
- MUST 对 `guide-arch` / `guide-plan` / `guide-ship` 三个阶段命令均生效

## 关键场景

| 场景 | `WT_ISSUES_JSON` | 用户选择 | 期望行为 |
|------|------------------|----------|----------|
| 1 | 有 13 个 issues | `guide-ship` | 弹窗提示清理，用户选择"跳过"后进入 |
| 2 | 有 13 个 issues | `guide-ship` | 弹窗提示清理，用户选择"清理"后进入清理流程 |
| 3 | `[]` | `guide-ship` | 无弹窗，直接进入 |
| 4 | 有 13 个 issues | `guide-plan` | 同场景 1，对所有阶段命令生效 |
| 5 | 有 13 个 issues | `guide-arch` | 同场景 1，对所有阶段命令生效 |