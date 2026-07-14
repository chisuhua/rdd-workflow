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
  assert_no_dup_version skills/guide.md
}

@test "status.md frontmatter has at most one version key" {
  assert_no_dup_version skills/status.md
}

@test "guide.md metadata.version matches skill_field semver pattern" {
  run python3 -c "
import yaml,sys
d=yaml.safe_load(open('skills/guide.md').read().split('---',2)[1])
v=d.get('metadata',{}).get('version','')
import re
sys.exit(0 if re.match(r'^\d+\.\d+(\.\d+)?$', str(v)) else 2)
"
  [ "$status" -eq 0 ]
}
