"""``rddf hub retry-failed`` — list / retry Hub auto-file failures.

Reads .cross-repo-audit.jsonl, surfaces entries with
`decision == 'fail-auto-issue'`. Retry is a stub here (real retry
needs gh auth + network); the listing is the primary use case.
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path


AUDIT_FILE = ".rddf/state/.cross-repo-audit.jsonl"


def _audit_path():
    root = os.environ.get("RDDF_PROJECT_ROOT", ".")
    return Path(root) / AUDIT_FILE


def _load_failed_entries(path):
    out = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("decision") == "fail-auto-issue":
            out.append(entry)
    return out


def cmd_hub_retry(args) -> int:
    if not args or args[0] in ("-h", "--help", "help"):
        print("usage: rddf hub retry-failed [list|retry <name>]")
        return 0
    sub = args[0]
    path = _audit_path()
    if sub == "list":
        failed = _load_failed_entries(path)
        if not failed:
            print("✅ no failed Hub auto-file entries")
            return 0
        print(f"❌ {len(failed)} failed Hub auto-file entries:")
        for e in failed:
            print(f"  - {e.get('proposal_name', '?')} ({e.get('timestamp', '?')})")
        return 0
    print(f"❌ hub: unknown sub-command {sub!r}", file=sys.stderr)
    return 2