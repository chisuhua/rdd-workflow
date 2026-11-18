#!/usr/bin/env bash
# Helper: run all .bats files individually and collect unique failures.
# Bypasses bats-core 1.13.0 `bats tests/ --recursive` infinite-loop bug
# by running each file with a per-file timeout.
#
# Two-level timeout (per fix-bats-per-file-timeout):
#   level 1: per-file  timeout  BATS_TIMEOUT            (default 30s)
#   level 2: per-test  BATS_TEST_TIMEOUT = BATS_TIMEOUT_RETRY (default 120s)
#            file-level cap = BATS_TIMEOUT_RETRY + BATS_TIMEOUT
# A file that hits level 1 is retried with a per-test timeout, so ONE stuck
# test no longer discards the whole file: the remaining tests of that file
# are still evaluated and their failures are collected. Only a file that
# still does not finish is "unevaluated" — and it is recorded BY NAME with a
# reason, so the regression gate can no longer hide it behind a footnote.
#
# Usage:
#   bash tests/scripts/collect_bats_failures.sh [DIR] [OUTPUT_FILE]
#   bash tests/scripts/collect_bats_failures.sh tests/integration/ /tmp/actual.txt
#
# Env (the defaults live HERE — report_regression.sh only passes them through):
#   BATS_TIMEOUT         level-1 per-file timeout in seconds (default: 30)
#   BATS_TIMEOUT_RETRY   level-2 per-test timeout in seconds (default: 120);
#                        must be >= BATS_TIMEOUT
#   BATS_RETRY_BUDGET    global budget for level-2 retries, in seconds
#                        (default: 600). When exhausted, the remaining
#                        timed-out files stay unevaluated (and the gate fails).
#   RDDF_BATS_COLLECT_ACTIVE=1
#                        refuse to start (recursive collection) → exit 2
#
# Products:
#   $OUTPUT                    failure names, one per line, sorted + unique
#   $OUTPUT.hangs              unevaluated files, one per line:
#                              "<path> rc=124 elapsed=<Ns> last_tap=<n> kind=<hang|slow>"
#   $OUTPUT.per-test-timeouts  "<path> # <test name>" for every test that the
#                              per-test timeout killed (the file WAS evaluated;
#                              only that test did not finish)
#
# Exit codes:
#   0  collection completed (some files may still be unevaluated — see .hangs)
#   1  no .bats files found under DIR
#   2  infrastructure error (bad env, missing/too old bats, timeout rc 125/126/127)

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DIR="${1:-tests/integration/}"
OUTPUT="${2:-/tmp/bats-failures.txt}"

PER_FILE_TIMEOUT="${BATS_TIMEOUT:-30}"
RETRY_TIMEOUT="${BATS_TIMEOUT_RETRY:-120}"
RETRY_BUDGET="${BATS_RETRY_BUDGET:-600}"

die_infra() {
    printf '❌ %s\n' "$*" >&2
    exit 2
}

# ── env validation ────────────────────────────────────────────────────────────
# Every invalid value is an infrastructure error. Silently degrading here is
# what made the gate fail open: `BATS_TIMEOUT=0` means "no limit", so a real
# hang blocks forever and the job only dies when the CI runner kills it.
case "$PER_FILE_TIMEOUT" in
    ''|*[!0-9]*) die_infra "BATS_TIMEOUT must be a positive integer, got '$PER_FILE_TIMEOUT'" ;;
esac
[ "$PER_FILE_TIMEOUT" -ge 1 ] || die_infra "BATS_TIMEOUT must be >= 1 (0 = no limit ⇒ a real hang blocks forever), got '$PER_FILE_TIMEOUT'"
case "$RETRY_TIMEOUT" in
    ''|*[!0-9]*) die_infra "BATS_TIMEOUT_RETRY must be a positive integer, got '$RETRY_TIMEOUT'" ;;
esac
[ "$RETRY_TIMEOUT" -ge 1 ] || die_infra "BATS_TIMEOUT_RETRY must be >= 1, got '$RETRY_TIMEOUT'"
[ "$RETRY_TIMEOUT" -ge "$PER_FILE_TIMEOUT" ] || die_infra "BATS_TIMEOUT_RETRY ($RETRY_TIMEOUT) must be >= BATS_TIMEOUT ($PER_FILE_TIMEOUT)"
case "$RETRY_BUDGET" in
    ''|*[!0-9]*) die_infra "BATS_RETRY_BUDGET must be a positive integer, got '$RETRY_BUDGET'" ;;
