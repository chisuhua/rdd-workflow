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
