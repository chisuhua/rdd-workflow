---
name: rdd-verifier
description: 5th phase batch verifier — runs ac-verifier skill on ship-done changes, classifies failures heuristically (implementation_gap vs proposal_drift), routes failures back to guide-plan or guide-ship with 3-retry max. Called by user after guide-ship completes (Per ADR-0034).
license: MIT
compatibility: requires openspec CLI v1.3.1+, Python 3.11+, ANTHROPIC_API_KEY or OPENAI_API_KEY (or AC_LLM_MOCK=yes for tests)
metadata:
  author: rdd-workflow
  version: "1.0"
  evolved-from: "ac-verifier skill v1.0 (2026-08-17); promoted to phase by ADR-0034"
  user-invocable: true
role:
  title: "Verifier (验证治理者)"
  perspective: "5th phase state machine — guards archive by enforcing AC pass, classifies failures heuristically, routes loops back to plan/ship. High human involvement (AI classification + user confirm + failure routing decisions)."
  boundaries:
    owns:
      - ".rddf/state/.verifier-loop.json"
      - ".rddf/state/.ac-verdict-*.json"
      - ".rddf/state/.ac-verifier-blocked.jsonl"
    not_owns:
      - "openspec/changes/<name>/"
      - "docs/adr/ADR-*.md"
    human_involvement: "high"
---

# OpenSpec 工作流 — rdd-verifier (5th Phase)

本技能是 OpenSpec 工作流的**第 5 阶段**（验证回环），位于 `guide-ship` 完成、`archive` 之前。复用 `ac-verifier` 子技能作为 LLM 调用后端，加入**启发式失败分类**（implementation_gap vs proposal_drift）和**自动回环路由**（最多 3 次）。

**职责边界**：
- **角色定义**：见 frontmatter `role:` 字段（ADR-0028）
- **拥有**：`role.boundaries.owns` 列出的状态文件
- **不拥有**：`openspec/changes/*/`（不修改提案本身）、`docs/adr/ADR-*.md`（不写 ADR）
- **人工介入程度**：`high`（与 `guide-arch` 同档）

**v1.0 新增**（ADR-0034）：
- 从 ac-verifier 内嵌步骤升级为独立阶段
- 引入 SHA 指纹 verdict 缓存（与 `archive_gate_check` 共享）
- 引入启发式分类（无新 LLM 调用）
- 引入失败回环 + 3 次上限

**调用方式**：

```bash
# 直接调用（CLI 形式）
rddf rdd-verify [--dry-run] [--max-changes N] [--loop]

# Skill 形式（交互式状态机）
skill_use("rdd-verifier")
```

**与 ac-verifier 的边界**：
- `rddf ac-verify <name>` = 单 change 原子验证（无状态、无回环）
- `rddf rdd-verify` = 队列扫描 + 回环编排（有状态、写 `.verifier-loop.json`）

---

## State Machine (State Diagram)

```
[ENTRY: guide-ship done]
    ↓
[1] scan_queue.sh → list ship-done changes from .rddf/state/iteration.json
    ↓ (queue = ["change-a", "change-b", ...])
[2] FOR EACH change (serial, max $RDDF_VERIFIER_MAX_CHANGES):
    ├─ [2a] Check SHA cache (.ac-verdict-<name>.json):
    │   ├─ cache_hit + SHA match → reuse verdict (no LLM)
    │   ├─ cache_hit + SHA mismatch → "stale", re-run
    │   └─ no cache → run ac-verifier fresh
    │
    ├─ [2b] If verdict all PASS → mark loop_state.route="archive-ready"
    │
    └─ [2c] If any FAIL → classify_failure.sh:
        ├─ implementation_gap → user_confirm → route="guide-ship"
        │   (re-execute code in worktree → commit → re-enter verify)
        ├─ proposal_drift → user_confirm → route="guide-plan"
        │   (rewrite proposal/specs → plan → ship → verify again)
        └─ ambiguous → default = implementation_gap (conservative)
            │
            └─ append_classification(loop_count += 1)
                ├─ loop_count < $RDDF_VERIFIER_MAX_LOOPS → route to plan/ship
                └─ loop_count >= $RDDF_VERIFIER_MAX_LOOPS → route="halted" + audit log
                    │
                    └─ [EXIT 4] halted: manual review needed
[3] ALL PASS → [EXIT 0] archive can proceed
```

---

## Per-Change Flow Detail

### Step 1: Scan Queue

```bash
bash skills/rdd-verifier/scripts/scan_queue.sh
# Stdout: space-separated change names
# Honors RDDF_VERIFIER_MAX_CHANGES (default 10)
```

Source: `iteration.json` filter `status="ship-done"` and not archived.

### Step 2: Per-Change Verification

For each change in queue:

1. **Read SHA verdict cache** at `.rddf/state/.ac-verdict-<name>.json`
2. **If cache SHA == HEAD SHA** → skip ac-verifier, use cached verdict
3. **If cache SHA != HEAD SHA** → warn "stale", re-run ac-verifier
4. **If no cache** → run ac-verifier fresh, write cache after

