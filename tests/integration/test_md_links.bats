#!/usr/bin/env bats
# Contract test for tests/scripts/check_md_links.py — the tool that was lost in
# 2026-11-17 (it lived in /tmp, so the next round had to rediscover broken
# links by hand). Every guard here is mutation-verified: a checker that cannot
# fail is not a guard.

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
CHECK="$REPO_ROOT/tests/scripts/check_md_links.py"

setup() {
  TMPDOC="$BATS_TEST_TMPDIR/docs"
  mkdir -p "$TMPDOC"
}

@test "repo-wide scan is clean" {
  run python3 "$CHECK" --all
  [ "$status" -eq 0 ]
  [[ "$output" == *"markdown drift check passed"* ]]
}

@test "a broken relative link is reported with file and line" {
  printf "# doc\n\n[missing](./nowhere.md)\n" > "$TMPDOC/broken.md"
  run python3 "$CHECK" "$TMPDOC/broken.md"
  [ "$status" -eq 1 ]
  [[ "$output" == *"broken.md:3"* ]]
  [[ "$output" == *"nowhere.md"* ]]
}

@test "a wrong relative depth is reported (the ../adr/ typo class)" {
  mkdir -p "$TMPDOC/sub"
  printf "# doc\n\n[adr](../adr/ADR-0001-x.md)\n" > "$TMPDOC/sub/deep.md"
  run python3 "$CHECK" "$TMPDOC/sub/deep.md"
  [ "$status" -eq 1 ]
  [[ "$output" == *"deep.md:3"* ]]
}

@test "scanning zero files is a failure, not a silent pass" {
  mkdir -p "$BATS_TEST_TMPDIR/empty"
  run python3 "$CHECK" "$BATS_TEST_TMPDIR/empty"
  [ "$status" -eq 1 ]
  [[ "$output" == *"scan floor not met"* ]]
}

@test "a targeted scan of a link-free file is not a failure" {
  # 定向扫描的语义：调用方点名了这些文件，它们没有链接是合法结果。
  # 「0 链接 ⇒ 红」是**全量扫描**的防空转规则（见 unit 测试）。
  printf "# doc\n\nno links here\n" > "$TMPDOC/nolinks.md"
  run python3 "$CHECK" "$TMPDOC/nolinks.md"
  [ "$status" -eq 0 ]
}

@test "illustrative links inside inline code are not treated as links" {
  cat > "$TMPDOC/illustrative.md" <<'EOF'
# doc

see `[name](improvements/name.md)`
EOF
  run python3 "$CHECK" "$TMPDOC/illustrative.md"
  [ "$status" -eq 0 ]
}

@test "an unknown ADR reference is reported" {
  mkdir -p "$TMPDOC/architecture"
  printf "# arch\n\nper ADR-9999-nope.md\n" > "$TMPDOC/architecture/a.md"
  run python3 "$CHECK" --adr-refs "$TMPDOC/architecture"
  [ "$status" -eq 1 ]
  [[ "$output" == *"unknown ADR reference: ADR-9999"* ]]
}

@test "a stale count claim is reported" {
  printf "# doc\n\n- **999 skills** in skills/\n" > "$TMPDOC/count.md"
  run python3 "$CHECK" --versions "$TMPDOC/count.md"
  [ "$status" -eq 1 ]
  [[ "$output" == *"stale count"* ]]
}

@test "the checker has no third-party dependency" {
  run grep -E "^(import|from) " "$CHECK"
  [[ "$output" != *"yaml"* ]]
  [[ "$output" != *"requests"* ]]
}
