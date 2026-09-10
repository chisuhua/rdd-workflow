---
name: adr-0048-v4-stage-merge-revision
priority: P0
phase: phase-2
category: architecture-governance
type: improvement
依赖: 无（独立）
主题: v4 stage-merge 修订 — rdd-arch 完全脱离 roadmap + rdd-planner 完全接管 roadmap + rdd-builder P0 触发 rdd-quick（per user design intent 2026-09-09）
---

# adr-0048-v4-stage-merge-revision

## Why

2026-09-09 rdd-planner alignment audit（Oracle `ses_f7a9e01dbffe2Lqu8jYjg4YvL2`）揭示三类架构债务：

1. **rdd-arch 与 roadmap 边界未真正分离** — ADR-0043 §1 line 30 明文 "rdd-arch 不再生成 roadmap-related 数据"，但 `skills/rdd-arch/SKILL.md` 仍保留 Phase 4 roadmap-define + role.boundaries.owns 含 `roadmap.md` + `.rddf/roadmap/{features,phases}/*.md` + `.rddf/state/.populate-state.json`（审计 finding C-1）
2. **`recommended_route` 是死字段** — schema v1 声明 `recommended_route` 在 `_lib/schemas/planner_state_schema.json`，但 `_default_state()` 不写入、`render_state()` 不产出、`rddf planner status` 不展示，唯一测试仅验 schema 存在
3. **rdd-quick 缺乏结构化决策信号** — ADR-0047 D1 让 quick 自 triage 依赖 user natural language，错过 rdd-planner 已有的结构化 advisory；rdd-quick 失败升级时回 planner 形成潜在循环

user 设计意图（2026-09-09 对话）：
> 我想...rdd-arch里的Phase 4 roadmap-define任务移除，而是改成读取rdd-planner生成的反馈；而roadmap的创建和管理的事情统一由rdd-planner维护， rdd-planner还维护sprint的提案内容。对于rdd-quick的快速通道，你看看能不能再rdd-builder 里来判断和进入？

## 架构依据

ADR-0048 三个核心决策：

### 决策 1: rdd-arch 完全脱离 roadmap

- 删除 SKILL.md Phase 4 roadmap-define (L520-658 ~138 行)
- role.boundaries.owns 移除 `roadmap.md` + `.rddf/roadmap/{features,phases}/*.md` + `.rddf/state/.populate-state.json`
- arch-done 单门控（仅 ADR ≥ 1），移除 `roadmap.md 存在` 检查
- arch-done Phase X Roadmap Sync 块删除（不再调 `roadmap_incremental_update.sh`）
- 同步修复 `rdd-arch/SKILL.md` 预先存在的 YAML 缩进 bug（`boundaries:` 块 `owns:` / `not_owns:` 缺 2 空格缩进，导致 YAML 解析为 `boundaries: null`）

### 决策 2: rdd-planner 完全接管 roadmap

- 新增 SKILL.md Phase 0 roadmap-bootstrap：检测 `.rddf/roadmap.md` 缺失 → 引导 `rddf roadmap init`（4 模板）
- role.boundaries.owns 新增 `.rddf/roadmap/{features,phases}/*.md` + `.rddf/state/.populate-state.json`
- Phase 5 双门控：① `.rddf/roadmap.md` 存在 ② `.planner-state.json::recommended_route` 已写入
- `_compute_recommended_route` 启发式：从 active_projects 计算 simple|complex|unknown
  - simple: 全部 priority=P3 AND 无 complex 关键词 AND 不触碰 `_lib/core/` / `_lib/schemas/`
  - complex: 任意 priority∈{P0,P1} OR 触碰 `_lib/core/` / `_lib/schemas/` OR breaking-change/public-interface 关键词
  - unknown: 空 active_projects OR 混合信号
