#!/usr/bin/env bats

setup() {
  REPO_ROOT="${BATS_TEST_DIRNAME}/../.."
  cd "$REPO_ROOT"
}

@test "doc_truth_sync: package.json::skills[] publishes all 26 disk skills (Decision 3 = A)" {
  run python3 - <<'PY'
import json, sys
from pathlib import Path
# v4 stage-merge (ADR-0043) doubled 13→26 per-skill SKILL.md. INSTALL.md is the
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

@test "doc_truth_sync: AGENTS.md mentions 26 skills" {
  disk_root=$(ls skills/*.md 2>/dev/null | wc -l)
  disk_sub=$(ls skills/*/SKILL.md 2>/dev/null | wc -l)
  disk=$((disk_root + disk_sub))
  # AGENTS.md uses format "27 SKILL.md + INSTALL.md" (L72) or "27 SKILL.md" (L118)
  # — both reflect v4 stage-merge: 26 per-skill SKILL.md + 1 INSTALL.md bootstrap.
  # Accept either 26 (per-skill only) or 27 (per-skill + INSTALL).
  if ! grep -qE "(26|27) (SKILL\.md|个 .md|个子技能)" AGENTS.md; then
    echo "AGENTS.md missing 26 or 27 skills (disk has $disk: $disk_root root + $disk_sub subdir)"
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

@test "doc_truth_sync: INSTALL.md description lists 26 skills + npm-test-vs-pytest block" {
  if ! grep -qE "全部 26 个子技能" skills/INSTALL.md; then
    echo "INSTALL.md description missing '全部 26 个子技能'"
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
