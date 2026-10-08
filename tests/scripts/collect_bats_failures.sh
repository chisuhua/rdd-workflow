#!/usr/bin/env bash
# Helper: run all .bats files individually and collect unique failures.
# Bypasses bats-core 1.13.0 `bats tests/ --recursive` infinite-loop bug
# by running each file with a per-file timeout.
#
# Usage:
#   bash tests/scripts/collect_bats_failures.sh [DIR] [OUTPUT_FILE]
#   bash tests/scripts/collect_bats_failures.sh tests/integration/ /tmp/actual.txt
#
# Env:
#   BATS_TIMEOUT  per-file timeout in seconds (default: 30)

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DIR="${1:-tests/integration/}"
OUTPUT="${2:-/tmp/bats-failures.txt}"
PER_FILE_TIMEOUT="${BATS_TIMEOUT:-30}"

cd "$REPO_ROOT"

: > "$OUTPUT"
HANG_LOG="${OUTPUT}.hangs"
: > "$HANG_LOG"

shopt -s nullglob
files=("$DIR"*.bats)
shopt -u nullglob

if [ "${#files[@]}" -eq 0 ]; then
    printf '❌ no .bats files found under %s\n' "$DIR" >&2
    exit 1
fi

i=0
files_with_failures=0
hung_files=0
for f in "${files[@]}"; do
    i=$((i+1))
    # Run with per-file timeout; capture both output and exit code.
    # `timeout` exits 124 on real hang, otherwise the underlying command's
    # exit code (0 = clean, non-zero = test failures — normal case).
    # We do NOT use the exit code to decide hang vs failure because bats
    # returns non-zero on any test failure; instead we only flag a hang
    # when timeout itself returns 124.
    set +e
    OUTPUT_LINE=$(timeout "$PER_FILE_TIMEOUT" bats "$f" 2>&1)
    rc=$?
    set -e
    if [ "$rc" -eq 124 ]; then
        # Hang ≠ test failure: log separately so baseline stays clean.
        echo "$f" >> "$HANG_LOG"
        hung_files=$((hung_files + 1))
        continue
    fi
    NOT_OK=$(printf '%s\n' "$OUTPUT_LINE" | grep -E "^not ok" | sed -E 's/^not ok [0-9]+ //' || true)
    if [ -n "$NOT_OK" ]; then
        while IFS= read -r line; do
            [ -n "$line" ] && echo "$line" >> "$OUTPUT"
        done <<< "$NOT_OK"
        files_with_failures=$((files_with_failures + 1))
    fi
done

sort -u "$OUTPUT" -o "$OUTPUT"
unique=$(wc -l < "$OUTPUT")

printf '📋 Collected from %d .bats files under %s\n' "$i" "$DIR"
printf '   files with failures: %d\n' "$files_with_failures"
printf '   total unique failures: %d (sorted to %s)\n' "$unique" "$OUTPUT"
if [ "$hung_files" -gt 0 ]; then
    printf '   hung files: %d (skipped; see %s)\n' "$hung_files" "$HANG_LOG"
fi
