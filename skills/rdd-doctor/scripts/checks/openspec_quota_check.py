"""rdd-doctor category: `openspec-quota`.

Reports whether the project has more open change directories
(`openspec/changes/` minus `archive/`) than its own cap
(`.rddf/project.yaml` → `openspec.proposed_limit`; absent or `0` = unlimited).

Severity contract:
  - **no finding** when unconfigured or within the cap (AC-7) — a project that
    never opted in must not see this category at all;
  - **CRITICAL** when configured and exceeded (AC-6) — the project opted into
    the cap, so exceeding it is a real violation;
  - **WARNING** when the config value cannot be used (broken YAML / wrong type
    / negative / wrong nesting) — silently reading it as "unlimited" would make
    the gate permanently green;
  - **INFO** when the implementation module cannot be imported (a bare
    `skills/rdd-doctor/` copy without `_lib/`) — never raise: doctor_main turns
    checker exceptions into CRITICAL, which would be pure noise.

The verdict is computed by `_lib/openspec_quota.py` (the single
implementation shared with `rddf openspec quota`); this module only renders it.
That is why `import` is module-level and the call goes through the module
attribute — the shared-implementation test patches `openspec_quota.evaluate`.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Global install (`~/.agents/skills/rdd-doctor/...`): `_PROJECT_ROOT` is
# `~/.agents`, which holds no `_lib/` — the real package is at
# `~/.agents/skills/_lib`. Appended, never inserted, so a repo checkout's own
# `_lib/` (put in front above) keeps precedence.
_SKILLS_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_SKILLS_ROOT) not in sys.path:
    sys.path.append(str(_SKILLS_ROOT))

from doctor_render import Finding, Severity  # noqa: E402

_CATEGORY = "openspec-quota"
_CONFIG_FILE = ".rddf/project.yaml"

try:
    import _lib.openspec_quota as openspec_quota  # noqa: E402

    _IMPORT_ERROR: Exception | None = None
except Exception as exc:  # noqa: BLE001 - any import failure degrades to INFO
    openspec_quota = None
    _IMPORT_ERROR = exc


def run(project_root: Path | None = None) -> List[Finding]:
    """Return findings for the `openspec-quota` category. Never raises."""
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
    root = str(project_root)

    if openspec_quota is None:  # pragma: no cover - exercised by the reload test
        return [
            Finding(
                severity=Severity.INFO,
                category=_CATEGORY,
                file=_CONFIG_FILE,
                line=None,
                snippet=f"quota check unavailable: {_IMPORT_ERROR}",
                fix_hint=(
                    "install rdd-workflow so that _lib/openspec_quota.py is "
                    "importable; the quota is not enforced without it"
                ),
            )
        ]

    try:
        result = openspec_quota.evaluate(root)
    except openspec_quota.QuotaConfigError as exc:
        return [
            Finding(
                severity=Severity.WARNING,
                category=_CATEGORY,
                file=_CONFIG_FILE,
                line=openspec_quota.find_limit_line(root),
                snippet=str(exc),
                fix_hint=(
                    "fix .rddf/project.yaml: openspec.proposed_limit must be "
                    "an integer >= 0 (0 = unlimited)"
                ),
            )
        ]

    if result.ok:
        return []

    return [
        Finding(
            severity=Severity.CRITICAL,
            category=_CATEGORY,
            file=_CONFIG_FILE,
            line=openspec_quota.find_limit_line(root),
            snippet=(
                f"{result.active} open change(s) > proposed_limit {result.limit}"
            ),
            fix_hint=(
                "archive a change, or raise openspec.proposed_limit in "
                ".rddf/project.yaml"
            ),
        )
    ]
