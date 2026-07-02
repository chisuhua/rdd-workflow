# spec-workflow v1.x → v2.0 迁移指南

> **版本**: 2.0.0  
> **日期**: 2026-06-22  
> **目标读者**: 现有 v1.x 用户  
> **预计迁移时间**: 30 分钟 - 2 小时（取决于项目复杂度）

---

## 🚀 Quick Start for v1.x Users

v1.x 用户升级到 v2.0 最快只需两步：

```bash
# 1. 更新到最新版本
npm update spec-workflow

# 2. 手动验证 v1.x 状态文件存在（可选；CLI `spec-workflow migrate` 规划中，v2.1 实现）
ls -la .rddf/state/ .openspec/ proposal-suggestions.md
```

**无需修改现有技能文件**。`guide-spec` 调用将自动变更为 `guide-arch` → `guide-plan`。所有现有 worktree 和变化不受影响。

### 变更要点一览

| v1.x | v2.0 | 备注 |
|------|------|------|
| `skill_use("guide-spec")` | → `guide-arch` → `guide-plan` (自动) | 无需更改代码 |
| `skill_use("guide-ship")` | 不变 | 保持不变 |
| 双阶段 spec/ship | 三阶段 arch/plan/ship | 职责更清晰 |

---

## 📋 目录

