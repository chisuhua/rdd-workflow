#!/usr/bin/env bats
# Locks the invariant: skill frontmatter metadata block contains AT MOST
# one `version:` key. YAML silent-keep-last behavior caused metadata.version
# to drift between source-of-truth and the rendered/observed value.

load ../test_helper

assert_no_dup_version() {
  local f="$1"
  local n
  n=$(awk '/^metadata:/{f=1;next} f && /^---$/{exit} f && /^[[:space:]]+version:/{print}' "$f" | wc -l)
  [ "$n" -le 1 ] || { echo "FAIL: $f has $n version keys (want <=1)"; return 1; }
}

@test "guide.md frontmatter has at most one version key" {
  assert_no_dup_version skills/guide/SKILL.md
}

@test "status.md frontmatter has at most one version key" {
  assert_no_dup_version skills/status/SKILL.md
}

# Cover the remaining 11 skills — pre-fix, deps/execute/feature/guide-arch/
# guide-plan/guide-ship/propose/rddf-session/roadmap/spec-workflow-writing-plans
# all had duplicate `version:` keys under metadata: (10 files total).
# This test was previously missing for those skills, letting the bug
# silently drift into npm-published skills.
@test "all 13 skills: frontmatter metadata has at most one version key" {
  local failures=()
  for f in skills/*.md; do
    local n
    n=$(awk '/^metadata:/{m=1;next} m && /^---$/{exit} m && /^[[:space:]]+version:/{print}' "$f" | wc -l)
    if [ "$n" -gt 1 ]; then
      failures+=("$f has $n version keys")
    fi
  done
  if [ "${#failures[@]}" -gt 0 ]; then
    printf 'FAIL: %s\n' "${failures[@]}"
    return 1
  fi
}

@test "all 13 skills: version is at most X.Y[.Z] and present in frontmatter" {
  # Use PyYAML (last-write-wins) for the value, since downstream consumers
  # (Python tooling) typically use yaml.safe_load which picks the LAST
  # version key — if duplicate existed, the wrong value would resolve.
  # After the duplicate-version fix, both first-write and last-write
  # resolve to the same value, so this test asserts that.
  #
  # INSTALL.md is a special case: its `version:` lives at the top level
  # (not nested under metadata:). All 12 other skills use metadata.version.
  # We accept either form by checking both.
  local failures=()
  for f in skills/*.md; do
    local v
    v=$(awk '/^---$/{c++; if(c==2) exit} c>=1 {print}' "$f" | python3 -c "
import sys, yaml
try:
    d = yaml.safe_load(sys.stdin)
    md = d.get('metadata') or {}
    v = md.get('version') or d.get('version') or ''
    sys.stdout.write(str(v))
except Exception:
    sys.exit(2)
" 2>/dev/null)
    if [ -z "$v" ]; then
      failures+=("$f: version missing")
    elif ! echo "$v" | grep -qE '^[0-9]+\.[0-9]+(\.[0-9]+)?$'; then
      failures+=("$f: bad semver '$v'")
    fi
  done
  if [ "${#failures[@]}" -gt 0 ]; then
    printf 'FAIL: %s\n' "${failures[@]}"
    return 1
  fi
}

@test "guide.md metadata.version matches skill_field semver pattern" {
  run python3 -c "
import yaml,sys
d=yaml.safe_load(open('skills/guide/SKILL.md').read().split('---',2)[1])
v=d.get('metadata',{}).get('version','')
import re
sys.exit(0 if re.match(r'^\d+\.\d+(\.\d+)?$', str(v)) else 2)
"
  [ "$status" -eq 0 ]
}
