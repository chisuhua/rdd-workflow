#!/usr/bin/env bats

setup() {
  REPO_ROOT="${BATS_TEST_DIRNAME}/../.."
  cd "$REPO_ROOT"
}

@test "doc_truth_sync: package.json::skills[] publishes all disk skills (Decision 3 = A)" {
  run python3 - <<'PY'
import json, sys
from pathlib import Path
# v4 stage-merge (ADR-0043) doubled the per-skill SKILL.md count. INSTALL.md is the
# bootstrap entry, NOT a sub-skill, so it lives in skills/*.md but not in
# package.json::skills[]. Exclude it from the disk count.
disk = len(list(Path("skills").glob("*/SKILL.md")))
data = json.load(open("package.json"))
skills = data.get("skills", [])
assert len(skills) == disk, (
    f"package.json declares {len(skills)} skills, disk has {disk} */SKILL.md; "
    f"Decision 3 翻 A 后长度必须相等(无 src-only 例外)"
)
assert "feature" in skills, f"feature not in skills[]: {skills}"
assert "rddf-session" in skills, f"rddf-session not in skills[]: {skills}"
assert "_comment" not in data, (
    "Decision 3 = A 后 package.json 不应再有 `_comment` 字段声明 src-only; got: "
    + repr(data.get("_comment"))
)
PY
  [ "$status" -eq 0 ]
}

@test "doc_truth_sync: AGENTS.md states the actual sub-skill count" {
  disk_sub=$(ls skills/*/SKILL.md 2>/dev/null | wc -l)
  # The count is parsed from AGENTS.md and compared against the disk, so
  # adding a skill does not require editing this test. Asserting a literal
  # number here is what let the manifest drift go unnoticed: each new skill
  # made this test fail, and the fix was to edit the number, not the drift.
  mentioned=$(grep -oE "[0-9]+ (SKILL\.md|个子技能)" AGENTS.md | grep -oE "^[0-9]+" | sort -u)
  if [ -z "$mentioned" ]; then
    echo "AGENTS.md does not state a sub-skill count (disk has $disk_sub sub-skills)"
    return 1
  fi
  ok=0
  for n in $mentioned; do
    if [ "$n" -eq "$disk_sub" ]; then ok=1; fi
  done
  if [ "$ok" -ne 1 ]; then
    echo "AGENTS.md states sub-skill count(s): $mentioned — disk has $disk_sub"
    return 1
  fi
}

@test "doc_truth_sync: AGENTS.md ADR table lists 0001-0020 with no dup annotation" {
  for n in 0001 0010 0019 0020; do
    if ! grep -qE "ADR-${n}\b" AGENTS.md; then
      echo "AGENTS.md missing ADR-${n}"
      return 1
    fi
  done
  # After v2.0.2 renumber, no ADR-0013 dup annotation should remain
  if grep -qE "ADR-0013.*重复|重复.*ADR-0013|extract-scan-state.*incremental-skeleton-planning" AGENTS.md; then
    echo "AGENTS.md still has stale ADR-0013 dup annotation (v2.0.2 renumbered incremental-skeleton-planning to ADR-0020)"
    return 1
  fi
}

@test "doc_truth_sync: INSTALL.md description states the actual sub-skill count + npm-test-vs-pytest block" {
  disk_sub=$(ls skills/*/SKILL.md 2>/dev/null | wc -l)
  mentioned=$(grep -oE "全部 [0-9]+ 个子技能" skills/INSTALL.md | grep -oE "[0-9]+" | head -1)
  if [ -z "$mentioned" ]; then
    echo "INSTALL.md description missing the '全部 N 个子技能' statement (disk has $disk_sub)"
    return 1
  fi
  if [ "$mentioned" -ne "$disk_sub" ]; then
    echo "INSTALL.md says '全部 $mentioned 个子技能' but disk has $disk_sub sub-skills"
    return 1
  fi
  if ! grep -qE "npm test vs pytest" skills/INSTALL.md; then
    echo "INSTALL.md missing 'npm test vs pytest' reminder block"
    return 1
  fi
}

@test "doc_truth_sync: README.md directory tree lists rdd-arch / rdd-planner / loop_engine / _lib (v4 names)" {
  for name in rdd-arch rdd-planner loop_engine.py "_lib"; do
    if ! grep -qE "$name" README.md; then
      echo "README.md missing '$name' in tree or docs"
      return 1
    fi
  done
}

@test "doc_truth_sync: USAGE.md changelog banner names v2.0.1 + sync-workflow-contracts" {
  if ! grep -qE "v2\.0\.1" USAGE.md; then echo "missing v2.0.1"; return 1; fi
  if ! grep -qE "sync-workflow-contracts" USAGE.md; then echo "missing sync-workflow-contracts"; return 1; fi
}

@test "doc_truth_sync: USAGE.md state-file table uses dotted prefixes for handoff-style + canonical/legacy note" {
  for tail in ".arch-handoff.json" ".plan-handoff.json" ".deps-candidates.json" ".deps-output.md"; do
    full=".rddf/state/${tail}"
    if ! grep -qF "$full" USAGE.md; then echo "missing $full"; return 1; fi
  done
  for tail in "deps-analysis.json" "iteration.json" "sessions.json" "index.md"; do
    full=".rddf/state/${tail}"
    if ! grep -qF "$full" USAGE.md; then echo "missing $full"; return 1; fi
  done
}

@test "doc_truth_sync: AGENTS.md forbids undotted legacy .rddf/state/handoff.json (per general/spec.md Scenario 2)" {
  # general/spec.md Scenario 2 forbids undotted .rddf/state/handoff.json
  if grep -qE "(^|[^/])\.rddf/state/handoff\.json|rddf/state/plan-handoff\.json" AGENTS.md; then
    echo "AGENTS.md references undotted legacy handoff path"
    return 1
  fi
}
