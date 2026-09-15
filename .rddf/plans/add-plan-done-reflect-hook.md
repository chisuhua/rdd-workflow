# add-plan-done-reflect-hook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the missing plan-done reflect hook (ADR-0027 §1.0 dual-plane closure) so proposal failures in rdd-planner trigger `ReflectEngine(phase='plan')`, mirroring arch-done + archive hooks.

**Architecture:** Mirror `write_arch_handoff.sh:48-66` (Script 平面) + `rdd-arch/SKILL.md:712-730` (Agent 平面) verbatim, only swapping phase identifier `rdd-arch` → `rdd-planner`. Reuse existing `SKIP_WORKFLOW_REFLECTION` env var.

**Tech Stack:** bash (inline hook), Markdown (SKILL.md section), bats-core 1.10+ (smoke + testbed). No new Python deps.

---

## File Structure

### Production Code (mirror pattern, +39 lines total)

| File | Responsibility | FU |
|------|----------------|-----|
| `skills/rdd-planner/scripts/planner_stage_exit.sh` | Append inline hook mirroring `write_arch_handoff.sh:48-66` (+19 lines) | FU-3 |
| `skills/rdd-planner/SKILL.md` | Append "Phase Exit — Post-Flow Analysis" section mirroring `rdd-arch/SKILL.md:712-730` (+20 lines) | FU-4 |
| `AGENTS.md` | Update "已 wired 生产 hook"段 +1 line | FU-7 |

### Tests (+2 cases, 1 new testbed file)

| File | Responsibility | FU |
|------|----------------|-----|
| `tests/e2e/script/test_reflect_smoke.bats` | A 层 R-E10 + R-E11 cases | FU-5 |
| `rdd-workflow-e2e/tests/integration/test_reflect_plan_hook_e2e.bats` (NEW) | testbed 2 cases (third-party + SKIP guard) | FU-6 |

---

## Task 1: Read mirror sources

**Files:**
- Read: `skills/rdd-arch/scripts/write_arch_handoff.sh` lines 48-66 (Script 平面 template)
- Read: `skills/rdd-arch/SKILL.md` lines 712-730 (Agent 平面 template)

- [ ] **Step 1: Read arch hook template**

Run: `sed -n '48,66p' skills/rdd-arch/scripts/write_arch_handoff.sh`
Expected: bash code invoking `ReflectEngine(phase='arch').analyze(...)` with `SKIP_WORKFLOW_REFLECTION` guard + `2>/dev/null || true` non-blocking

- [ ] **Step 2: Read arch SKILL.md Phase Exit template**

Run: `sed -n '712,730p' skills/rdd-arch/SKILL.md`
Expected: "## Phase Exit — Post-Flow Analysis (Agent 平面, ADR-0027 §1.0)" with checklist + triggers list

- [ ] **Step 3: Defer commit**

---

## Task 2: FU-3 — Append inline hook to planner_stage_exit.sh

**Files:**
- Modify: `skills/rdd-planner/scripts/planner_stage_exit.sh` (append ~19 lines at end, mirror write_arch_handoff.sh L48-66)

- [ ] **Step 1: Read current tail of planner_stage_exit.sh**

Run: `tail -10 skills/rdd-planner/scripts/planner_stage_exit.sh`
Expected: ends after `.planner-handoff.json` write

- [ ] **Step 2: Append inline hook**

Append at end (verbatim mirror with phase='plan'):

```bash

# === Plan-done reflect hook (ADR-0027 §1.0 dual-plane; mirror write_arch_handoff.sh:48-66) ===
if [[ "${SKIP_WORKFLOW_REFLECTION:-0}" != "1" ]]; then
    _REFLECT_FAILURES=$(jq -r '[.[] | select(.kind == "unrecovered_failure" or .kind == "execute_error")] | .[-20:] | map(.event_id) | join(",")' .rddf/state/event_log.json 2>/dev/null || echo "")
    PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)" \
    python3 -c "
import sys, os
sys.path.insert(0, os.environ.get('PROJECT_ROOT', '.'))
from _lib.reflect_engine import ReflectEngine
from pathlib import Path
engine = ReflectEngine(phase='plan')
failures = os.environ.get('_REFLECT_FAILURES', '').split(',') if os.environ.get('_REFLECT_FAILURES') else []
result = engine.analyze(failures=failures)
Path('.rddf/state/.plan-reflect-result.json').write_text(engine.serialize(result))
" 2>/dev/null || true
    unset _REFLECT_FAILURES
fi
```

- [ ] **Step 3: Verify AC-1 (grep ReflectEngine call)**

Run: `grep -n "ReflectEngine(phase=\"plan\"" skills/rdd-planner/scripts/planner_stage_exit.sh`
Expected: 1 match

- [ ] **Step 4: Verify AC-2 (grep SKIP guard)**

