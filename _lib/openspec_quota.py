"""OpenSpec change quota (KPI slot) — the single implementation.

Policy: a project may cap how many change directories are open at once
(`openspec/changes/` minus `archive/`). The cap lives in
`.rddf/project.yaml` under `openspec.proposed_limit` (ADR-0036 is the config
seam); **absent or `0` means unlimited**, so upgrading never changes an
existing project's behaviour.

Three facts this module exists to keep true (see
`openspec/changes/add-openspec-kpi-quota/design.md`):

1. **One counting authority.** `count_active` delegates to
   `skills._lib.state_reader.list_change_dirs` — the same function `rddf
   status` and `_lib/discover_ship_changes.py` consume. Re-implementing the
   listing here would re-create the drift this change is meant to remove.
2. **One validation path.** `--limit` (CLI) and the config value both go
   through :func:`validate_limit`.
3. **Loud on misconfiguration.** A broken/typed/wrongly-nested value raises
   :class:`QuotaConfigError`; it is never silently read as `0`. A quota that
   silently disables itself is worse than no quota.

Callers must reach the functions through the module
(`openspec_quota.evaluate(...)`, `state_reader.list_change_dirs(...)`) rather
than binding names with `from … import` — the "single implementation" proof
(monkeypatching the module attribute) depends on that lookup happening at
call time.

Disk counting is deliberate: `openspec list --json` would make the verdict
depend on the installed CLI's internal status model (and on there being a CLI
at all), while the policy is about "how many change dirs are open".
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import yaml

CONFIG_FILE = ".rddf/project.yaml"
CONFIG_SECTION = "openspec"
LIMIT_KEY = "proposed_limit"

#: `0` / absent ⇒ unlimited.
UNLIMITED = 0


class QuotaConfigError(Exception):
    """`.rddf/project.yaml` carries a quota value that cannot be used.

    Raised instead of degrading to "unlimited": a silently ignored limit
    makes the gate permanently green, which is the failure mode this
    mechanism exists to prevent.
    """


@dataclass(frozen=True)
class QuotaResult:
    """Outcome of one quota evaluation.

    `limit is None` means unlimited (unconfigured or explicitly `0`).
    """

    active: int
    limit: int | None
    ok: bool


def validate_limit(value: Any, *, source: str) -> int:
    """Validate a limit value; return it as a non-negative int.

    Rejects `bool` explicitly: PyYAML (YAML 1.1) parses `yes` / `on` / `true`
    into `True`, and `isinstance(True, int)` is `True` — without this check
    `proposed_limit: yes` would silently become a limit of 1.
    """
    if isinstance(value, bool):
        raise QuotaConfigError(
            f"{source}: 期望整数，得到布尔值 {value!r}"
            "（YAML 的 yes/on/true 会被解析成布尔；请写 0 或正整数）"
        )
    if not isinstance(value, int):
        raise QuotaConfigError(
            f"{source}: 期望整数，得到 {type(value).__name__} {value!r}"
        )
    if value < 0:
        raise QuotaConfigError(
            f"{source}: 不得为负数（得到 {value}；0 表示不限）"
        )
    return value


def _load_config(project_root: str) -> dict[str, Any]:
    """Read `.rddf/project.yaml`; return {} when the file is absent/empty."""
    path = os.path.join(project_root, CONFIG_FILE)
    try:
        with open(path, encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
    except FileNotFoundError:
        return {}
    except yaml.YAMLError as exc:
        raise QuotaConfigError(f"{CONFIG_FILE}: YAML 解析失败（{exc}）") from exc
    except OSError as exc:
        raise QuotaConfigError(f"{CONFIG_FILE}: 无法读取（{exc}）") from exc

    if raw is None:  # empty file
        return {}
    if not isinstance(raw, dict):
        raise QuotaConfigError(
            f"{CONFIG_FILE}: 顶层必须是 mapping，得到 {type(raw).__name__}"
        )
    if LIMIT_KEY in raw:
        raise QuotaConfigError(
            f"{CONFIG_FILE}: `{LIMIT_KEY}` 必须写在 `{CONFIG_SECTION}:` 段下，"
            "不能放在顶层"
        )
    return dict(raw)


def read_limit(project_root: str) -> int:
    """Return the configured limit; `0` means unlimited.

    Raises :class:`QuotaConfigError` for any value that cannot be used as-is.
    """
    data = _load_config(project_root)
    section = data.get(CONFIG_SECTION)
    if section is None:
        return UNLIMITED
    if not isinstance(section, dict):
        raise QuotaConfigError(
            f"{CONFIG_FILE}: `{CONFIG_SECTION}:` 段必须是 mapping，"
            f"得到 {type(section).__name__}"
        )
    if LIMIT_KEY not in section:
        return UNLIMITED
    return validate_limit(
        section[LIMIT_KEY],
        source=f"{CONFIG_FILE}:{CONFIG_SECTION}.{LIMIT_KEY}",
    )


def find_limit_line(project_root: str) -> int | None:
    """1-based line of the `proposed_limit:` key, for finding locations.

    Display-layer helper only: doctor findings point at the config file, and
    the line number comes from here so the check module never parses YAML.
    """
    path = os.path.join(project_root, CONFIG_FILE)
    try:
        with open(path, encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if line.lstrip().startswith(f"{LIMIT_KEY}:"):
                    return line_no
    except OSError:
        return None
    return None


def count_active(project_root: str) -> int:
    """Number of open change dirs — delegated, never re-implemented."""
    # Runtime attribute lookup on purpose (not `from … import list_change_dirs`):
    # the single-authority property is what keeps this number equal to the one
    # `rddf status` prints, and it is what the AC-5 test pins down by patching
    # the module attribute. `getattr` is also what lets mypy type-check this
    # module: `skills/_lib/state_reader.py` is an identity-merge shim whose
    # exported names are invisible to static analysis.
    import skills._lib.state_reader as state_reader

    list_change_dirs = getattr(state_reader, "list_change_dirs")
    return len(list_change_dirs(project_root))


def evaluate(project_root: str, override: int | None = None) -> QuotaResult:
    """Evaluate the quota.

    Args:
        project_root: Project root (the dir holding `.rddf/` and `openspec/`).
        override: `--limit` value; validated by the same
            :func:`validate_limit` as the config value. `None` ⇒ read config.

    Returns:
        :class:`QuotaResult`; `limit is None` means unlimited.
    """
    if override is None:
        limit = read_limit(project_root)
    else:
        limit = validate_limit(override, source="--limit")
    active = count_active(project_root)
    if limit == UNLIMITED:
        return QuotaResult(active=active, limit=None, ok=True)
    return QuotaResult(active=active, limit=limit, ok=active <= limit)
