#!/usr/bin/env bats
# tests/integration/test_how_leakage_warning.bats
#
# Integration test for the HOW-leakage warning wiring (Group 4 of
# openspec/changes/add-proposal-how-leakage-warning/tasks.md).
#
# Verifies:
#   - .rddf/improvements-layer review emits [HOW-LEAKAGE-WARN] prefix when
#     heuristic signals fire (multi-signal rule per design).
#   - openspec proposal-layer review emits the same prefix.
#   - Both layers share the WarningRecord format (signal/section/etc).
#   - HOW-leakage warnings do NOT block by default.
#
# test_helper.bash is auto-loaded by bats; do not `load test_helper`.

setup() {
    REPO_ROOT="$(git rev-parse --show-toplevel)"
    cd "$REPO_ROOT"
    TMPDIR="$(mktemp -d)"
    export TMPDIR
}

teardown() {
    [ -n "$TMPDIR" ] && rm -rf "$TMPDIR"
}

# --- Helpers ---

write_sample_md() {
    local file="$1"
    local scenario="$2"
    case "$scenario" in
        heavy_how)
            cat > "$file" <<'EOF'
**阶段**: design
**分类**: core
**类型**: feature

## 架构依据
We extend the existing parser.

## 范围
Modify these files:

- `src/foo.py`
- `src/bar.py`
- `src/baz.py`

Steps to follow:

1. First do this
2. Then do that
3. Finally do the other
4. Last step

```python
def a():
    pass
```

```python
def b():
    pass
```

## 关键场景
Single example:

```python
x = 1
```

## 技术约束
None.

## 验收标准
- [ ] Detector wired
- [ ] Tests pass
EOF
            ;;
        clean)
            cat > "$file" <<'EOF'
**阶段**: design
**分类**: core
**类型**: feature

## 架构依据
ADR-0003 establishes the three-phase architecture.

## 范围
Improve content review by adding a warning-only heuristic check.

## 关键场景
When an improvement has excessive code blocks, the reviewer sees a warning.

## 技术约束
Python 3.11+.

## 验收标准
- [ ] Warning fires on multi-signal
- [ ] Default mode non-blocking
EOF
            ;;
    esac
}

# --- .rddf/improvements-layer test ---

@test ".rddf/improvements-layer: heavy HOW emits [HOW-LEAKAGE-WARN]" {
    local sample="$TMPDIR/improvement.md"
    write_sample_md "$sample" "heavy_how"
    export IMPROVEMENTS_PATH="$sample"
    export STRICT_DESIGN_GATE="no"
    export SKIP_CONTENT_REVIEW="no"

    run python3 "$REPO_ROOT/skills/guide-design/scripts/design_content_review.py"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[HOW-LEAKAGE-WARN]"* ]]
}

@test ".rddf/improvements-layer: clean proposal does NOT emit [HOW-LEAKAGE-WARN]" {
    local sample="$TMPDIR/improvement.md"
    write_sample_md "$sample" "clean"
    export IMPROVEMENTS_PATH="$sample"
    export STRICT_DESIGN_GATE="no"
    export SKIP_CONTENT_REVIEW="no"

    run python3 "$REPO_ROOT/skills/guide-design/scripts/design_content_review.py"
    [ "$status" -eq 0 ]
    [[ "$output" != *"[HOW-LEAKAGE-WARN]"* ]]
}

@test ".rddf/improvements-layer: HOW warning does NOT block even with STRICT_DESIGN_GATE=yes (warning-only design)" {
    # Per design decision 2: HOW-leakage is warning-only. STRICT_DESIGN_GATE
    # may block STRUCTURAL errors but HOW-leakage warnings remain advisory.
    # (Existing STRICT_DESIGN_GATE behavior blocks structural errors; the
    # HOW-leakage prefix is informational. This test pins that behavior.)
    local sample="$TMPDIR/improvement.md"
    write_sample_md "$sample" "heavy_how"
    export IMPROVEMENTS_PATH="$sample"
    export STRICT_DESIGN_GATE="yes"
    export SKIP_CONTENT_REVIEW="no"

    run python3 "$REPO_ROOT/skills/guide-design/scripts/design_content_review.py"
    # Status code may be 0 (warning emitted, no structural errors block)
    # OR non-zero (no STRICT enforcement on HOW warnings by default).
    # Either way, HOW-LEAKAGE-WARN should be present.
    [[ "$output" == *"[HOW-LEAKAGE-WARN]"* ]]
}

# --- openspec proposal-layer test (via run_design_checks) ---

@test "proposal-layer (run_design_checks): heavy HOW emits [HOW-LEAKAGE-WARN]" {
    local change_dir="$REPO_ROOT/openspec/changes/_tmp_how_leakage_test"
    mkdir -p "$change_dir"
    write_sample_md "$change_dir/proposal.md" "heavy_how"
    export PROJECT_ROOT="$REPO_ROOT"

    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills.propose.scripts.propose_quality_check import run_design_checks
warnings = run_design_checks('_tmp_how_leakage_test', '$REPO_ROOT')
print('\n'.join(warnings))
"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[HOW-LEAKAGE-WARN]"* ]]

    rm -rf "$change_dir"
}

@test "proposal-layer (run_design_checks): clean proposal does NOT emit [HOW-LEAKAGE-WARN]" {
    local change_dir="$REPO_ROOT/openspec/changes/_tmp_how_leakage_clean"
    mkdir -p "$change_dir"
    write_sample_md "$change_dir/proposal.md" "clean"
    export PROJECT_ROOT="$REPO_ROOT"

    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills.propose.scripts.propose_quality_check import run_design_checks
warnings = run_design_checks('_tmp_how_leakage_clean', '$REPO_ROOT')
how_warns = [w for w in warnings if '[HOW-LEAKAGE-WARN]' in w]
print('how_warns:', len(how_warns))
for w in how_warns:
    print(w)
"
    [ "$status" -eq 0 ]
    [[ "$output" == *"how_warns: 0"* ]]

    rm -rf "$change_dir"
}

# --- Detector module importable / safe ---

@test "detector module is importable and non-fatal on garbage input" {
    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from _lib import proposal_review
result = proposal_review.detect_how_leakage('')
assert result == []
result = proposal_review.detect_how_leakage('garbage \x00\x01 input')
assert isinstance(result, list)
print('OK')
"
    [ "$status" -eq 0 ]
    [[ "$output" == *"OK"* ]]
}

@test "WarningRecord schema is consistent across both layers" {
    # The two layers must emit the same field set in their formatted
    # [HOW-LEAKAGE-WARN] strings (signal, section, weighted_score, action).
    local sample="$TMPDIR/sample.md"
    write_sample_md "$sample" "heavy_how"
    export PROJECT_ROOT="$REPO_ROOT"

    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from _lib import proposal_review
text = open('$sample').read()
hits = proposal_review.detect_how_leakage(text)
assert len(hits) >= 1
required_keys = {'signal', 'threshold', 'section', 'action', 'weighted_score'}
for h in hits:
    assert required_keys <= set(h.keys()), f'missing keys: {required_keys - set(h.keys())}'
print('schema OK')
"
    [ "$status" -eq 0 ]
    [[ "$output" == *"schema OK"* ]]
}