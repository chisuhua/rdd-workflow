"""Trigger data model and manager for the v3-scheduled-triggers change.

Provides Trigger dataclass + TriggerManager for register/unregister/dedup operations.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Optional
import datetime
import time
import uuid

from skills._lib.rate_limiter import TokenBucket


def _now_iso() -> str:
    return datetime.datetime.now().isoformat()


@dataclass
class Trigger:
    """A scheduled or event-driven trigger."""
    type: str  # "cron" | "fs" | "git" | "webhook"
    config: dict  # type-specific config (cron expr, paths, etc.)
    rate_limit: int = 60  # max fires per hour
    enabled: bool = True
    id: str = field(default_factory=lambda: f"trigger_{uuid.uuid4().hex[:8]}")
    created_at: str = field(default_factory=_now_iso)
    last_fire_at: Optional[str] = None
    token_bucket: float = 0.0  # current bucket level

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Trigger":
        # Filter to known fields for forward compat
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})

    def get_bucket(self) -> TokenBucket:
        """Get or reconstruct a TokenBucket for this trigger's rate_limit.

        Uses token_bucket field as persisted state; falls back to from_rate_limit.
        """
        if self.rate_limit <= 0:
            # Zero rate limit: only 1 fire ever allowed (capacity 1, no refill)
            return TokenBucket(capacity=1.0, refill_rate=0.0, tokens=self.token_bucket if self.token_bucket > 0 else 1.0)
        if self.token_bucket > 0:
            return TokenBucket.from_dict({
                "capacity": float(self.rate_limit),
                "refill_rate": self.rate_limit / 3600.0,
                "tokens": self.token_bucket,
                "last_refill": time.time(),
            })
        return TokenBucket.from_rate_limit(self.rate_limit)

class TriggerManager:
    """Manages a collection of triggers with dedup and rate limiting hooks."""

    def __init__(self, triggers: Optional[list] = None):
        self.triggers: list[Trigger] = triggers or []

    def register(self, trigger: Trigger) -> str:
        if not trigger.enabled:
            return trigger.id
        # Dedup by (type, config)
        for existing in self.triggers:
            if existing.type == trigger.type and existing.config == trigger.config:
                return existing.id
        self.triggers.append(trigger)
        return trigger.id

    def unregister(self, trigger_id: str) -> bool:
        before = len(self.triggers)
        self.triggers = [t for t in self.triggers if t.id != trigger_id]
        return len(self.triggers) < before

    def get_enabled(self) -> list:
        return [t for t in self.triggers if t.enabled]

    def deduplicate_events(self, event_type: str, payload: dict) -> list:
        """Return list of unique trigger IDs that match this event (deduped by type+config)."""
        seen: set = set()
        result: list = []
        for t in self.triggers:
            if t.enabled and t.type == event_type and self._matches(t, payload):
                key = (t.type, str(sorted(t.config.items())))
                if key not in seen:
                    seen.add(key)
                    result.append(t.id)
        return result

    def _matches(self, trigger: Trigger, payload: dict) -> bool:
        """Default match: all config keys present in payload."""
        for k, v in trigger.config.items():
            if payload.get(k) != v:
                return False
        return True

    def fire(self, trigger_id: str) -> bool:
        """Record a fire event subject to rate limiting. Returns False if rate-limited."""
        for t in self.triggers:
            if t.id == trigger_id:
                bucket = t.get_bucket()
                if not bucket.consume(1.0):
                    return False  # rate-limited
                t.last_fire_at = _now_iso()
                t.token_bucket = bucket.tokens  # persist bucket state
                return True
        return False
