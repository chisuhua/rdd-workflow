# tests/unit/test_reflect_cooldown.py
import json, os, time, pytest, tempfile
from pathlib import Path

# Add project root to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from skills._lib.reflect_cooldown import CooldownManager


class TestCooldownManager:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cooldown_file = os.path.join(self.tmpdir, "reflect-cooldown.json")
        self.manager = CooldownManager(self.cooldown_file, cooldown_hours=24)

    def test_record_and_check_cooldown(self):
        fp = "ship:archive-done:worktree-timeout"
        # Initially not cooling
        assert not self.manager.is_cooling(fp)
        # Record it
        self.manager.record(fp)
        # Now it should be cooling
        assert self.manager.is_cooling(fp)

    def test_different_fingerprints_independent(self):
        fpa = "plan:plan-done:quality-fail"
        fpb = "ship:archive-done:worktree-timeout"
        self.manager.record(fpa)
        assert self.manager.is_cooling(fpa)
        assert not self.manager.is_cooling(fpb)

    def test_expired_cooldown(self):
        fp = "plan:plan-done:quality-fail"
        self.manager.record(fp)
        # Artificially age the timestamp past 24h
        with open(self.cooldown_file) as f:
            data = json.load(f)
        data[fp]["last_triggered_at"] = (time.time() - 25 * 3600)
        with open(self.cooldown_file, 'w') as f:
            json.dump(data, f)
        assert not self.manager.is_cooling(fp)

    def test_cleanup_expired_removes_old_entries(self):
        fp_old = "old:fingerprint:1"
        fp_new = "new:fingerprint:2"
        self.manager.record(fp_old)
        self.manager.record(fp_new)
        with open(self.cooldown_file) as f:
            data = json.load(f)
        data[fp_old]["last_triggered_at"] = (time.time() - 25 * 3600)
        with open(self.cooldown_file, 'w') as f:
            json.dump(data, f)
        self.manager.cleanup_expired()
        with open(self.cooldown_file) as f:
            data = json.load(f)
        assert fp_old not in data
        assert fp_new in data

    def test_file_not_exists_returns_not_cooling(self):
        if os.path.exists(self.cooldown_file):
            os.remove(self.cooldown_file)
        assert not self.manager.is_cooling("any:fingerprint:here")

    def test_record_preserves_existing_entries(self):
        fp1 = "fp:one"
        fp2 = "fp:two"
        self.manager.record(fp1)
        self.manager.record(fp2)
        with open(self.cooldown_file) as f:
            data = json.load(f)
        assert fp1 in data
        assert fp2 in data
