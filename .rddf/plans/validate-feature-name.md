# validate-feature-name Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `parent_feature` name validation to rdd-workflow's propose and approve entry points, warning on typos against existing features (with `STRICT_FEATURE_VALIDATION=yes` opt-in for blocking), to prevent orphaned feature nodes in `iteration.json` that drift downstream feature views.

**Architecture:** Single-source-of-truth helper `_collect_existing_features()` reads `iteration.json` (not `roadmap-meta.yaml` to avoid double-write drift), returns the set of unique `parent_feature` values excluding `__ungrouped__`. Both entry points (Python `propose_change.py::create_skeleton_change` + bash `approve_proposal.sh`) call this helper via env-var injection, emit consistent WARNING output, and respect `STRICT_FEATURE_VALIDATION=yes` opt-in for blocking exit.

**Tech Stack:** Python 3.11+ (stdlib `json`, `os`, `pathlib`), bash (for `approve_proposal.sh`), pytest, bats.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/propose/scripts/propose_change.py` | Add `_collect_existing_features()` helper + integrate validation in `create_skeleton_change` (warning + STRICT exit) |
| `skills/guide-design/scripts/approve_proposal.sh` | Add inline `python3 -c` call to same helper before writing `roadmap-meta.yaml` (warning output matching Python) |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_validate_feature_name.py` | 3 cases: typo detection warns, correct spelling silent, empty `iteration.json` passes |

---

### Task 1: Helper implementation with TDD red→green

**Files:**
- Create: `tests/unit/test_validate_feature_name.py`
- Modify: `skills/propose/scripts/propose_change.py` (add helper at module bottom)

- [ ] **Step 1: Write the failing test (TDD red)**

Create `tests/unit/test_validate_feature_name.py`:

```python
"""Tests for _collect_existing_features() helper in propose_change.py."""
import json
import sys
from pathlib import Path

import pytest

# Add project root to sys.path so we can import the module
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "propose" / "scripts"))

from propose_change import _collect_existing_features  # noqa: E402


def _write_iteration(tmp_path: Path, changes: list[dict]) -> Path:
    """Helper: write a test iteration.json under tmp_path."""
    iter_path = tmp_path / ".rddf" / "state" / "iteration.json"
    iter_path.parent.mkdir(parents=True, exist_ok=True)
    iter_path.write_text(json.dumps({"version": 1, "changes": changes}))
    return iter_path


def test_typo_detection_returns_existing_features(tmp_path):
    """GIVEN iteration.json with parent_feature='wave-core'
       WHEN helper collects existing features
       THEN 'wave-core' is in result, typo 'wave-cores' would be detected as missing."""
    _write_iteration(tmp_path, [
        {"name": "change-a", "parent_feature": "wave-core", "status": "proposed"},
    ])
    # Patch the helper to look in tmp_path
    # (or mock the project_root parameter)
    result = _collect_existing_features(tmp_path)
    assert "wave-core" in result
    assert "wave-cores" not in result  # typo is NOT in existing set


def test_correct_spelling_silent_pass(tmp_path):
    """GIVEN iteration.json with parent_feature='wave-core'
       WHEN checking new value 'wave-core' against result
       THEN no missing (i.e., value is in set → no warning needed)."""
    _write_iteration(tmp_path, [
        {"name": "change-a", "parent_feature": "wave-core", "status": "proposed"},
    ])
    result = _collect_existing_features(tmp_path)
    # Correct spelling: result contains the value → silent pass
    assert "wave-core" in result


def test_empty_iteration_passes_all_values(tmp_path):
    """GIVEN iteration.json does not exist
       WHEN helper is called
       THEN returns empty set (any parent_feature value passes)."""
    # tmp_path has no .rddf/state/iteration.json
    result = _collect_existing_features(tmp_path)
    assert result == set()


def test_ungrouped_excluded(tmp_path):
    """GIVEN iteration.json with parent_feature='__ungrouped__'
       WHEN helper collects
       THEN __ungrouped__ is excluded (synthetic key, not user-selectable)."""
    _write_iteration(tmp_path, [
        {"name": "change-a", "parent_feature": "__ungrouped__", "status": "proposed"},
    ])
    result = _collect_existing_features(tmp_path)
    assert "__ungrouped__" not in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_validate_feature_name.py -v`
