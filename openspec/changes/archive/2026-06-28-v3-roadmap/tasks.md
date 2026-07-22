## Task 1: Evaluate 4 unimplemented ADRs for effort/value

**Files:**
- Read: `docs/adr/ADR-0009-scheduled-triggers.md`
- Read: `docs/adr/ADR-0010-multi-session-management.md`
- Read: `docs/adr/ADR-0011-phase-step-pipeline-model.md`
- Read: `docs/adr/ADR-0012-flow-customization-layer.md`
- Read: `skills/_lib/session.py` (existing lightweight session v2.0)
- Read: `skills/_lib/loop_state.py` (loop engine state)

- [ ] **Step 1: Evaluate ADR-0009 (Scheduled Triggers)**

Read `docs/adr/ADR-0009-scheduled-triggers.md` and answer:
- Is the design mature enough for implementation? (49-line placeholder file — likely not)
- What's the estimated effort? (S/M/L/XL)
- What's the business value for users?
- Dependencies on other ADRs?

Record findings for decision table.

- [ ] **Step 2: Evaluate ADR-0010 (Full Multi-Session)**

Read ADR-0010 and read the existing `skills/_lib/session.py` to understand delta:
- What is missing from v2.0's lightweight implementation?
- Parallel session execution required?
- Parent-child session tree required?
- What's the estimated effort to complete?
- Can this be done as a v2.1 additive change (backward compatible)?

Record findings.

- [ ] **Step 3: Evaluate ADR-0011 (Step Pipeline)**

Read ADR-0011 and assess:
- What changes to the existing phase model are needed?
- Would this break existing `guide-arch`/`guide-plan`/`guide-ship` skills?
- Dependencies on ADR-0012?
- Effort estimate and value proposition.

Record findings.

- [ ] **Step 4: Evaluate ADR-0012 (Flow Customization)**

Read ADR-0012 and assess:
- Dependency on ADR-0011's step model?
- Custom skill registration mechanism?
- `flow.yaml` schema complexity?
- Effort estimate and value proposition.

Record findings.

---

## Task 2: Update docs/adr/README.md with target release decisions

**Files:**
- Modify: `docs/adr/README.md`

- [ ] **Step 1: Add Target Release column to ADR status table**

Edit the ADR status table in `docs/adr/README.md` to add a "Target Release" column for unimplemented ADRs:

```
| ADR | 标题 | 实施状态 | 目标版本 |
|-----|------|---------|---------|
| ADR-0009 | 定时循环 | ❌ 未实施 | v3.0 |
| ADR-0010 | 多会话管理 | ⚠️ 部分实施 | v2.1（完整版）|
| ADR-0011 | 阶段步骤化 | ❌ 未实施 | v3.0 |
| ADR-0012 | 流程定制层 | ❌ 未实施 | v3.0 |
```

- [ ] **Step 2: Verify**

Run:
```bash
cd /workspace/project/rdd-workflow && python3 -c "
with open('docs/adr/README.md') as f:
    c = f.read()
for adr in ['ADR-0009', 'ADR-0010', 'ADR-0011', 'ADR-0012']:
    assert adr in c, f'{adr} must be in README'
    # Find the line and verify it has a target version
    lines = [l for l in c.split('\n') if adr in l]
    assert any('v2.1' in l or 'v3.0' in l for l in lines), f'{adr} must have target version'
print('✅ All ADRs have target release')
"
```

- [ ] **Step 3: Commit**

```bash
cd /workspace/project/rdd-workflow && git add docs/adr/README.md && git commit -m "docs(adr): add target release column for unimplemented ADRs — ADR-0009/0011/0012→v3.0, ADR-0010→v2.1"
```

---

## Task 3: Create placeholder openspec changes for each future ADR

**Files:**
- Create: `openspec/changes/v2-multi-session/`
- Create: `openspec/changes/v3-scheduled-triggers/`
- Create: `openspec/changes/v3-step-pipeline/`
- Create: `openspec/changes/v3-flow-customization/`

