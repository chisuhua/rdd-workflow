#!/usr/bin/env bash
# Selectively refresh tests/KNOWN_FAILURES.txt.
#
# Modes:
#   --scope <path>     Bats scope (file or dir; default: tests/integration/)
#                      May be repeated. Useful to avoid bats-core 1.13.0
#                      infinite-loop bug triggered by `bats tests/ --recursive`
#                      (see https://github.com/bats-core/bats-core/issues/...)
#   --actual <file>    Skip running bats; use this file's contents (one failure
#                      per line) as the actual failure set. For testing/import.
#   --dry-run          Print the diff to stdout; do NOT modify the file
#   --keep-comments    Preserve all existing comments verbatim (default: on)
#   --help             Show this help and exit
#
# Selective refresh logic (vs. previous wholesale regeneration):
#   1. Parse KNOWN_FAILURES.txt line-by-line:
#      - Blank lines and lines starting with '#' are comments → PRESERVED
#      - Lines of the form "name # comment" are entries → evaluated:
#          * if `name` is in the current failure set → KEPT (with original comment)
#          * if `name` is NOT failing anymore → DROPPED (the test was fixed)
#   2. After walking the original file, append a "newly added" section listing
#      failures that are NEW (not in the previous baseline) with a placeholder
#      comment "reason required (added YYYY-MM-DD by refresh_known_failures.sh)".
#   3. Print a diff summary: kept, removed, added.
#
# Why selective: the previous wholesale regeneration wiped all curated
# comment history (which explained WHY each entry was pre-existing) and
# gave every entry a placeholder comment, making the baseline hard to
# audit. Selective mode preserves that provenance.
#
# Usage:
#   bash tests/scripts/refresh_known_failures.sh
#   bash tests/scripts/refresh_known_failures.sh --scope tests/integration/test_adr_directory.bats
#   bash tests/scripts/refresh_known_failures.sh --dry-run --scope tests/integration/

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BASELINE="$REPO_ROOT/tests/KNOWN_FAILURES.txt"
TMP_DIR="$(mktemp -d -t rdd-refresh-known-failures-XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

SCOPES=()
DRY_RUN=0
KEEP_COMMENTS=1
ACTUAL_FILE=""
while [ $# -gt 0 ]; do
    case "$1" in
        --scope)        SCOPES+=("$2"); shift 2 ;;
        --actual)       ACTUAL_FILE="$2"; shift 2 ;;
        --dry-run)      DRY_RUN=1; shift ;;
        --keep-comments) KEEP_COMMENTS=1; shift ;;
        --no-keep-comments) KEEP_COMMENTS=0; shift ;;
        -h|--help)
            sed -n '2,30p' "$0"
            exit 0
            ;;
        *)
            printf '❌ unknown arg: %s\n' "$1" >&2
            exit 2
            ;;
    esac
done

if [ "${#SCOPES[@]}" -eq 0 ] && [ -z "$ACTUAL_FILE" ]; then
    SCOPES=("tests/integration/")
fi

if [ -n "$ACTUAL_FILE" ]; then
    if [ ! -f "$ACTUAL_FILE" ]; then
        printf '❌ --actual file not found: %s\n' "$ACTUAL_FILE" >&2
        exit 2
    fi
    cp "$ACTUAL_FILE" "$TMP_DIR/actual"
else
    if ! command -v bats >/dev/null 2>&1; then
        printf '❌ bats-core is required to refresh the baseline\n' >&2
        exit 127
    fi

    set +e
    (cd "$REPO_ROOT" && bats "${SCOPES[@]}") >"$TMP_DIR/bats-output" 2>&1
    bats_status=$?
    set -e

    sed -nE 's/^not ok [0-9]+ (.*)$/\1/p' "$TMP_DIR/bats-output" \
      | sed -E 's/[[:space:]]+#.*$//' \
      | sed '/^[[:space:]]*$/d' \
      | sort -u >"$TMP_DIR/actual"

    if [ "$bats_status" -eq 127 ] && [ ! -s "$TMP_DIR/actual" ]; then
        printf '❌ Bats could not run; baseline was not changed\n' >&2
        cat "$TMP_DIR/bats-output" >&2
        exit 127
    fi