- `recommended_route` 字段从 optional → required（schema v1.1）：
  - `_lib/schemas/planner_state_schema.json` `required[]` 加入
  - `_lib/schemas/planner_handoff_schema.json` `required[]` 加入（handoff v1.1 新增字段）
  - `_default_state()` 默认 `"unknown"`（排除 semantic hash，state_revision 不被它 bump）
  - `write_state()` 自动注入 `"unknown"` 默认值（向后兼容 pre-ADR-0048 调用者）

### 决策 3: rdd-builder P0 触发 rdd-quick

- P0 prompt 从 4-option 升为 5-option（HARD pause）：1.approve / 2.reject / 3.defer / 4.revise / **5.dispatch-quick**
- 推荐提示：仅当 `recommended_route=simple AND AC ≤ 2 AND files ≤ 2 AND 无 public interface 改动` 时显示 💡
- 选项 5 触发逻辑：
  - 写 `.rddf/state/rdd-quick-context.json`（NEW schema，传递 proposal.md 内容）
  - 写 `.rddf/state/builder/<change>.json::approval_status="dispatched_to_quick"` + `dispatch_quick_at` + `dispatch_quick_outcome`
  - 委托 `skill_use("rdd-quick") --from-builder`
  - 发出 `DISPATCH_TO_QUICK=1 CHANGE_NAME=<change>` marker 给 orchestrator
- `--dispatch-quick` CLI flag：auto-pick case 5（前提是 recommended_route=simple）
- `_lib/builder_deps.py::read_planner_recommended_route()`：读取 handoff 推荐路径（缺/坏时降级 unknown）

### 关联修订

- **ADR-0038** AMENDMENT #2：planner 完全独占 roadmap（被 ADR-0048 §Decision 1 取代）
- **ADR-0042** AMENDED per ADR-0048：planner advisory 升级（rdd-arch 完全脱离后更依赖 planner feedback）
- **ADR-0047** AMENDED per ADR-0048：D1 立场反转 — `rdd-quick self-triages regardless` → `rdd-builder P0 触发主路径 + rdd-quick 自 triage fallback`；升级契约从 `skill_use("rdd-planner")` → `skill_use("rdd-builder")`（避免 planner → builder → quick → planner 循环）
- **fix-v4-rdd-planner-scope-over-assignment AC-13** 从 optional → required

## Capabilities

- capability-rdd-arch-slim (rdd-arch 完全脱离 roadmap)
- capability-rdd-planner-roadmap-ownership (rdd-planner 完全独占 roadmap + recommended_route advisor)
- capability-rdd-builder-dispatch-quick (rdd-builder P0 5-option + rdd-quick 集成)

## Impact

### 正向

- ✅ 修复审计 finding C-1（rdd-arch 角色表错位）：边界彻底分离
- ✅ rdd-arch 简化（5 phase → 实际只 4 phase 工作）：删除 Phase 4 + 单门控
- ✅ `recommended_route` 字段从死字段升级为 required + 完整数据流：rdd-planner 计算 → 写 state → 写 handoff → rdd-builder P0 读取 → rdd-quick 消费
- ✅ rdd-quick 决策点获得结构化 advisory（而非纯 natural language self-triage）
- ✅ 升级路径避免循环：quick → builder P0 重新决策（不再回 planner）

### 风险与缓解

| 风险 | 缓解 |
|---|---|
| 反转 ADR-0047 D1 立场需 user override | ADR-0048 + ADR-0047 amendment 同步记录 |
| rdd-builder P0 5-option 增加决策复杂度 | 推荐提示（💡）前置展示；保留 1-4 经典路径不变 |
| `recommended_route` 启发式可能误判 | 仅为 advisory；rdd-builder P0 保留用户最终决策权（HARD pause） |
| 旧调用方按 ADR-0047 找 `skill_use("rdd-planner")` 升级 quick 失效 | SKILL.md + guide 推荐菜单同步更新 |
| 零污染契约（4 个 sha256 hash）需更新 | `test_rdd_quick_isolation.bats` 已重新捕获 rdd-planner role block 哈希 |
| planner-handoff.py 无 FileLock + atomic_write | KNOWN LIMITATION 在 docstring 标注；提交独立 fix 跟踪 |

