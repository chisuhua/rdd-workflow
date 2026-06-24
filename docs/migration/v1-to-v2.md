# spec-workflow v1.x → v2.0 迁移指南

> **版本**: 2.0.0  
> **日期**: 2026-06-22  
> **目标读者**: 现有 v1.x 用户  
> **预计迁移时间**: 30 分钟 - 2 小时（取决于项目复杂度）

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
| `.zcf/.roadmap-state.json` | 通过同步层自动更新 | v3.0 移除 |
| `proposal-suggestions.md` | 通过同步层自动更新 | v3.0 移除 |
| `.sisyphus/plans/*.md` | 保持不变 | 长期支持 |

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
- [ ] 运行 `spec-workflow migrate --check`（检查迁移就绪状态）
- [ ] 运行 `spec-workflow migrate --dry-run`（预览迁移）
- [ ] 运行 `spec-workflow migrate --apply`（执行迁移）
- [ ] 验证状态向量（`cat .zcf/state-vector.json`）
- [ ] 运行测试（`bats tests/`）
- [ ] 创建 `.spec-workflow.json`（可选）
- [ ] 尝试 loop 模式（可选）

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

### 自动迁移

首次运行 v2.0 时，会自动执行迁移：

```bash
$ skill_use("guide-spec")

🔄 检测到 v1.x 状态文件，开始迁移...
✅ 迁移 .zcf/.roadmap-state.json → state-vector.json
✅ 迁移 proposal-suggestions.md → state-vector.json
✅ 迁移 openspec/changes/*/ .openspec.yaml → state-vector.json
✅ 迁移 .sisyphus/plans/*.md → state-vector.json
✅ 创建 .zcf/event-log.jsonl

迁移完成！状态向量已生成。
```

### 手动迁移

如果需要手动迁移：

```bash
spec-workflow migrate --apply
```

### 验证迁移结果

```bash
# 检查状态向量
cat .zcf/state-vector.json | jq '.version'  # 应该输出 "2.0"

# 检查事件流
wc -l .zcf/event-log.jsonl  # 应该有迁移事件

# 检查向后兼容文件
ls -la .zcf/.roadmap-state.json  # 应该仍然存在（同步层维护）
ls -la proposal-suggestions.md   # 应该仍然存在（同步层维护）
```

### 状态文件映射

| v1.x 文件 | v2.0 状态向量字段 | 同步层 |
|----------|------------------|--------|
| `.zcf/.roadmap-state.json` | `arch_side.roadmap` | ✅ 双向同步 |
| `proposal-suggestions.md` | `plan_side.active_changes` | ✅ 双向同步 |
| `openspec/changes/*/ .openspec.yaml` | `plan_side.active_changes[].artifacts` | ✅ 单向读取 |
| `.sisyphus/plans/*.md` | `ship_side.worktrees[].plan` | ✅ 单向读取 |
| `git worktree list` | `ship_side.worktrees` | ✅ 实时扫描 |

---

## 技能文件变更

### 新增技能文件

| 文件 | 说明 | 必须 |
|------|------|------|
| `skills/guide-arch.md` | 架构定义阶段 | ✅ 是 |
| `skills/guide-plan.md` | 变更生成阶段（原 guide-spec） | ✅ 是 |
| `skills/loop.md` | Loop 引擎入口 | ✅ 是 |
| `skills/_lib/state_vector.py` | 状态向量操作 | ✅ 是 |
| `skills/_lib/event_log.py` | 事件流操作 | ✅ 是 |
| `skills/_lib/session_v20.py` | 轻量级会话协调器 | ✅ 是 |

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

# 方式 2: 查看状态向量
cat .zcf/state-vector.json | jq '.'

# 方式 3: 查看事件流
tail -f .zcf/event-log.jsonl | jq '.'

# 方式 4: 生成进度报告
spec-workflow report
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

**症状**: `spec-workflow migrate --apply` 报错

**解决**:
```bash
# 1. 检查错误日志
cat .zcf/migration-error.log

# 2. 检查 v1.x 状态文件完整性
spec-workflow migrate --check

# 3. 手动修复缺失文件
# 如果 .zcf/.roadmap-state.json 缺失
echo '{"current_phase": "core", "completion": 0.0}' > .zcf/.roadmap-state.json

# 4. 重试迁移
spec-workflow migrate --apply
```

### 问题 2: 状态向量与现有文件不一致

**症状**: 状态向量显示 change 已完成，但 `proposal-suggestions.md` 显示未完成

**解决**:
```bash
# 1. 检查同步层状态
spec-workflow sync --check

# 2. 强制同步（状态向量 → 现有文件）
spec-workflow sync --from state-vector

# 3. 强制同步（现有文件 → 状态向量）
spec-workflow sync --from legacy
```

### 问题 3: Loop 引擎不启动

**症状**: `skill_use("loop", ...)` 无响应

**解决**:
```bash
# 1. 检查 Python 依赖
python3 -c "import json, subprocess; print('OK')"

# 2. 检查状态向量
cat .zcf/state-vector.json | jq '.version'  # 应该是 "2.0"

# 3. 检查配置文件
cat .spec-workflow.json | jq '.'  # 应该是有效 JSON

# 4. 查看事件流
tail .zcf/event-log.jsonl | jq '.type'  # 查看最后的事件类型

# 5. 回退到菜单模式
skill_use("guide-plan")  # 使用 v1.x 兼容模式
```

### 问题 4: 门控检查失败

**症状**: 阶段切换时报 "Gate check failed"

**解决**:
```bash
# 1. 查看门控失败详情
cat .zcf/event-log.jsonl | jq 'select(.type == "gate_failed")'

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
rm .zcf/state-vector.json
rm .zcf/event-log.jsonl
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

## 获取帮助

- **文档**: `docs/` 目录
- **ADR**: `docs/adr/` 目录
- **问题反馈**: GitHub Issues
- **社区讨论**: GitHub Discussions

---

**文档维护者**: sisyphus  
**最后更新**: 2026-06-22  
**下次审查**: v2.0 发布后