- [ ] **Step 1: Create v2-multi-session placeholder change**

```bash
cd /workspace/project/rdd-workflow && openspec new change v2-multi-session \
  --description "Implement full multi-session management (ADR-0010): parent-child session trees, parallel execution, dependency scheduling. v2.0 has lightweight baseline (session.py); this completes the vision." \
  --goal "Complete ADR-0010 multi-session management with parallel execution support and dependency scheduling"
```

Then create its `proposal.md`:
```markdown
## Why

ADR-0010 defines a multi-session management system with parent-child session trees, parallel execution, and dependency scheduling. v2.0.0-beta ships a lightweight base (`skills/_lib/session.py`). This change completes the ADR-0010 vision by adding the remaining capabilities.

## What Changes

- **Extend** `skills/_lib/session.py` with parent-child session tree support
- **Add** `skills/_lib/session_manager.py` for parallel session coordination
- **Add** `skills/_lib/dependency_scheduler.py` for cross-session dependency resolution
- **Update** state vector schema with `sub_sessions` fields
```

- [ ] **Step 2: Create v3-scheduled-triggers placeholder change**

```bash
cd /workspace/project/rdd-workflow && openspec new change v3-scheduled-triggers \
  --description "Implement scheduled triggers for loop engine (ADR-0009): cron-like event triggers, time-based detector, scheduled action execution" \
  --goal "Implement ADR-0009 scheduled triggers for the loop engine"
```

Create `proposal.md` with ADR-0009 scope summary.

- [ ] **Step 3: Create v3-step-pipeline placeholder change**

```bash
cd /workspace/project/rdd-workflow && openspec new change v3-step-pipeline \
  --description "Implement phase-step pipeline execution model (ADR-0011): replace monolithic phase with composable steps, trigger conditions, step engine" \
  --goal "Implement ADR-0011 phase-step pipeline execution model"
```

Create `proposal.md` with ADR-0011 scope summary.

- [ ] **Step 4: Create v3-flow-customization placeholder change**

```bash
cd /workspace/project/rdd-workflow && openspec new change v3-flow-customization \
  --description "Implement flow customization layer (ADR-0012): .rdd-workflow/flow.yaml, custom skill registration, conditional step skipping" \
  --goal "Implement ADR-0012 flow customization layer (depends on ADR-0011)"
```

Create `proposal.md` with ADR-0012 scope summary.

- [ ] **Step 5: Verify all 4 placeholder changes exist**

Run:
```bash
cd /workspace/project/rdd-workflow && ls -d openspec/changes/*/ | grep -v archive/ && echo "---" && echo "Total active changes: $(ls -d openspec/changes/*/ | grep -v archive/ | wc -l)"
```

Expected: 5 active changes (v3-roadmap + 4 placeholders).

- [ ] **Step 6: Commit placeholder changes**

```bash
cd /workspace/project/rdd-workflow && git add openspec/changes/v2-multi-session/ openspec/changes/v3-scheduled-triggers/ openspec/changes/v3-step-pipeline/ openspec/changes/v3-flow-customization/ && git commit -m "feat(openspec): create placeholder changes for 4 future ADRs — v2-multi-session, v3-scheduled-triggers, v3-step-pipeline, v3-flow-customization"
```

---

## Task 4: Update roadmap.md with v3.0 vision

**Files:**
- Modify: `roadmap.md`

- [ ] **Step 1: Replace generic Phase-1 with concrete v3.0 phases**

Current `roadmap.md` has a single generic "Phase 1: User-defined" phase. Replace with:

