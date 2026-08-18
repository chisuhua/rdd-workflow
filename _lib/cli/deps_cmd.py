"""``rddf deps`` subcommand handler.

Reads ``deps-analysis.json`` and renders a dependency table with
execution order and file conflict information.

The JSON is produced by ``skills/deps/scripts/deps_output.py``
(``build_analysis`` + ``write_analysis``). We prefer loading it via
that module's ``load_analysis`` helper, but fall back to raw JSON
parsing if the module is unavailable (e.g. during testing).

Usage::

    python3 -m skills._lib.cli deps
    python3 -m skills._lib.cli deps cross-repo --spokes org/foo,org/bar

The project root is injected by ``cli.__main__`` via the
``RDDF_PROJECT_ROOT`` env var; falls back to ``os.getcwd()`` when unset.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def _load_data(project_root: str) -> Optional[dict]:
    """Load deps-analysis.json, preferring the shared helper when available.

    Tries ``skills.deps.scripts.deps_output.load_analysis`` first
    (which validates schema version + structure). Falls back to raw
    JSON parsing when the module is not importable.
    """
    try:
        from skills.deps.scripts import deps_output as do
        return do.load_analysis(project_root)
    except ImportError:
        pass

    # Fallback: direct JSON parsing.
    path = os.path.join(project_root, ".rddf", "state", "deps-analysis.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _safe(val: Any, default: str = "-") -> str:
    """Return ``val`` or ``default`` if ``val`` is ``None``."""
    if val is None:
        return default
    s = str(val)
    return s if s else default


def cmd_deps_cross_repo(args: list[str]) -> int:
    """Handle ``rddf deps cross-repo``.

    Thin subprocess wrapper that delegates to the existing
    ``skills/deps/scripts/cross_repo_cli.py`` argparse entry point
    (cross-repo dependency graph analysis, ADR-0030). Args are forwarded
    verbatim; exit codes propagate transparently.

    Args:
        args: CLI args forwarded verbatim to ``cross_repo_cli.py``
            (e.g. ``["--spokes", "org/foo,org/bar"]`` or ``["--help"]``).

    Returns:
        Exit code from the ``cross_repo_cli.py`` subprocess.
    """
    project_root = Path(
        os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    )
    script = project_root / "skills" / "deps" / "scripts" / "cross_repo_cli.py"

    result = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(project_root),
    )
    return result.returncode


def cmd_deps(args: list[str]) -> int:
    """Handle ``rddf deps``.

    Renders a dependency analysis table from ``deps-analysis.json``:

        🔗 依赖分析结果
        ────────────────────────────────────────────
        模式: AI subagent
        变更数: N

        NAME       STATUS  GROUP  BLOCKER  CONFIDENCE
        ────────── ─────── ────── ──────── ──────────
        ...

        ⚠ 文件冲突:
          change-A ↔ change-B: path/to/file

        推荐执行顺序:
          1. change-A
          2. change-B

    Args:
        args: Remaining CLI args. When the first arg is ``cross-repo``,
            control is handed to :func:`cmd_deps_cross_repo`; otherwise
            the plain ``deps`` table is rendered (no options).

    Returns:
        0 on success, 1 on JSON parse error.
    """
    if args and args[0] == "cross-repo":
        return cmd_deps_cross_repo(args[1:])

    project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()

    analysis = _load_data(project_root)
    if analysis is None:
        print("deps-analysis.json 不存在 — 请先运行 deps")
        return 0

    changes: Dict[str, dict] = analysis.get("changes", {}) or {}
    execution_order: list[str] = analysis.get("execution_order", []) or []
    fallback: bool = analysis.get("fallback", True)
    updated_at: str = analysis.get("updated_at", "")

    mode_label = "静态分析 (无 AI)" if fallback else "AI subagent"

    # ── Header ──────────────────────────────────────────────────────
    print("🔗 依赖分析结果")
    print("────────────────────────────────────────────")
    if updated_at:
        print(f"更新: {updated_at}")
    print(f"模式: {mode_label}")
    print(f"变更数: {len(changes)}")
    print()

    if not changes:
        print("(无变更数据)")
        return 0

    # ── Table ───────────────────────────────────────────────────────
    header = f"{'NAME':<30} {'STATUS':<14} {'GROUP':<6} {'BLOCKER':<22} {'CONFIDENCE':<10}"
    sep = f"{'-' * 30} {'-' * 14} {'-' * 6} {'-' * 22} {'-' * 10}"
    print(header)
    print(sep)

    # Sort by execution_order (preserving order), then by name.
    order_index = {name: i for i, name in enumerate(execution_order)}
    sorted_names = sorted(
        changes.keys(),
        key=lambda n: (order_index.get(n, 999), n),
    )

    for name in sorted_names:
        c = changes[name]
        status = _safe(c.get("status"), "ready")
        group = _safe(c.get("parallel_group"), "")
        blocker = _safe(c.get("blocker"), "-")
        confidence = _safe(c.get("confidence"), "high")

        name_disp = name[:30]
        status_disp = status[:14]
        group_disp = str(group)[:6]
        blocker_disp = blocker[:22]
        conf_disp = confidence[:10]

        print(
            f"{name_disp:<30} {status_disp:<14} {group_disp:<6} "
            f"{blocker_disp:<22} {conf_disp:<10}"
        )

    # ── File conflicts ──────────────────────────────────────────────
    all_conflicts: list[tuple[str, str, str]] = []
    for name, c in changes.items():
        conflicts = c.get("conflicts") or []
        for other in conflicts:
            path_hint = ""
            # Try to find a conflict path if available.
            if isinstance(other, dict):
                path_hint = other.get("path", "")
                other_name = other.get("name", str(other))
            else:
                other_name = str(other)
            # Avoid duplicate pairs (A→B and B→A).
            pair = tuple(sorted([name, other_name]))
            all_conflicts.append((name, other_name, path_hint))

    if all_conflicts:
        print()
        print("⚠ 文件冲突:")
        seen_pairs: set[tuple[str, str]] = set()
        for entry in all_conflicts:
            a = entry[0]
            b = entry[1]
            path_hint = entry[2] if len(entry) > 2 else ""
            if a <= b:
                pair = (a, b)
            else:
                pair = (b, a)
            if pair in seen_pairs:  # type: ignore[arg-type]
                continue
            seen_pairs.add(pair)
            if path_hint:
                print(f"   {a} ↔ {b}: {path_hint}")
            else:
                print(f"   {a} ↔ {b}")

    # ── Execution order ─────────────────────────────────────────────
    if execution_order:
        print()
        print("推荐执行顺序:")
        for i, name in enumerate(execution_order, 1):
            print(f"  {i}. {name}")
    else:
        print()
        print("推荐执行顺序: (无数据)")

    return 0


__all__ = ["cmd_deps", "cmd_deps_cross_repo"]