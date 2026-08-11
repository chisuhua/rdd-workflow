# Improvement Proposal: 基于依赖分析的执行模式决策

## 元数据

| 字段 | 值 |
|------|---|
| 标题 | 基于 deps 分析的执行模式决策 |
| 优先级 | P1 |
| 类型 | 架构改进 |
| 影响范围 | guide-plan, guide-ship, deps |
| 提案时间 | 2026-07-24 |
| 来源 | 用户反馈 + 架构优化 |

## 为什么（Why）

### 当前问题

1. **决策时机滞后**：执行模式在 `guide-ship` Phase 1 才决定，但此时所有 changes 已提交，无法提前优化
2. **决策维度不足**：仅基于 "是否有其他 worktree" 和 "changes 数量"，忽略了依赖关系和文件冲突
3. **批量处理低效**：17 个 changes 全部创建 worktree，即使其中 5 个是小改动且无冲突

### 用户痛点

```bash
# 当前场景
fix-append-approved-output:
  - 文件数: 1
  - 冲突文件: 无
  - 依赖: 无
  - 改动量: 极小（1 行删除）

当前行为: 创建 worktree → 生成计划 → 执行 → 归档
期望行为: 直接在当前 session 轻量执行
浪费: worktree 创建时间 (~30s) + 上下文切换开销
```

## 做什么（What Changes）

### 核心思路

**在 plan 阶段的 deps 分析时就决定执行模式**，并将决策写入 `.plan-handoff.json`，`guide-ship` 直接读取使用。

### 决策维度

deps 分析能提供的关键信息：

| 信息类型 | 来源 | 对执行模式的影响 |
|---------|------|-----------------|
| **文件冲突** | deps-analysis.json → conflicts | 有冲突 → 强制 worktree |
| **依赖关系** | deps-analysis.json → dependency_graph | 有依赖 → 可能需要 worktree |
| **独立性** | deps-analysis.json → all_independent | 完全独立 → 可轻量模式 |
| **改动量** | design.md + tasks.md | 小改动 → 优先轻量模式 |

### 新的字段设计

在 `.rddf/state/deps-analysis.json` 中增加执行模式建议：

```json
{
  "version": 2,
  "timestamp": "2026-07-24T10:00:00Z",
  "total_changes": 17,
  "dependency_graph": {...},
  "conflicts": [],
  "all_independent": true,
  
  // 新增字段
  "execution_mode_recommendations": {
    "fix-append-approved-output": {
      "mode": "lightweight",
      "reason": "无文件冲突 + 单文件改动 + 独立无依赖",
      "confidence": "high",
      "details": {
        "file_count": 1,
        "has_conflicts": false,
        "has_dependencies": false,
        "is_independent": true,
        "change_size": "small"
      }
    },
    "parallel-wave-execution": {
      "mode": "worktree",
      "reason": "多文件改动 + 并行执行场景",
      "confidence": "high",
      "details": {
        "file_count": 8,
        "has_conflicts": false,
        "has_dependencies": true,
        "is_independent": false,
        "change_size": "large"
      }
    }
  },
  
  // 批量处理时的优化建议
  "batch_optimization": {
    "can_parallelize": true,
    "recommended_waves": [
      {
        "wave": 1,
        "changes": ["fix-append-approved-output", "fix-mark-approved-completed"],
        "mode": "lightweight",
        "reason": "全部小改动 + 无冲突 + 可批量处理"
      },
      {
        "wave": 2,
        "changes": ["parallel-wave-execution"],
        "mode": "worktree",
        "reason": "大改动 + 并行执行场景"
      }
    ]
  }
}
```

## 如何实现（How）

### Phase 1: deps 输出扩展

修改 `skills/deps/scripts/deps_output.py::render_markdown_report()`，增加执行模式分析：