## Acceptance

### AC summary (checklist for review tracking)

- [x] AC-1: ADR-0048 文件创建（`docs/adr/ADR-0048-v4-stage-merge-revision.md`）
- [x] AC-2: rdd-arch SKILL.md 删除 Phase 4 roadmap-define
- [x] AC-3: rdd-arch role.boundaries.owns 移除 3 个 roadmap 相关项
- [x] AC-4: arch-done 单门控（移除 roadmap 检查）
- [x] AC-5: rdd-planner SKILL.md 新增 Phase 0 roadmap-bootstrap
- [x] AC-6: rdd-planner SKILL.md Phase 5 双门控
- [x] AC-7: planner_state_schema.json recommended_route required (v1.1)
- [x] AC-8: planner_handoff_schema.json recommended_route required (v1.1)
- [x] AC-9: rdd_builder SKILL.md P0 5-option + dispatch-quick
- [x] AC-10: phase0_approval.sh case 5 写 rdd-quick-context.json + builder-handoff
- [x] AC-11: rdd_quick SKILL.md L200 升级契约改 skill_use('rdd-builder')
- [x] AC-12: rdd_quick SKILL.md owns 增 rdd-quick-context.json
- [x] AC-13: ADR-0038/0042/0047 同步 AMEND 块
- [x] AC-14: AGENTS.md 状态文件表修订（plan-handoff 标 RETIRE）
- [x] AC-15: docs/adr/README.md 表格行同步（ADR-0038/0042/0047/0048 状态文字）
- [x] AC-16: 新增 4 个 bats + 1 个 pytest 测试文件（共 125 个测试，全部通过）
- [x] AC-17: 既有 test_rdd_quick.bats 加 6 个 ADR-0048 升级契约测试
- [x] AC-18: test_rdd_quick_isolation.bats 重新捕获 rdd-planner role block hash

### Detailed AC

#### AC-1: ADR-0048 文件存在

`ls docs/adr/ADR-0048-v4-stage-merge-revision.md` 成功。

#### AC-2~4: rdd-arch 边界清理

- `grep -E "^## Phase 4:.*roadmap" skills/rdd-arch/SKILL.md` 返回 0 hits
- `extract_role_boundaries skills/rdd-arch/SKILL.md` 输出 owns 不含 `roadmap.md` / `.rddf/roadmap/features` / `.rddf/roadmap/phases` / `.populate-state`
- `bash skills/rdd-arch/scripts/arch_done_gate.sh` 单门控（无 `roadmap.*存在` if 检查）

#### AC-5~6: rdd-planner Phase 0 + Phase 5

- `grep -c "roadmap-bootstrap" skills/rdd-planner/SKILL.md` ≥ 1
- `grep -c "双门控" skills/rdd-planner/SKILL.md` ≥ 1

#### AC-7~8: schemas

`recommended_route` 在两个 schema 的 `required[]` 中。

#### AC-9~10: rdd-builder 5-option + case 5

- `bash skills/rdd-builder/scripts/phase0_approval.sh test-change --dispatch-quick` 当 recommended_route=simple 时 exit 0 + 写 rdd-quick-context.json + builder-handoff dispatched_to_quick

#### AC-11~12: rdd-quick 修订

- `grep -F 'skill_use("rdd-builder")' skills/rdd-quick/SKILL.md` 命中（在升级建议块）
- `grep -F 'not_owns:       - "roadmap.md"'` 不出现在 planner 的 not_owns
- `grep -F "rdd-quick-context.json" skills/rdd-quick/SKILL.md` 命中 owns 列表

#### AC-13: ADR 同步