esac
[ "$RETRY_BUDGET" -ge 1 ] || die_infra "BATS_RETRY_BUDGET must be >= 1 (0 = no retry at all ⇒ every slow file stays unevaluated), got '$RETRY_BUDGET'"

# ── recursion guard ───────────────────────────────────────────────────────────
# collect exports the marker to its children. A nested collection (a test that
# drives this script) sees it and refuses instead of collecting inside a
# collection. Deliberate nested collections opt out explicitly with
# RDDF_BATS_COLLECT_ACTIVE=0.
if [ "${RDDF_BATS_COLLECT_ACTIVE:-0}" = "1" ]; then
    die_infra "collect_bats_failures.sh: refusing to start — RDDF_BATS_COLLECT_ACTIVE=1 (recursive collection)"
fi
export RDDF_BATS_COLLECT_ACTIVE=1

# ── bats availability + per-test timeout support ─────────────────────────────
# BATS_TEST_TIMEOUT exists since bats 1.5.0. Without it the level-2 retry
# cannot attribute a stuck test by name — it would silently degrade back to
# "discard the whole file" while the report claimed per-test attribution.
command -v bats >/dev/null 2>&1 || die_infra "bats not found in PATH"
BATS_VERSION_RAW="$(bats --version 2>/dev/null | head -1 || true)"
BATS_VERSION="$(printf '%s' "$BATS_VERSION_RAW" | sed -nE 's/^Bats ([0-9]+)\.([0-9]+)\.([0-9]+).*/\1 \2/p')"
if [ -z "$BATS_VERSION" ]; then
    die_infra "cannot determine the bats version from 'bats --version' ('$BATS_VERSION_RAW') — per-test timeout attribution needs bats >= 1.5.0"
fi
BATS_MAJOR="${BATS_VERSION%% *}"
BATS_MINOR="${BATS_VERSION#* }"
if [ "$BATS_MAJOR" -lt 1 ] || { [ "$BATS_MAJOR" -eq 1 ] && [ "$BATS_MINOR" -lt 5 ]; }; then
    die_infra "bats '$BATS_VERSION_RAW' does not support BATS_TEST_TIMEOUT (need >= 1.5.0)"
fi

cd "$REPO_ROOT"

shopt -s nullglob
files=("$DIR"*.bats)
shopt -u nullglob

if [ "${#files[@]}" -eq 0 ]; then
    printf '❌ no .bats files found under %s\n' "$DIR" >&2
    exit 1
fi

# M is computed BEFORE the loop: it is the denominator of the report and must
# not depend on how far the loop got.
M="${#files[@]}"

# Write into a private temp dir and move the results into place at the end —
# two concurrent collections writing the same $OUTPUT used to truncate each
# other (`: > "$OUTPUT"`), which silently shrank the failure set.
WORK="$(mktemp -d -t rdd-bats-collect-XXXXXX)"
trap 'rm -rf "$WORK"' EXIT
OUT_TMP="$WORK/failures"
HANG_TMP="$WORK/hangs"
PT_TMP="$WORK/per-test-timeouts"
: > "$OUT_TMP"
: > "$HANG_TMP"
: > "$PT_TMP"

FILE_TIMEOUT=$((RETRY_TIMEOUT + PER_FILE_TIMEOUT))
budget_left=$RETRY_BUDGET
evaluated=0
unevaluated=0
files_with_failures=0
per_test_count=0

