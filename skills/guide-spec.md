---
name: guide-spec
description: Spec-side state machine for OpenSpec workflow — guides user from setup through roadmap, propose, deps, and emits "ready for guide-ship" handoff. Owns openspec/changes/<name>/ artifacts. Called by user when starting new changes.
license: MIT
compatibility: Requires openspec CLI v1.3.1+, git 2.25+
metadata:
  author: sisyphus
  version: "1.0"  # P0: Spec-side state machine, split from guide
  evolved-from: "split from guide.md v3.0"
  user-invocable: true
---

# OpenSpec 工作流 — Spec-Side Guide (v2.0 Alias)

> ⚠️ **v2.0 兼容模式**: `guide-spec` 现在是 `guide-arch` + `guide-plan` 的别名。
> 原有功能保持不变，只是将架构定义（arch）和变更生成（plan）分离为独立技能。
> 本技能将按顺序调用 `guide-arch` → `guide-plan`。
>
> **v3.0 弃用计划**: 此别名将在 v3.0 移除。建议新用户直接调用 `guide-arch` 或 `guide-plan`。

## 职责边界

本技能作为向后兼容别名，自身不实现任何状态机逻辑。它按两步完成 spec 端流程：

| 步骤 | 调用的技能 | 职责 |
|------|-----------|------|
| Step 1 | `guide-arch` | 架构定义：setup → adr-create → architecture → roadmap-define → arch-done |
| Step 2 | `guide-plan` | 变更生成：scan → propose → deps → plan-done |

**向后兼容保证**:
- `skill_use("guide-spec")` 行为与 v1.x 完全一致（只是内部实现改为两步调用）
- 所有已提交的 change 和进行中的 worktree 不受影响
- 状态文件（.rddf/state/）格式向后兼容

## Step 1: 架构定义 (Architecture Definition)

```bash
# 调用 guide-arch 技能
# guide-arch 会执行: setup → adr-create → architecture → roadmap-define → arch-done
skill_use("guide-arch")
```

## Step 2: 变更生成 (Change Generation)

```bash
# 在 arch-done 验证通过后，调用 guide-plan 技能
# guide-plan 会执行: scan → propose → deps → plan-done
skill_use("guide-plan")
```

## 退出

Spec 端完成。所有架构定义和变更生成工作由 `guide-arch` 和 `guide-plan` 分别完成。

```bash
echo "✅ Spec-side complete (via guide-arch → guide-plan alias). Changes are committed."
echo ""
echo "💡 Next: skill_use(\"guide-ship\")"
echo "   This will scan your committed changes and start worktree creation + execution."
```