```markdown
# 项目路线图

## 元信息
- **版本**: 2
- **创建时间**: 2026-06-07T09:16:26+08:00
- **最后更新**: 2026-06-28
- **当前阶段**: v2.0 (已完成)

## v2.0 已完成 (2026-06-26)

v2.0.0-beta 已发布。详见 `docs/v2-implementation-plan.md`。

## v2.1 规划

### Phase 1: 完整多会话支持
**目标**: 完成 ADR-0010 的完整实现（并行会话、依赖调度）
**状态**: 📋 待启动
**对应 Change**: `v2-multi-session`
**预计工作量**: 中型 (2-3 周)

## v3.0 规划

### Phase 1: 定时循环与事件触发
**目标**: 实现 ADR-0009 定时触发器
**状态**: 📋 待规划
**对应 Change**: `v3-scheduled-triggers`
**预计工作量**: 小型 (1-2 周)

### Phase 2: 阶段步骤化执行
**目标**: 实现 ADR-0011 步骤化执行模型
**状态**: 📋 待规划
**对应 Change**: `v3-step-pipeline`
**预计工作量**: 大型 (3-4 周)
**依赖**: Phase 3 (流程定制层可降级为独立实现)

### Phase 3: 流程定制层
**目标**: 实现 ADR-0012 自定义流程
**状态**: 📋 待规划
**对应 Change**: `v3-flow-customization`
**预计工作量**: 大型 (3-4 周)
**依赖**: Phase 2 (步骤化执行模型为基础)
```

- [ ] **Step 2: Verify roadmap.md structure**

Run:
```bash
cd /workspace/project/rdd-workflow && python3 -c "
with open('roadmap.md') as f:
    c = f.read()
assert '版本 2' in c or '版本: 2' in c, 'Version should be 2'
assert 'v2.0' in c, 'Must mention v2.0 completion'
assert 'v2.1' in c, 'Must have v2.1 section'
assert 'v3.0' in c, 'Must have v3.0 section'
for change in ['v2-multi-session', 'v3-scheduled-triggers', 'v3-step-pipeline', 'v3-flow-customization']:
    assert change in c, f'Must mention {change}'
print('✅ roadmap.md verified')
"
```

- [ ] **Step 3: Commit roadmap.md**

```bash
cd /workspace/project/rdd-workflow && git add roadmap.md && git commit -m "docs(roadmap): update from generic Phase-1 to concrete v2.1/v3.0 plan with 4 ADR-backed phases"
```

---

## Task 5: Final verification

- [ ] **Step 1: Verify git log**

Run: `cd /workspace/project/rdd-workflow && git log --oneline -7`

Expected: 5 commits forming a coherent history.

- [ ] **Step 2: Verify openspec changes**

Run:
```bash
cd /workspace/project/rdd-workflow && for change in v3-roadmap v2-multi-session v3-scheduled-triggers v3-step-pipeline v3-flow-customization; do
    echo -n "$change: "
    openspec validate "$change" 2>&1 | head -1
done
```

Expected: All 5 changes valid.

- [ ] **Step 3: Run tests to confirm no regressions**

Run: `cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/ -q --tb=short`

Expected: All tests pass (no production code was changed).

---

## Self-Review

### 1. Spec Coverage

| Requirement | Plan Covers? | Task # |
|------------|-------------|--------|
| Evaluate 4 unimplemented ADRs | ✅ | Task 1 |
| Add target release to ADR README | ✅ | Task 2 |
| Create placeholder changes | ✅ | Task 3 (4 sub-changes) |
| Update roadmap.md with v3.0 vision | ✅ | Task 4 |
| Final verification | ✅ | Task 5 |

### 2. Placeholder Scan

No TBDs, TODOs, or "implement later" found. Decisions are explicitly deferred (e.g., "effort estimate to be confirmed in Task 1").

### 3. Type Consistency

- Placeholder change names match the ADR references: ADR-0009 → v3-scheduled-triggers, ADR-0010 → v2-multi-session, ADR-0011 → v3-step-pipeline, ADR-0012 → v3-flow-customization
- ADR README target release table columns match the decisions documented in design.md
- roadmap.md phase names match placeholder change names