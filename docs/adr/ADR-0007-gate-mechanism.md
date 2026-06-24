# ADR-0007: 门控机制设计 (Gate Mechanism)

> **状态**: 已采纳
> **日期**: 2026-06-22
> **决策者**: sisyphus
> **依据**: ADR-0003 (三阶段架构), ADR-0004 (Loop 引擎核心设计)
> **调研来源**: Requesty Loop Engineering, Looper

## Context

spec-workflow v1.x 的阶段切换只有简单验证（如"active_changes.count >= 1"），缺乏严格的检查清单和失败处理机制。在 v2.0 的三阶段架构（arch → plan → ship）中，需要确保每个阶段完成时必须通过质量检查，才能进入下一阶段。

**核心问题**:
1. **质量保障缺失**: 阶段切换时没有检查清单，可能跳过关键步骤
2. **失败处理不明确**: 验证失败时没有清晰的修复建议
3. **缺乏灵活性**: 紧急情况无法灵活处理（如强制切换）
4. **不可观测**: 验证结果没有记录到事件流，难以调试

**设计目标**:
- 引入**门控机制 (Gate Mechanism)**，每个阶段定义检查清单
- 支持两级严重度（error 阻止切换，warning 只警告）
- 提供修复建议和用户选择（返回/查看/强制/中止）
- 所有检查结果记录到事件流

**约束**:
- 不能过度复杂化（保持检查清单简洁）
- 必须支持自定义扩展（插件机制）
- 必须向后兼容（v1.x 的简单验证继续有效）

## Decision

我们实现**门控机制 (Gate Mechanism)** 作为阶段切换的验证层：

### 1. 检查清单定义

每个阶段定义一组 Checks，全部通过才算完成：

```python
# skills/_lib/gate.py

class GateMechanism:
    """门控机制：验证通过才允许阶段切换"""
    
    GATES = {
        "arch_done": [
            Check(
                name="adr_exists",
                condition=lambda state: len(state.arch_side.adr.files) >= 1,
                message="至少需要 1 个 ADR 文档",
                severity="error"
            ),
            Check(
                name="roadmap_defined",
                condition=lambda state: state.arch_side.roadmap.exists,
                message="roadmap.md 必须存在",
                severity="error"
            ),
            Check(
                name="gap_analysis_complete",
                condition=lambda state: state.arch_side.architecture.pending_gaps == 0,
                message="所有架构差距分析已完成",
                severity="warning"
            )
        ],
        
        "plan_done": [
            Check(
                name="changes_committed",
                condition=lambda state: all(
                    c.status == "committed" for c in state.plan_side.active_changes
                ),
                message="所有 changes 必须已提交",
                severity="error"
            ),
            Check(
                name="artifacts_complete",
                condition=lambda state: all(
                    c.artifacts.get(".openspec.yaml") for c in state.plan_side.active_changes
                ),
                message="所有 changes 必须包含 .openspec.yaml",
                severity="error"
            ),
            Check(
                name="deps_analyzed",
                condition=lambda state: all(
                    c.deps_analysis for c in state.plan_side.active_changes
                ),
                message="依赖分析必须完成",
                severity="warning"
            )
        ],
        
        "ship_done": [
            Check(
                name="worktrees_empty",
                condition=lambda state: len(state.ship_side.worktrees) == 0,
                message="所有 worktrees 必须已清理",
                severity="error"
            ),
            Check(
                name="archive_empty",
                condition=lambda state: len(state.ship_side.pending_archive) == 0,
                message="所有 changes 必须已归档",
                severity="error"
            ),
            Check(
                name="tests_pass",
                condition=lambda state: self.verify_tests(state),
                message="所有测试必须通过",
                severity="error"
            )
        ]
    }
```

### 2. 严重度分级

| 严重度 | 行为 | 示例 |
|--------|------|------|
| **error** | 阻止阶段切换，必须修复 | ADR 不存在、artifacts 未完成 |
| **warning** | 显示警告，允许继续 | 差距分析未完成、依赖分析未完成 |

### 3. 门控验证流程

```python
def verify_transition(self, from_phase: str, to_phase: str, state: StateVector) -> GateResult:
    """验证阶段切换是否允许"""
    gate_name = f"{from_phase}_done"
    checks = self.GATES.get(gate_name, [])
    
    if not checks:
        return GateResult(passed=True, checks=[])  # 无门控
    
    # 执行所有检查
    results = []
    for check in checks:
        passed = check.condition(state)
        results.append(CheckResult(
            name=check.name,
            passed=passed,
            message=check.message,
            severity=check.severity
        ))
    
    # 判定是否通过
    errors = [r for r in results if not r.passed and r.severity == "error"]
    warnings = [r for r in results if not r.passed and r.severity == "warning"]
    
    passed = len(errors) == 0
    
    # 记录到事件流
    event_log.record("gate_check", {
        "from_phase": from_phase,
        "to_phase": to_phase,
        "passed": passed,
        "errors": [r.name for r in errors],
        "warnings": [r.name for r in warnings]
    })
    
    return GateResult(passed=passed, checks=results, errors=errors, warnings=warnings)
```

