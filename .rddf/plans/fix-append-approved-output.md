# fix-append-approved-output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix double-echo bug in `state.sh::append_approved` where function echoes success AND caller loop echoes too, producing 2 lines per approval.

**Architecture:** Remove success echo from inside `append_approved`, keep return code semantics. Caller already has format control. Move internal log to `>&2` if needed.

**Tech Stack:** Bash, bats-core.

---

## File Structure

### Production Code
| File | Responsibility |
|---|---|
| `skills/_lib/state.sh` | Remove success echo from `append_approved` function |

### Tests
| File | Responsibility |
|---|---|
| `tests/integration/test_state_append_approved.bats` | 3 regression tests |

---

## Task 1: Write failing test for single-line output

**Files:**
- Test: `tests/integration/test_state_append_approved.bats`

@done-test1 Write failing test**

```bash
@test "append_approved: single output line per approval":
    source skills/_lib/state.sh
    run bash -c "source skills/_lib/state.sh && append_approved 'test-name'"
    # Should have at most 1 line of output (or 0)
    [ "$(echo "$output" | wc -l)" -le 1 ]
```

@done-test2 Run test, verify fail**

Run: `bats tests/integration/test_state_append_approved.bats`
Expected: FAIL (currently 1 line echo from function + would be 1 from caller = 2 lines)

- [x] **Step 3: Modify state.sh to remove internal echo**

In `state.sh`, find `append_approved` function and remove the line:
```bash
echo "✅ $name added to approved list"
```

- [x] **Step 4: Run test, verify pass**

Run: `bats tests/integration/test_state_append_approved.bats`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add skills/_lib/state.sh tests/integration/test_state_append_approved.bats
git commit -m "fix(state): remove double-echo in append_approved"
```

## Task 2: Verify return code semantics preserved

**Files:**
- Test: `tests/integration/test_state_append_approved.bats`

@done-test1 Write return code test**

```bash
@test "append_approved: returns 0 on success":
    source skills/_lib/state.sh
    run bash -c "source skills/_lib/state.sh && append_approved 'test-name'"
    [ "$status" -eq 0 ]
```

@done-test2 Run test, verify pass**

Run: `bats tests/integration/test_state_append_approved.bats`
Expected: PASS

- [x] **Step 3: Commit**

```bash
git commit -am "test(state): verify append_approved return semantics"
```