fi

BASELINE_PATH="$BASELINE" \
ACTUAL_PATH="$TMP_DIR/actual" \
DRY_RUN="$DRY_RUN" \
KEEP_COMMENTS="$KEEP_COMMENTS" \
REPO_ROOT="$REPO_ROOT" \
python3 - <<'PY'
import os, sys
from datetime import date
from pathlib import Path

baseline = Path(os.environ["BASELINE_PATH"])
actual   = Path(os.environ["ACTUAL_PATH"])
dry_run  = os.environ["DRY_RUN"] == "1"
repo_root = Path(os.environ["REPO_ROOT"])

# Read actual failures (already deduped + sorted by the bash pipeline)
actual_set = set()
if actual.exists():
    for line in actual.read_text(encoding="utf-8").splitlines():
        name = line.strip()
        if name:
            actual_set.add(name)

# Parse baseline: walk line-by-line, classify each line
raw = baseline.read_text(encoding="utf-8") if baseline.exists() else ""
raw_lines = raw.splitlines()

# New layout (selective output):
#   [original comment lines, preserved verbatim]
#   [original entry lines that STILL fail, preserved verbatim]
#   [blank line]
#   # === YYYY-MM-DD refresh summary: kept=K, removed=R, added=A
#   [newly added entry lines]
# Entries are emitted in deterministic order (sorted) within their group.

orig_entries_seen = []
orig_lines_out = []
removed = []
seen_keys = set()

for line in raw_lines:
    stripped = line.strip()
    if not stripped or stripped.lstrip().startswith("#"):
        orig_lines_out.append(line)
        continue
    # rsplit: bats test names may contain "#" (e.g. "AGENTS.md: trap #6 ...");
    # the human reason is always the segment after the LAST " # ".
    if " # " in line:
        full_key = line.rsplit(" # ", 1)[0].strip()
    else:
        full_key = line.strip()
    if not full_key:
        orig_lines_out.append(line)
        continue
    if full_key in seen_keys:
        continue
    seen_keys.add(full_key)
    orig_entries_seen.append((full_key, line))
    if full_key in actual_set:
        orig_lines_out.append(line)
    else:
        removed.append(full_key)

kept_count = sum(1 for k, _ in orig_entries_seen if k in actual_set)
added = sorted(n for n in actual_set if n not in seen_keys)

today = date.today().isoformat()
summary = (
    f"# === {today} refresh summary (selective): "
    f"kept={kept_count}, removed={len(removed)}, added={len(added)} ==="
)

# Build output
out_lines = list(orig_lines_out)
# Trim trailing blank lines for clean join
while out_lines and not out_lines[-1].strip():
    out_lines.pop()

out_lines.append("")  # blank before summary
out_lines.append(summary)

if added:
    out_lines.append(f"# Newly added failures as of {today}:")
    for name in added:
        out_lines.append(
            f"{name} # reason required (added {today} by refresh_known_failures.sh)"
        )

new_content = "\n".join(out_lines) + "\n"

# Report
print(f"📋 Baseline:  {baseline}")
print(f"   Source failures file: {actual}")
print(f"   kept:    {kept_count}")
print(f"   removed: {len(removed)}")
for n in removed:
    print(f"     - {n}")
print(f"   added:   {len(added)}")
for n in added:
    print(f"     + {n}")

if dry_run:
    print()
    print("--- diff (dry-run, file NOT modified) ---")
    import difflib
    diff = difflib.unified_diff(
        raw_lines + [""], new_content.splitlines() + [""],
        fromfile="before", tofile="after (dry-run)", lineterm=""
    )
    for line in diff:
        print(line)
    sys.exit(0)

# Atomic write
tmp = baseline.with_suffix(baseline.suffix + ".tmp")
tmp.write_text(new_content, encoding="utf-8")
tmp.replace(baseline)
print()
print(f"✅ wrote {baseline}")
PY