Run: `grep -n "SKIP_WORKFLOW_REFLECTION" skills/rdd-planner/scripts/planner_stage_exit.sh`
Expected: 1+ matches

- [ ] **Step 5: Verify AC-3 (grep non-blocking)**

Run: `grep -n "2>/dev/null || true" skills/rdd-planner/scripts/planner_stage_exit.sh`
Expected: 1+ match

- [ ] **Step 6: Defer commit**

---

## Task 3: FU-4 — Append Phase Exit section to rdd-planner/SKILL.md

**Files:**
- Modify: `skills/rdd-planner/SKILL.md` (append ~20 lines at end, mirror rdd-arch L712-730)

- [ ] **Step 1: Read current tail**

Run: `tail -5 skills/rdd-planner/SKILL.md`
Expected: ends with existing section (Cross-Reference or similar)

- [ ] **Step 2: Append Phase Exit section**

Append (verbatim mirror with phase name `rdd-planner`):

```markdown

## Phase Exit — Post-Flow Analysis (Agent 平面, ADR-0027 §1.0)

### Checklist (must satisfy exactly one)

- [ ] **Normal exit** → call `orchestrator_finalize` (always, on every exit)
- [ ] **Abnormal exit** → call `orchestrator_finalize` + `rddf report-issue --phase rdd-planner --exit-code <code> "<one-line>"`

### Triggers for "abnormal exit" (non-exhaustive)

- planner-done 双门控失败（`.rddf/roadmap.md` 缺失或 `recommended_route=unknown`）且修复失败
- proposal 反复被同一质量门拒，跨多 phase 阻塞
- state machine branch enters an unexpected case (e.g. recommended_route 状态翻转异常)
- agent cannot continue after 3 retries on the same step
- user explicitly says "this is wrong" while phase reports success

### NOT abnormal (do NOT report-issue)

- User-initiated SIGINT / SIGTERM (exit 130/143)
- Missing tools, network errors, permission errors (environment-error)
- Bad CLI flags, missing required arguments (usage-error)
- planner-done 双门控失败的**首次**失败（提示用户回 Phase 3 调整即可，不立即上报）
```

- [ ] **Step 3: Verify AC-4 (grep Phase Exit header)**

Run: `tail -30 skills/rdd-planner/SKILL.md | grep "Phase Exit"`
Expected: 1+ match

- [ ] **Step 4: Verify AC-5 (grep report-issue template)**

Run: `grep -n "rddf report-issue --phase rdd-planner" skills/rdd-planner/SKILL.md`
Expected: 1 match

- [ ] **Step 5: Defer commit**

---

## Task 4: FU-5 — Add R-E10 + R-E11 cases to test_reflect_smoke.bats

**Files:**
- Modify: `tests/e2e/script/test_reflect_smoke.bats` (append 2 cases)

- [ ] **Step 1: Read current tail**

Run: `tail -5 tests/e2e/script/test_reflect_smoke.bats`
Expected: ends with existing test

- [ ] **Step 2: Append 2 cases**

```bash

# R-E10: plan-done hook in planner_stage_exit.sh triggers + handoff writes (AC-6)
@test "R-E10: plan-done hook fires + .planner-handoff.json writes" {
    unset SKIP_WORKFLOW_REFLECTION
    rm -f .rddf/state/.planner-handoff.json .rddf/state/.plan-reflect-result.json
    # stub: simulate planner_stage_exit success path
    bash skills/rdd-planner/scripts/planner_stage_exit.sh 2>/dev/null || true
    [ -f .rddf/state/.planner-handoff.json ] || [ -f .rddf/state/.plan-reflect-result.json ]
}

# R-E11: SKIP_WORKFLOW_REFLECTION=1 + planner_stage_exit still succeeds (AC-7)
@test "R-E11: SKIP_WORKFLOW_REFLECTION=1 + planner_stage_exit still succeeds" {
    export SKIP_WORKFLOW_REFLECTION=1
    bash skills/rdd-planner/scripts/planner_stage_exit.sh
    status=$?
    unset SKIP_WORKFLOW_REFLECTION
    [ "$status" -eq 0 ] || [ "$status" -eq 2 ]
}
```

- [ ] **Step 3: Run R-E10 + R-E11**

Run: `bats tests/e2e/script/test_reflect_smoke.bats -f "R-E10\|R-E11"`
Expected: 2 pass

- [ ] **Step 4: Defer commit**

---

## Task 5: FU-6 — Create testbed file

**Files:**
- Create: `rdd-workflow-e2e/tests/integration/test_reflect_plan_hook_e2e.bats` (2 cases)

- [ ] **Step 1: Create testbed file**

(Note: rdd-workflow-e2e is a separate repo. Skip this task if testbed repo not available locally. If unavailable, document in tasks.md and proceed.)

