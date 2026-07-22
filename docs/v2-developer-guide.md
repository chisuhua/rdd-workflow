# rdd-workflow v2.0 开发者指南

> **版本**: 2.0.0  
> **日期**: 2026-06-22  
> **目标读者**: 想要扩展 rdd-workflow 的开发者

---

## 📋 目录

- [概述](#概述)
- [扩展 Detectors](#扩展-detectors)
- [扩展 Actions](#扩展-actions)
- [自定义门控](#自定义门控)
- [添加验证脚本](#添加验证脚本)
- [自定义 Human-in-Loop 节点](#自定义-human-in-loop-节点)
- [开发工作流](#开发工作流)
- [测试指南](#测试指南)

---

## 概述

rdd-workflow v2.0 是**高度可扩展**的架构，允许开发者自定义：

| 扩展点 | 说明 | 文件位置 |
|--------|------|---------|
| **Detectors** | 状态检测器 | `.rdd-workflow/detectors/` |
| **Actions** | 执行动作 | `.rdd-workflow/actions/` |
| **Gates** | 门控检查 | `.rdd-workflow/gates/` |
| **Verifiers** | 验证脚本 | `.rdd-workflow/verifiers/` |
| **Human-in-Loop** | 人工节点 | `.rdd-workflow/human_nodes/` |

---

## 扩展 Detectors

Detectors 用于检测当前状态，为 Plan 阶段提供输入。

### Detector 模板

```python
"""
自定义 Detector: 检测待处理 changes
"""

from state_vector import StateVector
from typing import Dict

class PendingChangesDetector:
    """待处理 changes 检测器"""
    
    def __init__(self, state_vector: StateVector):
        self.sv = state_vector
    
    def detect(self) -> Dict:
        """
        检测待处理 changes
        
        Returns:
            {
                "detected": bool,
                "count": int,
                "changes": list,
                "message": str
            }
        """
        state = self.sv.load()
        changes = state.get("plan_side", {}).get("active_changes", [])
        
        return {
            "detected": len(changes) > 0,
            "count": len(changes),
            "changes": changes,
            "message": f"Found {len(changes)} pending changes"
        }

# 使用示例
sv = StateVector()
detector = PendingChangesDetector(sv)
result = detector.detect()
print(result["message"])  # "Found 2 pending changes"
```

### 注册 Detector

在 `.rddf.json` 中注册：

```json
{
  "detectors": {
    "custom": [
      {
        "name": "pending_changes",
        "class": "PendingChangesDetector",
        "script": ".rdd-workflow/detectors/pending_changes.py"
      }
    ]
  }
}
```

### 内置 Detectors

| Detector | 说明 | 返回 |
|---------|------|------|
| `ArchDetector` | 检测 Arch 阶段状态 | ADR 数量、roadmap 状态 |
| `PlanDetector` | 检测 Plan 阶段状态 | active changes、依赖图 |
| `ShipDetector` | 检测 Ship 阶段状态 | worktrees、archive 状态 |
| `GateDetector` | 检测门控状态 | 门控检查结果 |

---

## 扩展 Actions

Actions 用于执行具体操作，被 Plan 阶段调用。

### Action 模板

```python
"""
自定义 Action: 创建 ADR
"""

from state_vector import StateVector
from event_log import EventLog
from typing import Dict

class CreateADRAction:
    """创建 ADR 动作"""
    
    def __init__(self, state_vector: StateVector, event_log: EventLog):
        self.sv = state_vector
        self.el = event_log
    
    def execute(self, params: Dict) -> Dict:
        """
        执行创建 ADR 动作
        
        Args:
            params: {
                "title": str,
                "status": str,
                "content": str
            }
        
        Returns:
            {
                "success": bool,
                "adr_id": str,
                "message": str
            }
        """
        # 1. 生成 ADR ID
        state = self.sv.load()
        adr_count = len(state.get("arch_side", {}).get("adr", []))
        adr_id = f"ADR-{adr_count + 1:04d}"
        
        # 2. 创建 ADR 文件
        adr_content = params["content"]
        adr_path = f"docs/adr/{adr_id}-{params['title'].lower().replace(' ', '-')}.md"
        
        with open(adr_path, 'w') as f:
            f.write(adr_content)
        
        # 3. 更新状态向量
        with self.sv.lock():
            state = self.sv.load()
            state["arch_side"]["adr"].append({
                "id": adr_id,
                "title": params["title"],
                "status": params["status"],
                "path": adr_path
            })
            self.sv.save(state)
        
        # 4. 记录事件
        self.el.append("adr_created", {
            "adr_id": adr_id,
            "title": params["title"],
            "status": params["status"]
        })
        
        return {
            "success": True,
            "adr_id": adr_id,
            "message": f"Created {adr_id}: {params['title']}"
        }

# 使用示例
sv = StateVector()
el = EventLog()
action = CreateADRAction(sv, el)

result = action.execute({
    "title": "Multi-session management",
    "status": "proposed",
    "content": "# ADR-0010: Multi-session management\n\n..."
})
print(result["message"])  # "Created ADR-0010: Multi-session management"
```

### 注册 Action

在 `.rddf.json` 中注册：

```json
{
  "actions": {
    "custom": [
      {
        "name": "create_adr",
        "class": "CreateADRAction",
        "script": ".rdd-workflow/actions/create_adr.py"
      }
    ]
  }
}
```

### 内置 Actions

| Action | 说明 | 参数 |
|--------|------|------|
| `CreateADRAction` | 创建 ADR | title, status, content |
| `UpdateRoadmapAction` | 更新 roadmap | phases, changes, metrics |
| `CreateChangeAction` | 创建 change | title, description, artifacts |
| `CreateWorktreeAction` | 创建 worktree | change, branch, path |
| `ExecuteWorkUnitAction` | 执行 work unit | worktree, unit, plan |
| `ArchiveChangeAction` | 归档 change | change, archive_path |

---

## 自定义门控

门控是阶段切换前的质量检查点。

### 门控模板

```python
"""
自定义门控: 代码质量检查
"""

from state_vector import StateVector
from typing import Dict

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
    
    # 检查 1: 代码质量分数
    quality_score = calculate_quality_score()
    checks.append({
        "name": "code_quality",
        "passed": quality_score >= 0.8,
        "severity": "warning",
        "message": f"Quality score: {quality_score:.2f} (expected ≥ 0.8)"
    })
    
    # 检查 2: 测试覆盖率
    test_coverage = calculate_test_coverage()
    checks.append({
        "name": "test_coverage",
        "passed": test_coverage >= 0.7,
        "severity": "warning",
        "message": f"Test coverage: {test_coverage:.2f} (expected ≥ 0.7)"
    })
    
    # 检查 3: 无安全漏洞
    security_issues = scan_security_issues()
    checks.append({
        "name": "no_security_issues",
        "passed": len(security_issues) == 0,
        "severity": "error",
        "message": f"Found {len(security_issues)} security issues" if security_issues else "No security issues"
    })
    
    # 计算是否通过
    passed = all(c["passed"] or c["severity"] == "warning" for c in checks)
    
    return {
        "passed": passed,
        "checks": checks
    }

def calculate_quality_score() -> float:
    """计算代码质量分数"""
    # 实现质量评分逻辑
    return 0.85

def calculate_test_coverage() -> float:
    """计算测试覆盖率"""
    # 实现测试覆盖率计算
    return 0.78

def scan_security_issues() -> list:
    """扫描安全漏洞"""
    # 实现安全扫描
    return []
```

### 注册自定义门控

在 `.rddf.json` 中注册：

```json
{
  "gates": {
    "ship_done": [
      {
        "name": "code_quality_check",
        "script": ".rdd-workflow/gates/code_quality.py",
        "severity": "warning"
      }
    ]
  }
}
```

---

## 添加验证脚本

验证脚本用于 Human-in-Loop 节点的自动验证。

### 验证脚本模板

```python
"""
自定义验证脚本: 检查 change 格式
"""

import sys
import json
from pathlib import Path

def verify(change_path: str) -> dict:
    """
    验证 change 格式
    
    Args:
        change_path: change 目录路径
    
    Returns:
        {
            "passed": bool,
            "message": str,
            "details": dict
        }
    """
    details = {}
    
    # 检查 1: .openspec.yaml 存在
    yaml_path = Path(change_path) / ".openspec.yaml"
    if not yaml_path.exists():
        return {
            "passed": False,
            "message": ".openspec.yaml not found",
            "details": {"file_exists": False}
        }
    
    details["file_exists"] = True
    
    # 检查 2: YAML 格式正确
    try:
        import yaml
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        
        required_fields = ["version", "name", "description"]
        missing = [f for f in required_fields if f not in data]
        
        if missing:
            return {
                "passed": False,
                "message": f"Missing fields: {', '.join(missing)}",
                "details": {"missing_fields": missing}
            }
        
        details["fields_complete"] = True
    
    except Exception as e:
        return {
            "passed": False,
            "message": f"YAML parse error: {str(e)}",
            "details": {"parse_error": str(e)}
        }
    
    # 检查 3: proposal.md 存在
    proposal_path = Path(change_path) / "proposal.md"
    if not proposal_path.exists():
        return {
            "passed": False,
            "message": "proposal.md not found",
            "details": {"proposal_exists": False}
        }
    
    details["proposal_exists"] = True
    
    # 检查 4: design.md 存在
    design_path = Path(change_path) / "design.md"
    if not design_path.exists():
        return {
            "passed": False,
            "message": "design.md not found",
            "details": {"design_exists": False}
        }
    
    details["design_exists"] = True
    
    # 检查 5: tasks.md 存在
    tasks_path = Path(change_path) / "tasks.md"
    if not tasks_path.exists():
        return {
            "passed": False,
            "message": "tasks.md not found",
            "details": {"tasks_exists": False}
        }
    
    details["tasks_exists"] = True
    
    return {
        "passed": True,
        "message": "All checks passed",
        "details": details
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_change.py <change_path>")
        sys.exit(1)
    
    change_path = sys.argv[1]
    result = verify(change_path)
    
    print(json.dumps(result, indent=2))
    
    if not result["passed"]:
        sys.exit(1)
```

### 注册验证脚本

在 Human-in-Loop 节点配置中指定：

```json
{
  "interaction": {
    "human_in_loop_nodes": [
      {
        "node": "plan.change_select",
        "verification_mode": "script",
        "script": ".rdd-workflow/verifiers/verify_change.py"
      }
    ]
  }
}
```

---

## 自定义 Human-in-Loop 节点

### Human-in-Loop 节点模板

```python
"""
自定义 Human-in-Loop 节点: 架构评审
"""

from state_vector import StateVector
from event_log import EventLog
from typing import Dict

class ArchitectureReviewNode:
    """架构评审节点"""
    
    def __init__(self, state_vector: StateVector, event_log: EventLog):
        self.sv = state_vector
        self.el = event_log
    
    def execute(self, context: Dict) -> Dict:
        """
        执行架构评审
        
        Args:
            context: {
                "change": str,
                "adr_id": str,
                "review_criteria": list
            }
        
        Returns:
            {
                "approved": bool,
                "feedback": str,
                "requires_changes": bool
            }
        """
        # 1. 加载 ADR
        state = self.sv.load()
        adr = None
        for a in state.get("arch_side", {}).get("adr", []):
            if a["id"] == context["adr_id"]:
                adr = a
                break
        
        if not adr:
            return {
                "approved": False,
                "feedback": f"ADR {context['adr_id']} not found",
                "requires_changes": False
            }
        
        # 2. 显示评审信息
        print(f"\n📋 Architecture Review: {adr['title']}")
        print(f"Change: {context['change']}")
        print(f"Review criteria:")
        for criterion in context["review_criteria"]:
            print(f"  - {criterion}")
        
        # 3. 请求人工确认
        print("\n评审标准:")
        print("  1. 架构是否符合现有设计？")
        print("  2. 是否引入不必要的复杂性？")
        print("  3. 是否有更好的替代方案？")
        
        approval = input("\n是否批准此架构决策？[y/n]: ").strip().lower()
        
        if approval == "y":
            # 4. 记录事件
            self.el.append("architecture_reviewed", {
                "adr_id": context["adr_id"],
                "change": context["change"],
                "approved": True
            })
            
            return {
                "approved": True,
                "feedback": "Architecture approved",
                "requires_changes": False
            }
        else:
            # 5. 请求反馈
            feedback = input("\n请提供反馈意见: ").strip()
            
            # 6. 记录事件
            self.el.append("architecture_reviewed", {
                "adr_id": context["adr_id"],
                "change": context["change"],
                "approved": False,
                "feedback": feedback
            })
            
            return {
                "approved": False,
                "feedback": feedback,
                "requires_changes": True
            }

# 使用示例
sv = StateVector()
el = EventLog()
node = ArchitectureReviewNode(sv, el)

result = node.execute({
    "change": "add-auth",
    "adr_id": "ADR-0010",
    "review_criteria": [
        "符合现有认证架构",
        "不引入额外复杂性",
        "支持多因素认证"
    ]
})
```

### 注册 Human-in-Loop 节点

在 `.rddf.json` 中注册：

```json
{
  "interaction": {
    "human_in_loop_nodes": [
      {
        "node": "arch.architecture_review",
        "class": "ArchitectureReviewNode",
        "script": ".rdd-workflow/human_nodes/architecture_review.py",
        "verification_mode": "human",
        "skip_if": "never"
      }
    ]
  }
}
```

---

## 开发工作流

### 1. 创建扩展目录

```bash
mkdir -p .rdd-workflow/{detectors,actions,gates,verifiers,human_nodes}
```

### 2. 编写扩展代码

```bash
# 创建自定义 detector
cat > .rdd-workflow/detectors/pending_changes.py << 'EOF'
from state_vector import StateVector

class PendingChangesDetector:
    def __init__(self, state_vector):
        self.sv = state_vector
    
    def detect(self):
        state = self.sv.load()
        changes = state.get("plan_side", {}).get("active_changes", [])
        return {
            "detected": len(changes) > 0,
            "count": len(changes),
            "changes": changes
        }
EOF
```

### 3. 注册扩展

```bash
# 更新 .rddf.json
cat > .rddf.json << 'EOF'
{
  "version": "2.0",
  "detectors": {
    "custom": [
      {
        "name": "pending_changes",
        "class": "PendingChangesDetector",
        "script": ".rdd-workflow/detectors/pending_changes.py"
      }
    ]
  }
}
EOF
```

### 4. 测试扩展

```bash
# 测试 detector
python3 -c "
from state_vector import StateVector
from .rdd-workflow.detectors.pending_changes import PendingChangesDetector

sv = StateVector()
detector = PendingChangesDetector(sv)
result = detector.detect()
print(result)
"
```

### 5. 提交扩展

```bash
git add .rdd-workflow/
git commit -m "Add custom pending_changes detector"
```

---

## 测试指南

### 单元测试

```python
"""
测试自定义 Detector
"""

import unittest
from unittest.mock import Mock
from .rdd-workflow.detectors.pending_changes import PendingChangesDetector

class TestPendingChangesDetector(unittest.TestCase):
    
    def test_detect_no_changes(self):
        """测试无 changes 场景"""
        sv = Mock()
        sv.load.return_value = {"plan_side": {"active_changes": []}}
        
        detector = PendingChangesDetector(sv)
        result = detector.detect()
        
        self.assertFalse(result["detected"])
        self.assertEqual(result["count"], 0)
    
    def test_detect_with_changes(self):
        """测试有 changes 场景"""
        sv = Mock()
        sv.load.return_value = {
            "plan_side": {
                "active_changes": [
                    {"id": "add-auth"},
                    {"id": "add-user-profile"}
                ]
            }
        }
        
        detector = PendingChangesDetector(sv)
        result = detector.detect()
        
        self.assertTrue(result["detected"])
        self.assertEqual(result["count"], 2)
        self.assertEqual(len(result["changes"]), 2)

if __name__ == "__main__":
    unittest.main()
```

### 集成测试

```python
"""
集成测试: 完整 Loop 流程
"""

import unittest
from loop_engine import LoopEngine
from state_vector import StateVector
from event_log import EventLog

class TestLoopEngineIntegration(unittest.TestCase):
    
    def setUp(self):
        """测试前准备"""
        self.sv = StateVector(".rddf/state/test-state-vector.json")
        self.el = EventLog(".rddf/state/test-event-log.jsonl")
        
        # 初始化状态
        self.sv.reset()
        self.el.clear()
    
    def tearDown(self):
        """测试后清理"""
        import os
        if os.path.exists(".rddf/state/test-state-vector.json"):
            os.remove(".rddf/state/test-state-vector.json")
        if os.path.exists(".rddf/state/test-event-log.jsonl"):
            os.remove(".rddf/state/test-event-log.jsonl")
    
    def test_complete_loop(self):
        """测试完整 Loop 流程"""
        config = {
            "interaction": {"mode": "loop"},
            "loop": {"max_iterations": 10, "max_retries": 1}
        }
        
        engine = LoopEngine(config)
        result = engine.run("complete all pending changes")
        
        self.assertEqual(result["status"], "success")
        self.assertGreater(result["iterations"], 0)

if __name__ == "__main__":
    unittest.main()
```

### 运行测试

```bash
# 运行单元测试
python3 -m pytest tests/unit/ -v

# 运行集成测试
python3 -m pytest tests/integration/ -v

# 运行所有测试
python3 -m pytest tests/ -v

# 运行特定测试
python3 -m pytest tests/unit/test_detector.py -v
```

---

## 最佳实践

### 1. 遵循单一职责原则

每个 Detector/Action/Gate 只负责一个功能：

```python
# ✅ 好的设计
class PendingChangesDetector:
    def detect(self):
        # 只检测 changes
        pass

class ADRCountDetector:
    def detect(self):
        # 只检测 ADR 数量
        pass

# ❌ 不好的设计
class EverythingDetector:
    def detect(self):
        # 检测所有东西（职责不清）
        pass
```

---

### 2. 提供清晰的错误消息

```python
# ✅ 好的错误消息
return {
    "passed": False,
    "message": "ADR count is 0, expected ≥ 1. Run 'skill_use(\"guide-arch\")' to create an ADR."
}

# ❌ 不好的错误消息
return {
    "passed": False,
    "message": "Failed"
}
```

---

### 3. 使用类型提示

```python
from typing import Dict, List, Optional

class CreateADRAction:
    def execute(self, params: Dict[str, str]) -> Dict[str, any]:
        # 类型提示提高代码可读性
        pass
```

---

### 4. 编写文档字符串

```python
def check(state: dict) -> dict:
    """
    执行门控检查
    
    Args:
        state: 当前状态向量
    
    Returns:
        检查结果字典，包含 passed 和 checks 字段
    
    Raises:
        ValueError: 如果 state 格式不正确
    """
    pass
```

---

### 5. 添加日志

```python
import logging

logger = logging.getLogger(__name__)

class CreateADRAction:
    def execute(self, params: Dict) -> Dict:
        logger.info(f"Creating ADR: {params['title']}")
        
        # ... 执行逻辑 ...
        
        logger.info(f"ADR created: {adr_id}")
        return result
```

---

## 下一步

- **查看 API 参考**: [v2-api-reference.md](v2-api-reference.md)
- **查看配置 Schema**: [v2-config-schema.md](v2-config-schema.md)
- **查看 ADR 文档**: `docs/adr/` 目录

---

**文档维护者**: sisyphus  
**最后更新**: 2026-06-22  
**下次审查**: v2.0 发布后

