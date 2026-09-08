#!/usr/bin/env bats
# tests/integration/test_phase2_no_broken_refs.bats
#
# Phase 2 regression test: every SKILL.md source line must resolve to an existing file.
# Per Phase 1's validation pattern (Task 3.2) — extended for Phase 2's
# $REPO_ROOT paths and readlink handling.

load ../test_helper

setup() {
  cd "$REPO_ROOT"
}

# Helper: extract path from a `source "..."` line, expand vars, check existence
resolve_source_line() {
  local line="$1"
  local skill="$2"
  local path

  # Strip leading whitespace and "source"
  # Handle both `source "..."` and `  source "..."` forms, as well as
  # `bash -c 'source "..."'` forms (where source is inside single quotes).
  # The path is the FIRST double-quoted string after `source` — use non-greedy
  # `[^"]*` so multi-statement lines (e.g. `source "X"; cmd "$y"`) extract X
  # not the whole suffix.
  path=$(echo "$line" | sed -E 's/.*source[[:space:]]+"([^"]*)".*/\1/')
  [ -z "$path" ] && return 1
  # If the sed didn't match (no source + double-quote pattern), skip
  [[ "$path" == "$line" ]] && return 1

  # Expand variables (skills/<skill>/ + ../ tricks)
  if [[ "$path" == *'$REPO_ROOT'* ]]; then
    path="${path//\$REPO_ROOT/$REPO_ROOT}"
  elif [[ "$path" == *'$(dirname'* ]]; then
    # $(dirname BASH_SOURCE) -> skills/<skill>/ (the SKILL.md directory)
    # Handle both $(dirname "${BASH_SOURCE[0]:-$0}") and
    # $(dirname "$(readlink -f "${BASH_SOURCE[0]:-$0}")")
    local skill_dir="$REPO_ROOT/skills/$skill"
    # Replace the $(dirname ...) expression with the skill directory
    path=$(echo "$path" | sed "s|\$(dirname \"\${BASH_SOURCE\[0\]:-\$0}\")|$skill_dir|g")
    path=$(echo "$path" | sed "s|\$(dirname \"\$(readlink -f \"\${BASH_SOURCE\[0\]:-\$0}\")\")|$skill_dir|g")
  elif [[ "$path" == *'$SCRIPT_DIR'* ]]; then
    # $SCRIPT_DIR is defined as the skill directory (skills/<skill>), NOT scripts/
    path=$(echo "$path" | sed "s|\$SCRIPT_DIR|$REPO_ROOT/skills/$skill|g")
  elif [[ "$path" == *'$_SCRIPT_DIR'* ]]; then
    # $_SCRIPT_DIR is defined as the skill directory (skills/<skill>), NOT scripts/
    path=$(echo "$path" | sed "s|\$_SCRIPT_DIR|$REPO_ROOT/skills/$skill|g")
  elif [[ "$path" == *'$SKILL_DIR'* ]]; then
    # $SKILL_DIR is defined as the skill directory (skills/<skill>)
    path=$(echo "$path" | sed "s|\$SKILL_DIR|$REPO_ROOT/skills/$skill|g")
  fi

  echo "$path"
}

@test "phase2_no_broken_refs: all SKILL.md source lines resolve to existing files" {
  errors=0
  for f in skills/*/SKILL.md; do
    skill=$(basename "$(dirname "$f")")
    while IFS= read -r line; do
      # Skip comments
      [[ "$line" =~ ^[[:space:]]*# ]] && continue
      # Only check lines with `source ... _lib/` or `scripts/`
      [[ "$line" =~ source ]] || continue
      # Static check can only validate LITERAL paths. Any source line that
      # contains dynamic expansion must be skipped:
      # - $HOME / ${PROJECT_ROOT:-...} (install-time resolved)
      # - $(resolve_rdd_skill_dir ...) / $(resolve_rdd_lib_dir) (resolver call)
      # - $(dirname "${BASH_SOURCE[0]:-$0}") (per-skill relative)
      # - chained `|| source ...` fallbacks (resolver picks one)
      # The runtime rdd-env-check (rdd-env-check skill) is the canonical gate
      # for dynamic paths; this static check only catches typos in literal ones.
      if [[ "$line" == *'$'* ]] || [[ "$line" == *'||'* ]]; then
        continue
      fi
      path=$(resolve_source_line "$line" "$skill")
      [ -z "$path" ] && continue
      if [ ! -f "$path" ]; then
        echo "❌ BROKEN: $f → $line → $path"
        errors=$((errors + 1))
      fi
    done < <(grep -E 'source.*_lib|source.*scripts' "$f")
  done
  [ "$errors" -eq 0 ] || {
    echo "FAIL: $errors broken source refs"
    return 1
  }
}


@test "phase2_no_broken_refs: rdd-arch sources rddf_session_hooks (v4 only one)" {
  # v4 stage-merge (ADR-0043) consolidated guide-design+plan+ship into rdd-builder,
  # so only rdd-arch still sources the rddf-session hooks (2 references at L114
  # entry + L756 close). rdd-planner/rdd-builder use rddf-session via in-process
  # Python calls (no shell source).
  f="skills/rdd-arch/SKILL.md"
  count=$(grep -c '\.\./rddf-session/scripts/rddf_session_hooks\.sh' "$f")
  [ "$count" -ge 1 ] || {
    echo "FAIL: $f missing ../rddf-session/scripts/rddf_session_hooks.sh"
    return 1
  }
  path="$REPO_ROOT/skills/rdd-arch/../rddf-session/scripts/rddf_session_hooks.sh"
  [ -f "$path" ] || {
    echo "FAIL: $path doesn't exist"
    return 1
  }
}