for f in "${files[@]}"; do
    rc=0
    OUTPUT_LINE=""
    start_ts=$(date +%s)
    # `timeout` exits 124 on a real hang, otherwise the underlying command's
    # exit code (0 = clean, non-zero = test failures — the normal case).
    # `--kill-after` makes sure a stuck child cannot survive the timeout and
    # compete with the following files.
    if OUTPUT_LINE=$(timeout -k 5 "$PER_FILE_TIMEOUT" bats --tap "$f" 2>&1); then
        rc=0
    else
        rc=$?
    fi
    case "$rc" in
        125|126|127) die_infra "bats/timeout infrastructure failure on $f (rc=$rc)" ;;
    esac

    if [ "$rc" -eq 124 ] && [ "$budget_left" -ge "$FILE_TIMEOUT" ]; then
        # Level 2: per-test timeout. bats kills the ONE stuck test; the other
        # tests of the same file still run and are still evaluated.
        budget_left=$((budget_left - FILE_TIMEOUT))
        if RETRY_LINE=$(timeout -k 5 "$FILE_TIMEOUT" env BATS_TEST_TIMEOUT="$RETRY_TIMEOUT" bats --tap "$f" 2>&1); then
            rc=0
        else
            rc=$?
        fi
        case "$rc" in
            125|126|127) die_infra "bats/timeout infrastructure failure on $f during the retry (rc=$rc)" ;;
        esac
        # The level-1 output is DISCARDED, never merged: SIGTERM may have cut
        # a TAP line in half, and merging it would pollute the failure set.
        OUTPUT_LINE="$RETRY_LINE"
    fi
    elapsed=$(( $(date +%s) - start_ts ))

    if [ "$rc" -eq 124 ]; then
        # Still not finished ⇒ UNEVALUATED. Its failures are unknown, so its
        # partial output is NOT merged into the failure set either.
        tap_progress=$(printf '%s\n' "$OUTPUT_LINE" | grep -cE '^(ok|not ok) ' || true)
        tap_progress="${tap_progress:-0}"
        if [ "$tap_progress" -eq 0 ]; then kind="hang"; else kind="slow"; fi
        printf '%s rc=124 elapsed=%ss last_tap=%s kind=%s\n' "$f" "$elapsed" "$tap_progress" "$kind" >> "$HANG_TMP"
        unevaluated=$((unevaluated + 1))
        continue
    fi

    evaluated=$((evaluated + 1))

    # Per-test timeouts are a separate category: the test did not finish, but
    # the file WAS evaluated. Keeping them out of the failure set is what
    # stops a timeout from masquerading as a regression.
    PER_TEST="$(printf '%s\n' "$OUTPUT_LINE" | grep -E '^not ok .*# timeout after [0-9]+s$' || true)"
    if [ -n "$PER_TEST" ]; then
        while IFS= read -r line; do
            [ -n "$line" ] || continue
            name="$(printf '%s' "$line" | sed -E 's/^not ok [0-9]+ //; s/ # timeout after [0-9]+s$//')"
            printf '%s # %s\n' "$f" "$name" >> "$PT_TMP"
            per_test_count=$((per_test_count + 1))
        done <<< "$PER_TEST"
    fi

    NOT_OK="$(printf '%s\n' "$OUTPUT_LINE" | grep -E '^not ok' | grep -vE '# timeout after [0-9]+s$' | sed -E 's/^not ok [0-9]+ //' || true)"
    if [ -n "$NOT_OK" ]; then
        while IFS= read -r line; do
            [ -n "$line" ] && echo "$line" >> "$OUT_TMP"
        done <<< "$NOT_OK"
        files_with_failures=$((files_with_failures + 1))
    fi
done

sort -u "$OUT_TMP" -o "$OUT_TMP"
unique=$(wc -l < "$OUT_TMP" | tr -d ' ')

mkdir -p "$(dirname "$OUTPUT")"
mv -f "$OUT_TMP" "$OUTPUT"
mv -f "$HANG_TMP" "${OUTPUT}.hangs"
mv -f "$PT_TMP" "${OUTPUT}.per-test-timeouts"

printf '📋 Collected from %d .bats files under %s\n' "$M" "$DIR"
printf '   files with failures: %d\n' "$files_with_failures"
printf '   total unique failures: %d (sorted to %s)\n' "$unique" "$OUTPUT"
printf '   evaluated: %d/%d files\n' "$evaluated" "$M"
printf '   unevaluated: %d file(s) (see %s)\n' "$unevaluated" "${OUTPUT}.hangs"
printf '   per-test timeouts: %d (see %s)\n' "$per_test_count" "${OUTPUT}.per-test-timeouts"