```bash
# Pseudo-code for Step 2 (per change)
SHA=$(git rev-parse HEAD)
CACHE=".rddf/state/.ac-verdict-${CHANGE_NAME}.json"

if [ -f "$CACHE" ] && cache_SHA_matches_$SHA; then
    echo "♻️  Reusing ac-verifier verdict cache"
    VERDICT=$(read_cache_verdict)
else
    bash skills/rdd-verifier/scripts/run_verification.sh "$CHANGE_NAME"
    # Wrapper writes cache after successful run
fi
```

### Step 3: Heuristic Classification (FAIL only)

```bash
bash skills/rdd-verifier/scripts/classify_failure.sh "$CHANGE_NAME"
# Stdout: "AC-N:label" lines (e.g., "AC-1:implementation_gap")
```

Per Oracle §E + ADR-0034 §5.1:
- **Drift keywords checked first** (`exists but`, `discrepan`, `mismatch`, `differs from ac`) → `proposal_drift`
- **Gap keywords** (`not implement`, `missing`, `absent`, `todo: implement`) → `implementation_gap`
- **Ambiguous** (no keyword match) → conservative default = `implementation_gap`

Rationale: implementation_gap → `guide-ship` re-run cost < proposal_drift → `guide-plan` rewrite cost.

### Step 4: User Confirmation + Route

Per ADR-0034 §6 + user experience:

```
[AI classification result]
AC-1: implementation_gap  (code missing)
AC-2: proposal_drift      (code exists but mismatches AC)

[?] Confirm or override? (y/n/edit):
```

User options:
- `y` → accept AI labels, route per labels
- `n` → manual override per AC (re-classify)
- `e` → edit AC description (proposal drift by definition)

### Step 5: Loop State Update

```bash
bash skills/rdd-verifier/scripts/route_loop.sh "$CHANGE_NAME" "$LABEL"
# Updates .verifier-loop.json: append_classification + route
# Exit 0: routed (guide-ship / guide-plan)
# Exit 1: halted (max_loops reached, audit log written)
```

---

## Exit Codes (per ADR-0034 §7.1)

| Code | Meaning | Caller Action |
|------|---------|---------------|
| 0 | All changes verified, archive can proceed | Proceed to `archive` |
| 1 | AC fail, route decision printed to stderr | Jump to indicated phase (plan/ship) |
| 2 | Skipped (`SKIP_RDD_VERIFIER=yes`) | Proceed to `archive` (bypass) |
| 3 | ac-verifier internal error (LLM/API key) | Investigate env config |
| **4** | **Halted (max_loops exceeded)** | **Manual review required** |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SKIP_RDD_VERIFIER` | `no` | Skip 5th phase entirely (emergency only) |
| `RDDF_VERIFIER_MAX_LOOPS` | `3` | Max retry loops per change |
| `RDDF_VERIFIER_MAX_CHANGES` | `10` | Max changes per scan (cost guardrail) |
| `RDDF_VERIFIER_DRY_RUN` | `no` | Scan + suggest, no state mutation |
| `STRICT_AC_GATE` | `no` | Promote AC fail to archive blocker (shared semantic with archive_gate_check) |
| `FORCE_ARCHIVE_BYPASS_VERIFIER` | `no` | Bypass halted state for force-archive |

---

## Audit Log

When `route="halted"`, append to `.rddf/state/.ac-verifier-blocked.jsonl`:

```json
{
  "ts": "2026-08-26T...",
  "change": "my-change",
  "loop_count": 3,
  "classifications": ["implementation_gap", "implementation_gap", "proposal_drift"],
  "last_label": "proposal_drift",
  "halt_reason": "max_loops=3 reached with label=proposal_drift",
  "codebase_commit": "abc1234"
}
```

This log is read-only forensic record. `rdd-doctor --category plan-tdd` can check it during diagnostics.

---

## State Files Owned

| File | Schema | Purpose |
|------|--------|---------|
| `.rddf/state/.verifier-loop.json` | `verifier_loop_schema.json` v1 | Loop count, classification history, route, halt reason |
| `.rddf/state/.ac-verdict-<name>.json` | `ac_verdict_cache_schema.json` v1 | SHA-fingerprint verdict cache (shared with archive_gate_check) |
| `.rddf/state/.ac-verifier-blocked.jsonl` | append-only JSONL | Audit log for halted changes |

All 3 files are `.rddf/state/` gitignored, per AGENTS.md state file convention.

---

## Sub-Skills Referenced

| Sub-skill | Purpose | Type |
|-----------|---------|------|
| `ac-verifier` | LLM-based AC verification (mock-able) | Bash wrapper + Python |
| `guide-plan` | Proposal/spec rewrite (loop-back target) | Phase |
| `guide-ship` | Code re-execution (loop-back target) | Phase |
| `archive` | Final archive (only after verify pass) | Phase |

---

## See Also

- Spec: `docs/superpowers/specs/2026-08-26-rdd-verifier-design.md`
- Plan: `docs/superpowers/plans/2026-08-26-rdd-verifier-implementation.md`
- ADR: `docs/adr/ADR-0034-rdd-verifier-verify-phase-architecture.md`
- Oracle 评审: 82/100 分
- `_lib/verifier/`: heuristic classification + SHA cache + loop state modules
- `skills/rdd-verifier/scripts/`: 4 bash orchestration helpers
- `_lib/cli/rdd_verify_cmd.py`: `rddf rdd-verify` CLI backend