```python
def analyze_execution_mode(change_name: str, project_root: str) -> dict:
    """分析单个 change 的执行模式建议"""
    
    # 1. 读取 design.md 和 tasks.md
    design_file = f"openspec/changes/{change_name}/design.md"
    tasks_file = f"openspec/changes/{change_name}/tasks.md"
    
    # 2. 统计文件数
    file_count = 0
    if os.path.exists(design_file):
        with open(design_file) as f:
            file_count = len([l for l in f if re.match(r'^- (Create|Modify|Delete):', l)])
    
    # 3. 统计任务数
    task_count = 0
    if os.path.exists(tasks_file):
        with open(tasks_file) as f:
            task_count = len([l for l in f if l.strip().startswith('- [ ]')])
    
    # 4. 检测风险关键词
    is_risky = False
    if os.path.exists(f"openspec/changes/{change_name}/proposal.md"):
        with open(f"openspec/changes/{change_name}/proposal.md") as f:
            content = f.read().lower()
            is_risky = any(kw in content for kw in 
                ['refactor', 'restructure', 'migration', 'breaking change', 'architecture'])
    
    # 5. 决策逻辑
    if is_risky:
        return {
            "mode": "worktree",
            "reason": "高风险操作（refactor/migration）",
            "confidence": "high",
            "details": {
                "file_count": file_count,
                "task_count": task_count,
                "is_risky": is_risky,
                "change_size": "large"
            }
        }
    elif file_count <= 2 and task_count <= 3:
        return {
            "mode": "lightweight",
            "reason": "小改动 + 低复杂度",
            "confidence": "high",
            "details": {
                "file_count": file_count,
                "task_count": task_count,
                "is_risky": is_risky,
                "change_size": "small"
            }
        }
    elif file_count <= 5 and task_count <= 6:
        return {
            "mode": "lightweight",  # 中等改动优先轻量
            "reason": "中等改动 + 可控范围",
            "confidence": "medium",
            "details": {
                "file_count": file_count,
                "task_count": task_count,
                "is_risky": is_risky,
                "change_size": "medium"
            }
        }
    else:
        return {
            "mode": "worktree",
            "reason": "大改动 + 需要隔离",
            "confidence": "high",
            "details": {
                "file_count": file_count,
                "task_count": task_count,
                "is_risky": is_risky,
                "change_size": "large"
            }
        }
```

### Phase 2: deps 输出写入 JSON

在 `deps` Step 5b 中写入结构化 JSON：

```python
def write_deps_analysis_json(project_root: str, analysis: dict):
    """写入 deps-analysis.json"""
    
    output_path = f"{project_root}/.rddf/state/deps-analysis.json"
    
    # 读取现有内容（如果存在）
    existing = {}
    if os.path.exists(output_path):
        with open(output_path) as f:
            existing = json.load(f)
    
    # 合并新字段
    existing.update({
        "version": 2,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        **analysis
    })
    
    # 原子写入
    with open(output_path, 'w') as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
```

### Phase 3: plan-handoff 扩展

在 `guide-plan` Phase 5 (plan-done) 时，将执行模式建议写入 `.plan-handoff.json`：

```json
{
  "version": 2,
  "plan_complete_at": "2026-07-24T10:00:00Z",
  "committed_changes": [...],
  
  // 新增字段
  "execution_mode_decisions": {
    "fix-append-approved-output": {
      "mode": "lightweight",
      "reason": "无文件冲突 + 单文件改动 + 独立无依赖",
      "confidence": "high"
    },
    ...
  },
  
  "batch_strategy": {
    "total_changes": 17,
    "lightweight_count": 5,
    "worktree_count": 12,
    "estimated_time_saved": "2-3 minutes"
  }
}
```

### Phase 4: guide-ship 使用决策

修改 `skills/guide-ship/scripts/ship_plan.sh`：

```bash
detect_execution_mode() {
  local project_root="$1"
  local change_name="$2"
  
  # 优先读取 plan-handoff.json 中的决策
  local handoff_file="$project_root/.rddf/state/.plan-handoff.json"
  
  if [ -f "$handoff_file" ]; then
    local mode
    mode=$(python3 -c "
import json, sys
with open('$handoff_file') as f:
    data = json.load(f)
    decisions = data.get('execution_mode_decisions', {})
    change = decisions.get('$change_name', {})
    print(change.get('mode', ''))
" 2>/dev/null)
    
    if [ -n "$mode" ]; then
      echo "$mode"
      local reason
      reason=$(python3 -c "
import json, sys
with open('$handoff_file') as f:
    data = json.load(f)
    decisions = data.get('execution_mode_decisions', {})
    change = decisions.get('$change_name', {})
    print(change.get('reason', ''))
" 2>/dev/null)
      echo "📋 Plan 阶段已决策: $mode ($reason)" >&2
      return 0
    fi
  fi
  
  # Fallback: 使用当前逻辑（向后兼容）
  # ... 现有的 detect_execution_mode 逻辑 ...
}
```

