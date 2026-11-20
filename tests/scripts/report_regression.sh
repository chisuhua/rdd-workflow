#!/usr/bin/env bash
# Compare the current Bats failure set with tests/KNOWN_FAILURES.txt and
# report regressions + zombie baseline entries.
#
# Reuses the per-file collection pattern from collect_bats_failures.sh to
# avoid `bats tests/ --recursive` (slow on 265+ files, occasionally
# hangs in bats-core 1.13.0 due to a known temp-file race).
#
# Output sections:
#   - 已知失败    (known): test name appears in baseline AND still failing
#   - 新增失败    (new):  test name is failing but NOT in baseline → REGRESSION
#   - 已修复      (fixed/stale): baseline entry no longer fails → ZOMBIE
#
# Exit code:
#   0 - no new failures AND no unevaluated file outside the named baseline
#       (zombie entries are warnings, not errors)
#   1 - new failures detected (regression) OR an unevaluated file is not
#       listed in tests/KNOWN_UNEVALUATED.txt
#   2 - infrastructure error (Bats missing, baseline missing, collect failed,
#       collect summary missing, file-count mismatch, …)
#
# Zombie entries are warnings only — they don't fail the gate. After
# reviewing, run `bash tests/scripts/refresh_known_failures.sh` to retire
# them. Zombie detection prevents the 5-month-stale baseline pattern
# (per add-baseline-freshness-doctor 2026-10-08).
#
# Env:
#   RDDF_KNOWN_FAILURES_FILE  Override the baseline path (default
#                             `<repo>/tests/KNOWN_FAILURES.txt`). Exists so
#                             tests can drive this script against a temp file
#                             instead of mutating the repo's real baseline —
#                             see tests/integration/test_known_failures_baseline.bats.
#                             The same name is honoured by
#                             refresh_known_failures.sh, so both scripts
#                             can drive the same temp baseline.
#   RDDF_UNEVALUATED_FILE     Override the unevaluated baseline path (default
#                             `<repo>/tests/KNOWN_UNEVALUATED.txt`).
#   BATS_TIMEOUT / BATS_TIMEOUT_RETRY / BATS_RETRY_BUDGET
#                             Passed through to collect_bats_failures.sh.
#                             The DEFAULTS live in collect_bats_failures.sh —
#                             this script never re-defaults them, otherwise
#                             `BATS_TIMEOUT_RETRY=300 report_regression.sh`
#                             would be silently ignored.
#   SKIP_UNEVALUATED_GATE=yes Emergency bypass: an unevaluated file outside
#                             the named baseline does not fail the gate. The
#                             bypass is written to .rddf/state/.bypass-audit.jsonl.
#                             CI asserts the variable is NOT set.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BASELINE="${RDDF_KNOWN_FAILURES_FILE:-$REPO_ROOT/tests/KNOWN_FAILURES.txt}"
UNEVALUATED_BASELINE="${RDDF_UNEVALUATED_FILE:-$REPO_ROOT/tests/KNOWN_UNEVALUATED.txt}"
TMP_DIR="$(mktemp -d -t rdd-known-failures-XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

if [ ! -f "$BASELINE" ]; then
  printf '❌ baseline file is missing: %s\n' "$BASELINE" >&2
  exit 2
fi

# 1. Collect current failures (bypasses the slow/buggy recursive invocation).
#    A non-zero exit is an infrastructure error, never "some failures found":
#    collect exits 2 on a bad env / a missing bats / a timeout rc 125-127,
#    and in all those cases the failure set is NOT trustworthy.
ACTUAL="$TMP_DIR/actual"
if bash "$SCRIPT_DIR/collect_bats_failures.sh" tests/integration/ "$ACTUAL" >"$TMP_DIR/collect.log" 2>&1; then
  :
else
  collect_rc=$?
  printf '❌ collect_bats_failures.sh failed (exit %s); inspect collect.log:\n' "$collect_rc" >&2
  cat "$TMP_DIR/collect.log" >&2
  exit 2
fi

