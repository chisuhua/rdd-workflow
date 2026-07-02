# spec-workflow v2.0 门控机制指南

> **版本**: 2.0.0  
> **日期**: 2026-06-22  
> **ADR 参考**: [ADR-0007](../adr/ADR-0007-gate-mechanism.md)

---

## 📋 目录

- [概述](#概述)
- [门控检查清单](#门控检查清单)
- [门控失败处理](#门控失败处理)
- [自定义门控插件](#自定义门控插件)
- [强制切换流程](#强制切换流程)
- [门控最佳实践](#门控最佳实践)

---

## 概述

### 什么是门控？

门控（Gate）是阶段切换前的**质检查点**，确保满足必要条件后才能进入下一阶段。

```
Arch 阶段 ──[门控]──→ Plan 阶段 ──[门控]──→ Ship 阶段
```

### 门控 vs 验证

| 特性 | 门控 (Gate) | 验证 (Verification) |
|------|------------|-------------------|
| **时机** | 阶段切换前 | 每次迭代后 |
| **目的** | 防止进入下一阶段 | 检查当前迭代结果 |
| **严重度** | error / warning | pass / fail |
| **处理** | 必须修复 error | 可重试或自适应 |

---

## 门控检查清单

### Arch 阶段门控 (arch_done)

| 检查项 | 条件 | 严重度 | 说明 |
|--------|------|-------|------|
| **adr_exists** | `arch_side.adr.count >= 1` | error | 必须至少创建 1 个 ADR |
| **roadmap_defined** | `arch_side.roadmap.exists == true` | error | 必须定义 roadmap.md |
| **gap_analysis_complete** | `arch_side.architecture.pending_gaps == 0` | warning | 建议完成架构差距分析 |

**示例输出**:
```
[门控检查: arch_done]
✅ adr_exists: PASS (3 ADRs found)
✅ roadmap_defined: PASS (roadmap.md exists)
⚠️ gap_analysis_complete: WARNING (1 pending gap)
  ⚠️ 建议完成架构差距分析

门控通过（1 warning），许切换阶段
```

---

### Plan 阶段门控 (plan_done)

| 检查项 | 条件 | 严重度 | 说明 |
|--------|------|-------|------|
| **changes_committed** | `plan_side.active_changes.count >= 1` | error | 必须至少 1 个 active change |
| **artifacts_complete** | `all changes have .openspec.yaml` | error | 所有 changes 必须有 artifacts |
| **deps_analysis_done** | `plan_side.deps_analysis.complete == true` | warning | 建议完成依赖分析 |

**示例输出**:
```
[门控检查: plan_done]
✅ changes_committed: PASS (2 active changes)
✅ artifacts_complete: PASS (2/2 changes have .openspec.yaml)
⚠️ deps_analysis_done: WARNING (not completed)
  ⚠️ 建议完成依赖分析，避免执行顺序错误

门控通过（1 warning），允许切换阶段
```

---

### Ship 阶段门控 (ship_done)

| 检查项 | 条件 | 严重度 | 说明 |
|--------|------|-------|------|
| **worktrees_empty** | `ship_side.worktrees.count == 0` | error | 所有 worktrees 必须清理 |
| **archive_empty** | `plan_side.active_changes.count == 0` | error | 所有 changes 必须归档 |
| **tests_passed** | `ship_side.tests.pass_rate == 1.0` | error | 所有测试必须通过 |
| **no_merge_conflicts** | `ship_side.merge.conflicts == 0` | error | 不能有 merge conflicts |

**示例输出**:
```
[门控检查: ship_done]
✅ worktrees_empty: PASS (0 worktrees)
✅ archive_empty: PASS (0 active changes)
✅ tests_passed: PASS (15/15 tests passed)
✅ no_merge_conflicts: PASS (0 conflicts)

✅ 所有门控通过！

目标达成: complete all pending changes
```

---

## 门控失败处理

### 错误处理流程

```
❌ 门控检查失败: arch_done

失败项:
  ❌ adr_exists: FAIL (0 ADRs found, expected ≥ 1)
  ❌ roadmap_defined: FAIL (roadmap.md not found)

请选择:
  1. 返回 Arch 阶段修复（推荐）
  2. 查看详细信息
  3. 强制切换（不推荐，需确认）
  4. 中止

选择 [1-4]:
```

### 选项 1: 返回修复（推荐）

```
✅ 返回 Arch 阶段

[自动修复建议]
💡 创建 ADR:
  - 运行: skill_use("guide-arch")
  - 选择: "1. 创建 ADR"

💡 创建 roadmap:
  - 编辑: roadmap.md
  - 添加: phases, changes, metrics

修复后重新运行门控检查？[y/n]:
```

### 选项 2: 查看详细信息

```
📋 门控失败详细信息

检查项: adr_exists
  当前值: 0
  期望值: ≥ 1
  说明: 必须至少建 1 个 ADR
  修复方法: 
    1. 运行 skill_use("guide-arch")
    2. 选择 "1. 创建 ADR"
    3. 填写 ADR 内容
    4. 保存为 docs/adr/ADR-XXXX-xxx.md

检查项: roadmap_defined
  当前值: false
  期望值: true
  说明: 必须定义 roadmap.md
  修复方法:
    1. 创建 roadmap.md
    2. 添加 phases 定义
    3. 添加 changes 列表
    4. 添加 metrics

是否返回修复？[y/n]:
```

### 选项 3: 强制切换

```
⚠️ 强制切换警告

您正在尝试强制切换到下一阶段，这可能导致：
  ❌ 质量下降
  ❌ 后续阶段失败
  ❌ 需要返工

强制切换理由（必填）:
> 紧急修复，后续会补充 ADR 和 roadmap

⚠️ 此操作将被记录到事件流，并需要二次确认。

是否确认强制切换？[y/N]:
```

---

## 自定义门控插件

### 插件结构

门控插件是 Python 脚本，位于 `.spec-workflow/gates/` 目录：

```
.spec-workflow/
└── gates/
    ├── arch_done.py
    ├── plan_done.py
    └── ship_done.py
```

### 插件模板

```python
"""
自定义门控插件: arch_done
"""

from state_vector import StateVector

def check(state: dict) -> dict:
    """
    执行门控检查
    
    Args:
        state: 当前状态向量
    
    Returns:
        {
            "passed": bool,
            "checks": [
                {
                    "name": str,
                    "passed": bool,
                    "severity": "error" | "warning",
                    "message": str
                }
            ]
        }
    """
    checks = []
    
    # 检查 1: ADR 存在
    adr_count = len(state.get("arch_side", {}).get("adr", []))
    checks.append({
        "name": "adr_exists",
        "passed": adr_count >= 1,
        "severity": "error",
        "message": f"{adr_count} ADRs found, expected ≥ 1"
    })
    
    # 检查 2: roadmap 存在
    roadmap_exists = state.get("arch_side", {}).get("roadmap", {}).get("exists", False)
    checks.append({
        "name": "roadmap_defined",
        "passed": roadmap_exists,
        "severity": "error",
        "message": "roadmap.md not found" if not roadmap_exists else "roadmap.md exists"
    })
    
    # 检查 3: 差距分析完成
    pending_gaps = state.get("arch_side", {}).get("architecture", {}).get("pending_gaps", 0)
    checks.append({
        "name": "gap_analysis_complete",
        "passed": pending_gaps == 0,
        "severity": "warning",
        "message": f"{pending_gaps} pending gaps" if pending_gaps > 0 else "no pending gaps"
    })
    
    # 计算是否通过
    passed = all(c["passed"] or c["severity"] == "warning" for c in checks)
    
    return {
        "passed": passed,
        "checks": checks
    }
```

### 注册自定义门控

在 `.spec-workflow.json` 中注册：

```json
{
  "gates": {
    "arch_done": [
      {
        "name": "custom_adr_check",
        "script": ".spec-workflow/gates/arch_done.py",
        "severity": "error"
      }
    ]
  }
}
```

### 访问状态向量

门控插件可以通过 `state_vector` 模块访问状态：

```python
from state_vector import StateVector

def check(state: dict) -> dict:
    # 读取状态
    adr_count = len(state["arch_side"]["adr"])
    
    # 读取事件流
    from event_log import EventLog
    events = EventLog().query(type="adr_created", limit=10)
    
    # 返回检查结果
    return {
        "passed": adr_count >= 1,
        "checks": [...]
    }
```

---

## 门控条件表达式

### 支持的操作符

| 操作符 | 说明 | 示例 |
|--------|------|------|
| `==` | 等于 | `arch_side.adr.count == 1` |
| `!=` | 不等于 | `ship_side.worktrees.count != 0` |
| `>=` | 大于等于 | `arch_side.adr.count >= 1` |
| `<=` | 小于等于 | `ship_side.tests.failed <= 0` |
| `>` | 大于 | `plan_side.active_changes.count > 0` |
| `<` | 小于 | `arch_side.architecture.pending_gaps < 1` |
| `&&` | 与 | `adr.count >= 1 && roadmap.exists == true` |
| `||` | 或 | `tests.passed == true || tests.skipped == true` |
| `!` | 非 | `!roadmap.exists` |

### 内置函数

| 函数 | 说明 | 示例 |
|------|------|------|
| `count()` | 计数 | `arch_side.adr.count()` |
| `exists()` | 检查存在 | `roadmap.exists()` |
| `all()` | 全部满足 | `changes.all(.openspec.yaml.exists())` |
| `any()` | 任一满足 | `changes.any(.status == "active")` |

### 示例

```json
{
  "gates": {
    "arch_done": [
      {
        "name": "adr_and_roadmap",
        "condition": "arch_side.adr.count() >= 1 && arch_side.roadmap.exists() == true",
        "severity": "error",
        "message": "必须创建 ADR 和 roadmap"
      },
      {
        "name": "all_changes_have_artifacts",
        "condition": "plan_side.active_changes.all(.artifacts.exists() == true)",
        "severity": "error",
        "message": "所有 changes 必须有 artifacts"
      }
    ]
  }
}
```

---

## 强制切换流程

### 何时使用强制切换

**允许场景**:
- ✅ 紧急修复（hotfix）
- ✅ 实验性功能
- ✅ 已知风险，已评估

**禁止场景**:
- ❌ 常规开发
- ❌ 避免创建工作
- ❌ 跳过测试

### 强制切换步骤

```
步骤 1: 选择强制切换
  ↓
步骤 2: 填写理由（必填）
  ↓
步骤 3: 二次确认
  ↓
步骤 4: 记录到事件流
  ↓
步骤 5: 切换到下一阶段
```

### 事件流记录

强制切换会被记录到事件流：

```json
{
  "timestamp": "2026-06-22T10:30:00Z",
  "type": "gate_forced",
  "data": {
    "gate": "arch_done",
    "failed_checks": [
      "adr_exists",
      "roadmap_defined"
    ],
    "reason": "紧急修复，后续会补充 ADR 和 roadmap",
    "confirmed_by": "user",
    "confirmation_time": "2026-06-22T10:30:05Z"
  }
}
```

### 审计报告

强制切换会出现在审计报告中：

```
📊 审计报告

强制切换记录:
  1. 2026-06-22T10:30:00Z
     Gate: arch_done
     失败项: adr_exists, roadmap_defined
     理由: 紧急修复，后续会补充 ADR 和 roadmap
     确认人: user

⚠️ 建议: 尽快补充缺失的 ADR 和 roadmap
```

---

## 门控最佳实践

### 1. 设置合理的严重度

```json
{
  "gates": {
    "arch_done": [
      {
        "name": "adr_exists",
        "severity": "error"  // ✅ 必须通过
      },
      {
        "name": "gap_analysis_complete",
        "severity": "warning"  // ✅ 建议通过，但可强制切换
      }
    ]
  }
}
```

---

### 2. 提供清晰的错误消息

```json
{
  "gates": {
    "arch_done": [
      {
        "name": "adr_exists",
        "condition": "arch_side.adr.count >= 1",
        "severity": "error",
        "message": "必须至少创建 1 个 ADR（docs/adr/ADR-XXXX-xxx.md）"
      }
    ]
  }
}
```

---

### 3. 提供自动修复建议

```python
def get_repair_suggestions(check_name: str) -> list:
    """获取修复建议"""
    suggestions = {
        "adr_exists": [
            "运行 skill_use('guide-arch')",
            "选择 '1. 创建 ADR'",
            "填写 ADR 内容",
            "保存为 docs/adr/ADR-XXXX-xxx.md"
        ],
        "roadmap_defined": [
            "创建 roadmap.md",
            "添加 phases 定义",
            "添加 changes 列表",
            "添加 metrics"
        ]
    }
    return suggestions.get(check_name, [])
```

---

### 4. 自定义门控插件

对于复杂检查，编写自定义插件：

```python
# .spec-workflow/gates/custom_quality_check.py

def check(state: dict) -> dict:
    """自定义质量检查"""
    
    # 检查代码质量分数
    quality_score = calculate_quality_score()
    
    return {
        "passed": quality_score >= 0.8,
        "checks": [
            {
                "name": "code_quality",
                "passed": quality_score >= 0.8,
                "severity": "warning",
                "message": f"Quality score: {quality_score:.2f} (expected ≥ 0.8)"
            }
        ]
    }
```

---

### 5. 监控门控失败率

```bash
# 查看门控失败统计
spec-workflow gates stats

# 输出:
# Gate: arch_done
#   总检查次数: 50
#   通过次数: 45 (90%)
#   失败次数: 5 (10%)
#   强制切换次数: 1 (2%)
#
# Gate: plan_done
#   总检查次数: 48
#   通过次数: 46 (96%)
#   失败次数: 2 (4%)
#   强制切换次数: 0 (0%)
```

---

## 故障排查

### 问题 1: 门控检查一直失败

**症状**: 门控检查失败，但看起来应该通过

**解决**:
```bash
# 1. 查看门控条件
cat .spec-workflow.json | jq '.gates.arch_done'

# 2. 查看当前状态
cat .rddf/state/state-vector.json | jq '.arch_side'

# 3. 手动验证条件
# 例如：检查 ADR 数量
ls docs/adr/ADR-*.md | wc -l

# 4. 检查门控插件逻辑
cat .spec-workflow/gates/arch_done.py
```

---

### 问题 2: 门控插件报错

**症状**: 门控检查时 Python 报错

**解决**:
```bash
# 1. 查看错误日志
cat .rddf/state/event-log.jsonl | jq 'select(.type == "gate_error")'

# 2. 检查 Python 依赖
python3 -c "import state_vector; print('OK')"

# 3. 检查插件语法
python3 -m py_compile .spec-workflow/gates/arch_done.py

# 4. 手动运行插件
python3 -c "
from gates.arch_done import check
import json
state = json.load(open('.rddf/state/state-vector.json'))
result = check(state)
print(json.dumps(result, indent=2))
"
```

---

### 问题 3: 强制切换后无法回滚

**症状**: 强制切换后发现后续阶段失败

**解决**:
```bash
# 1. 查看强制切换记录
cat .rddf/state/event-log.jsonl | jq 'select(.type == "gate_forced")'

# 2. 返回上一阶段修复
skill_use("guide-arch")  # 返回 Arch 阶段

# 3. 修复缺失项
# 例如：创建 ADR
# 例如：创建 roadmap

# 4. 重新切换
```

---

## 下一步

- **查看 ADR-0007**: [ADR-0007-gate-mechanism.md](../adr/ADR-0007-gate-mechanism.md)
- **查看配置 Schema**: [v2-config-schema.md](../v2-config-schema.md)
- **查看 Loop 引擎指南**: [v2-loop-engine-guide.md](../v2-loop-engine-guide.md)

---

**文档维护者**: sisyphus  
**最后更新**: 2026-06-22  
**下次审查**: v2.0 发布后

