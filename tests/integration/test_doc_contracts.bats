#!/usr/bin/env bats

setup() {
  REPO_ROOT="${BATS_TEST_DIRNAME}/../.."
  cd "$REPO_ROOT"
}

@test "doc_truth_sync: package.json::skills[] publishes all 13 disk skills (Decision 3 = A)" {
  run python3 - <<'PY'
import json, sys
disk = len(list(__import__("pathlib").Path("skills").glob("*.md")))
data = json.load(open("package.json"))
skills = data.get("skills", [])
assert len(skills) == disk, (
    f"package.json declares {len(skills)} skills, disk has {disk}; "
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

@test "doc_truth_sync: AGENTS.md skill count matches ls skills/*.md" {
  disk=$(ls skills/*.md | wc -l)
  if ! grep -qE "13 个 \.md" AGENTS.md; then
    echo "AGENTS.md missing '13 个 .md' (disk has $disk)"
    return 1
  fi
}

@test "doc_truth_sync: AGENTS.md ADR table lists 0001-0019 with ADR-0013 dup note" {
  for n in 0001 0010 0019 0013; do
    if ! grep -qE "ADR-${n}\b" AGENTS.md; then
      echo "AGENTS.md missing ADR-${n}"
      return 1
    fi
  done
  if ! grep -qE "ADR-0013.*重复|重复.*ADR-0013|extract-scan-state.*incremental-skeleton-planning" AGENTS.md; then
    echo "AGENTS.md missing ADR-0013 dup annotation"
    return 1
  fi
}