Expected: FAIL with `ImportError: cannot import name '_collect_existing_features' from 'propose_change'`

- [ ] **Step 3: Write minimal implementation**

In `skills/propose/scripts/propose_change.py`, append at module bottom (before any `if __name__ == "__main__":` block):

```python
def _collect_existing_features(project_root) -> set:
    """Collect unique parent_feature values from iteration.json, excluding __ungrouped__.

    Single source of truth: only reads .rddf/state/iteration.json (not roadmap-meta.yaml)
    to avoid double-write drift scenarios.

    Returns empty set if iteration.json is missing or has no changes.
    Excludes __ungrouped__ synthetic key (it's a fallback bucket, not user-selectable).
    """
    from pathlib import Path
    import json as _json

    iter_path = Path(project_root) / ".rddf" / "state" / "iteration.json"
    if not iter_path.is_file():
        return set()

    try:
        data = _json.loads(iter_path.read_text())
    except (ValueError, OSError):
        return set()

    features = set()
    for change in data.get("changes", []):
        pf = change.get("parent_feature")
        if pf and pf != "__ungrouped__":
            features.add(pf)
    return features
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_validate_feature_name.py -v`
Expected: PASS — 4/4 tests green

- [ ] **Step 5: Verify no regression in existing propose_change tests**

Run: `pytest tests/unit/test_propose_change*.py -q --tb=short`
Expected: all green (existing 43 tests stay green; new helper is additive)

---

### Task 2: Wire validation into `create_skeleton_change`

**Files:**
- Modify: `skills/propose/scripts/propose_change.py::create_skeleton_change` (call helper before write; emit WARNING; STRICT exit)

- [ ] **Step 1: Locate the write site**

In `skills/propose/scripts/propose_change.py`, find `create_skeleton_change` function and identify where `parent_feature` is written to `iteration.json` (the `add_or_update_change` call). Insert validation BEFORE that call.

- [ ] **Step 2: Add validation block**

```python
import os
import sys

# Inside create_skeleton_change, right before the add_or_update_change call:
existing_features = _collect_existing_features(project_root)
if parent_feature and parent_feature not in existing_features:
    msg = (
        f"⚠️  parent_feature='{parent_feature}' not in existing features "
        f"{sorted(existing_features)[:10]}"
        + (f" (and {len(existing_features) - 10} more)" if len(existing_features) > 10 else "")
        + ". Possible typo — verify spelling or use an existing feature name. "
        + "Set STRICT_FEATURE_VALIDATION=yes to block on typo."
    )
    print(msg, file=sys.stderr)
    if os.environ.get("STRICT_FEATURE_VALIDATION") == "yes":
        sys.exit(2)
```

- [ ] **Step 3: Manual smoke test**

Run a quick interactive check (do NOT commit yet):
```bash
mkdir -p /tmp/vfn-test/.rddf/state
echo '{"version":1,"changes":[{"name":"a","parent_feature":"wave-core","status":"proposed"}]}' > /tmp/vfn-test/.rddf/state/iteration.json
PYTHONPATH=skills/propose/scripts python3 -c "
import sys
sys.path.insert(0, 'skills/propose/scripts')
from propose_change import create_skeleton_change, _collect_existing_features
print('Existing:', _collect_existing_features('/tmp/vfn-test'))
" 2>&1 | head -5
```

Expected output: `Existing: {'wave-core'}` — helper works in isolation.

- [ ] **Step 4: Run existing test suite to confirm no regression**

