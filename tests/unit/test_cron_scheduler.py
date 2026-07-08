"""Unit tests for skills/_lib/schedulers/cron_scheduler.py"""
import datetime
import time
from skills._lib.triggers import Trigger, TriggerManager
from skills._lib.schedulers.cron_scheduler import (
    CronScheduler, CronExpressionError, validate_cron, next_fire_time,
)


def test_validate_cron_valid():
    assert validate_cron("0 * * * *") is True
    assert validate_cron("*/5 * * * *") is True
    assert validate_cron("0 2 * * 0") is True


def test_validate_cron_invalid():
    assert validate_cron("not a cron") is False
    assert validate_cron("") is False
    assert validate_cron("99 * * * *") is False  # minute > 59


def test_next_fire_time():
    base = datetime.datetime(2026, 1, 1, 0, 0, 0)
    # "0 * * * *" = top of every hour
    nxt = next_fire_time("0 * * * *", after=base)
    assert nxt == datetime.datetime(2026, 1, 1, 1, 0, 0)


def test_next_fire_invalid_raises():
    import pytest
    with pytest.raises(CronExpressionError):
        next_fire_time("invalid")


def test_scheduler_schedule_returns_true_for_cron():
    m = TriggerManager([Trigger(type="cron", config={"expression": "0 * * * *"})])
    fired = []
    sched = CronScheduler(m, on_fire=lambda tid: fired.append(tid))
    t = m.triggers[0]
    assert sched.schedule(t) is True
    sched.stop()


def test_scheduler_schedule_returns_false_for_non_cron():
    m = TriggerManager([Trigger(type="fs", config={"path": "/tmp"})])
    sched = CronScheduler(m, on_fire=lambda tid: None)
    assert sched.schedule(m.triggers[0]) is False


def test_scheduler_schedule_invalid_raises():
    m = TriggerManager([Trigger(type="cron", config={"expression": "bad"})])
    sched = CronScheduler(m, on_fire=lambda tid: None)
    import pytest
    with pytest.raises(CronExpressionError):
        sched.schedule(m.triggers[0])


def test_scheduler_schedule_all_skips_invalid():
    m = TriggerManager([
        Trigger(type="cron", config={"expression": "0 * * * *"}),
        Trigger(type="cron", config={"expression": "bad"}),
        Trigger(type="fs", config={"path": "/tmp"}),
    ])
    sched = CronScheduler(m, on_fire=lambda tid: None)
    count = sched.schedule_all()
    assert count == 1
    sched.stop()


def test_scheduler_dedup_double_schedule():
    m = TriggerManager([Trigger(type="cron", config={"expression": "0 * * * *"})])
    sched = CronScheduler(m, on_fire=lambda tid: None)
    t = m.triggers[0]
    assert sched.schedule(t) is True
    assert sched.schedule(t) is False  # already scheduled
    sched.stop()