### 4. 门控失败处理

```python
def handle_gate_failure(self, result: GateResult, state: StateVector):
    """处理门控失败"""
    if result.passed:
        return  # 通过，继续
    
    # 显示失败详情
    print("❌ 门控验证失败，无法切换阶段")
    print(f"\n错误 ({len(result.errors)}):")
    for check in result.errors:
        print(f"  - {check.name}: {check.message}")
    
    if result.warnings:
        print(f"\n警告 ({len(result.warnings)}):")
        for check in result.warnings:
            print(f"  - {check.name}: {check.message}")
    
    # 提供修复建议
    print("\n建议修复操作:")
    for check in result.errors:
        suggestion = self.get_suggestion(check.name)
        print(f"  {suggestion}")
    
    # 用户选择
    choice = show_menu(
        title="门控失败",
        options=[
            "1. 返回上一阶段修复",
            "2. 查看详细信息",
            "3. 强制切换（不推荐）",
            "4. 中止"
        ]
    )
    
    if choice == 1:
        return "back"
    elif choice == 2:
        self.show_details(result)
        return "retry"
    elif choice == 3:
        # 记录强制切换
        event_log.record("force_transition", {
            "from_phase": result.from_phase,
            "to_phase": result.to_phase,
            "bypassed_errors": [c.name for c in result.errors]
        })
        return "force"
    else:
        return "abort"
```

### 5. 插件机制

支持用户添加自定义检查：

```python
# .spec-workflow/plugins/my_gate_checks.py

def custom_adr_compliance_check(state: StateVector) -> bool:
    """自定义检查：ADR 合规性"""
    for adr_file in state.arch_side.adr.files:
        content = Path(adr_file).read_text()
        if "## Context" not in content:
            return False
    return True

# 注册到门控
register_gate_check("arch_done", "adr_compliance", custom_adr_compliance_check)
```

**注册 API**:
```python
def register_gate_check(gate_name: str, check_name: str, condition: Callable):
    """注册自定义门控检查"""
    GateMechanism.CUSTOM_CHECKS.setdefault(gate_name, []).append(
        Check(name=check_name, condition=condition, severity="warning")
    )
```

### 6. 门控检查清单总览

| 阶段 | 检查项 | 严重度 | 说明 |
|------|--------|--------|------|
| **arch_done** | adr_exists | error | 至少 1 个 ADR |
| | roadmap_defined | error | roadmap.md 存在 |
| | gap_analysis_complete | warning | 差距分析完成 |
| **plan_done** | changes_committed | error | changes 已提交 |
| | artifacts_complete | error | .openspec.yaml 存在 |
| | deps_analyzed | warning | 依赖分析完成 |
| **ship_done** | worktrees_empty | error | worktrees 已清理 |
| | archive_empty | error | changes 已归档 |
| | tests_pass | error | 测试通过 |

### 影响范围

- **In Scope**:
  - 新增 `skills/_lib/gate.py` (门控机制实现)
  - 更新 `skills/guide-arch.md`、`skills/guide-plan.md`、`skills/guide-ship.md` (调用门控)
  - 更新 `skills/loop-engine.py` (阶段切换前调用门控)
  
- **Out Scope**:
  - 不改变现有阶段逻辑（只增加验证层）
  - 不改变状态文件格式

### 备选方案

| 备选 | 理由 |
|------|------|
| **无门控（保持现状）** | 拒绝：质量保障缺失，可能跳过关键步骤 |
| **只有 error（二元判定）** | 拒绝：缺乏灵活性，warning 场景无法处理 |
| **error + warning + 插件** | 接受：平衡严格性和灵活性 |

## Consequences

### 正面

- **质量保障**: 每个阶段完成必须通过检查清单，防止跳过关键步骤
- **清晰反馈**: 错误详情 + 修复议，用户知道如何修复
- **灵活处理**: 允许强制切换（需确认并记录），应对紧急情况
- **可观测性**: 所有检查结果记录到事件流，便于调试
- **可扩展**: 插件机制支持自定义检查

### 负面 / 风险

- **检查清单维护**: 新增检查项需要更新代码
  - **缓解**: v2.1 支持配置文件定义检查项
- **强制切换滥用**: 用户可能频繁强制切换
  - **缓解**: 强制切换记录到事件流，定期审计
- **插件安全风险**: 恶意插件可能绕过检查
  - **缓解**: 插件需要用户显式启用，记录到审计日志

### 后续待办

- [ ] 实现 `skills/_lib/gate.py` (门控机制核心)
- [ ] 在三阶段状态机中集成门控验证
- [ ] 添加门控单元测试（检查清单、失败处理、插件）
- [ ] 添加集成测试（阶段切换场景）
- [ ] 编写门控机制文档和插件开发指南
- [ ] v2.1 支持配置文件定义检查项

## References

- ADR-0003 — 三阶段架构 (arch → plan → ship)
- ADR-0004 — Loop 引擎核心设计
- Requesty Loop Engineering — 5 大构建块（Verify 阶段门控）
- Looper — 控制设计（刹车机制）
- `skills/_lib/gate.py` — 门控机制实现（待创建）