## 影响分析（Impact）

### 受影响文件

| 文件 | 改动类型 | 改动量 |
|------|---------|--------|
| `skills/deps/scripts/deps_output.py` | 新增函数 `analyze_execution_mode` | +80 行 |
| `skills/deps/scripts/deps_output.py` | 修改 `render_markdown_report` | +20 行 |
| `skills/_lib/schemas/deps_analysis_schema.json` | 版本 bump + 新字段 | +50 行 |
| `skills/guide-plan/scripts/plan_done_gate.sh` | 写入 execution_mode_decisions | +30 行 |
| `skills/guide-ship/scripts/ship_plan.sh` | 读取并使用决策 | +40 行 |
| `tests/unit/test_deps_output.py` | 新增测试 | +60 行 |

### 不受影响

- `guide-arch` — 不涉及执行模式
- `execute` — 不涉及模式决策
- `status` / `propose` / `roadmap` — 不涉及

## 关键场景（Key Scenarios）

### 场景 1: 单 change + 小改动

```
GIVEN 用户创建 change "fix-append-approved-output"
  AND design.md 显示 1 个文件修改
  AND tasks.md 显示 1 个任务
WHEN guide-plan 执行 deps 分析
THEN deps-analysis.json 记录 "mode": "lightweight"
  AND plan-handoff.json 记录执行模式决策
WHEN guide-ship 读取决策
THEN 使用轻量模式，跳过 worktree 创建
  AND 节省 30s 创建时间
```

### 场景 2: 批量处理 + 混合改动

```
GIVEN 用户有 17 个 changes
  AND 其中 5 个是小改动（1-2 文件）
  AND 其中 12 个是大改动（5+ 文件）
WHEN guide-plan 执行 deps 分析
THEN deps-analysis.json 记录每个 change 的执行模式
  AND batch_strategy 显示优化建议
WHEN guide-ship 批量处理
THEN 5 个小改动使用轻量模式
  AND 12 个大改动使用 worktree 模式
  AND 总时间节省约 2-3 分钟
```

### 场景 3: 文件冲突检测

```
GIVEN change A 修改 "skills/_lib/state.sh"
  AND change B 也修改 "skills/_lib/state.sh"
WHEN guide-plan 执行 deps 分析
THEN deps-analysis.json 记录冲突
  AND execution_mode_recommendations 强制两个 change 都使用 worktree
  AND reason 说明 "文件冲突需要隔离"
```

### 场景 4: 向后兼容

```
GIVEN plan-handoff.json 不存在或版本为 1
  AND deps-analysis.json 不包含 execution_mode_recommendations
WHEN guide-ship 调用 detect_execution_mode
THEN fallback 到当前逻辑
  AND 不影响现有行为
```

## 验收标准（Acceptance Criteria）

### 必须满足

- [ ] deps 阶段正确分析每个 change 的执行模式
- [ ] deps-analysis.json 包含 execution_mode_recommendations 字段
- [ ] plan-handoff.json 包含 execution_mode_decisions 字段
- [ ] guide-ship 正确读取并使用决策
- [ ] 小改动（≤2 文件，≤3 任务）默认使用轻量模式
- [ ] 大改动（≥6 文件或 ≥7 任务或高风险关键词）强制 worktree
- [ ] 文件冲突时强制 worktree
- [ ] 向后兼容（无决策时 fallback 到当前逻辑）

### 应该满足

- [ ] 批量处理时显示时间节省预估
- [ ] 用户可以手动覆盖决策（环境变量或命令行参数）
- [ ] 日志清晰说明决策原因

### 可以满足

- [ ] deps 报告中增加执行模式可视化
- [ ] guide-plan 输出中显示执行模式统计

## 测试计划

### 单元测试

