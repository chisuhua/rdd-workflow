#!/usr/bin/env bash
# Compare the current recursive Bats failure set with tests/KNOWN_FAILURES.txt.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BASELINE="$REPO_ROOT/tests/KNOWN_FAILURES.txt"
TMP_DIR="$(mktemp -d -t rdd-known-failures-XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

if ! command -v bats >/dev/null 2>&1; then
  printf '❌ bats-core is required to report regressions\n' >&2
  exit 127
fi

if [ ! -f "$BASELINE" ]; then
  printf '❌ baseline file is missing: %s\n' "$BASELINE" >&2
  exit 1
fi

set +e
(cd "$REPO_ROOT" && bats tests/ --recursive) >"$TMP_DIR/bats-output" 2>&1
bats_status=$?
set -e

sed -nE 's/^not ok [0-9]+ (.*)$/\1/p' "$TMP_DIR/bats-output" \
  | sed -E 's/[[:space:]]+# (pre-existing|historical)[^[:alnum:]].*$//' \
  | sed '/^[[:space:]]*$/d' \
  | sort -u >"$TMP_DIR/actual"

sed -E 's/[[:space:]]+# (pre-existing|historical)[^[:alnum:]].*$//' "$BASELINE" \
  | sed '/^[[:space:]]*$/d' \
  | sort -u >"$TMP_DIR/baseline"

known_count=$(comm -12 "$TMP_DIR/actual" "$TMP_DIR/baseline" | wc -l | tr -d ' ')
new_count=$(comm -23 "$TMP_DIR/actual" "$TMP_DIR/baseline" | wc -l | tr -d ' ')
stale_count=$(comm -13 "$TMP_DIR/actual" "$TMP_DIR/baseline" | wc -l | tr -d ' ')

printf 'Bats exit status: %s\n' "$bats_status"
printf '已知失败: %s\n' "$known_count"
printf '新增失败: %s\n' "$new_count"
printf '基线中已修复: %s\n' "$stale_count"

if [ "$new_count" -gt 0 ]; then
  printf '%s\n' '新增失败明细:'
  comm -23 "$TMP_DIR/actual" "$TMP_DIR/baseline"
  exit 1
fi

# A non-zero Bats status with only baseline failures is expected. A non-zero
# status without TAP failures indicates an infrastructure error and must fail.
if [ "$bats_status" -ne 0 ] && [ "$known_count" -eq 0 ] && [ "$stale_count" -eq 0 ]; then
  printf '❌ Bats failed without a baseline-matched TAP failure; inspect raw output:\n' >&2
  cat "$TMP_DIR/bats-output" >&2
  exit "$bats_status"
fi

printf '%s\n' '✅ 0 新增失败'
exit 0
