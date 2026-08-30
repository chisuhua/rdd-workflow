"""Additional CronScheduler coverage: edge cases + idempotency."""
from __future__ import annotations

import datetime

import pytest

from skills._lib.schedulers.cron_scheduler import (
    CronScheduler, CronExpressionError, next_fire_time, validate_cron,
)
from skills._lib.triggers import Trigger, TriggerManager


class TestCronValidation:
    def test_valid_cron_ok(self):
        assert validate_cron("*/5 * * * *") is True
        assert validate_cron("0 8 * * 1") is True

    def test_invalid_cron_rejected(self):
        assert validate_cron("not-a-cron") is False
        assert validate_cron("") is False
        assert validate_cron("61 * * * *") is False  # minute out of range

    def test_next_fire_time_after(self):
        base = datetime.datetime(2026, 1, 1, 0, 0, 0)
        nxt = next_fire_time("*/15 * * * *", after=base)
        assert nxt >= base
        assert (nxt - base).total_seconds() <= 900

    def test_next_fire_invalid_raises(self):
        with pytest.raises(CronExpressionError):
            next_fire_time("bad", after=datetime.datetime.now())


class TestCronSchedulerIdempotency:
    def test_schedule_same_trigger_twice_noop(self):
        mgr = TriggerManager()
        mangled = []  # collect on_fire calls
        sched = CronScheduler(mgr, on_fire=lambda tid: mangled.append(tid))
        trg = Trigger(id="t1", type="cron", config={"expression": "0 0 1 1 *"})
        mgr.register(trg)
        assert sched.schedule(trg) is True
        assert sched.schedule(trg) is False  # already scheduled (idempotent)
        sched.stop()

    def test_schedule_all_counts(self):
        mgr = TriggerManager()
        trg1 = Trigger(id="a", type="cron", config={"expression": "0 0 1 1 *"})
        trg2 = Trigger(id="b", type="cron", config={"expression": "bad"})
        mgr.register(trg1)
        mgr.register(trg2)
        sched = CronScheduler(mgr, on_fire=lambda tid: None)
        assert sched.schedule_all() == 1  # invalid expression skipped
        sched.stop()