Run: `pytest tests/unit/test_propose_change*.py -q --tb=short`
Expected: all green (validation is non-blocking default; existing tests don't trigger validation)

---

### Task 3: Wire validation into `approve_proposal.sh` (bash side)

**Files:**
- Modify: `skills/guide-design/scripts/approve_proposal.sh` (add inline python3 helper call before `roadmap-meta.yaml` write)

- [ ] **Step 1: Locate the parent_feature write site**

In `skills/guide-design/scripts/approve_proposal.sh`, find where `roadmap-meta.yaml` is written (the `cat > "$CHANGE_DIR/roadmap-meta.yaml" <<EOF` block with `parent_feature: "$PARENT_FEATURE"`).

- [ ] **Step 2: Insert validation block before the write**

Add this BEFORE the `cat > "$CHANGE_DIR/roadmap-meta.yaml" <<EOF` line:

```bash
# Validate parent_feature against existing features (D4 design-proposal-creation)
if [ -n "$PARENT_FEATURE" ] && [ "$PARENT_FEATURE" != "__ungrouped__" ]; then
    VALIDATION_OUTPUT=$(PROJECT_ROOT="$PROJECT_ROOT" PARENT_FEATURE="$PARENT_FEATURE" \
        STRICT_FEATURE_VALIDATION="${STRICT_FEATURE_VALIDATION:-}" \
        python3 - <<'PYEOF'
import os
import sys
from pathlib import Path
sys.path.insert(0, "skills/propose/scripts")
from propose_change import _collect_existing_features
existing = _collect_existing_features(os.environ["PROJECT_ROOT"])
pf = os.environ["PARENT_FEATURE"]
strict = os.environ.get("STRICT_FEATURE_VALIDATION", "") == "yes"
if pf and pf not in existing:
    listed = sorted(existing)[:10]
    suffix = f" (and {len(existing) - 10} more)" if len(existing) > 10 else ""
    msg = (
        f"⚠️  parent_feature='{pf}' not in existing features {listed}{suffix}. "
        f"Possible typo — verify spelling or use an existing feature name."
    )
    print(msg, file=sys.stderr)
    sys.exit(2 if strict else 0)
PYEOF
    ) || {
        rc=$?
        if [ "$rc" -eq 2 ]; then
            echo "❌ parent_feature validation blocked approve (STRICT_FEATURE_VALIDATION=yes)" >&2
            exit 2
        fi
    }
fi
```

- [ ] **Step 3: Verify bats tests still pass**

Run: `bats tests/integration/test_approve_proposal_*.bats`
Expected: 8/9 pass (1 known failure per `tests/KNOWN_FAILURES.txt` baseline). If a NEW failure appears, the validation is too aggressive — fix or relax.

---

### Task 4: Final validation suite

**Files:** (no file changes)

- [ ] **Step 1: Run Python unit suite**

Run: `pytest tests/unit/ -q --tb=short`
Expected: all green (including new 4 test_validate_feature_name.py cases)

- [ ] **Step 2: Run Python integration suite**

Run: `pytest tests/integration/ -q --tb=short`
Expected: all green

- [ ] **Step 3: Run smoke bats**

Run: `bats tests/smoke.bats`
Expected: all green (smoke covers skill discovery, no regression from new files)

- [ ] **Step 4: Run quick regression check**

Run: `./test.sh --quick`
Expected: all green (or only baseline known failures)

- [ ] **Step 5: Aggregate commit (worktree commit flow)**

Per v2.0.5+ worktree commit flow rule (lightweight mode still requires commit before archive):
```bash
cd "$(git rev-parse --show-toplevel)"
git status --short
git add -A
git commit -m "feat(propose): add parent_feature validation to propose + approve entry points

- New _collect_existing_features() helper in propose_change.py (single source of truth from iteration.json, excludes __ungrouped__)
- create_skeleton_change: warning on missing feature (default), STRICT_FEATURE_VALIDATION=yes opt-in for blocking
- approve_proposal.sh: same helper via inline python3 invocation, matching output format
- New test_validate_feature_name.py with 4 cases (typo, match, empty baseline, __ungrouped__ exclusion)

Acceptance:
- [x] tests/unit/test_validate_feature_name.py 4/4 green
- [x] tests/unit/test_propose_change*.py 43/43 still green
- [x] tests/integration/test_approve_proposal_*.bats 8/9 still green (1 known failure)"
git log -1 --oneline
```

Expected: 1 new commit on `openspec/validate-feature-name` branch.

---

## Notes

- Default behavior is non-blocking warning (matches `STRICT_DESIGN_GATE` / `STRICT_ARCH_GATE` opt-in philosophy)
- `__ungrouped__` is excluded from the existing-feature set (synthetic fallback bucket, not user-selectable)
- Helper is the SINGLE source of truth — both entry points call the same function
- `roadmap-meta.yaml` is intentionally NOT read by the helper (avoids double-write drift scenarios, per design Decision 1)
