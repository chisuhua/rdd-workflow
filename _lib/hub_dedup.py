"""Hub auto-file dedup (per phase-3-general-20260829063814).

Hash the proposal content; skip auto-issue if recent audit log entry
matches the same hash + name.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path


def compute_proposal_hash(imp_path) -> str:
    """SHA256 hex of the .rddf/improvements/<name>.md body."""
    p = Path(imp_path)
    body = p.read_bytes()
    return hashlib.sha256(body).hexdigest()


def was_filed_recently(name: str, content_hash: str, log_path) -> bool:
    """Return True if the latest audit log entry for `name` matches `content_hash`."""
    p = Path(log_path)
    if not p.exists():
        return False
    latest_match: bool = False
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("proposal_name") != name:
            continue
        latest_match = (entry.get("hub_hash") == content_hash)
    return latest_match