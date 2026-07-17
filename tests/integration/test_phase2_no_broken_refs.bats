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
  path=$(echo "$line" | sed -E 's/^[[:space:]]*source[[:space:]]+"([^"]+)".*/\1/')
  [ -z "$path" ] && return 1

  # Expand variables (skills/<skill>/ + ../ tricks)
  if [[ "$path" == *'$REPO_ROOT'* ]]; then
    path="${path//\$REPO_ROOT/$REPO_ROOT}"
  elif [[ "$path" == *'$(dirname'* ]]; then
    # $(dirname BASH_SOURCE) → skills/<skill>/
    path=$(echo "$path" | sed "s|\$(dirname \"\${BASH_SOURCE\[0\]:-\$0}\")|$REPO_ROOT/skills/$skill|g")
    path=$(echo "$path" | sed "s|\$(dirname \"\$(readlink -f \"\${BASH_SOURCE\[0\]:-\$0}\")\")|$REPO_ROOT/skills/$skill|g")
  elif [[ "$path" == *'$SCRIPT_DIR'* ]] || [[ "$path" == *'$_SCRIPT_DIR'* ]]; then
    path=$(echo "$path" | sed "s|\$SCRIPT_DIR|$REPO_ROOT/skills/$skill/scripts|g")
    path=$(echo "$path" | sed "s|\$_SCRIPT_DIR|$REPO_ROOT/skills/$skill/scripts|g")
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

@test "phase2_no_broken_refs: guide.md readlink path resolves" {
  # Phase 1 N1 lesson: readlink -f pattern must be manually fixed
  line=$(grep -n 'readlink.*scan-state' skills/guide/SKILL.md)
  [ -n "$line" ] || {
    skip "guide.md readlink pattern not found (expected post-Phase-2)"
  }
  # Resolve manually (the helper doesn't handle readlink expansions)
  path="$REPO_ROOT/skills/guide/scripts/scan-state.sh"
  [ -f "$path" ] || {
    echo "FAIL: guide.md readlink path resolves to $path which doesn't exist"
    return 1
  }
}

@test "phase2_no_broken_refs: 3 cross-skill rddf-session sources resolve" {
  for skill in guide-arch guide-plan guide-ship; do
    f="skills/$skill/SKILL.md"
    line=$(grep -n '\.\./rddf-session/scripts/rddf_session_hooks\.sh' "$f")
    [ -n "$line" ] || {
      echo "FAIL: $f missing ../rddf-session/scripts/rddf_session_hooks.sh"
      return 1
    }
    path="$REPO_ROOT/skills/$skill/../rddf-session/scripts/rddf_session_hooks.sh"
    [ -f "$path" ] || {
      echo "FAIL: $path doesn't exist"
      return 1
    }
  done
}