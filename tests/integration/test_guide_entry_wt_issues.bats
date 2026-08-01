#!/usr/bin/env bats

load ../test_helper

init_repo() {
  local repo="$1"
  git init -q "$repo"
  git -C "$repo" config user.email "t@t"
  git -C "$repo" config user.name "t"
  touch "$repo/init"
  ln -s "$REPO_ROOT/skills" "$repo/skills"
  git -C "$repo" add init skills
  git -C "$repo" commit -q -m init
}

run_guide_entry() {
  local repo="$1"
  run bash -c "cd '$repo' && SKILL_DIR='$REPO_ROOT/skills/guide' source '$REPO_ROOT/skills/guide/scripts/guide_entry.sh' && guide_entry --json"
}

@test "guide_entry --json: clean tree produces identical output" {
  local repo="$BATS_TEST_TMPDIR/guide-entry-clean"
  init_repo "$repo"

  run_guide_entry "$repo"

  [ "$status" -eq 0 ]
  expected=$(<"$REPO_ROOT/tests/integration/fixtures/guide_entry_clean.json")
  [ "$output" = "$expected" ]
}

@test "guide_entry --json: untracked improvements file is info-only" {
  local repo="$BATS_TEST_TMPDIR/guide-entry-untracked"
  init_repo "$repo"
  mkdir -p "$repo/improvements"
  printf 'new\n' > "$repo/improvements/foo.md"

  run_guide_entry "$repo"

  [ "$status" -eq 0 ]
  OUTPUT="$output" python3 -c 'import json, os; text = os.environ["OUTPUT"]; payload = text.split("---BEGIN_RECO_JSON---\n", 1)[1].split("\n---END_RECO_JSON---", 1)[0]; data = json.loads(payload); assert any(issue.get("category") == "untracked_file" and issue.get("severity") == "info" for issue in data["wt_issues"])'
}
