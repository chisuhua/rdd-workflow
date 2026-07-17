#!/usr/bin/env bats
# tests/integration/test_skill_metadata_consistency.bats
#
# Cross-skill consistency: the 9-skill set must agree across three
# independent sources:
#   1. package.json `skills[]` array
#   2. skills/*.md files on disk (10 target + 1 writing-plans)
#   3. smoke.bats:19-29 hard-coded list
#
# Run: bats tests/integration/test_skill_metadata_consistency.bats

load ../test_helper

setup() {
  cd "$REPO_ROOT"
}

@test "package.json skills[] contains the 10 target skill names" {
  # package.json may also list writing-plans (which is excluded from
  # the 10-skill test surface). The test only asserts the 10 target names
  # are all present.
  run python3 -c "
import json, sys
with open('package.json') as f:
    data = json.load(f)
skills = set(data.get('skills', []))
expected = {'INSTALL', 'deps', 'execute', 'guide', 'guide-ship', 'guide-arch', 'guide-plan', 'propose', 'roadmap', 'status'}
missing = expected - skills
if missing:
    print(f'missing from package.json skills[]: {sorted(missing)}', file=sys.stderr)
    sys.exit(1)
"
  [ "$status" -eq 0 ]
}

@test "every package.json skills[] entry has a matching skills/<name>/SKILL.md or skills/<name>.md" {
  # INSTALL stays at top-level (skills/INSTALL.md); others moved to skills/<name>/SKILL.md
  run python3 -c "
import json, os, sys
with open('package.json') as f:
    data = json.load(f)
skills = data.get('skills', [])
for s in skills:
    # INSTALL is at top level, others moved to per-skill subdirectory
    candidates = [f'skills/{s}/SKILL.md', f'skills/{s}.md']
    if not any(os.path.isfile(p) for p in candidates):
        print(f'missing: {candidates}', file=sys.stderr)
        sys.exit(1)
"
  [ "$status" -eq 0 ]
}

@test "smoke.bats 10-skill list matches package.json skills[] (target set)" {
  # smoke.bats:25-35 hard-codes the 10 target skill files (mixed INSTALL.md + SKILL.md).
  # Extract each skill name from the literal and compare to the target set
  # in package.json (allowing extras like prometheus-planning).
  smoke_skills=$(grep -oE 'skills/[A-Za-z0-9_-]+(\.md|/SKILL\.md)' tests/smoke.bats | \
                 sed -E 's|skills/||; s|\.md||; s|/SKILL||' | sort -u)
  pkg_target_skills=$(python3 -c "
import json
target = {'INSTALL', 'deps', 'execute', 'guide', 'guide-ship', 'guide-arch', 'guide-plan', 'propose', 'roadmap', 'status'}
all_skills = set(json.load(open('package.json'))['skills'])
print('\n'.join(sorted(target & all_skills)))
")
  if [ "$smoke_skills" != "$pkg_target_skills" ]; then
    echo "smoke_skills: $smoke_skills" >&2
    echo "pkg_target:   $pkg_target_skills" >&2
    return 1
  fi
}

@test "prometheus-planning.md no longer exists (v2.0 self-contained)" {
  # v2.0 removed prometheus-planning.md entirely (replaced by spec-workflow/* skills)
  ! [ -f skills/prometheus-planning.md ]
  # No test_<name>_skill.bats file references it
  ! ls tests/integration/test_prometheus_planning_skill.bats 2>/dev/null
  # Verify the 8+ test files cover the target skills
  count=$(ls tests/integration/test_*_skill.bats 2>/dev/null | wc -l)
  [ "$count" -ge 8 ]
}
