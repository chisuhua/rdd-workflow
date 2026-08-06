# skills/_lib/reflect_cooldown.py
"""24h fingerprint-based cooldown manager for reflect_engine."""

import json, os, time
from pathlib import Path


class CooldownManager:
    """Manages cooldown state for reflection fingerprints.

    State file: .rddf/state/reflect-cooldown.json
    Format: {fingerprint: {last_triggered_at: float, first_triggered_at: float}}
    """

    def __init__(self, cooldown_file=None, cooldown_hours=24):
        if cooldown_file is None:
            root = self._find_project_root()
            cooldown_file = os.path.join(root, ".rddf", "state", "reflect-cooldown.json")
        self.cooldown_file = cooldown_file
        self.cooldown_seconds = cooldown_hours * 3600

    @staticmethod
    def _find_project_root():
        """Find the project root by looking for .git directory."""
        current = Path.cwd()
        for parent in [current] + list(current.parents):
            if (parent / ".git").exists():
                return str(parent)
        return str(current)

    def _read(self):
        """Read cooldown file, return {} if missing or invalid."""
        if not os.path.exists(self.cooldown_file):
            return {}
        try:
            with open(self.cooldown_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _write(self, data):
        """Write cooldown data atomically."""
        os.makedirs(os.path.dirname(self.cooldown_file), exist_ok=True)
        tmp = self.cooldown_file + ".tmp"
        with open(tmp, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp, self.cooldown_file)

    def is_cooling(self, fingerprint):
        """Check if a fingerprint is within the cooldown window."""
        data = self._read()
        entry = data.get(fingerprint)
        if entry is None:
            return False
        last = entry.get("last_triggered_at", 0)
        elapsed = time.time() - last
        return elapsed < self.cooldown_seconds

    def record(self, fingerprint):
        """Record a trigger event for a fingerprint."""
        data = self._read()
        now = time.time()
        if fingerprint not in data:
            data[fingerprint] = {"first_triggered_at": now}
        data[fingerprint]["last_triggered_at"] = now
        self._write(data)

    def cleanup_expired(self):
        """Remove entries that have exceeded the cooldown window."""
        data = self._read()
        now = time.time()
        expired = [fp for fp, entry in data.items()
                   if (now - entry.get("last_triggered_at", 0)) > self.cooldown_seconds]
        for fp in expired:
            del data[fp]
        if expired:
            self._write(data)
