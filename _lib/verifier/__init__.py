"""rdd-verifier 5th phase Python helpers.

Per ADR-0034 §4.1: re-exports the public API for use by both the CLI
backend and the SKILL.md state machine.

Modules are added progressively:
  - classify: heuristic failure labeling (Task 4)
  - cache: SHA-fingerprint verdict cache (Task 5)
  - loop_state: .verifier-loop.json load/save (Task 6)
"""
from _lib.verifier.classify import classify_failure  # noqa: F401
from _lib.verifier.cache import (  # noqa: F401
    verdict_cache,
    read_verdict_cache,
    is_cache_fresh,
)

__all__ = [
    "classify_failure",
    "verdict_cache",
    "read_verdict_cache",
    "is_cache_fresh",
]