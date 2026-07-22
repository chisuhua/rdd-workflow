# ADR-0014: Add execute-review phase and debt-reflow mechanism to three-phase workflow

> **v3.0.0 note**: Originally authored as "spec-workflow". Renamed to "rdd-workflow" in v3.0.0 (2026-07-22). See ADR-0023.


> **状态**: 待定
> **日期**: 2026-07-08
> **决策者**: sisyphus

## Context

rdd-workflow v2.0 三阶段架构（ADR-0003）定义了 `arch → plan → ship` 的严格前向流转。但在生产使用中发现两个结构性缺口：

### 缺口 1：execute 后产生的债务无回流路径

`guide-ship` Phase 2 (execute) 在 worktree 内执行实施计划。执行过程中常发现三类新债务：

| 债务类型 | 示例 | 当前处理 |
|---------|------|---------|
| 范围内债务 | 新 API 的测试覆盖 incomplete | 手动追加到 tasks.md，无自动化 |
| 旁效应债务 | 修 A 文件发现 B 文件有遗留 TODO | 无记录机制，丢失或靠人工记忆 |
| 架构漂移 | 执行结果偏离 ADR 定义的目标架构 | 无检测机制，漂移积累 |

当前唯一回流路径是 `guide-ship` ship-done 的 "回到 spec 端" 手动选项（`guide-ship.md:860-870`），但它是全量重建——用户需要从头跑 `guide-plan → scan → propose → deps`。新产生的债务 change 对已完成的 deps 分析完全不可见。

### 缺口 2：deeps 分析运行于 execute 之前，无法感知执行后信息

`deps.md:158-257` 三轴分析（文件冲突 + ADR 引用 + 接口依赖）在 plan 阶段执行，此时无实现、无代码 diff、无测试回归信息。execute 完成后的信息（新增 TODO 标记、回归测试失败、文件变更范围扩大）都在 deps 的视野之外。

### 相关 ADR/文档

- ADR-0003 §2.1: 三阶段架构定义，ship 端 5 阶段（plan → execute → archive → cleanup → ship-done）
- ADR-0007 §3.1: 门控机制，三个过渡点（arch_done / plan_done / ship_done）
- `gate.py:112-128`: 9 个默认检查，分布在三类过渡点
- `guide-ship.md:842-887`: ship-done 的退出判定
- `proposal-suggestions-format.md:18-44`: 8 字段 schema（name, priority, source, status, phase, category, description, effort）
- 前次分析：22 个流程缺陷 + 5 个检查项归属判定

### 约束

- 不改变 `arch → plan → ship` 三阶段核心流程
- 不要求每个 execute 都必须 review（review 可跳过）
- 新产生的 debt change 不应阻塞当前 change 的 archive（debt change 可 deferred）
- 向后兼容：现有 proposal-suggestions.md 消费者不受影响

## Decision

我们在 `guide-ship` Phase 2 (execute) 和 Phase 3 (archive) 之间插入 **Phase 2.5: review** 阶段，并提供完整的债务回流机制。

### 修改后的流程

```
guide-ship (修改后):
  Phase 1: plan (创建 worktree + 生成计划)
  Phase 2: execute (在 worktree 内执行任务)
  Phase 2.5: review (✨ 新增 — 执行后审查)
      │
      ├── 范围內债务 → 追加 tasks.md → 返回 execute 继续执行
      ├── 旁效应债务 → 创建新 change → proposal-suggestions.md (type=debt)
      │                            → (可选) 重新 deps
      ├── 架构漂移   → 回注 guide-arch → 生成差距分析
      └── 无债务     → 直接进入 archive (默认)
  Phase 3: archive
  Phase 4: cleanup
  Phase 5: ship-done
```

### 决策 1：Phase 2.5 插入在 execute 和 archive 之间

**选择理由**：这是唯一有代码可 review 的时间点——execute 完成了，tasks.md 有结果，git diff 可算，测试结果可知。在 deps 之前 review 没有代码可看，在 archive 之后回退成本太高。

### 决策 2：债务按类型分流，不混用

| 债务类型 | 机制 | 是否需要 re-deps |
|---------|------|----------------|
| 范围内债务（当前 change 的 scope 内不完整） | 追加到当前 change 的 tasks.md | ❌ 不需要，当前 change 的 scope 未变 |
| 旁效应债务（独立的新 change） | 创建新 change + 追加到 proposal-suggestions.md | ⚠️ 检查文件冲突后决定 |
| 架构漂移（ADR 目标 vs 实现偏离） | 回注 guide-arch → 生成 drift-analysis.md | ❌ 不需要，arch 阶段独立处理 |

**选择理由**：债务的归属决定其生命周期。把"范围内测试不完整"和"B 文件的遗留 TODO"混为一谈会让 deps 分析产生虚假冲突。

