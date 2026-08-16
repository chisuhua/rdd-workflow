# enforce-plan-tdd-5step-new Implementation Plan

> TDD 5-step structure. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `guide-ship/scripts/ship_plan.sh` 加 `check_plan_tdd` 入口,新 plans 缺 canonical TDD markers 阻断 archive;`SKIP_PLAN_TDD_CHECK=yes` opt-out。

**Architecture:** Reuse rdd-doctor's plan-tdd check via subprocess call — parse JSON output, exit 1 if any CRITICAL/ERROR finding. Skip via env var with audit log append.

---

### Task 1: check_plan_tdd function

- [x] **Step 1: Write failing bats test** — `tests/integration/test_guide_ship_plan_tdd_check.bats`(compliant plan passes / non-compliant fails / SKIP_PLAN_TDD_CHECK=yes skip)
- [x] **Step 2: Verify test fails** — `bats tests/integration/test_guide_ship_plan_tdd_check.bats`(应 FAIL function not found)
- [x] **Step 3: Add check_plan_tdd function** — 在 `skills/guide-ship/scripts/ship_plan.sh` 中实现 `check_plan_tdd()` 调用 `rddf doctor --category plan-tdd --quiet --json`
- [x] **Step 4: Verify test passes** — `bats tests/integration/test_guide_ship_plan_tdd_check.bats`(全 PASS)
- [x] **Step 5: Defer commit**

### Task 2: SKIP opt-out + audit

- [x] **Step 1: Write audit log helper** — `skills/_lib/ship_audit.py::append_skip_audit(change_name, reason)`
- [x] **Step 2: Integrate in check_plan_tdd** — `SKIP_PLAN_TDD_CHECK=yes` 时调 `append_skip_audit` 写入 `.rddf/state/.ship-audit.jsonl`
- [x] **Step 3: Add old-plan recommendation** — plan file mtime > 60天时输出 informational 建议
- [x] **Step 4: Defer commit**

### Task 3: Wire into Phase 1

- [x] **Step 1: Add check call in run_ship_phase1** — 在 `run_ship_phase1` 开始处加 `check_plan_tdd "$PLAN_FILE"`
- [x] **Step 2: Verify gate triggers** — 模拟 non-compliant plan,确认 exit 1 + user message
- [x] **Step 3: Defer commit**

### Task 4: Final verify

- [x] **Step 1: bats all pass** — `bats tests/integration/test_guide_ship_plan_tdd_check.bats`(4 cases)
- [x] **Step 2: pytest no regressions** — `python3 -m pytest tests/unit/ -q --tb=short`
- [x] **Step 3: openspec validate** — `openspec validate enforce-plan-tdd-5step-new`
- [x] **Step 4: Defer commit**
