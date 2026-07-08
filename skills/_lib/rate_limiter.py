"""TokenBucket rate limiter with persistence support for v3-scheduled-triggers."""
from __future__ import annotations
import time
from dataclasses import dataclass


@dataclass
class TokenBucket:
    """Token bucket rate limiter.

    - capacity: max tokens the bucket can hold
    - refill_rate: tokens added per second
    - A call to consume(n) returns True if n tokens are available; otherwise False.
    """
    capacity: float
    refill_rate: float
    tokens: float = 0.0
    last_refill: float = 0.0

    def __post_init__(self):
        if self.last_refill == 0.0:
            self.last_refill = time.time()
        if self.tokens == 0.0:
            self.tokens = self.capacity  # start full

    def _refill(self) -> None:
        now = time.time()
        elapsed = now - self.last_refill
        if elapsed > 0:
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now

    def consume(self, n: float = 1.0) -> bool:
        """Try to consume n tokens. Returns True if successful."""
        self._refill()
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False

    def to_dict(self) -> dict:
        return {
            "capacity": self.capacity,
            "refill_rate": self.refill_rate,
            "tokens": self.tokens,
            "last_refill": self.last_refill,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TokenBucket":
        return cls(
            capacity=data["capacity"],
            refill_rate=data["refill_rate"],
            tokens=data.get("tokens", 0.0),
            last_refill=data.get("last_refill", 0.0),
        )

    @classmethod
    def from_rate_limit(cls, rate_per_hour: int) -> "TokenBucket":
        """Create bucket that allows `rate_per_hour` fires per hour.

        Capacity = rate_per_hour (allows initial burst), refill at rate_per_hour / 3600 per second.
        """
        if rate_per_hour <= 0:
            raise ValueError("rate_per_hour must be positive")
        return cls(
            capacity=float(rate_per_hour),
            refill_rate=rate_per_hour / 3600.0,
        )
