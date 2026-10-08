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
#   0 - no new failures (zombie entries are warnings, not errors)
#   1 - new failures detected (regression)
#   2 - infrastructure error (Bats missing, baseline missing, etc.)
#
# Zombie entries are warnings only — they don't fail the gate. After
# reviewing, run `bash tests/scripts/refresh_known_failures.sh` to retire
# them. Zombie detection prevents the 5-month-stale baseline pattern
# (per add-baseline-freshness-doctor 2026-10-08).

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BASELINE="$REPO_ROOT/tests/KNOWN_FAILURES.txt"
TMP_DIR="$(mktemp -d -t rdd-known-failures-XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

if [ ! -f "$BASELINE" ]; then
  printf '❌ baseline file is missing: %s\n' "$BASELINE" >&2
  exit 2
fi

# 1. Collect current failures (bypasses the slow/buggy recursive invocation).
ACTUAL="$TMP_DIR/actual"
if BATS_TIMEOUT="${BATS_TIMEOUT:-30}" bash "$SCRIPT_DIR/collect_bats_failures.sh" \
      tests/integration/ "$ACTUAL" >"$TMP_DIR/collect.log" 2>&1; then
  bats_status=0
else
  # collect_bats_failures.sh exits 1 if no .bats files found; treat as infra
  # error if the output is empty.
  if [ ! -s "$ACTUAL" ]; then
    printf '❌ No Bats failures collected; inspect collect.log:\n' >&2
    cat "$TMP_DIR/collect.log" >&2
    exit 2
  fi
  bats_status=1
fi

# 2. Parse + diff via Python (handles '#' in test names, supports
#    structured output for the report).
BASELINE_PATH="$BASELINE" \
ACTUAL_PATH="$ACTUAL" \
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
    # Zombie entries are warnings, not errors. They were captured as
    # warnings precisely so the gate doesn't fail when the baseline
    # has stale entries — only REGRESSIONS (new failures) fail the gate.
    print()
    print("ℹ️  baseline has zombie entries. Run:")
    print("    bash tests/scripts/refresh_known_failures.sh --dry-run")

print()
print("✅ 0 新增失败")
PY
rc=$?

if [ "$rc" -ne 0 ] && [ "$rc" -ne 1 ]; then
  printf '❌ report_regression.sh internal error (exit %d)\n' "$rc" >&2
  exit 2
fi

exit "$rc"
