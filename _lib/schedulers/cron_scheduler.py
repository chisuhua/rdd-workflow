"""CronScheduler — converts cron expressions to next-fire timestamps using croniter."""
from __future__ import annotations
import datetime
import threading
from typing import Callable, Optional

from croniter import croniter

from skills._lib.triggers import Trigger, TriggerManager


class CronExpressionError(ValueError):
    """Raised when a cron expression is invalid."""


def validate_cron(expression: str) -> bool:
    """Return True if expression is a valid 5-field cron string."""
    if not isinstance(expression, str) or not expression.strip():
        return False
    try:
        croniter(expression)
        return True
    except (ValueError, KeyError, TypeError):
        return False


def next_fire_time(expression: str, after: Optional[datetime.datetime] = None) -> datetime.datetime:
    """Compute next fire time after given datetime (defaults to now)."""
    if not validate_cron(expression):
        raise CronExpressionError(f"Invalid cron expression: {expression!r}")
    base = after or datetime.datetime.now()
    return croniter(expression, base).get_next(datetime.datetime)


class CronScheduler:
    """Schedules cron-based triggers. Each trigger runs in its own daemon thread."""

    def __init__(self, manager: TriggerManager, on_fire: Callable[[str], None]):
        self.manager = manager
        self.on_fire = on_fire  # called with trigger_id when trigger fires
        self._threads: dict[str, threading.Thread] = {}
        self._stop = threading.Event()

    def schedule(self, trigger: Trigger) -> bool:
        """Schedule a single cron trigger in a background thread."""
        if trigger.type != "cron":
            return False
        expression = trigger.config.get("expression", "")
        if not validate_cron(expression):
            raise CronExpressionError(f"Trigger {trigger.id}: invalid expression {expression!r}")
        if trigger.id in self._threads:
            return False  # already scheduled
        thread = threading.Thread(
            target=self._loop, args=(trigger, expression),
            name=f"cron-{trigger.id}", daemon=True,
        )
        self._threads[trigger.id] = thread
        thread.start()
        return True

    def _loop(self, trigger: Trigger, expression: str) -> None:
        """Wait until next fire time, fire callback, repeat."""
        while not self._stop.is_set():
            try:
                nxt = next_fire_time(expression)
                wait_secs = (nxt - datetime.datetime.now()).total_seconds()
                if wait_secs > 0:
                    if self._stop.wait(timeout=wait_secs):
                        return  # stopped during sleep
                # Fire
                if not self.manager.fire(trigger.id):
                    continue  # rate-limited
                self.on_fire(trigger.id)
            except Exception:
                # Catch all to keep thread alive
                if self._stop.wait(timeout=60):
                    return

    def schedule_all(self) -> int:
        """Schedule all cron triggers in the manager. Returns count scheduled."""
        count = 0
        for trigger in self.manager.get_enabled():
            if trigger.type == "cron":
                try:
                    if self.schedule(trigger):
                        count += 1
                except CronExpressionError:
                    pass  # skip invalid
        return count

    def stop(self) -> None:
        """Signal all threads to stop and wait for them."""
        self._stop.set()
        for thread in self._threads.values():
            thread.join(timeout=2.0)
        self._threads.clear()