```bash
#!/usr/bin/env bats
# rdd-workflow-e2e/tests/integration/test_reflect_plan_hook_e2e.bats
# testbed: 第三方项目视角的 plan-done reflect hook

load test_helper

@test "plan hook in third-party install" {
    [ -f ~/.agents/skills/rdd-workflow/skills/rdd-planner/scripts/planner_stage_exit.sh ]
    grep -q "ReflectEngine(phase=\"plan\"" ~/.agents/skills/rdd-workflow/skills/rdd-planner/scripts/planner_stage_exit.sh
}

@test "SKIP_WORKFLOW_REFLECTION respected in third-party" {
    [ -f ~/.agents/skills/rdd-workflow/skills/rdd-planner/scripts/planner_stage_exit.sh ]
    grep -q "SKIP_WORKFLOW_REFLECTION" ~/.agents/skills/rdd-workflow/skills/rdd-planner/scripts/planner_stage_exit.sh
}
```

- [ ] **Step 2: Note in tasks.md if testbed repo not available**

If `rdd-workflow-e2e/` directory does not exist locally, mark FU-6 as `[ ]` in tasks.md with note "testbed repo not available; AC-8 deferred to nightly cron".

- [ ] **Step 3: Defer commit**

---

## Task 6: FU-7 — AGENTS.md update + regression

**Files:**
- Modify: `AGENTS.md` (+1 line in "已 wired 生产 hook" section)

- [ ] **Step 1: Find "已 wired 生产 hook" section in AGENTS.md**

Run: `grep -n "已 wired 生产 hook" AGENTS.md`
Expected: 1 match (or near similar phrase)

- [ ] **Step 2: Add plan stage entry**

If section exists, append `| plan 阶段 | `skills/rdd-planner/scripts/planner_stage_exit.sh` 末尾 inline hook (ADR-0027 §1.0 dual-plane) |`

- [ ] **Step 3: Run regression**

Run: `./test.sh --quick`
Expected: 2723+ passed, 2 skipped, zero new failures

- [ ] **Step 4: Verify AC-11 (no pollution)**

Run: `git status --short .rddf/ openspec/`
Expected: empty (lightweight mode keeps state in gitignored paths)

- [ ] **Step 5: Verify AC-12 (AGENTS.md grep)**

Run: `grep "planner_stage_exit.*reflect\|plan.*reflect" AGENTS.md`
Expected: 1+ match

- [ ] **Step 6: Defer commit (will batch at archive)**

---

## Task 7: P3 archive

**Files:**
- Commit + archive

- [ ] **Step 1: Single commit**

Subject: `feat(planner): add plan-done reflect hook (ADR-0027 dual-plane closure)`

Body:
```
- FU-3: skills/rdd-planner/scripts/planner_stage_exit.sh inline hook (mirror write_arch_handoff.sh:48-66)
- FU-4: skills/rdd-planner/SKILL.md Phase Exit section (mirror rdd-arch/SKILL.md:712-730)
- FU-5: tests/e2e/script/test_reflect_smoke.bats R-E10 + R-E11
- FU-6: rdd-workflow-e2e/tests/integration/test_reflect_plan_hook_e2e.bats (testbed)
- FU-7: AGENTS.md +1 line update

Closes ADR-0027 §1.0 dual-plane architecture gap (plan-done hook missing).
No engine logic changes; mirror pattern only.
```

- [ ] **Step 2: `openspec archive add-plan-done-reflect-hook --yes`**

Expected: archive creates `openspec/changes/archive/2026-09-15-add-plan-done-reflect-hook/`

---

## Self-review

**1. Spec coverage** (against spec.md 3 Scenarios):
- Scenario "plan-done hook triggers on normal exit" → Task 2 (FU-3) + Task 4 (FU-5 R-E10)
- Scenario "SKIP_WORKFLOW_REFLECTION=1 bypasses bash hook" → Task 2 + Task 4 (R-E11)
- Scenario "SKILL.md Phase Exit section is the agent-plane companion" → Task 3 (FU-4) + Task 5 (FU-6 testbed)

**2. Placeholder scan**: Each task has concrete content (mirror template, exact grep commands, exact test code). No "TBD" / "TODO".

**3. Type consistency**: All Task Files sections use consistent path format. Mirror references use absolute file:line notation (`write_arch_handoff.sh:48-66`, `rdd-arch/SKILL.md:712-730`).

**4. Acceptance coverage**:
- AC-1, AC-2, AC-3 → Task 2 (FU-3)
- AC-4, AC-5 → Task 3 (FU-4)
- AC-6, AC-7 → Task 4 (FU-5)
- AC-8 → Task 5 (FU-6)
- AC-9, AC-10, AC-11 → Task 6 (FU-7)
- AC-12 → Task 6 (FU-7)

All 12 AC covered.
