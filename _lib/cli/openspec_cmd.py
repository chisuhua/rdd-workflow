"""``rddf openspec`` — OpenSpec-side policies. Currently one sub-action: quota.

`quota` reports (and gates) the number of open change directories against the
project's own cap in `.rddf/project.yaml` (`openspec.proposed_limit`; absent or
`0` means unlimited).

The verdict itself lives in :mod:`_lib.openspec_quota` — this module is only
argument parsing + rendering, so the CLI and the `openspec-quota` doctor
category can never disagree.

Exit codes: ``0`` within limit (or unlimited) · ``1`` exceeded ·
``2`` usage or configuration error.
"""
from __future__ import annotations

import json
import os
import sys

import _lib.openspec_quota as openspec_quota

_USAGE = """usage: rddf openspec quota [--json] [--limit N]

Report the number of open change directories (openspec/changes/ minus
archive/) against the project's cap.

The cap comes from .rddf/project.yaml:

    openspec:
      proposed_limit: 3      # 0 or absent = unlimited

Options:
  --json        machine-readable output: {"active", "limit", "ok"}
                (limit is null when unlimited; on a config error the object
                is {"error", "active": null, "limit": null, "ok": false})
  --limit N     override the configured cap for this run
                (0 = unlimited; negative / non-integer ⇒ exit 2)
  -h, --help    this message

Exit codes: 0 = within limit (or unlimited) · 1 = exceeded ·
            2 = usage or configuration error
"""


def _project_root() -> str:
    """Env override → canonical resolver (never the raw cwd anti-pattern).

    Imported lazily from `__main__` (where it is defined): the
    `skills._lib.cli` re-export is a PEP 562 `__getattr__` and therefore
    invisible to mypy.
    """
    from _lib.cli.__main__ import resolve_project_root

    return os.environ.get("RDDF_PROJECT_ROOT") or resolve_project_root()


def _emit_error(message: str, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(
            {"error": message, "active": None, "limit": None, "ok": False},
            ensure_ascii=False,
        ))
    else:
        print(f"❌ openspec quota: {message}", file=sys.stderr)


def _parse_quota_args(args: list[str]) -> tuple[bool, int | None, int | None]:
    """Return (as_json, limit_override, exit_code).

    `exit_code` is None unless the arguments themselves are unusable.
    """
    as_json = False
    limit: int | None = None
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--json":
            as_json = True
            index += 1
        elif arg == "--limit":
            if index + 1 >= len(args):
                _emit_error("--limit 需要一个值（0 表示不限）", as_json=as_json)
                return as_json, None, 2
            raw = args[index + 1]
            try:
                limit = int(raw)
            except ValueError:
                _emit_error(f"--limit 需要整数，得到 {raw!r}", as_json=as_json)
                return as_json, None, 2
            index += 2
        else:
            _emit_error(f"未知参数 {arg!r}（可用: --json, --limit N, --help）", as_json=as_json)
            return as_json, None, 2
    return as_json, limit, None


def _cmd_quota(args: list[str]) -> int:
    if args and args[0] in ("-h", "--help"):
        print(_USAGE, end="")
        return 0

    as_json, limit, early_exit = _parse_quota_args(args)
    if early_exit is not None:
        return early_exit

    try:
        result = openspec_quota.evaluate(_project_root(), override=limit)
    except openspec_quota.QuotaConfigError as exc:
        _emit_error(str(exc), as_json=as_json)
        return 2

    if as_json:
        print(json.dumps(
            {"active": result.active, "limit": result.limit, "ok": result.ok},
            ensure_ascii=False,
        ))
    else:
        limit_text = "unlimited" if result.limit is None else f"limit {result.limit}"
        verdict = "✅ OK" if result.ok else "❌ EXCEEDED"
        print(f"OpenSpec change quota: {result.active} active / {limit_text} → {verdict}")
        if not result.ok and result.limit is not None:
            print(f"   archive {result.active - result.limit} change(s), "
                  "or raise openspec.proposed_limit")
    return 0 if result.ok else 1


def cmd_openspec(args: list[str]) -> int:
    """Handle ``rddf openspec <sub-action>``. Returns a process exit code."""
    if not args or args[0] in ("-h", "--help"):
        print(_USAGE, end="")
        return 0

    action = args[0]
    if action != "quota":
        print(f"❌ openspec: 未知子动作 {action!r}（可用: quota）", file=sys.stderr)
        return 2
    return _cmd_quota(args[1:])
