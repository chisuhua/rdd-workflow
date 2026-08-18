## Context

**背景**

`skills/_lib/design_done_gate.py` 实现 2 个函数 `check_hub_pending()` / `check_cross_repo_approvals()`, 文档化于 README §跨项目协同 章节, 声称 `SKIP_HUB_CHECK=true` 紧急跳过。Oracle 2026-08-18 审查发现: **这 2 个函数在生产代码中无任何调用方** — `guide-design/SKILL.md` 的 `check_design_done_gate()` 从不调用它们。

**失真链路**

- README 承诺: "Hub 网络故障时 `SKIP_HUB_CHECK=true` 可绕过 design-done 门控"
- 文档承诺: `docs/strict-gate-boundary.md` 把 `RDDF_REQUIRE_HUB_APPROVAL` / `SKIP_HUB_CHECK` 写进门控矩阵
- 真相: gate 函数是孤儿代码, `SKIP_HUB_CHECK` env var 被一个**未被任何路径调用**的函数读取

**已有机制（接线而非新增）**

- `skills/_lib/design_done_gate.py` 两个 orphan 函数已实现（含单元测试 `tests/unit/test_design_done_gate.py`）
- `skills/guide-design/scripts/design_proposal_review.sh` 是 design-done 门控链入口, 缺对 `check_hub_pending` / `check_cross_repo_approvals` 的调用
- `skills/_lib/cross_repo_gate.py` 已知存在, 可作为调用样板
- `STRICT_HUB_APPROVAL=no` 已在 `skills/_lib/config.py` 注册（Hub 端 env var, 不是 Spoke 端）

## Goals / Non-Goals

**Goals:**

**In Scope**:

- **gate 调用接入**: 修改 `skills/guide-design/SKILL.md` Phase 4 `check_design_done_gate()`, 末尾追加 2 个新 check（顺序: 现有 pending check → 新 `check_hub_pending` → 新 `check_cross_repo_approvals`）
- **env var wired**: `SKIP_HUB_CHECK=true` 真实生效（当前函数读取但不被调用, 改动后默认严格、env var 临时绕过）
- **bats 集成测试**: `tests/integration/test_design_done_hub_gates.bats` 覆盖 4 个场景（默认通过 / hub pending 阻断 / cross-repo 未批准阻断 / SKIP_HUB_CHECK 绕过）
- **rdd-doctor 巡检**: 在 `rdd-doctor --category plan-tdd` 中增加 orphan gate 检测项（防止后续再次漂移）
- **README 同步**: `README.md` §"紧急跳过" 章节补明确默认值（默认 OFF, 紧急时 ON）

**Non-Goals:**

**Out Scope**:

- **不重写** `design_done_gate.py` 函数本体（仅接线, 复用既有实现）
- **不修改** Hub 端 `STRICT_HUB_APPROVAL` 逻辑（属 ADR-0031 跨项目决策, 不属本仓）
- **不调整** `check_design_done_gate()` 中既有 5 个 check 的顺序或行为
- **不引入** 新 env var（保留 `SKIP_HUB_CHECK` 与 `RDDF_REQUIRE_HUB_APPROVAL`）

## Decisions

### Decision 1: Approach from proposal 关键场景

The proposal's 5 key scenarios drive the implementation:

### 场景 1 — 默认严格模式

```bash
# 仓库有 Hub pending issue 但未关闭
$ ls .rddf/state/.cross-repo-pending.json
# → 含 pending: ["org/rdd-hub#42"]

$ skill_use("guide-design")
# → Phase 4 gate check:
#    ✅ 既有 5 个 check pass
#    ❌ NEW: check_hub_pending() → 检测到 1 个 pending → exit 1
#    决策: 阻断 design-done, 需先关闭 Hub Issue 或设置 SKIP_HUB_CHECK
```

### 场景 2 — cross-repo 提案未获 Hub 批准

```bash
# 仓库最近 approval 含 cross_repo_federation 分类, hub_approved=false
$ cat .rddf/state/.cross-repo-audit.jsonl | jq 'select(.decision=="approve" and .hub_state!="approved")'
# → 至少 1 行

$ skill_use("guide-design")
# → Phase 4 gate check:
#    ✅ 既有 5 个 check pass
#    ❌ NEW: check_cross_repo_approvals() → 检测到 1 行 hub_state!=approved → exit 1
```

### 场景 3 — 紧急跳过（`SKIP_HUB_CHECK=true`）

```bash
$ SKIP_HUB_CHECK=true skill_use("guide-design")
# ✅ 全过（含 2 个新 check, 因 env var 被函数读取且被调用, 真实生效）
# 决策: design-done pass (仅紧急 hotfix 用, audit log 仍记录 SKIP 原因)
```

### 场景 4 — rdd-doctor 巡检防漂移

```bash
$ rdd-doctor --category state --check orphan-gates
# 扫描 guide-design/SKILL.md 是否调用 design_done_gate.py 的所有函数
# → 检测 orphan function 立即报告 CRITICAL（防止后续再次漂移）
```

### Decision 2: Technical Constraints Adherence

1. **依赖顺序**: 必须在 `fix-adr-0031-safety-gate-substantiation`（P0）落地后再合入 — 因为 audit log 必须先非空, `check_cross_repo_approvals` 才能验证
2. **fail-open 收紧**: 默认严格, `SKIP_HUB_CHECK` 不会回退到默认 ON
3. **既有回归**: `tests/integration/test_design_done_gate*.bats` 4 个既有 case 必须继续通过
4. **Documentation drift 检测**: `rdd-doctor` 巡检项须覆盖到 orphan gate pattern
5. **顺序保证**: 新 check 追加在 `check_design_done_gate()` 末尾（不动既有 5 个 check）
6. **单元测试**: `tests/unit/test_design_done_gate.py` 已覆盖函数行为；本次仅补集成测试不补单测
7. **CI 兼容**: bats fixture 需 `SKIP_HUB_CHECK` 临时放行（与既有 PR 流程一致）

### Implementation Sequence

**Depends on (must merge first):**

- `fix-adr-0031-safety-gate-substantiation`

## Risks / Trade-offs

- **Test failure on existing approve_proposal.sh suite**: 既有 4 个 bats 测试 (`test_strict_human_approval.bats`) 必须保持通过,新增 ≥ 5 个 case 锁定新行为
- **CI 兼容性**: `read -s` 在非交互终端需 fallback (用 `RDDF_APPROVE_ACTOR` env var)
- **Audit log crash-safety**: `append_audit_log_entry` 必须在 accept 前同步写入, atomic_write 保证
- **Hub Issue re-fetch network error**: 区分 network (fail-open + warning) vs auth (fail-closed)
- **Schema backward compatibility**: iteration.json v7 字段添加但不破坏 v6 现有消费者 (字段缺省默认为空)

## References

- `.rddf/improvements/fix-orphan-hub-gates-wiring.md` — 完整 5 段 proposal
- `openspec/changes/fix-orphan-hub-gates-wiring/proposal.md` — 落盘的完整 proposal
- ADR-0030 / ADR-0031 — Hub-and-Spoke 联邦架构 + 跨项目 RFC 人类决策
