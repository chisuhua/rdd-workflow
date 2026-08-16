# backfill-proposal-approved-col4 Implementation Plan

> TDD 5-step structure. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修 `proposal-approved.md` column drift + 升级 rdd-doctor 检查至 CRITICAL + 加 CI gate。

**Architecture:** Investigation-first — 先 awk 验证 column 分布 → 修复任何真正 drift → 修改 rdd-doctor 检查返回 CRITICAL → 加 CI step。

---

### Task 1: 调查 column 分布

- [x] **Step 1: Write failing audit script** — 创建 `skills/rdd-doctor/scripts/investigate_column_drift.sh`(检测 proposal-approved.md 中每行 | 数)
- [x] **Step 2: Run audit, verify baseline** — `bash skills/rdd-doctor/scripts/investigate_column_drift.sh proposal-approved.md`(应该有 152 行 4-col,0 行 3-col)
- [x] **Step 3: Document findings** — 写 `docs/adr/ADR-XXXX-proposal-approved-format.md`(记录 4-col 约定)
- [x] **Step 4: Verify investigation matches doctor findings** — 对比 awk 输出 vs `rddf doctor --category proposal-table --json`
- [x] **Step 5: Defer commit**

### Task 2: 升级 rdd-doctor 严重度

- [x] **Step 1: Write failing test** — `tests/unit/test_proposal_table_severity.py`(期望 CRITICAL on drift)
- [x] **Step 2: Verify test fails** — 跑测试应 FAIL(WARNING not CRITICAL)
- [x] **Step 3: Modify check severity** — `skills/rdd-doctor/scripts/checks/proposal_table_check.py::run()` 改 WARNING → CRITICAL
- [x] **Step 4: Verify test passes** — 跑测试应 PASS
- [x] **Step 5: Defer commit**

### Task 3: CI gate

- [x] **Step 1: Add workflow step** — `.github/workflows/test.yml` 加 `rddf doctor --category proposal-table --quiet` 到"断言质量门控"section
- [x] **Step 2: Verify CI config** — `cat .github/workflows/test.yml | grep proposal-table`
- [x] **Step 3: Defer commit**

### Task 4: Final verify

- [x] **Step 1: Run all checks** — `rddf doctor --category proposal-table --quiet`(exit 0) + `python3 -m pytest tests/unit/test_proposal_table_severity.py -v`(PASS)
- [x] **Step 2: Defer commit**
