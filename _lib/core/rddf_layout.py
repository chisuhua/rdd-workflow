"""Single source of truth for the `.rddf/` layout.

ADR-0026 defines the two storage classes (`runtime-only` / `committed`) and
the dot-prefix path convention; this module turns that decision into an
executable manifest. `class` comes from ADR-0026 and nothing else — there is
no third classification.

The manifest is pure data: no IO, no imports from the rest of `_lib`. Two
consumers read it:

- `rddf layout --json` — the machine-readable view (consumers / third-party CI)
- `skills/rdd-doctor/scripts/checks/layout_check.py` — the diagnostic view

Note on the `class` field: `class` is a Python keyword, so the dataclass
attribute is `layout_class` and `as_dicts()` maps it back to the JSON key
`class` (the name the contract uses).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CLASSES = ("runtime-only", "committed")
REQUIRED_WHEN = ("always", "worktree", "never")
SEVERITIES = ("WARNING", "INFO")
ROLES = ("rdd", "agent", "user", "git", "external-tool")

Kind = Literal["dir", "file"]
RequiredWhen = Literal["always", "worktree", "never"]
StorageClass = Literal["runtime-only", "committed"]


@dataclass(frozen=True)
class LayoutEntry:
    """One top-level entry of `.rddf/`.

    path           — name relative to `.rddf/` (may be a glob, e.g. `.roadmap-migrate-backup-*`)
    kind           — `dir` | `file`
    read_by        — who reads it (observable facts, not judgements)
    write_by       — who writes it
    required_when  — `always` | `worktree` | `never` (never = not required to exist)
    transient      — ephemeral entry (registered so it is not reported as unregistered)
    layout_class   — ADR-0026 storage class: `runtime-only` | `committed`
    severity       — severity of this entry's *missing* judgement
    """

    path: str
    kind: Kind
    read_by: tuple[str, ...]
    write_by: tuple[str, ...]
    required_when: RequiredWhen
    transient: bool
    layout_class: StorageClass
    severity: str


RDFF_LAYOUT: tuple[LayoutEntry, ...] = (
    LayoutEntry(
        # `state/` holds two families of files: rdd-written runtime state
        # (state_vector, event log, handoffs, verifier namespace) and
        # agent-written governance state (`.rddf/state/role.json`,
        # `.rddf/state/pair.json` — the opencode build-agent role registry).
        # The agent writes but does not read rdd's state internals.
        "state", "dir", ("rdd",), ("rdd", "agent"), "always", False, "runtime-only", "WARNING",
    ),
    LayoutEntry(
        "wt", "dir", ("rdd",), ("git",), "worktree", False, "runtime-only", "WARNING",
    ),
    LayoutEntry(
        "detectors", "dir", ("rdd",), ("user",), "never", False, "runtime-only", "INFO",
    ),
    LayoutEntry(
        "actions", "dir", ("rdd",), ("user",), "never", False, "runtime-only", "INFO",
    ),
    LayoutEntry(
        "issues", "dir", ("rdd",), ("rdd",), "never", False, "runtime-only", "INFO",
    ),
    LayoutEntry(
        "improvements", "dir", ("rdd",), ("rdd", "agent"), "always", False, "committed", "WARNING",
    ),
    LayoutEntry(
        # Proposal index files (ADR-0026: internal metadata under `.rddf/`).
        # `never` + INFO because projects created before the move keep them at
        # the project root — a missing `.rddf/` copy is not drift (see
        # `_lib/core/rddf_paths.py` for the read/write resolution rule).
        "improvement-approved.md", "file", ("rdd",), ("rdd", "agent"), "never", False, "committed", "INFO",
    ),
    LayoutEntry(
        "improvement-suggestions.md", "file", ("rdd",), ("rdd", "agent"), "never", False, "committed", "INFO",
    ),
    LayoutEntry(
        "plans", "dir", ("rdd",), ("rdd", "agent"), "always", False, "committed", "WARNING",
    ),
    LayoutEntry(
        "roadmap", "dir", ("rdd",), ("agent",), "always", False, "committed", "WARNING",
    ),
    LayoutEntry(
        "roadmap.md", "file", ("rdd",), ("agent",), "always", False, "committed", "WARNING",
    ),
    LayoutEntry(
        "project.yaml", "file", ("rdd",), ("user",), "always", False, "committed", "WARNING",
    ),
    LayoutEntry(
        "reviews", "dir", ("agent",), ("agent",), "never", False, "committed", "INFO",
    ),
    LayoutEntry(
        "config", "dir", ("external-tool",), ("external-tool",), "never", False, "committed", "INFO",
    ),
    LayoutEntry(
        "skill-profiles", "dir", ("rdd",), ("user",), "never", False, "committed", "INFO",
    ),
    LayoutEntry(
        # commit-gate 门禁声明（ADR-commit-verification-gate D3）：仓级**committed** 配置。
        # `never` + INFO：未声明的仓不设门禁（D3 明文决策）⇒ 缺失不是 drift。
        "commit-gate.json", "file", ("external-tool",), ("user",), "never", False, "committed", "INFO",
    ),
    LayoutEntry(
        # deferral 豁免清单（add-deferral-registration-guard）：doctor 的 deferral-registration
        # category 读它。`never` + INFO：没有豁免的仓不需要该文件。
        "deferral-exemptions.txt", "file", ("rdd",), ("agent",), "never", False, "committed", "INFO",
    ),
    LayoutEntry(
        ".roadmap-migrate-backup-*", "dir", ("rdd",), ("rdd",), "never", True, "runtime-only", "INFO",
    ),
)


def as_dicts() -> list[dict]:
    """Return the manifest as JSON-ready dicts, sorted by `path`."""
    out: list[dict] = []
    for e in sorted(RDFF_LAYOUT, key=lambda x: x.path):
        out.append({
            "path": e.path,
            "kind": e.kind,
            "read_by": list(e.read_by),
            "write_by": list(e.write_by),
            "required_when": e.required_when,
            "transient": e.transient,
            "class": e.layout_class,
            "severity": e.severity,
        })
    return out
