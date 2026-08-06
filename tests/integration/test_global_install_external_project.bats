#!/usr/bin/env bats
# tests/integration/test_global_install_external_project.bats
#
# Simulates a third-party project that uses the GLOBAL install of rdd-workflow
# (`~/.agents/skills/`) without copying anything into its own tree. Exercises
# every entry surface:
#   - rddf CLI from PATH (~/.local/bin/rddf symlink)
#   - resolver fallback (resolve_rdd_skill_dir / resolve_rdd_lib_dir)
#   - Python `from _lib.xxx import yyy` (proves .pth works)
#   - bash `source ~/.agents/skills/_lib/state.sh` (proves runtime helpers)
#   - documented double-bootstrap pattern from external project
#
# Skip-not-fail policy: every test skips cleanly when the global install is
# absent (CI may not have run install.sh --global), so the suite remains
# runnable everywhere.

load ../test_helper

RDDF_HOME_BIN="${HOME}/.local/bin/rddf"
RDDF_GLOBAL_LIB="${HOME}/.agents/skills/_lib"

setup() {
  EXTERNAL_ROOT="${BATS_TMPDIR}/external-project-$$"
  mkdir -p "$EXTERNAL_ROOT"
  cd "$EXTERNAL_ROOT"
  # Init as a git repo so rddf's `git rev-parse --git-common-dir` detection
  # lands on this directory (not on cwd fallback).
  git init -q
  git config user.email "test@example.com"
  git config user.name "Test"
  echo "external project" > README.md
  git add README.md
  git commit -q -m "init"
  # Force PROJECT_ROOT so the resolver does NOT pick up rdd-workflow source.
  export PROJECT_ROOT="$EXTERNAL_ROOT"
  # Tiny package.json so `rddf version` has a version field to print.
  echo '{"name":"external","version":"9.9.9"}' > package.json
}

teardown() {
  rm -rf "$EXTERNAL_ROOT"
  # Intentionally do NOT touch ${BATS_TEST_DIRNAME}/../../.rddf — that's the
  # rdd-workflow source repo's runtime state dir, AND its .rddf/plans/ is
  # git-tracked. Other bats tests (test_init_smoke.bats) rely on stale state
  # files; removing them would cascade-fail unrelated suites.
}

# ── rddf CLI entry surface ─────────────────────────────────────────

@test "global_install: ~/.local/bin/rddf is a symlink to skills/cli/rddf.sh" {
  [ -L "$RDDF_HOME_BIN" ] || skip "rddf not installed globally (run install.sh --global)"
  target="$(readlink -f "$RDDF_HOME_BIN")"
  [[ "$target" == *"/skills/cli/rddf.sh" ]]
}

@test "global_install: rddf --help works from external project (no local install)" {
  [ -x "$RDDF_HOME_BIN" ] || skip "rddf not installed globally"
  cd "$EXTERNAL_ROOT"
  run "$RDDF_HOME_BIN" --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"usage:"* ]]
  [[ "$output" == *"subcommands:"* ]]
  [[ "$output" == *"version"* ]]
}

@test "global_install: rddf from non-rdd-workflow project prints friendly notice + exits 0" {
  # No .rddf/state/ in EXTERNAL_ROOT → rddf's __main__ early-exit branch
  # (line 148-150) should print a friendly message and return 0, NOT crash.
  # This is the key safety property: global install must never raise
  # stack traces when invoked from the wrong project.
  [ -x "$RDDF_HOME_BIN" ] || skip "rddf not installed globally"
  cd "$EXTERNAL_ROOT"
  run "$RDDF_HOME_BIN" version
  [ "$status" -eq 0 ]
  [[ "$output" == *"not a rdd-workflow project"* ]]
  # Must NOT contain Python traceback markers
  [[ "$output" != *"Traceback"* ]]
  [[ "$output" != *"ImportError"* ]]
}

@test "global_install: rddf version reads package.json from external project" {
  # Add a minimal .rddf/state/ so rddf enters the project branch (not early-exit),
  # then verify version subcommand reads OUR package.json, not the source repo's.
  [ -x "$RDDF_HOME_BIN" ] || skip "rddf not installed globally"
  cd "$EXTERNAL_ROOT"
  mkdir -p .rddf/state
  echo '{}' > .rddf/state/.arch-handoff.json
  run "$RDDF_HOME_BIN" version
  [ "$status" -eq 0 ]
  [[ "$output" == *"9.9.9"* ]]
  [[ "$output" != *"3.0.0"* ]]   # not the source repo's version
}

# ── Resolver fallback (the heart of cross-project isolation) ───────

@test "global_install: resolve_rdd_skill_dir falls back to ~/.agents/skills/<name>" {
  # Bootstrap pattern documented in README:
  #   source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" \
  #     2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
  # Here we use the global path directly (project-local copy absent).
  [ -f "$RDDF_GLOBAL_LIB/skill_root.sh" ] || skip "global skill_root.sh missing"
  # shellcheck source=/dev/null
  source "$RDDF_GLOBAL_LIB/skill_root.sh"
  result="$(resolve_rdd_skill_dir guide-arch)"
  [ "$result" = "$HOME/.agents/skills/guide-arch" ]
  [ -d "$result" ]
  [ -f "$result/SKILL.md" ]
}

