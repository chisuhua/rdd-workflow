# plan-quality-and-validation

**优先级**: P0 | **来源**: 2026-08-04 session 复盘
**阶段**: default | **分类**: core-impl
**类型**: improvement

## 架构依据

本次会话中两个 plan 出现预期不符,执行阶段才暴露问题:
- `execute-gate-unified-regression`: plan 假设脚本只定义函数,实际测试要求直接 bash 执行 → 需补加 `BASH_SOURCE[0]` guard
- `python-failures-baseline`: plan Step 4 期望 "17 passed",实际 "16 passed + 1 cross-stage conflict" → 需 `RDDF_ALLOW_CROSS_STAGE_PARALLEL=yes`

plan 生成器缺乏 dry-run 验证和发布前检查清单,导致执行阶段返工。

## 范围

**In Scope**:
- plan 生成器加入 dry-run 步骤:用临时 fixture 验证 step 3 代码 + step 4 断言可行性
- `skills/rdd-workflow-writing-plans/SKILL.md` 加入发布前检查清单:
  - Step 5 脚本能否直接 bash 执行(需 `BASH_SOURCE[0]` guard)
  - expected 数字是否基于实际测试运行(非估算)
  - 涉及跨 stage 测试的 plan 加入 `RDDF_ALLOW_CROSS_STAGE_PARALLEL=yes` env var
  - worktree 源不在 sys.path 的 LSP 噪音容忍
- 脚本型 plan 模板自动生成 direct-execution guard

**Out of Scope**:
- 重写整个 rdd-workflow-writing-plans 技能
- 修改 execute 技能

## 设计

### Dry-run 验证

plan 生成器在输出前执行轻量级验证:
```python
# 临时 fixture 中验证 step 3 代码片段语法
import ast
ast.parse(step3_code)

# 对 expected 数字,运行现有 fixture 估算(collect-only)
pytest existing_fixtures --collect-only -q | wc -l
```

### 检查清单(写入 SKILL.md)

```markdown
## Plan Quality Checklist (生成 plan 前必检)

- [ ] 所有 `Run:` 命令在 dry-run 中能解析(无未定义命令)
- [ ] expected 数字基于实际测试运行(非估算)
- [ ] 涉及跨 stage 测试的 plan 加入 `RDDF_ALLOW_CROSS_STAGE_PARALLEL=yes` env var
- [ ] 脚本型 step 5 含 `BASH_SOURCE[0]` guard(如适用,允许独立 bash 执行)
- [ ] 不依赖主仓库实时状态(worktree 隔离考虑,优先用 fixture)
- [ ] 不假设未验证的 fixture 路径(优先使用 `$BATS_TEST_TMPDIR`)
- [ ] 测试 helper import 路径在 worktree 内有效(若使用 `from skills.xxx import`,确认 worktree 含完整源码树)
```

### 自动 Guard 生成

rdd-workflow-writing-plans 模板检测 step 5 含 bash 脚本且定义函数时,自动追加:
```bash
if [ "${BASH_SOURCE[0]:-$0}" = "${0}" ]; then
  defined_function "$@"
fi
```

## 影响

- **正向**: plan 准确性提升,减少执行阶段返工
- **正向**: expected 数字可靠,execute 阶段预期明确
- **风险**: dry-run 增加 plan 生成时间(预期 +10-30 秒)
- **兼容性**: 不破坏现有 plan 格式,仅增强生成逻辑

## 验收

- 5 个历史 plan 重生成,所有 expected 数字与实际测试运行匹配
- dry-run 失败时 plan 生成报错,不让用户接受不准的 plan
- 检查清单文档化,新 plan 默认通过
- 自动 guard 生成覆盖 100% 脚本型 step 5
- SKILL.md 的"Task 结构"示例更新为带 guard 的标准模板