- `grep -c "ADR-0048" docs/adr/ADR-0038-rdd-planner-crosscutting.md` ≥ 1
- `grep -c "ADR-0048" docs/adr/ADR-0042-rdd-arch-rdd-planner-bidirectional-feedback.md` ≥ 1
- `grep -c "AMENDED (per ADR-0048" docs/adr/ADR-0047-rdd-quick-bypass-path.md` ≥ 1

#### AC-14~15: AGENTS.md + README.md 同步

- `grep "已 RETIRE per v4 spec" AGENTS.md` 命中（plan-handoff 行标注）
- `grep "DOUBLE-AMENDED" docs/adr/README.md` 命中（ADR-0038 行）
- `grep "AMENDED (per ADR-0048, 2026-09-09)" docs/adr/README.md` 命中（ADR-0042 行）

#### AC-16: 新测试

- `bats tests/integration/test_rdd_builder_dispatch_quick.bats` → 16/16 ok
- `bats tests/integration/test_rdd_planner_recommended_route.bats` → 13/13 ok
- `bats tests/integration/test_rdd_arch_no_roadmap.bats` → 16/16 ok
- `bats tests/integration/test_rdd_planner_roadmap_bootstrap.bats` → 16/16 ok
- `pytest tests/unit/test_recommended_route.py` → 40/40 ok

#### AC-17: test_rdd_quick.bats 加 6 个 ADR-0048 测试

- `bats tests/integration/test_rdd_quick.bats` → 20/20 ok (含原 14 + 新 6)

#### AC-18: isolation hash 重新捕获

- `bats tests/integration/test_rdd_quick_isolation.bats` → 4/4 ok（rdd-planner role block sha256 = 69653d...）

## What Changes

18 个文件 modified + 6 个文件 created，按 4 commit 拆分（review-friendly）：

1. **commit 1** docs(adr): ADR-0048 + amendments + README sync (5 files)
2. **commit 2** feat(skills+...): SKILL.md + scripts + new schema (12 files)
3. **commit 3** feat(_lib): advisory signal pipeline + dispatch-quick writer (7 files)
4. **commit 4** test(adr-0048): comprehensive coverage (9 files)

## 验收标准

- [x] AC-1: ADR-0048 文件创建
- [x] AC-2: rdd-arch 删除 Phase 4
- [x] AC-3: rdd-arch role.boundaries.owns 清理
- [x] AC-4: arch-done 单门控
- [x] AC-5: rdd-planner Phase 0
- [x] AC-6: rdd-planner Phase 5 双门控
- [x] AC-7: planner-state schema v1.1
- [x] AC-8: planner-handoff schema v1.1
- [x] AC-9: rdd-builder 5-option
- [x] AC-10: phase0 case 5
- [x] AC-11: rdd-quick L200 升级契约
- [x] AC-12: rdd-quick owns context
- [x] AC-13: ADR-0038/0042/0047 同步
- [x] AC-14: AGENTS.md 状态文件表
- [x] AC-15: README.md 表格同步
- [x] AC-16: 新测试 125 个全绿
- [x] AC-17: test_rdd_quick.bats 加 6 测试
- [x] AC-18: isolation hash 重新捕获

## Reference

- **Oracle 审查**: `ses_f7a9e01dbffe2Lqu8jYjg4YvL2`（2026-09-09 rdd-planner 架构审查，20m）
- **user design intent**: 2026-09-09 对话 — 3 项设计改动批准
- **ADR-0043**: rdd-workflow v4 stage-merge architecture（基线）
- **ADR-0038**: rdd-planner Horizontal Orchestrator（AMENDMENT #2）
- **ADR-0042**: rdd-arch rename + planner 双向反馈（AMENDED）
- **ADR-0047**: rdd-quick bypass path（AMENDED D1）
- **`.rddf/improvements/fix-v4-rdd-planner-scope-over-assignment.md`**: AC-13 升级
- **实施 commits**: `95964b0` + `fcfc850` + `c9e70a1` + `137dcd0`
