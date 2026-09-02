"""External verification hook runner (M4 verification hook).

Per rfc-rddf-project-yaml-config-i10: when project.yaml sets
``verification.provider: hook``, ``rddf rdd-verify`` delegates to
``tools/verify_change.sh {change}`` instead of LLM semantic check.

Exit code mapping:
    0 → passed
    1 → failed
    2+ → error

Security: hook path must resolve under ``{project_root}/tools/`` to
prevent path-traversal injection via project.yaml.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional


HOOK_RELATIVE_PATH = Path("tools") / "verify_change.sh"
DEFAULT_TIMEOUT_SECONDS = 300


class HookPathError(ValueError):
    """Raised when the configured hook path violates the safety whitelist."""


def run_verification_hook(
    change_name: str,
    project_root: Path,
    *,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    hook_path: Optional[Path] = None,
) -> str:
    """Run the configured verification hook and return a verdict string.

    Args:
        change_name: Change identifier passed as the hook's positional argument.
        project_root: Absolute project root; the hook must live under
            ``{project_root}/tools/``.
        timeout: Maximum seconds to wait for the hook (default 300).
        hook_path: Optional explicit hook path override. Defaults to
            ``{project_root}/tools/verify_change.sh``.

    Returns:
        One of ``"passed"``, ``"failed"``, ``"error"``, ``"skipped"``.
        ``"skipped"`` is returned when no hook script is configured.
    """
    project_root = Path(project_root).resolve()
    hook = (hook_path or (project_root / HOOK_RELATIVE_PATH)).resolve()

    if not str(hook).startswith(str(project_root) + "/tools/"):
        raise HookPathError(
            f"hook path must resolve under {project_root}/tools/, got {hook}"
        )

    if not hook.exists():
        return "skipped"

    try:
        result = subprocess.run(
            [str(hook), change_name],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return "error"

    if result.returncode == 0:
        return "passed"
    if result.returncode == 1:
        return "failed"
    return "error"


def cache_key(change_name: str, project_root: Path, hook_path: Path) -> str:
    """Compute a SHA-based cache key for hook verdicts.

    Mirrors ``_lib/verifier/cache.py::cache_key`` semantics but adds the
    hook command path so different hooks don't share cache entries.
    """
    import hashlib

    payload = json.dumps(
        {
            "change": change_name,
            "root": str(Path(project_root).resolve()),
            "hook": str(Path(hook_path).resolve()),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