```python
# tests/unit/test_deps_output.py

def test_analyze_execution_mode_small_change():
    """小改动应推荐 lightweight"""
    result = analyze_execution_mode("fix-small-typo", project_root)
    assert result["mode"] == "lightweight"
    assert result["details"]["change_size"] == "small"

def test_analyze_execution_mode_large_change():
    """大改动应推荐 worktree"""
    result = analyze_execution_mode("refactor-architecture", project_root)
    assert result["mode"] == "worktree"
    assert result["details"]["change_size"] == "large"

def test_analyze_execution_mode_risky_keywords():
    """包含 refactor/migration 关键词应强制 worktree"""
    result = analyze_execution_mode("migration-to-v3", project_root)
    assert result["mode"] == "worktree"
    assert result["details"]["is_risky"] == True
```

### 集成测试

```bash
# tests/integration/test_execution_mode_decision.bats

@test "guide-plan: deps 分析写入执行模式决策" {
    # 创建小改动 change
    create_test_change "test-small" --files 1 --tasks 1
    
    # 运行 guide-plan
    run skill_use("guide-plan")
    [ "$status" -eq 0 ]
    
    # 验证 deps-analysis.json
    run jq -r '.execution_mode_recommendations.test-small.mode' .rddf/state/deps-analysis.json
    [ "$output" = "lightweight" ]
    
    # 验证 plan-handoff.json
    run jq -r '.execution_mode_decisions.test-small.mode' .rddf/state/.plan-handoff.json
    [ "$output" = "lightweight" ]
}

@test "guide-ship: 读取执行模式决策" {
    # 准备 plan-handoff.json
    echo '{"version":2,"execution_mode_decisions":{"test-123":{"mode":"lightweight"}}}' \
        > .rddf/state/.plan-handoff.json
    
    # 调用 detect_execution_mode
    source skills/guide-ship/scripts/ship_plan.sh
    run detect_execution_mode "$PROJECT_ROOT" "test-123"
    
    [ "$output" = "lightweight" ]
}
```

## 风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 决策不准确导致高风险改动未隔离 | 高 | 低 | 保守阈值 + 用户手动覆盖 |
| deps-analysis.json 格式变更导致兼容性问题 | 中 | 低 | 版本号 + 向后兼容 fallback |
| 批量处理时轻量模式导致文件冲突 | 高 | 中 | deps 冲突检测强制 worktree |
| 用户不理解自动决策 | 低 | 中 | 清晰日志 + 文档说明 |

## 实施计划

### Wave 1: 核心功能（P1）

1. `deps_output.py` 新增 `analyze_execution_mode()` 函数
2. `deps_output.py` 写入 `execution_mode_recommendations` 到 JSON
3. `plan_done_gate.sh` 写入 `execution_mode_decisions` 到 handoff
4. `ship_plan.sh` 读取并使用决策
5. 单元测试 + 集成测试

**预计时间**: 2-3 小时  
**预期收益**: 每个小改动节省 30s，批量处理节省 2-3 分钟

### Wave 2: 优化与增强（P2）

1. 批量处理优化策略（wave 分组）
2. 用户手动覆盖机制
3. 日志与可视化改进
4. 文档更新

**预计时间**: 1-2 小时

### Wave 3: 监控与调优（P3）

1. 收集实际使用数据
2. 调整阈值参数
3. 性能优化

**预计时间**: 持续进行

## 参考资料

- ADR-0003: 三阶段架构（arch → plan → ship）
- ADR-0022: manual_deps 字段
- `skills/deps/SKILL.md`: deps 分析流程
- `skills/guide-plan/SKILL.md`: plan 阶段状态机
- `skills/guide-ship/SKILL.md`: ship 阶段状态机
- `skills/_lib/schemas/deps_analysis_schema.json`: deps 输出 schema

## 附录：决策树可视化

```
                      deps 分析
                         │
          ┌──────────────┴──────────────┐
          │                             │
    文件冲突检测                    改动量评估
          │                             │
    ┌─────┴─────┐              ┌────────┴────────┐
    │           │              │                 │
  有冲突     无冲突          小改动           大改动
    │           │              │                 │
  worktree   继续判断      lightweight       worktree
              │
              │
        依赖关系检测
              │
        ┌─────┴─────┐
        │           │
     有依赖      无依赖
        │           │
    worktree   lightweight
```
