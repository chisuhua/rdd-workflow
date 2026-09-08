#!/usr/bin/env bash
# tests/e2e/_lib/golden_compare.bash
# Golden output lock helper per 2026-09-08-e2e-test-plan-design.md §3.1
# Combines: (1) full file sha256 + (2) key-field extracted values.
# Drift detected = either sha changed OR key field value changed.
# Uses env-var passing to Python to avoid Oracle C1 bash injection.

# golden_compare::update <golden_file> <actual_file> <csv_fields>
# Compute sha256 + extract <csv_fields> as JSON paths, write to <golden_file>.
golden_compare::update() {
    local golden="$1" actual="$2" fields="$3"
    local sha
    sha=$(sha256sum "$actual" | awk '{print $1}')
    {
        echo "sha256:$sha"
        echo "fields:$fields"
        echo "values:"
    } > "$golden"
    GOLDEN_COMPARE_ACTUAL="$actual" \
    GOLDEN_COMPARE_FIELDS="$fields" \
    GOLDEN_COMPARE_OUT="$golden" \
    python3 -c '
import json, os
data = json.load(open(os.environ["GOLDEN_COMPARE_ACTUAL"]))
fields = os.environ["GOLDEN_COMPARE_FIELDS"].split(",")
out = open(os.environ["GOLDEN_COMPARE_OUT"], "a")
for f in fields:
    f = f.strip()
    if not f:
        continue
    parts = f.split(".")
    val = data
    for p in parts:
        if val is None:
            break
        if p.isdigit():
            val = val[int(p)] if isinstance(val, list) and int(p) < len(val) else None
        elif isinstance(val, dict):
            val = val.get(p)
        else:
            val = None
    out.write(f"  {f}={val}\n")
out.close()
'
}

# golden_compare::check <golden_file> <actual_file> <csv_fields>
# Return 0 if both sha and key fields match, 1 if any drift, 2 on error.
golden_compare::check() {
    local golden="$1" actual="$2" fields="$3"
    local actual_golden
    actual_golden=$(mktemp)
    golden_compare::update "$actual_golden" "$actual" "$fields"
    if diff -q "$golden" "$actual_golden" >/dev/null 2>&1; then
        rm -f "$actual_golden"
        return 0
    else
        diff "$golden" "$actual_golden" >&2 || true
        rm -f "$actual_golden"
        return 1
    fi
}

# golden_compare::regen <golden_file> <actual_file> <csv_fields>
# Alias for update, used when UPDATE_GOLDEN=1 env is set.
golden_compare::regen() {
    golden_compare::update "$@"
}