### 决策 3：旁效应债务的 deps 重新分析由文件冲突驱动

```
if new_change.files ∩ archived_changed_files ≠ ∅:
    → 必须重新 deps (依赖关系变了)
else:
    → 跳过 deps (debt change 可 deferred 到下次 sprint)
```

**选择理由**：deps 分析的核心价值是检测文件冲突和接口依赖。新 change 只改未变更的文件，就不会与已完成的 change 冲突。按 change type 判断（"type=debt 所以跳过 deps"）是伪规则——关键看文件。

### 决策 4：proposal-suggestions.md 增加 `type` 字段

```json
{
  "name": "cleanup-fix-ns-pollution-debt",
  "type": "debt",        // ✨ 新增: "functional" | "debt" | "refactor"
  "priority": "P2",
  "source": "execute review: fix-ns-pollution",
  "status": "待创建",
  ...
}
```

**选择理由**：
- 区分债务和功能 change，用户可按 type 过滤
- 向后兼容：消费者用 `.get('type', 'functional')` 默认值
- `scan-state.sh` 可基于 debt 计数生成新推荐分支

### 决策 5：review 门控作为 ship_done 的新 check

通过 `gate.py` 的 `register_gate_check()` 注册 `review_debt_recorder` 检查：

```python
Check("review_debt_recorder", _check_review_debt_recorder,
      "未记录的 execute 后债务", "请在 Phase 2.5 审查债务或选择跳过", "warning")
```

作为 warning（不阻断 archive），因为 debt 可 deferred 到下次 sprint。用户可选择"跳过 review"进入 archive。

### 影响范围

- **In Scope**:
  - `skills/guide-ship.md` Phase 2.5 新增（review phase）
  - `docs/proposal-suggestions-format.md` 加 `type` 字段
  - `skills/propose.md` Phase 2 分类分配逻辑
  - `skills/_lib/gate.py` ship_done 新增 check
  - `skills/_lib/iteration.py` status 新增 "review"
- **Out Scope**:
  - 架构漂移检测的自动实现（mend-adr 模式属于 arch 阶段，留待后续 ADR）
  - CI 时的基线快照（属于外部工具 Erode/SonarQube 范围）

### 备选方案

| 备选 | 理由 |
|------|------|
| A: review 放在 deps 之后、execute 之前 | 没有实现可验证——review 等价于重读提案。拒绝。 |
| B: review 放在 archive 之后 | 回退成本高，需要在 main branch 上做 revert。拒绝。 |
| C: 不区分债务类型，统一创建新 change | 范围內债务（测试不完整）不应单独成为 change——它和原始 change 同生命周期。拒绝。 |
| D: 自动创建 change，不经用户确认 | 债务是否需要立即修复是人工判断。自动化会制造噪音。拒绝。 |

## Consequences

### 正面

- **债务可见**：execute 产生的所有新 TODO/回归/不完整项被自动采集并分类记录
- **安全回流**：旁效应债务重新走 deps 分析（如需要），不掉入依赖黑洞
- **不阻塞 archive**：debt change 可标记为 deferred，当前 change 正常归档
- **向后兼容**：已有 proposal-suggestions 消费者不受影响（`.get('type', 'functional')`）
- **可扩展**：Phase 2.5 的交互菜单支持未来增加 more sophisticated 债务检测器

### 负面 / 风险

- **增加了一个用户交互步骤**：每个 execute 完成后需要一个 review 交互。缓解：默认选项 4 是"跳过"，用户按一次回车即可
- **deps 重新分析成本**：如果旁效应债务 change 触发了文件冲突，需要重新 deps。缓解：仅在文件冲突时触发
- **iteration.py schema 需要升级**：`additionalProperties: false` 不允许新增 status。需要 bump version

### 后续待办

- [ ] 架构漂移检测的自动实现（mend-adr 模式）— 未来 ADR
- [ ] review 阶段可配置（SKIP_REVIEW=yes 环境变量）— v2.1
- [ ] 基于 debt 计数的 scan-state 推荐分支 — 未来 ADR

## References

- `docs/adr/ADR-0003-three-phase-architecture.md` — 三阶段架构设计（phase 模型依据）
- `docs/adr/ADR-0007-gate-mechanism.md` — 门控机制（review 门控的设计依据）
- `skills/guide-ship.md` Phase 2-5 — ship 端 5 阶段（插入点）
- `skills/execute.md` — execute 的行为定义
- `skills/propose.md` Phase 2 — 分类分配逻辑
- `skills/_lib/gate.py:112-128` — 默认检查列表（新增 check 的位置）
- `skills/_lib/iteration.py:22-26` — status 枚举（新增 "review" 的位置）
- `docs/proposal-suggestions-format.md` — schema 定义（新增 type 字段）
- `docs/proposal-suggestions-format.md:98-112` — 5 个 consumer 列表