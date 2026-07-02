# spec-workflow v2.0 记忆系统指南

> **版本**: 2.0.0  
> **日期**: 2026-06-22  
> **ADR 参考**: [ADR-0006](../adr/ADR-0006-state-vector-event-log.md)

---

## 📋 目录

- [概述](#概述)
- [中断恢复](#中断恢复)
- [配置推荐](#配置推荐)
- [失败模式学习](#失败模式学习)
- [记忆归档命令](#记忆归档命令)
- [记忆数据结构](#记忆数据结构)
- [最佳实践](#最佳实践)

---

## 概述

### 什么是记忆系统？

记忆系统（Memory System）是 spec-workflow v2.0 的**智能学习机制**，从历史执行中学习，提供：

1. **中断恢复**: 从中断点继续，不丢失进度
2. **配置推荐**: 基于历史成功执行推荐配置
3. **失败模式学习**: 识别重复失败，提供建议
4. **执行洞察**: 分析执行模式，优化流程

### 记忆 vs 事件流

| 特性 | 记忆系统 | 事件流 |
|------|---------|--------|
| **目的** | 长期学习和恢复 | 短期审计和追溯 |
| **存储** | 状态向量中 | 独立文件 (event-log.jsonl) |
| **保留** | 可配置（默认 90 天） | 永久保留 |
| **查询** | 结构化查询 | 顺序扫描 |
| **用途** | 配置推荐、中断恢复 | 审计、调试 |

---

## 中断恢复

### 自动中断检测

Loop 引擎启动时自动检测中断：

```
🔄 检测到中断的会话

📊 中断信息:
  - 会话 ID: sess_20260622_001
  - 目标: complete add-auth change
  - 中断时间: 2026-06-22T10:00:00Z
  - 中断原因: user_disconnect
  - 最后阶段: ship
  - 最后节点: execute_work_units
  - 已完成迭代: 5
  - 已完成进度: 60% (9/15 work units)

是否恢复执行？[y/n]:
```

### 恢复流程

```
步骤 1: 加载状态向量
  ↓
步骤 2: 恢复 worktree 状态
  ↓
步骤 3: 显示历史执行记录
  ↓
步骤 4: 推荐配置（基于记忆）
  ↓
步骤 5: 从断点继续
```

### 恢复示例

```
🔄 恢复执行: add-auth

📊 历史执行记录:
  - 上次执行: 2026-06-22T10:00:00Z
  - 上次结果: 中断
  - 中断原因: user_disconnect
  - 已迭代: 5 次
  - 已完成: 9/15 work units (60%)

💡 建议:
  - 从 work unit 10 继续
  - Merge 前先运行完整测试套件

📊 基于历史执行，推荐配置:
  - max_iterations: 50 (原 100)
  - max_retries: 3 (原 3)
  - verification_method: multi_model (原 human)

是否使用推荐配置？[y/n]: y

✅ 使用推荐配置，开始恢复...

[恢复状态]
✅ Worktree: add-auth-wt 已存在
✅ 进度: 60% (9/15 work units)
✅ 下一阶段: execute_work_units (从 unit 10 开始)

继续执行？[y/n]: y

⚙️ 恢复执行...
```

### 手动恢复

```bash
# 查看中断的会话
spec-workflow memory list-sessions --status interrupted

# 输出:
# Session ID                    Goal                      Interrupted
# sess_20260622_001            complete add-auth          2026-06-22T10:00:00Z
# sess_20260621_003            refactor database          2026-06-21T15:30:00Z

# 恢复特定会话
spec-workflow memory resume sess_20260622_001
```

---

## 配置推荐

### 推荐算法

```python
def recommend_config(goal: str, memory: dict) -> dict:
    """
    基于历史执行推荐配置
    
    Args:
        goal: 当前目标
        memory: 记忆数据
    
    Returns:
        recommended_config: 推荐配置
    """
    # 1. 找到相似目标的历史执行
    similar_executions = find_similar_executions(goal, memory["executions"])
    
    if not similar_executions:
        return get_default_config()
    
    # 2. 分析成功执行
    successful = [e for e in similar_executions if e["status"] == "success"]
    
    if not successful:
        return get_default_config()
    
    # 3. 计算推荐值
    avg_iterations = avg(e["iterations"] for e in successful)
    avg_retries = avg(e["retries"] for e in successful)
    
    # 4. 添加安全边际
    recommended = {
        "max_iterations": int(avg_iterations * 1.5),
        "max_retries": int(avg_retries * 2),
        "verification_method": most_common(e["verification_method"] for e in successful),
        "parallel_limit": most_common(e["parallel_limit"] for e in successful)
    }
    
    return recommended
```

### 推荐示例

```
📊 基于历史执行，推荐配置

相似目标的历史执行: 5 次
成功执行: 4 次 (80% 成功率)

历史执行统计:
  - 平均迭代次数: 33
  - 平均重试次数: 1.5
  - 常用验证方法: multi_model (3/4)
  - 常用并行限制: 3 (3/4)

推荐配置:
  - max_iterations: 50 (基于平均值 33 * 1.5)
  - max_retries: 3 (基于平均值 1.5 * 2)
  - verification_method: multi_model
  - parallel_limit: 3

成功率: 80% (4/5)
置信度: 高

是否使用推荐配置？[y/n]:
```

### 拒绝推荐

如果拒绝推荐，可以使用自定义配置：

```
是否使用推荐配置？[y/n]: n

请输入自定义配置:
  max_iterations: 100
  max_retries: 3
  verification_method: human
  parallel_limit: 2

✅ 使用自定义配置
```

---

## 失败模式学习

### 重复失败检测

```
⚠️ 警告: change 'refactor-db' 已失败 3 次

📊 学习到的洞察:
  - 问题: Merge 后测试失败频率高
  - 根本原因: 数据库 schema 不兼容
  - 建议: Merge 前先运行完整测试套件
  - 置信度: 85%
  - 出现次数: 5 次（类似 changes）

历史失败记录:
  1. 2026-06-20T10:00:00Z - test_failure (unit 12)
  2. 2026-06-21T14:30:00Z - test_failure (unit 8)
  3. 2026-06-22T09:15:00Z - test_failure (unit 15)

请选择:
  1. 继续执行（应用推荐配置）
  2. 查看失败详情
  3. 暂停此 change，先处理其他
  4. 中止

选择 [1-4]:
```

### 推荐修复策略

```
📊 推荐修复策略

基于历史失败分析，推荐以下策略:

策略 1: 先运行测试再 Merge
  - 适用性: 85% (类似场景成功率)
  - 步骤:
    1. 在 worktree 中运行完整测试套件
    2. 修复失败的测试
    3. 确认所有测试通过
    4. Merge 到 main

策略 2: 分阶段 Merge
  - 适用性: 70%
  - 步骤:
    1. 先 Merge 非破坏性更改
    2. 运行测试
    3. 再 Merge schema 更改
    4. 运行迁移脚本

策略 3: 使用 feature flag
  - 适用性: 60%
  - 步骤:
    1. 添加 feature flag
    2. 在新 flag 下开发
    3. 逐步启用
    4. 移除旧代码

推荐策略: 策略 1 (最高成功率)

是否应用推荐策略？[y/n]:
```

### 失败模式数据库

```json
{
  "memory": {
    "failure_patterns": [
      {
        "pattern_id": "fp_001",
        "description": "Merge 后测试失败",
        "symptoms": [
          "test_failure after merge",
          "integration test failure"
        ],
        "root_cause": "数据库 schema 不兼容",
        "solution": "Merge 前先运行完整测试套件",
        "confidence": 0.85,
        "occurrences": 5,
        "success_rate": 0.80,
        "first_seen": "2026-06-20T10:00:00Z",
        "last_seen": "2026-06-22T09:15:00Z"
      },
      {
        "pattern_id": "fp_002",
        "description": "循环迭代过多",
        "symptoms": [
          "max_iterations exceeded",
          "stagnation detected"
        ],
        "root_cause": "目标过于宽泛",
        "solution": "拆分目标为更小的子目标",
        "confidence": 0.90,
        "occurrences": 3,
        "success_rate": 0.75,
        "first_seen": "2026-06-18T14:00:00Z",
        "last_seen": "2026-06-21T16:30:00Z"
      }
    ]
  }
}
```

---

## 记忆归档命令

### 查看记忆

```bash
# 查看记忆摘要
spec-workflow memory summary

# 输出:
# 记忆系统状态:
#   总执行次数: 50
#   成功执行: 42 (84%)
#   失败执行: 8 (16%)
#   
#   学习到的失败模式: 3
#   平均成功率: 84%
#   记忆保留天数: 90
#   
#   存储使用:
#     状态向量: 15 KB
#     执行记录: 50 条
#     失败模式: 3 条

# 查看执行历史
spec-workflow memory list-executions

# 输出:
# 执行历史 (最近 10 条):
#   1. 2026-06-22T10:00:00Z - complete add-auth - SUCCESS (15 iterations)
#   2. 2026-06-21T15:30:00Z - refactor database - FAILURE (test_failure)
#   3. 2026-06-21T10:00:00Z - add user profile - SUCCESS (22 iterations)
#   4. 2026-06-20T14:00:00Z - implement auth - SUCCESS (18 iterations)
#   5. 2026-06-20T09:00:00Z - setup CI - SUCCESS (8 iterations)

# 查看失败模式
spec-workflow memory list-failure-patterns

# 输出:
# 失败模式 (3 条):
#   1. Merge 后测试失败 (5 次, 置信度: 85%)
#      建议: Merge 前先运行完整测试套件
#   
#   2. 循环迭代过多 (3 次, 置信度: 90%)
#      建议: 拆分目标为更小的子目标
#   
#   3. Worktree 创建失败 (2 次, 置信度: 75%)
#      建议: 检查 git worktree 限制
```

### 归档记忆

```bash
# 归档过期记忆（默认 90 天）
spec-workflow memory archive

# 输出:
# 归档记忆:
#   归档执行记录: 20 条 (> 90 天)
#   归档失败模式: 1 条 (> 90 天)
#   
#   归档文件: .rddf/state/memory-archive-2026-06-22.json
#   当前记忆: 30 条执行记录, 2 条失败模式

# 自定义归档时间
spec-workflow memory archive --retention-days 60

# 导出记忆
spec-workflow memory export --output memory-export.json

# 导入记忆
spec-workflow memory import --input memory-export.json
```

### 清理记忆

```bash
# 清理所有记忆（危险操作）
spec-workflow memory clear --confirm

# 输出:
# ⚠️ 警告: 此操作将删除所有记忆数据
# 
# 将删除:
#   - 50 条执行记录
#   - 3 条失败模式
#   - 配置推荐缓存
# 
# 此操作不可恢复！
# 
# 是否确认？[y/N]:
```

---

## 记忆数据结构

### 状态向量中的记忆字段

```json
{
  "memory": {
    "enabled": true,
    "retention_days": 90,
    "auto_suggest_config": true,
    "executions": [
      {
        "execution_id": "exec_20260622_001",
        "session_id": "sess_20260622_001",
        "goal": "complete add-auth change",
        "status": "success",
        "started_at": "2026-06-22T09:00:00Z",
        "completed_at": "2026-06-22T10:00:00Z",
        "iterations": 15,
        "retries": 1,
        "final_score": 0.91,
        "verification_method": "multi_model",
        "parallel_limit": 3,
        "changes_completed": ["add-auth"],
        "errors": [],
        "warnings": []
      }
    ],
    "failure_patterns": [
      {
        "pattern_id": "fp_001",
        "description": "Merge 后测试失败",
        "symptoms": ["test_failure after merge"],
        "root_cause": "数据库 schema 不兼容",
        "solution": "Merge 前先运行完整测试套件",
        "confidence": 0.85,
        "occurrences": 5,
        "success_rate": 0.80,
        "first_seen": "2026-06-20T10:00:00Z",
        "last_seen": "2026-06-22T09:15:00Z"
      }
    ],
    "config_recommendations": {
      "complete_changes": {
        "max_iterations": 50,
        "max_retries": 3,
        "verification_method": "multi_model",
        "parallel_limit": 3,
        "success_rate": 0.84,
        "sample_size": 50
      }
    }
  }
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `enabled` | boolean | 是否启用记忆系统 |
| `retention_days` | integer | 记忆保留天数 |
| `auto_suggest_config` | boolean | 是否自动推荐配置 |
| `executions` | array | 执行历史记录 |
| `failure_patterns` | array | 失败模式数据库 |
| `config_recommendations` | object | 配置推荐缓存 |

---

### 执行记录字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `execution_id` | string | 执行 ID |
| `session_id` | string | 会话 ID |
| `goal` | string | 目标描述 |
| `status` | string | 执行状态 (success/failure/interrupted) |
| `started_at` | string | 开始时间 (ISO 8601) |
| `completed_at` | string | 完成时间 (ISO 8601) |
| `iterations` | integer | 迭代次数 |
| `retries` | integer | 重试次数 |
| `final_score` | number | 最终评分 (0-1) |
| `verification_method` | string | 验证方法 |
| `parallel_limit` | integer | 并行限制 |
| `changes_completed` | array | 完成的 changes 列表 |
| `errors` | array | 错误列表 |
| `warnings` | array | 警告列表 |

---

### 失败模式字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `pattern_id` | string | 模式 ID |
| `description` | string | 模式描述 |
| `symptoms` | array | 症状列表 |
| `root_cause` | string | 根本原因 |
| `solution` | string | 解决方案 |
| `confidence` | number | 置信度 (0-1) |
| `occurrences` | integer | 出现次数 |
| `success_rate` | number | 解决成功率 (0-1) |
| `first_seen` | string | 首次出现时间 |
| `last_seen` | string | 最后出现时间 |

---

## 最佳实践

### 1. 启用记忆系统

```json
{
  "memory": {
    "enabled": true,
    "retention_days": 90,
    "auto_suggest_config": true
  }
}
```

**原因**: 
- ✅ 支持中断恢复
- ✅ 自动推荐配置
- ✅ 学习失败模式

---

### 2. 设置合理的保留时间

| 项目类型 | 推荐保留时间 | 原因 |
|---------|------------|------|
| **活跃项目** | 90 天 | 足够学习近期模式 |
| **长期项目** | 180 天 | 学习长期趋势 |
| **短期项目** | 30 天 | 减少存储 |
| **实验项目** | 14 天 | 快速迭代 |

---

### 3. 定期归档记忆

```bash
# 每周归档一次
crontab -e

# 添加:
# 0 2 * * 0 spec-workflow memory archive --retention-days 90
```

---

### 4. 导出记忆备份

```bash
# 每月导出备份
spec-workflow memory export --output memory-backup-$(date +%Y-%m).json

# 存储到远程
aws s3 cp memory-backup-$(date +%Y-%m).json s3://backups/spec-workflow/
```

---

### 5. 监控记忆质量

```bash
# 查看记忆质量报告
spec-workflow memory quality-report

# 输出:
# 记忆质量报告:
#   总执行记录: 50
#   有效记录: 48 (96%)
#   无效记录: 2 (4%) - 数据不完整
#   
#   失败模式:
#     总模式: 3
#     高置信度 (≥ 0.8): 2
#     中置信度 (0.5-0.8): 1
#     低置信度 (< 0.5): 0
#   
#   推荐覆盖率:
#     有推荐的目标: 80% (40/50)
#     无推荐的目标: 20% (10/50)
#   
#   建议:
#     - 清理 2 条无效记录
#     - 增加 10 个目标的推荐覆盖
```

---

## 故障排查

### 问题 1: 中断无法恢复

**症状**: "No interrupted session found"

**解决**:
```bash
# 1. 检查记忆系统是否启用
cat .spec-workflow.json | jq '.memory.enabled'  # 应该是 true

# 2. 检查状态向量
cat .rddf/state/state-vector.json | jq '.memory'

# 3. 检查执行记录
cat .rddf/state/state-vector.json | jq '.memory.executions'

# 4. 手动恢复
spec-workflow memory list-sessions --status interrupted
spec-workflow memory resume <session-id>
```

---

### 问题 2: 配置推荐不准确

**症状**: 推荐配置不适合当前任务

**解决**:
```bash
# 1. 查看推荐依据
spec-workflow memory show-recommendations --goal "complete changes"

# 输出:
# 推荐依据:
#   相似执行: 5 次
#   成功执行: 4 次
#   平均迭代: 33
#   推荐迭代: 50 (33 * 1.5)
#   
#   如果推荐不准确，可能原因:
#   - 相似执行样本太少
#   - 目标描述不匹配
#   - 项目差异大

# 2. 增加样本量
# 继续执行更多任务，积累数据

# 3. 手动调整
# 拒绝推荐，使用自定义配置
```

---

### 问题 3: 记忆数据过大

**症状**: 状态向量文件过大（> 1 MB）

**解决**:
```bash
# 1. 查看记忆大小
du -h .rddf/state/state-vector.json

# 2. 归档过期记忆
spec-workflow memory archive --retention-days 30

# 3. 清理无效记录
spec-workflow memory clean --invalid-only

# 4. 压缩记忆
spec-workflow memory compact
```

---

## 下一步

- **查看 ADR-0006**: [ADR-0006-state-vector-event-log.md](../adr/ADR-0006-state-vector-event-log.md)
- **查看配置 Schema**: [v2-config-schema.md](../v2-config-schema.md)
- **查看 Loop 引擎指南**: [v2-loop-engine-guide.md](../v2-loop-engine-guide.md)

---

**文档维护者**: sisyphus  
**最后更新**: 2026-06-22  
**下次审查**: v2.0 发布后


