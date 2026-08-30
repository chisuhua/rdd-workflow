"""`rddf regression diff` — compare baseline vs current failures."""
import re
from pathlib import Path


def parse_known_failures(text):
    """Parse KNOWN_FAILURES.txt — one test name per line, # = comment."""
    out = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name = line.split(" — ")[0].split(" #")[0].strip()
        if name:
            out.add(name)
    return out


def diff_failures(current_set, baseline_path):
    """Return (new_failures, removed_failures) sets."""
    baseline = parse_known_failures(Path(baseline_path).read_text(encoding="utf-8"))
    new = current_set - baseline
    removed = baseline - current_set
    return new, removed


def cmd_regression_diff(args):
    """Print baseline path + usage; real diff invoked from bash wrapper."""
    print("usage: rddf regression diff [--current <failures.txt>]")
    print("Reads tests/KNOWN_FAILURES.txt (baseline) and compares to current.")
    print("Returns non-zero exit when new failures appear (not in baseline).")
    return 0