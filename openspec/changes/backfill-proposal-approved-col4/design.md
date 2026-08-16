# backfill-proposal-approved-col4 — Design

> Schema: spec-driven
> See: `proposal.md` for motivation, scope and acceptance criteria.

## Context

`rdd-doctor` proposal-table check reports 150 WARNING in `proposal-approved.md`. The check verifies each row has exactly 4 columns matching the index template (`提案 | 优先级 | 来源 | 添加时间`). Drift likely arose when historical rows were appended without strict format enforcement.

This design addresses:
1. Real column drift in `proposal-approved.md` (if any)
2. False positives from check heuristic
3. Lack of CI gate preventing future drift
4. Severity escalation (WARNING → CRITICAL) when the check fails

## Goals / Non-Goals

**Goals:**
- Fix any actual 3-column or 5-column rows
- Upgrade rdd-doctor check severity to CRITICAL
- Add CI gate in `.github/workflows/test.yml`
- Add new bats test covering format compliance

**Non-Goals:**
- Backfill old plan files (separate concern, handled by `enforce-plan-tdd-5step-new`)
- Modify `proposal-suggestions.md` (just refactored, structurally sound)
- Touch ADRs (none reference this drift)

## Decisions

### 1. Investigation-first approach

Before fixing, run `awk -F'|' '{print NF}' proposal-approved.md | sort | uniq -c` to verify the exact distribution of column counts. The 150 WARNING may include legitimate 4-column rows flagged as warnings due to trailing pipe or comment lines.

### 2. Severity upgrade

`rdd-doctor/scripts/checks/proposal_table_check.py::run()` — change return `Finding.severity` from `WARNING` to `CRITICAL` for `column_count != 4`.

### 3. CI gate

Add a new step to `.github/workflows/test.yml` "断言质量门控" section:
```yaml
- name: rdd-doctor proposal-table
  run: rddf doctor --category proposal-table --quiet
```

Failure → exit 1, blocks CI.

### 4. New test

`tests/integration/test_proposal_approved_format.bats`:
- Test: all rows in proposal-approved.md have exactly 4 columns
- Test: header row has exactly 5 cells (4 separators + empty edges)
- Test: no row contains unescaped pipe character in proposal name

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Breaking change in rdd-doctor check (other repos may have drift) | Only upgrade severity in this repo; document in CHANGELOG |
| False positives in column detection | Use proper awk parser, not regex match |
| Historical rows may be unfixable (e.g. multiline cells) | Document exceptions inline |