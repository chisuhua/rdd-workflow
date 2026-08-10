# 实施计划: wire-design-content-review-gate

> 对应 Change: `openspec/changes/wire-design-content-review-gate`
> 基于: tasks.md 中的 7 组 23 任务
> ADR 引用: ADR-0025 §D1/D4 (双层内容审查 + warning-default + SKIP escape hatch)
> 实施位置: 主线轻量模式 (`openspec/wire-design-content-review-gate` branch, 无 worktree)

## 概览

| 阶段 | 任务组 | 工作量 | 风险 |
|------|--------|--------|------|
| Wiring Investigation | 1.1-1.3 | 3 任务 | 低（只读） |
| Review invocation helper | 2.1-2.3 | 3 任务 | 低（新建 helper） |
| Single approve wiring | 3.1-3.3 | 3 任务 | 中（插入到 side-effect 前） |
| Batch approve wiring | 4.1-4.3 | 3 任务 | 低（沿用 single helper） |
| SKIP escape hatch | 5.1-5.3 | 3 任务 | 低（helper 内部 short-circuit） |
| Regression Coverage | 6.1-6.6 | 6 任务 | 中（新增 bats 测试） |
| Verification | 7.1-7.2 | 2 任务 | 低（验证 + 完整性） |

## 实施策略

**顺序**: 1 (读) → 2 (helper) → 3 (single wire) → 4 (batch wire) → 5 (skip) → 6 (测试) → 7 (终验)

**关键约束**:
- 单一 review 调用路径（design decision 1）：single + batch 共用 helper
- helper 读取 STRICT_DESIGN_GATE / SKIP_CONTENT_REVIEW（design decision 2）
- IMPROVEMENTS_PATH / PROJECT_ROOT 通过 env var 传递（design decision 3 / Oracle C1 safe）
- helper 调用必须在所有 approve-side-effect 之前

**聚合 commit**: Phase 2.7 统一聚合 1 个 commit（不逐任务 commit）。

## 关键文件

| 文件 | 操作 | 来源任务 |
|------|------|---------|
| `skills/guide-design/scripts/run_content_review.sh` | CREATE | 2.1-2.3 |
| `skills/guide-design/scripts/approve_proposal.sh` | MODIFY | 3.1-3.3 (插入 helper 调用) |
| `skills/guide-design/scripts/design_proposal_review.sh` | (无变更，间接沿用) | 4.1-4.3 |
| `tests/integration/test_wire_design_content_review_gate.bats` | CREATE | 6.1-6.5 |

## 实施步骤 (TDD 5 步)

### Group 1: Wiring Investigation (Tasks 1.1-1.3)

- 1.1 读 `design_content_review.sh` 确认 entry-point + exit-code 约定
- 1.2 读 `approve_proposal.sh` 确认 approve-side-effect 顺序
- 1.3 读 `design_proposal_review.sh` 确认 batch 编排

### Group 2: Review invocation helper (Tasks 2.1-2.3)

- 创建 `skills/guide-design/scripts/run_content_review.sh`:
  - 接收 `IMPROVEMENTS_PATH` / `PROJECT_ROOT` env var
  - 读取 `STRICT_DESIGN_GATE` / `SKIP_CONTENT_REVIEW`
  - 调用 `design_content_review.sh`
  - 透传 exit code (0 pass/warn, 1 blocking)
  - FD3 输出 `REVIEW_RESULT=pass|warn|block|skip` 用于调用方分支

### Group 3: Wire single approve (Tasks 3.1-3.3)

- 在 `approve_proposal.sh` 中,`check_archived` 分支后,`append_approved` 前插入 helper 调用
- 默认 mode: review exit 0 → continue approve (含 warning)
- STRICT mode: review exit 1 → abort approve (不写任何 side-effect)

### Group 4: Wire batch approve (Tasks 4.1-4.3)

- `design_proposal_review.sh` 的 batch 循环 (`a|all`) 已经循环调用 `approve_proposal.sh`
- 由于 approve_proposal.sh 已 wire helper, batch 自动逐项调用同一路径
- 单项 blocking 不静默吞掉: helper exit 1 会让 `approve_proposal.sh` exit 1,触发 `&& echo "✅ 已批准"` 的 false 短路

### Group 5: SKIP escape hatch (Tasks 5.1-5.3)

- helper 内部:`SKIP_CONTENT_REVIEW=yes` 时立即 stdout "review skipped",exit 0
- 不调用 `design_content_review.sh`
- 输出与 PASS 区分 ("review skipped" vs "improvements content review: OK")
- 不影响 approve 其他 side-effect

### Group 6: Regression Coverage (Tasks 6.1-6.6)

`tests/integration/test_wire_design_content_review_gate.bats`:
- 6.1 single approve invokes review.sh
- 6.2 default-mode warning allows approve
- 6.3 STRICT_DESIGN_GATE blocks approve on review blocking
- 6.4 SKIP_CONTENT_REVIEW skips review
- 6.5 batch invokes review per-item
- 6.6 (callers' responsibility): regression suite green

### Group 7: Final Verification (Tasks 7.1-7.2)

- 7.1 `openspec validate wire-design-content-review-gate --type change --json` → no errors
- 7.2 git diff 确认 `proposal-suggestions.md` / 其他 proposals / ADR / 历史未受影响

## 验收标准

1. helper 可独立调用,行为符合 design 决策 (Oracle C1 safe)
2. single approve + batch approve 共用同一 helper
3. STRICT_DESIGN_GATE=yes 在 review blocking 时阻止 approve-side-effect
4. SKIP_CONTENT_REVIEW=yes 跳过 review,不改变其他批准语义
5. 单项 warning 不阻断,blocking 阻断
6. 输出可区分 pass / warn / block / skip
7. bats 集成测试 11/11 通过
8. `openspec validate` 通过

## 风险与回退

- **风险**: helper 增加 review 开销 → 改进措施: <50ms per call,可接受
- **风险**: batch 单项 blocking 影响整个 batch → 沿用 design 决策: per-item 独立
- **回退**: 单 PR revert,无数据迁移