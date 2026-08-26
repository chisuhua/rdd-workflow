"""rdd-verifier 5th phase Python helpers.

Per ADR-0034 §4.1: re-exports the public API for use by both the CLI
backend and the SKILL.md state machine.

Modules:
  - classify: heuristic failure labeling
  - cache: SHA-fingerprint verdict cache
  - loop_state: .verifier-loop.json load/save
"""
from _lib.verifier.classify import classify_failure  # noqa: F401
from _lib.verifier.cache import (  # noqa: F401
    verdict_cache,
    read_verdict_cache,
    is_cache_fresh,
)
from _lib.verifier.loop_state import (  # noqa: F401
    load_loop_state,
    save_loop_state,
    init_loop_state,
)

__all__ = [
    "classify_failure",
    "verdict_cache",
    "read_verdict_cache",
    "is_cache_fresh",
    "load_loop_state",
    "save_loop_state",
    "init_loop_state",
]