@test "global_install: resolve_rdd_lib_dir falls back to ~/.agents/skills/_lib" {
  [ -f "$RDDF_GLOBAL_LIB/skill_root.sh" ] || skip "global skill_root.sh missing"
  # shellcheck source=/dev/null
  source "$RDDF_GLOBAL_LIB/skill_root.sh"
  result="$(resolve_rdd_lib_dir)"
  [ "$result" = "$HOME/.agents/skills/_lib" ]
  [ -d "$result" ]
  # Must be the real implementation, NOT the 14-line shim in skills/_lib/
  # (the real state.sh is > 1 KB; the shim is 367 bytes).
  size=$(stat -c %s "$result/state.sh" 2>/dev/null || stat -f %z "$result/state.sh")
  [ "$size" -gt 1000 ]
}

@test "global_install: documented double-bootstrap pattern succeeds from external project" {
  # This is the EXACT bootstrap line SKILL.md files use. From an external
  # project with no .opencode/skills/ copy, the first source fails and the
  # second source (global) succeeds — both must NOT abort the script.
  [ -f "$RDDF_GLOBAL_LIB/skill_root.sh" ] || skip "global skill_root.sh missing"
  cd "$EXTERNAL_ROOT"
  run bash -c '
    set -e
    source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" \
      2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
    type resolve_rdd_skill_dir >/dev/null
    type resolve_rdd_lib_dir >/dev/null
    echo "BOOTSTRAP_OK"
  '
  [ "$status" -eq 0 ]
  [[ "$output" == *"BOOTSTRAP_OK"* ]]
}

# ── Python module discovery (proves .pth is wired) ──────────────────

@test "global_install: Python can import _lib.gate classes from external project" {
  # Use a heredoc instead of `python3 -c` to avoid bats trying to interpret
  # `from` as a shell command (cosmetic noise in test output).
  cd "$EXTERNAL_ROOT"
  run python3 <<'PY'
from _lib.gate import GateMechanism, Severity
assert GateMechanism.__name__ == "GateMechanism", GateMechanism.__name__
assert GateMechanism.__module__ == "_lib.gate", GateMechanism.__module__
assert issubclass(Severity, object)
print("IMPORT_OK", GateMechanism.__name__, GateMechanism.__module__)
PY
  [ "$status" -eq 0 ]
  [[ "$output" == *"IMPORT_OK"* ]]
  [[ "$output" == *"GateMechanism"* ]]
}

@test "global_install: Python resolves _lib to global symlink target, not source" {
  # If a project happens to live inside a checkout that ALSO has _lib/ at
  # top-level (e.g. a sub-test), the .pth still wins because the source
  # repo is $REPO_ROOT, not $EXTERNAL_ROOT. Verify import path is correct.
  cd "$EXTERNAL_ROOT"
  run python3 -c "
import _lib
print(_lib.__file__)
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"${HOME}/.agents/skills/_lib"* ]] || \
  [[ "$output" == *"/rdd-workflow/_lib"* ]]
  # Either is acceptable; what matters is it's NOT $EXTERNAL_ROOT/_lib
  [[ "$output" != *"${EXTERNAL_ROOT}"* ]]
}

# ── Bash runtime helpers (proves _lib/*.sh resolves) ────────────────

@test "global_install: bash can source _lib/state.sh from external project" {
  [ -f "$RDDF_GLOBAL_LIB/state.sh" ] || skip "global state.sh missing"
  cd "$EXTERNAL_ROOT"
  run bash -c "
    source '$RDDF_GLOBAL_LIB/state.sh'
    type safe_python_json >/dev/null
    echo 'STATE_SH_OK'
  "
  [ "$status" -eq 0 ]
  [[ "$output" == *"STATE_SH_OK"* ]]
}

@test "global_install: ~14 sub-skill symlinks exist and resolve to source" {
  # Sanity: count global symlinks and verify each resolves to a real SKILL.md.
  # This catches 'install.sh --global partially failed' regressions.
  [ -d "${HOME}/.agents/skills" ] || skip "global skills dir missing"
  expected_skills=(add-improve deps execute feature guide guide-arch \
    guide-design guide-plan guide-ship propose rdd-env-check \
    rdd-workflow-brainstorm rdd-workflow-writing-plans rddf-session roadmap status)
  for s in "${expected_skills[@]}"; do
    link="${HOME}/.agents/skills/$s"
    [ -L "$link" ] || { echo "missing symlink: $link" >&2; return 1; }
    target="$(readlink -f "$link")"
    [ -f "$target/SKILL.md" ] || { echo "broken symlink: $link → $target" >&2; return 1; }
  done
}