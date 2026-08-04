#!/usr/bin/env bash
# Explicitly regenerate tests/KNOWN_FAILURES.txt from recursive Bats output.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BASELINE="$REPO_ROOT/tests/KNOWN_FAILURES.txt"
TMP_DIR="$(mktemp -d -t rdd-refresh-known-failures-XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

if ! command -v bats >/dev/null 2>&1; then
  printf '❌ bats-core is required to refresh the baseline\n' >&2
  exit 127
fi

set +e
(cd "$REPO_ROOT" && bats tests/ --recursive) >"$TMP_DIR/bats-output" 2>&1
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

BASELINE_PATH="$BASELINE" ACTUAL_PATH="$TMP_DIR/actual" python3 - <<'PY'
import os
from pathlib import Path

baseline = Path(os.environ["BASELINE_PATH"])
actual = Path(os.environ["ACTUAL_PATH"])

comments = {}
if baseline.exists():
    for raw in baseline.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, separator, comment = line.partition(" # ")
        comments[name.strip()] = comment.strip() if separator else ""

names = [line.strip() for line in actual.read_text(encoding="utf-8").splitlines() if line.strip()]
lines = []
for name in names:
    comment = comments.get(name, "reason required")
    lines.append(f"{name} # {comment}")

baseline.parent.mkdir(parents=True, exist_ok=True)
tmp = baseline.with_suffix(baseline.suffix + ".tmp")
tmp.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
tmp.replace(baseline)
print(f"✅ refreshed {len(lines)} known failures: {baseline}")
PY