- [概述](#概述)
- [向后兼容承诺](#向后兼容承诺)
- [迁移路径](#迁移路径)
- [配置迁移](#配置迁移)
- [状态文件迁移](#状态文件迁移)
- [技能文件变更](#技能文件变更)
- [常见场景迁移示例](#常见场景迁移示例)
- [故障排查](#故障排查)
- [回滚策略](#回滚策略)

---

## 概述

spec-workflow v2.0 是一次**重大架构升级**，从状态机驱动升级到 Loop 驱动。但我们会确保**平滑迁移**：

### v1.x vs v2.0 对比

| 特性 | v1.x | v2.0 | 迁移影响 |
|------|------|------|---------|
| **架构** | 双阶段（spec/ship） | 三阶段（arch/plan/ship） | 🟡 中等 |
| **交互** | 固定菜单 | 三种模式（loop/menu/hybrid） | 🟢 低 |
| **状态管理** | 13 个分散文件 | 统一状态向量 + 事件流 | 🟡 中等 |
| **技能文件** | guide-spec, guide-ship | guide-arch, guide-plan, guide-ship | 🟡 中等 |
| **配置** | 无统一配置 | `.spec-workflow.json` + `loop.yaml` | 🟢 低 |

---

## 向后兼容承诺

### ✅ 完全兼容（无需修改）

| v1.x 接口 | v2.0 行为 | 弃用时间 |
|-----------|----------|---------|
| `skill_use("guide-spec")` | 自动路由到 `guide-arch` → `guide-plan` | v3.0 移除 |
| `skill_use("guide-ship")` | 保持不变 | 长期支持 |
| `skill_use("propose")` | 保持不变 | 长期支持 |
| `skill_use("execute")` | 保持不变 | 长期支持 |
| `skill_use("status")` | 保持不变 | 长期支持 |

### 🟡 兼容但变化

| v1.x 接口 | v2.0 行为 | 说明 |
|-----------|----------|------|
| `.rddf/state/roadmap-state.json` | 通过同步层自动更新 | v3.0 移除 |
| `proposal-suggestions.md` | 通过同步层自动更新 | v3.0 移除 |
| `.rddf/plans/*.md` | 保持不变 | 长期支持 |

### ❌ 不兼容（需要迁移）

| v1.x 接口 | v2.0 替代 | 迁移方式 |
|-----------|----------|---------|
| 手动管理 13 个状态文件 | 自动同步到状态向量 | 首次运行自动迁移 |
| 硬编码 phase 逻辑 | Loop 引擎 5 大构建块 | 无需迁移，自动生效 |

---

## 迁移路径

### 推荐迁移流程

```
v1.x 用户
    ↓
1. 安装 v2.0（向后兼容模式）
    ↓
2. 首次运行 guide-spec（自动迁移状态文件）
    ↓
3. 验证迁移结果（检查状态向量）
    ↓
4. 创建 .spec-workflow.json（可选）
    ↓
5. 尝试 loop 模式（推荐）
    ↓
6. 完全切换到 v2.0 工作流（可选）
```

### 迁移检查清单

- [ ] 备份现有项目（`git commit` 或 `git tag v1-backup`）
- [ ] 安装 spec-workflow v2.0
- [ ] 手动验证 v1.x 状态文件存在（`ls -la .rddf/state/ .openspec/ proposal-suggestions.md`；CLI `migrate --check` 规划中，v2.1 实现）
- [ ] 手动预览迁移范围（`git diff --stat v1-backup -- .rddf/state/ .openspec/ .rddf/`；CLI `migrate --dry-run` 规划中，v2.1 实现）
- [ ] 手动执行迁移（参见下方『手动迁移』章节；CLI `migrate --apply` 规划中，v2.1 实现）
- [ ] 验证状态向量（`cat .rddf/state/state-vector.json`；当前版本未使用此路径，状态存储于 Python 库层）
- [ ] 运行测试（`bats tests/`）
- [ ] 创建 `.spec-workflow.json`（可选）
- [ ] 尝试 loop 模式（可选）

---

## 💡 Conceptual Changes

### 从"双阶段"到"三阶段"

v1.x 的 spec 端将"架构定义"（ADR、roadmap）和"变更生成"（propose、deps）混合在一起。
v2.0 将它们拆分为独立阶段：

```
v1.x spec 端:          v2.0 三阶段:
setup                  guide-arch (架构定义)
  ↓                       ↓  arch-done gate
roadmap               guide-plan (变更生成)
  ↓                       ↓  plan-done gate
propose               guide-ship (变更执行，不变)
  ↓
deps
  ↓  spec-done
guide-ship
```

### 架构治理前置

v2.0 要求**先定义架构，再生成变更**。这意味着：
- 新项目必须先创建 ADR 和 roadmap（arch 阶段）
- 现有项目已有 roadmap 的可直接进入 plan 阶段
- `guide` 推荐器会自动检测当前阶段

### 向后兼容机制

`guide-spec.md` 保留为别名，内部调用 `guide-arch` → `guide-plan`。三个阶段之间的交接通过 `.rddf/state/arch-handoff.json` 和 `.rddf/state/plan-handoff.json` 实现。

---

## 配置迁移

### 选项 1: 不配置（使用默认值）

**适用场景**: 简单项目，不需要自定义

v2.0 会自动使用默认配置：
```json
{
  "version": "2.0",
  "interaction": {
    "mode": "hybrid"
  },
  "loop": {
    "max_iterations": 100,
    "max_retries": 3
  }
}
```

### 选项 2: 最小配置（推荐）

**适用场景**: 大多数项目

创建 `.spec-workflow.json`:
```json
{
  "version": "2.0",
  "interaction": {
    "mode": "hybrid",
    "human_in_loop_nodes": [
      "arch.adr_create",
      "ship.archive_confirm",
      "ship.execute_error"
    ]
  },
  "loop": {
    "max_iterations": 100,
    "max_retries": 3,
    "parallel_limit": 3
  },
  "verification": {
    "method": "human"
  }
}
```

### 选项 3: 完整配置（高级）

**适用场景**: 复杂项目，需要精细控制

```json
{
  "version": "2.0",
  "interaction": {
    "mode": "hybrid",
    "human_in_loop_nodes": [
      {
        "node": "arch.adr_create",
        "verification_mode": "human",
        "skip_if": "never"
      },
      {
        "node": "plan.change_select",
        "verification_mode": "script",
        "skip_if": "auto_select_changes",
        "script": ".spec-workflow/scripts/verification/check_changes.py"
      },
      {
        "node": "ship.archive_confirm",
        "verification_mode": "multi_model",
        "skip_if": "auto_archive",
        "executor_agent": "coder",
        "reviewer_agent": "reviewer",
        "review_criteria": [
          "all tests pass",
          "no merge conflicts"
        ]
      }
    ]
  },
  "loop": {
    "max_iterations": 100,
    "max_retries": 3,
    "parallel_limit": 3,
    "circuit_breaker": {
      "enabled": true,
      "consecutive_failures": 3,
      "action": "escalate_to_human"
    }
  },
  "verification": {
    "method": "multi_model",
    "executor_agent": "coder",
    "reviewer_agent": "reviewer",
    "weights": {
      "executor": 0.4,
      "reviewer": 0.6
    },
    "divergence_threshold": 0.4
  },
  "memory": {
    "enabled": true,
    "retention_days": 90,
    "auto_suggest_config": true
  }
}
```

### 选项 4: 便携规范（loop.yaml）

**适用场景**: 团队协作，需要版本控制

创建 `.spec-workflow/loops/complete-changes.yaml`:
```yaml
version: "2.0"
name: "complete-all-changes"
description: "自动完成所有待处理 changes"

goal:
  description: "complete all pending changes"
  success_criteria:
    - "active_changes.count == 0"
    - "worktrees.count == 0"
    - "roadmap.completion >= 0.8"

interaction:
  mode: "hybrid"

loop:
  max_iterations: 100
  max_retries: 3
  parallel_limit: 3

verification:
  method: "multi_model"
  executor_agent: "coder"
  reviewer_agent: "reviewer"

control:
  circuit_breaker:
    enabled: true
    consecutive_failures: 3
```

使用：
```bash
skill_use("loop", {
  "goal": "complete all pending changes",
  "config_file": ".spec-workflow/loops/complete-changes.yaml"
})
```

---

## 状态文件迁移

> **⚠️ 当前版本（v2.0）实现状态**
> - `.rddf/state/state-vector.json` 和 `.rddf/state/event-log.jsonl` **当前版本未使用此路径，状态存储于 Python 库层**（`skills/_lib/state_vector.py`、`skills/_lib/event_log.py`，内存中维护）
> - 本节中 `cat .rddf/state/state-vector.json`、`tail -f .rddf/state/event-log.jsonl` 等命令展示的是 v2.0 完整设计下的预期行为；当前请使用下方表格中映射的源文件（`.rddf/state/roadmap-state.json`、`proposal-suggestions.md`、`openspec/changes/*/ .openspec.yaml`、`.rddf/plans/*.md`）作为状态查询入口
> - 统一 CLI 工具 `spec-workflow migrate / sync / report` 规划中，v2.1 实现

### 自动迁移

首次运行 v2.0 时，会自动执行迁移：

```bash
$ skill_use("guide-spec")

🔄 检测到 v1.x 状态文件，开始迁移...
✅ 迁移 .rddf/state/roadmap-state.json → 状态向量（Python 库层）
✅ 迁移 proposal-suggestions.md → 状态向量（Python 库层）
✅ 迁移 openspec/changes/*/ .openspec.yaml → 状态向量（Python 库层）
✅ 迁移 .rddf/plans/*.md → 状态向量（Python 库层）
✅ 初始化事件流（内存中维护，event-log.py 写入时点：loop 启动/节点完成/门控切换）

迁移完成！状态向量已生成。
```

### 手动迁移

如果需要手动迁移（CLI `spec-workflow migrate --apply` 规划中，v2.1 实现）：

```bash
# 1. 备份 v1.x 状态文件
git tag v1-backup

# 2. 验证源文件完整（手动迁移的"就绪检查"）
ls -la .rddf/state/roadmap-state.json
ls -la proposal-suggestions.md
ls openspec/changes/
ls .rddf/plans/

# 3. 触发自动迁移（首次调用 guide-spec 时自动完成）
skill_use("guide-spec")
# → 输出参见上方『自动迁移』章节

# 4. 验证（参见下方『验证迁移结果』）
```

### 验证迁移结果

```bash
# 检查状态向量（当前版本未使用此路径，状态存储于 Python 库层；下方命令为 v2.0 完整设计演示）
cat .rddf/state/state-vector.json | jq '.version'  # 应该输出 "2.0"

# 检查事件流（同上）
wc -l .rddf/state/event-log.jsonl  # 应该有迁移事件

# 当前可用的状态查询入口（手动读取源文件）
cat .rddf/state/roadmap-state.json | jq '.'
cat proposal-suggestions.md
ls openspec/changes/ | wc -l
ls .rddf/plans/ | wc -l

# 检查向后兼容文件
ls -la .rddf/state/roadmap-state.json  # 应该仍然存在（同步层维护）
ls -la proposal-suggestions.md   # 应该仍然存在（同步层维护）
```

### 状态文件映射

| v1.x 文件 | v2.0 状态向量字段 | 同步层 |
|----------|------------------|--------|
| `.rddf/state/roadmap-state.json` | `arch_side.roadmap` | ✅ 双向同步 |
| `proposal-suggestions.md` | `plan_side.active_changes` | ✅ 双向同步 |
| `openspec/changes/*/ .openspec.yaml` | `plan_side.active_changes[].artifacts` | ✅ 单向读取 |
| `.rddf/plans/*.md` | `ship_side.worktrees[].plan` | ✅ 单向读取 |
| `git worktree list` | `ship_side.worktrees` | ✅ 实时扫描 |

---

## 技能文件变更

### 新增技能文件

| 文件 | 说明 | 必须 |
|------|------|------|
| `skills/guide-arch.md` | 架构定义阶段 | ✅ 是 |
| `skills/guide-plan.md` | 变更生成阶段（原 guide-spec） | ✅ 是 |
| `skills/loop_engine.py` | Loop 引擎入口 | ✅ 是 |
| `skills/_lib/state_vector.py` | 状态向量操作 | ✅ 是 |
| `skills/_lib/event_log.py` | 事件流操作 | ✅ 是 |
| `skills/_lib/session.py` | 轻量级会话协调器 | ✅ 是 |

### 保留技能文件

| 文件 | 说明 | 变更 |
|------|------|------|
| `skills/guide-ship.md` | 变更执行阶段 | 🟡 小调整 |
| `skills/propose.md` | 生成 proposal | ✅ 无变化 |
| `skills/execute.md` | 执行 work units | ✅ 无变化 |
| `skills/status.md` | 查看状态 | 🟡 增加状态向量查询 |
| `skills/roadmap.md` | roadmap 管理 | ✅ 无变化 |

### 弃用技能文件

| 文件 | 替代 | 弃用时间 |
|------|------|---------|
| `skills/guide-spec.md` | `guide-arch.md` + `guide-plan.md` | v3.0 移除 |

---

## 常见场景迁移示例

### 场景 1: 创建新 change

**v1.x 方式**（仍然有效）:
```bash
skill_use("guide-spec")
# 菜单选择: 1. 创建新 change
# 输入 change 名称
# 生成 proposal
```

**v2.0 方式**（推荐）:
```bash
# 方式 1: 传统菜单（向后兼容）
skill_use("guide-plan")

# 方式 2: Loop 模式
skill_use("loop", {
  "goal": "create new change for auth feature",
  "mode": "hybrid"
})
```

### 场景 2: 执行 change

**v1.x 方式**（仍然有效）:
```bash
skill_use("guide-ship")
# 菜单选择: 1. 执行 change
# 选择 change
# 创建 worktree
# 生成 Prometheus 计划
# 执行 work units
```

**v2.0 方式**（推荐）:
```bash
# 方式 1: 传统菜单（向后兼容）
skill_use("guide-ship")

# 方式 2: Loop 模式（自动完成所有 changes）
skill_use("loop", {
  "goal": "complete all pending changes",
  "mode": "hybrid"
})
```

### 场景 3: 查看状态

**v1.x 方式**（仍然有效）:
```bash
skill_use("status")
# 显示 roadmap 状态
# 显示 active changes
# 显示 worktrees
```

**v2.0 方式**（增强）:
```bash
# 方式 1: 传统方式（向后兼容）
skill_use("status")

# 方式 2: 查看状态向量（当前版本未使用此路径，状态存储于 Python 库层；下方命令为 v2.0 完整设计演示）
cat .rddf/state/state-vector.json | jq '.'

# 方式 3: 查看事件流（同上）
tail -f .rddf/state/event-log.jsonl | jq '.'

# 方式 4: 生成进度报告（CLI `spec-workflow report` 规划中，v2.1 实现）
# 当前手动生成报告：组合方式 1-3 的输出，或：
cat .rddf/state/roadmap-state.json proposal-suggestions.md  # 综合源文件
ls openspec/changes/ .rddf/plans/                  # 列出活跃工作
```

### 场景 4: 中断后恢复

**v1.x 方式**:
```bash
skill_use("guide-ship")
# 自动扫描 worktrees
# 从上次中断的 work unit 继续
```

**v2.0 方式**（增强）:
```bash
skill_use("loop", {
  "goal": "resume add-auth change",
  "mode": "hybrid"
})

# 系统行为:
# 1. 恢复 worktree 状态
# 2. 🆕 显示历史执行记录
# 3. 🆕 推荐配置（基于记忆系统）
# 4. 从断点继续执行
```

---

## 故障排查

### 问题 1: 迁移失败

**症状**: 手动迁移步骤报错（CLI `spec-workflow migrate --apply` 规划中，v2.1 实现）

**解决**:
```bash
# 1. 检查错误日志（如有）
cat .rddf/state/migration-error.log 2>/dev/null || echo "无错误日志文件（v2.0 当前不生成此文件）"

# 2. 检查 v1.x 状态文件完整性（手动就绪检查；CLI `migrate --check` 规划中，v2.1 实现）
ls -la .rddf/state/roadmap-state.json
ls -la proposal-suggestions.md
ls openspec/changes/
ls .rddf/plans/

# 3. 手动修复缺失文件
# 如果 .rddf/state/roadmap-state.json 缺失
echo '{"current_phase": "core", "completion": 0.0}' > .rddf/state/roadmap-state.json

# 4. 重新触发自动迁移（CLI `migrate --apply` 规划中，v2.1 实现）
skill_use("guide-spec")  # 首次调用时自动完成迁移
```

### 问题 2: 状态向量与现有文件不一致

**症状**: 状态向量显示 change 已完成，但 `proposal-suggestions.md` 显示未完成

> **⚠️ 当前版本（v2.0）说明**：CLI `spec-workflow sync` 规划中，v2.1 实现。当前状态数据存储于 Python 库层（`skills/_lib/sync_state.py`），在内存中维护双向一致性。下方命令展示的是 v2.0 完整设计演示。

**解决**:
```bash
# 1. 检查同步层状态（CLI `sync --check` 规划中，v2.1 实现；当前手动检查）
git status .rddf/state/ proposal-suggestions.md openspec/ .rddf/

# 2. 强制同步（状态向量 → 现有文件；CLI `sync --from state-vector` 规划中，v2.1 实现）
# 当前手动操作：调用 skill_use("guide-spec") 触发 sync_state.py 的协调逻辑
skill_use("guide-spec")

# 3. 强制同步（现有文件 → 状态向量；CLI `sync --from legacy` 规划中，v2.1 实现）
# 当前手动操作：直接编辑源文件（.rddf/state/roadmap-state.json / proposal-suggestions.md）
# Loop 下次启动时 sync_state.py 会自动读取并同步
```

### 问题 3: Loop 引擎不启动

**症状**: `skill_use("loop", ...)` 无响应

**解决**:
```bash
# 1. 检查 Python 依赖
python3 -c "import json, subprocess; print('OK')"

# 2. 检查状态向量
cat .rddf/state/state-vector.json | jq '.version'  # 应该是 "2.0"

# 3. 检查配置文件
cat .spec-workflow.json | jq '.'  # 应该是有效 JSON

# 4. 查看事件流
tail .rddf/state/event-log.jsonl | jq '.type'  # 查看最后的事件类型

# 5. 回退到菜单模式
skill_use("guide-plan")  # 使用 v1.x 兼容模式
```

### 问题 4: 门控检查失败

**症状**: 阶段切换时报 "Gate check failed"

**解决**:
```bash
# 1. 查看门控失败详情
cat .rddf/state/event-log.jsonl | jq 'select(.type == "gate_failed")'

# 2. 检查缺失的检查项
# 例如：arch_done 门控失败
ls docs/adr/  # 检查 ADR 是否存在
cat roadmap.md  # 检查 roadmap 是否存在

# 3. 修复后重试
# 创建缺失的 ADR 或 roadmap

# 4. 强制切换（不推荐）
# 在菜单中选择 "3. 强制切换（需确认）"
```

---

## 回滚策略

### 如果迁移后出现问题

#### 选项 1: 回滚到 v1.x 代码

```bash
# 1. 切换回 v1.x 分支
git checkout v1.x-branch

# 2. 恢复状态文件（如果需要）
# v1.x 会继续使用现有文件，不受影响
```

#### 选项 2: 禁用 v2.0 特性

```bash
# 在 .spec-workflow.json 中禁用 Loop 引擎
{
  "version": "2.0",
  "interaction": {
    "mode": "menu"  # 改回菜单模式
  },
  "loop": {
    "enabled": false  # 禁用 Loop 引擎
  }
}
```

#### 选项 3: 完全回滚

```bash
# 1. 删除 v2.0 新增文件
rm .rddf/state/state-vector.json
rm .rddf/state/event-log.jsonl
rm .spec-workflow.json

# 2. 恢复 v1.x 技能文件
git checkout HEAD -- skills/

# 3. 重新安装 v1.x
npm install spec-workflow@1.x
```

---

## 下一步

迁移完成后，建议：

1. **阅读 Loop 引擎指南**: [v2-loop-engine-guide.md](v2-loop-engine-guide.md)
2. **查看配置 Schema**: [v2-config-schema.md](v2-config-schema.md)
3. **尝试 loop 模式**: `skill_use("loop", {goal: "complete all changes"})`
4. **查看 ADR 总结**: [v2-adr-summary.md](v2-adr-summary.md)

---

## ❓ 常见问题

### Q: 升级后我还能用 `skill_use("guide-spec")` 吗？

**可以。** `guide-spec` 保留了别名行为，自动调用 `guide-arch` → `guide-plan`。

### Q: 我只有简单的项目，不需要架构定义，可以跳过 arch 阶段吗？

**可以。** 如果项目已有 `roadmap.md`，`guide` 推荐器会直接建议进入 plan 阶段。

### Q: 升级会影响正在执行的 worktree 吗？

**不会。** `guide-ship` 技能保持不变。正在执行的 worktree 完全不受影响。

### Q: 需要更新我之前的 change 吗？

**不需要。** 已提交的 change artifacts 格式不变。新的 `guide-plan` 技能会识别它们。

### Q: 如何回滚到 v1.x 行为？

如果新三阶段流程不适合你的工作流，可以使用 `guide-spec` 别名（保留原始语义）。

---

## 获取帮助

- **文档**: `docs/` 目录
- **ADR**: `docs/adr/` 目录
- **问题反馈**: GitHub Issues
- **社区讨论**: GitHub Discussions

---

## 📋 v2.0 → v2.0.1 微迁移（`prometheus-planning` v1.1 → v1.2）

> **版本**: prometheus-planning v1.1 → v1.2  
> **日期**: 2026-06-29  
> **影响范围**: 使用 `guide-ship` Phase 1 计划生成的 v2.0 用户  
> **预计迁移时间**: 0 分钟（完全向后兼容）

### 概述

`prometheus-planning` 从 v1.1（三级回退）升级到 v1.2（二级回退 + 路径独占 + 混合 TDD）。用户**无需任何手动操作**——所有现有 `.rddf/plans/<name>.md` 文件继续工作,所有现有 worktree 不受影响。

### 变更点

| 维度 | v1.1 | v1.2 |
|---|---|---|
| 回退链深度 | 三级 (oh-my-opencode → superpowers → prometheus-start-work) | **二级** (oh-my-opencode → superpowers,**`prometheus-start-work` 已彻底删除**) |
| Skills 隔离 | 分支 A 同时加载 Prometheus + superpowers/writing-plans | **分支 A 仅加载 Prometheus,分支 B 仅加载 superpowers** |
| 路径策略 | 单一 `.rddf/plans/<name>.md` | **分支 A 写 `.rddf/` + 软链接 `docs/superpowers/plans/YYYY-MM-DD-<name>.md`**<br>**分支 B 写 superpowers 原生路径 + cp 桥接到 `.rddf/`** |
| TDD 纪律 | prompt 建议遵循 superpowers 格式 | **混合 TDD:大任务 (>50 行 OR >3 文件 OR 架构改动) 强制 5 步,小任务 (≤50 行 AND ≤3 文件) 紧凑 2-3 步** |
| `_lib/actions.py:action_generate_plan` | Stub (注释说"完整实现位于 prometheus-planning skill") | **真实实现**: 分发到 prometheus-planning skill,通过 `SKIP_PROMETHEUS_PLANNING` env var 显式控制,失败时返回明确错误 |
| `package.json:optionalEngines.prometheus-start-work` | 存在,标记 deprecated | **删除** |

### 迁移步骤

**无需操作**。直接 `npm update spec-workflow` 即可。

如果你使用了 `prometheus-start-work` 作为唯一回退路径:
1. **影响**: v1.2 检测链不再查找 `prometheus-start-work`。如果你的环境中只有它(没有 oh-my-opencode 或 superpowers),`prometheus-planning` 会报错。
2. **修复**: 安装 `oh-my-opencode` 或 superpowers 套件(任选一)。详见 README.md "实施计划生成器" 表格。

### 路径行为变化

**之前 (v1.1)**:
- 所有 `.rddf/plans/<name>.md` 由 prometheus-planning 一处生成
- `docs/superpowers/plans/` 目录仅由 superpowers/writing-plans 在外部触发时写入

**现在 (v1.2)**:
- 分支 A: prometheus-planning 写 `.rddf/plans/<name>.md`,**自动软链接**到 `docs/superpowers/plans/YYYY-MM-DD-<name>.md` (symlink `→ ../../.rddf/plans/<name>.md`)
- 分支 B: superpowers/writing-plans 写 `docs/superpowers/plans/YYYY-MM-DD-<name>.md`,**自动复制**到 `.rddf/plans/<name>.md` + 反向软链接
- 两边内容始终一致,通过 `readlink docs/superpowers/plans/YYYY-MM-DD-<name>.md` 可验证

### 混合 TDD 实际效果

**v2-core-foundation plan** (现有 superpowers plan 文件): 严格 TDD 5 步
```
### Task 3: Implement FileLock class
- [ ] **Step 1: Write the failing test**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write minimal implementation**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**
```

**小型 fix plan** (假设的紧凑格式):
```
### Task 1: Fix typo in error message
- [ ] **Step 1: 写测试** (if applicable)
- [ ] **Step 2: 实现 + 验证**
- [ ] **Step 3: Commit**
```

两种格式共存于同一 plan 中是合法且推荐的——大任务 5 步,小任务 2-3 步。

### 测试覆盖

- 新增: `tests/integration/test_writing_plans_integration.bats` — 覆盖分支 A/B 路径契约、软链接创建、TDD 模式识别
- 保留: `tests/integration/test_prometheus_planning.bats` — 验证三级回退的 v1.0 行为(兼容模式)
- 保留: `tests/integration/test_prometheus_check.bats` — 检查 prometheus 相关引用一致性

### 升级触发条件（何时重新评估）

- superpowers/writing-plans 引入破坏性变更(任务模板或契约路径) → 重新审视路径桥接逻辑
- oh-my-opencode 引入 `prometheus-plan` v2 API → 重新设计分支 A prompt
- `_lib/actions.py` 的 `action_generate_plan` 被 `loop_engine.py` 频繁调用(目前 stub 够用) → 引入完整的 plan 内容生成器

---

**文档维护者**: sisyphus  
**最后更新**: 2026-06-22  
**下次审查**: v2.0 发布后

