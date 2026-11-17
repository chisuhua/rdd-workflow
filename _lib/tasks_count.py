"""Canonical checkbox counter for tasks.md (fix-iteration-tasks-total).

Why this lives outside the `iteration` package: five call sites needed the
same (done, total) pair, and three of them (`skills/execute/scripts/
execute_step7.py`, `_lib/discover_ship_changes.py`, `skills/rdd-doctor/...
/tasks_checkbox_check.py`) sit outside `_lib.iteration`. Importing
`_lib.iteration.archive_sidecar` from there triggers the package's own
re-export shim and deadlocks against `_lib/iteration/store.py` (circular
init). This module has NO imports beyond `re`, so it is safe everywhere.

Counting rules — every caller must use this one:

  - indented sub-tasks count (a sub-task is a task)
  - ``[x]`` and ``[X]`` both count as done
  - ``-[x]`` without a space after the dash counts
  - checkboxes inside *balanced* fenced code blocks do NOT count
  - done and total come from the SAME regex, so ``done <= total`` always

The five rules that existed before disagreed on all of the above: only this
one accepted uppercase `[X]` AND indented sub-tasks, which is why `done` and
`total` could come from different populations.
"""
from __future__ import annotations

import re

_CHECKBOX = re.compile(r"^\s*-\s*\[([ xX])\]\s", re.MULTILINE)

_FENCE = re.compile(r"^\s*```", re.MULTILINE)


def _strip_fenced_code(text: str) -> str:
    """Drop fenced code blocks — checkboxes there are examples, not tasks.

    Only strips when the fences are balanced: an unclosed fence would
    otherwise swallow the rest of the file and under-count real tasks.
    """
    if len(_FENCE.findall(text)) % 2:
        return text  # unbalanced: count everything rather than risk undercount
    out: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(line)
    return "\n".join(out)


def count_tasks(text: str) -> tuple[int, int]:
    """Count ``(done, total)`` checkboxes in a tasks.md string.

    Returns:
        (done, total). ``(0, 0)`` for text with no checkboxes.
    """
    matches = _CHECKBOX.findall(_strip_fenced_code(text))
    done = sum(1 for m in matches if m in ("x", "X"))
    return done, len(matches)


def count_done_tasks(text: str) -> int:
    """The `done` half of :func:`count_tasks` (backward-compatible helper)."""
    return count_tasks(text)[0]


__all__ = ["count_tasks", "count_done_tasks"]