# 1b. The summary is mandatory. It used to be optional: when collect died
#     mid-run it printed no "hung files:" line, the count below defaulted to
#     0, and the report then claimed a complete run. A missing summary is an
#     infrastructure error, not "0 unevaluated files".
SUMMARY="$(sed -nE 's/^[[:space:]]*evaluated: ([0-9]+)\/([0-9]+) files.*/\1 \2/p' "$TMP_DIR/collect.log" | head -1 || true)"
if [ -z "$SUMMARY" ]; then
  printf '❌ collect summary missing (infrastructure error — this run cannot be judged):\n' >&2
  cat "$TMP_DIR/collect.log" >&2
  exit 2
fi
EVALUATED="${SUMMARY%% *}"
COLLECT_M="${SUMMARY##* }"

# 1c. M is computed here too — the report does not trust collect's stdout.
#     A mismatch means the two saw different file sets (e.g. the tree changed
#     mid-run) and the denominator of "评估 N/M" would be a lie.
M="$(ls "$REPO_ROOT"/tests/integration/*.bats 2>/dev/null | wc -l | tr -d ' ')"
if [ "$M" != "$COLLECT_M" ]; then
  printf '❌ file-count mismatch: collect saw %s files, the report sees %s\n' "$COLLECT_M" "$M" >&2
  exit 2
fi

# Scope declaration: this gate only covers tests/integration/*.bats. The rest
# of the repo's .bats files are covered by CI's `bats tests/ --recursive`
# step — but saying so is what keeps the report from creating a quieter
# version of an empty truth.
TOTAL_BATS="$(find "$REPO_ROOT/tests" -name '*.bats' -type f 2>/dev/null | wc -l | tr -d ' ')"
OUT_OF_SCOPE=$((TOTAL_BATS - M))
printf '📊 评估 %s/%s 个文件（scope: tests/integration/*.bats；仓库另 %s 个 .bats 不在本门范围）\n' \
  "$EVALUATED" "$M" "$OUT_OF_SCOPE"

# 1d. Unevaluated files × named baseline.
#     A file that was not evaluated can hide real failures, so it must be
#     NAMED — a count threshold ("up to 2 files may be hidden") tracks no
#     identity and is therefore unauditable. An unevaluated file that is not
#     listed in tests/KNOWN_UNEVALUATED.txt fails the gate.
UNLISTED=0
: > "$TMP_DIR/unlisted"
UNEVAL_COUNT=0
if [ -f "${ACTUAL}.hangs" ]; then
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    UNEVAL_COUNT=$((UNEVAL_COUNT + 1))
    f="${line%% rc=*}"
    if [ ! -f "$UNEVALUATED_BASELINE" ] || ! grep -qF -- "$f" "$UNEVALUATED_BASELINE"; then
      printf '  + %s\n' "$line" >> "$TMP_DIR/unlisted"
      UNLISTED=1
    fi
  done < "${ACTUAL}.hangs"
fi
printf '   未评估: %s 个文件\n' "$UNEVAL_COUNT"
if [ "$UNEVAL_COUNT" -gt 0 ]; then
  printf '⚠️  未评估文件（未纳入本次失败统计，可能隐藏真实失败）:\n'
  sed 's/^/    /' "${ACTUAL}.hangs"
