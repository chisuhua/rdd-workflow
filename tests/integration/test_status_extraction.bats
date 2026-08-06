#!/usr/bin/env bats
# tests/integration/test_status_extraction.bats
# Status extraction regression: Mode B sync detection/repair and Mode E
# iteration rendering were inlined as bash heredocs in status.md. They
# were extracted to:
#   - _lib/status_helpers.sh (detect_sync_issues, repair_sync_state)
#   - _lib/iteration.py::print_view
#
# These tests lock the refactor in place:
#   1. status_helpers.sh exists with detect_sync_issues and
#      repair_sync_state defined.
#   2. status.md Mode B sources the helper and calls both functions
#      (positive grep), and no longer inlines the bash heredocs
#      (negative grep on patterns that ONLY appeared in the old code).
#   3. iteration.py::print_view is defined and importable; status.md
#      Mode E uses the named import and no longer inlines the render
#      heredoc (negative grep on the old import alias).
#   4. Runtime: detect_sync_issues returns 1 when no issues, 0 when
#      Class 1 (PLAN_DONE > TASKS_DONE) fires. repair_sync_state marks
#      `- [ ]` to `- [x]` on the first matching line.

load ../test_helper

@test "_lib/status_helpers.sh exists with detect_sync_issues function" {
  [ -f "$REPO_ROOT/_lib/status_helpers.sh" ]
  grep -qE '^detect_sync_issues\(\)' "$REPO_ROOT/_lib/status_helpers.sh"
}

@test "_lib/status_helpers.sh also defines repair_sync_state" {
  [ -f "$REPO_ROOT/_lib/status_helpers.sh" ]
  grep -qE '^repair_sync_state\(\)' "$REPO_ROOT/_lib/status_helpers.sh"
}

@test "status.md Mode B sources and uses status_helpers.sh::detect_sync_issues" {
  [ -f "$REPO_ROOT/skills/status/SKILL.md" ]
  grep -nE 'source .*_lib/status_helpers.sh' "$REPO_ROOT/skills/status/SKILL.md"
  grep -nE 'detect_sync_issues "\$PROJECT_ROOT"' "$REPO_ROOT/skills/status/SKILL.md"
}

@test "status.md Mode B Step 3 uses status_helpers.sh::repair_sync_state" {
  [ -f "$REPO_ROOT/skills/status/SKILL.md" ]
  grep -nE 'repair_sync_state "\$PROJECT_ROOT"' "$REPO_ROOT/skills/status/SKILL.md"
}

@test "status.md Mode B no longer inlines the sync-detection bash heredoc" {
  [ -f "$REPO_ROOT/skills/status/SKILL.md" ]
  # The old inline used a `mktemp` call to stage the tasks.md edit.
  # That mktemp pattern is now ONLY in status_helpers.sh — must not
  # appear in status.md anymore.
  ! grep -nE 'mktemp -t status_tasks_XXXXXX.md' "$REPO_ROOT/skills/status/SKILL.md"
  # The old inline also used an awk substitution with desc=… variable.
  # Same story — must not appear in status.md anymore.
  ! grep -nE 'awk -v desc=' "$REPO_ROOT/skills/status/SKILL.md"
}

@test "_lib/iteration package::print_view is defined and importable" {
  # v2.0.8 Phase 3: iteration.py (single file) was promoted to a package
  # at _lib/iteration/ with __init__.py re-exporting print_view
  # from render.py. The import path `from skills._lib.iteration import
  # print_view` is unchanged.
  [ -d "$REPO_ROOT/_lib/iteration" ]
  [ -f "$REPO_ROOT/_lib/iteration/__init__.py" ]
  grep -qE 'print_view' "$REPO_ROOT/_lib/iteration/__init__.py"
  grep -qE '^def print_view\(' "$REPO_ROOT/_lib/iteration/render.py"
  REPO_ROOT="$REPO_ROOT" python3 -c '
import os, sys
sys.path.insert(0, os.environ["REPO_ROOT"])
from skills._lib.iteration import print_view
# Run against a scratch dir with no iteration.json so the
# "missing file" notice path is exercised (the project root has a
# real iteration.json which would render the active table instead).
import tempfile, io
from contextlib import redirect_stdout
scratch = tempfile.mkdtemp()
buf = io.StringIO()
with redirect_stdout(buf):
    rc = print_view(scratch)
assert rc == 0, f"print_view returned {rc}"
out = buf.getvalue()
assert "iteration.json" in out, f"expected missing-file notice, got: {out!r}"
print("OK")
'
}

@test "status.md Mode E uses iteration.py::print_view" {
  [ -f "$REPO_ROOT/skills/status/SKILL.md" ]
  grep -nE 'from skills\._lib\.iteration import print_view' "$REPO_ROOT/skills/status/SKILL.md"
}

@test "status.md Mode E no longer inlines the iteration render heredoc" {
  [ -f "$REPO_ROOT/skills/status/SKILL.md" ]
  # The old inline used `from skills._lib import iteration as it_mod`
  # followed by inline render logic that called
  # `it_mod.derive_feature_name(c["name"])`. After extraction both
  # patterns must be gone from status.md.
  ! grep -nE 'from skills\._lib import iteration as it_mod' "$REPO_ROOT/skills/status/SKILL.md"
  ! grep -nE 'it_mod\.derive_feature_name\(c\["name"\]\)' "$REPO_ROOT/skills/status/SKILL.md"
}

# ---- Runtime tests ----

@test "detect_sync_issues: returns 1 when no issues" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO" || return 1
  git init -q
  git config user.email "test@test"
  git config user.name  "test"
  echo "x" > a && git add a && git commit -q -m "init"

  source "$REPO_ROOT/_lib/status_helpers.sh"

  run detect_sync_issues "$TEST_REPO" "no-such-change" 0 0
  [ "$status" -eq 1 ]

  cd /
  rm -rf "$TEST_REPO"
}

@test "detect_sync_issues: returns 0 when PLAN_DONE > TASKS_DONE (Class 1)" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO" || return 1
  mkdir -p .rddf/plans openspec/changes/foo
  printf -- '- [x] task 1\n- [x] task 2\n' > .rddf/plans/foo.md
  printf -- '- [x] task 1\n- [ ] task 2\n' > openspec/changes/foo/tasks.md

  source "$REPO_ROOT/_lib/status_helpers.sh"

  run detect_sync_issues "$TEST_REPO" "foo" 0 0
  [ "$status" -eq 0 ]
  [[ "$output" == *"不同步"* ]]

  rm -rf "$TEST_REPO"
}

@test "repair_sync_state: marks '- [ ]' to '- [x]' in tasks.md" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO" || return 1
  mkdir -p openspec/changes/foo
  printf -- '- [ ] task A\n- [ ] task B\n' > openspec/changes/foo/tasks.md

  source "$REPO_ROOT/_lib/status_helpers.sh"

  run repair_sync_state "$TEST_REPO" "foo" "task A"
  [ "$status" -eq 0 ]
  grep -q '^- \[x\] task A' openspec/changes/foo/tasks.md
  grep -q '^- \[ \] task B' openspec/changes/foo/tasks.md

  rm -rf "$TEST_REPO"
}

@test "repair_sync_state: returns 1 when task description not found" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO" || return 1
  mkdir -p openspec/changes/foo
  printf -- '- [ ] task A\n' > openspec/changes/foo/tasks.md

  source "$REPO_ROOT/_lib/status_helpers.sh"

  run repair_sync_state "$TEST_REPO" "foo" "no such task"
  [ "$status" -eq 1 ]

  rm -rf "$TEST_REPO"
}