fi
if [ "$UNLISTED" -eq 1 ]; then
  if [ "${SKIP_UNEVALUATED_GATE:-no}" = "yes" ]; then
    reason="${RDDF_UNEVALUATED_BYPASS_REASON:-no reason given}"
    # The audit log belongs to the PROJECT, not to the checkout this script
    # runs from: in worktree mode the worktree is removed at archive time and
    # its .rddf/state/ with it ⇒ the audit entry would be lost. An explicitly
    # set RDDF_PROJECT_ROOT wins (that is how the tests point it elsewhere).
    if [ -z "${RDDF_PROJECT_ROOT:-}" ]; then
      AUDIT_ROOT="$REPO_ROOT"
      common_dir="$(git -C "$REPO_ROOT" rev-parse --git-common-dir 2>/dev/null || true)"
      case "$common_dir" in
        */.git) AUDIT_ROOT="$(dirname "$common_dir")" ;;
      esac
      RDDF_PROJECT_ROOT="$AUDIT_ROOT"
      export RDDF_PROJECT_ROOT
    fi
    # shellcheck source=../../_lib/bypass_audit.sh
    if [ -f "$REPO_ROOT/_lib/bypass_audit.sh" ]; then
      source "$REPO_ROOT/_lib/bypass_audit.sh"
      audit_bypass_log "SKIP_UNEVALUATED_GATE" "$reason" "" "regression-gate" || true
    fi
    printf '⏭  SKIP_UNEVALUATED_GATE=yes ⇒ 未评估门被跳过（已写 bypass 审计）\n'
    UNLISTED=0
  else
    printf '❌ 未评估文件不在 %s 内 ⇒ 门失败\n' "$UNEVALUATED_BASELINE" >&2
    sed 's/^/    /' "$TMP_DIR/unlisted" >&2
  fi
fi

# 2. Parse + diff via Python (handles '#' in test names, supports
#    structured output for the report).
#    SUPPRESS_SUCCESS_BANNER: when the unevaluated gate failed, the report
#    must NOT print "✅ 0 新增失败" — otherwise the only thing a reader sees
#    is a green checkmark.
SUPPRESS_SUCCESS_BANNER=0
[ "$UNLISTED" -eq 1 ] && SUPPRESS_SUCCESS_BANNER=1

BASELINE_PATH="$BASELINE" \
ACTUAL_PATH="$ACTUAL" \
SUPPRESS_SUCCESS_BANNER="$SUPPRESS_SUCCESS_BANNER" \
python3 - <<'PY'
import os, sys
from pathlib import Path

baseline = Path(os.environ["BASELINE_PATH"])
actual   = Path(os.environ["ACTUAL_PATH"])

# Parse baseline: preserve order, identify (name, key) pairs.
# rsplit " # " so test names containing '#' are preserved verbatim
# (same convention as refresh_known_failures.sh).
def parse_entries(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if " # " in s:
            key = s.rsplit(" # ", 1)[0].strip()
        else:
            key = s
        if key:
            out[key] = line
    return out

baseline_entries = parse_entries(baseline.read_text(encoding="utf-8"))
actual_set: set[str] = set()
if actual.exists():
    for line in actual.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s:
            actual_set.add(s)

known     = sorted(k for k in baseline_entries if k in actual_set)
new       = sorted(k for k in actual_set if k not in baseline_entries)
zombies   = sorted(k for k in baseline_entries if k not in actual_set)

print(f"已知失败: {len(known)}")
print(f"新增失败: {len(new)}")
print(f"已修复 (zombie): {len(zombies)}")

if new:
    print()
    print("=== 新增失败明细 (regressions — gate fails) ===")
    for n in new:
        print(f"  + {n}")
    sys.exit(1)

if zombies:
    print()
    print("=== 已修复 (zombie baseline entries — run refresh_known_failures.sh) ===")
    for z in zombies:
        print(f"  - {z}")
    # Zombie entries are warnings only. They were captured as
    # warnings precisely so the gate doesn't fail when the baseline
    # has stale entries — only REGRESSIONS (new failures) fail the gate.
    print()
    print("ℹ️  baseline has zombie entries. Run:")
    print("    bash tests/scripts/refresh_known_failures.sh --dry-run")

print()
if os.environ.get("SUPPRESS_SUCCESS_BANNER") == "1":
    print("⚠️  未评估门失败 ⇒ 本次不给出「0 新增失败」的结论")
else:
    print("✅ 0 新增失败")
PY
rc=$?

if [ "$rc" -ne 0 ] && [ "$rc" -ne 1 ]; then
  printf '❌ report_regression.sh internal error (exit %d)\n' "$rc" >&2
  exit 2
fi

# The unevaluated gate fails the gate even when no new failure was found.
if [ "$rc" -eq 0 ] && [ "$UNLISTED" -eq 1 ]; then
  exit 1
fi

exit "$rc"
