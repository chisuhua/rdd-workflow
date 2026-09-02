"""Tests for _lib/verifier/hook_runner (M4 verification hook)."""
from __future__ import annotations

import stat
from pathlib import Path

import pytest

from _lib.verifier.hook_runner import (
    HookPathError,
    cache_key,
    run_verification_hook,
)


def _write_hook(project_root: Path, body: str) -> Path:
    tools_dir = project_root / "tools"
    tools_dir.mkdir(exist_ok=True)
    hook = tools_dir / "verify_change.sh"
    hook.write_text(body)
    hook.chmod(hook.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return hook


def test_hook_runner_path_whitelist_blocks_escape(tmp_path):
    """Hook path resolving outside {project_root}/tools/ must raise."""
    outside = tmp_path.parent / "evil.sh"
    outside.write_text("#!/bin/bash\nexit 0\n")
    outside.chmod(0o755)

    with pytest.raises(HookPathError, match="must resolve under"):
        run_verification_hook("change-x", tmp_path, hook_path=outside)


def test_hook_runner_missing_script_returns_skipped(tmp_path):
    """No hook present → 'skipped' (backward compatible)."""
    assert run_verification_hook("change-x", tmp_path) == "skipped"


def test_hook_runner_exit_0_passes(tmp_path):
    _write_hook(tmp_path, "#!/bin/bash\nexit 0\n")
    assert run_verification_hook("change-x", tmp_path) == "passed"


def test_hook_runner_exit_1_fails(tmp_path):
    _write_hook(tmp_path, "#!/bin/bash\nexit 1\n")
    assert run_verification_hook("change-x", tmp_path) == "failed"


def test_hook_runner_exit_2_returns_error(tmp_path):
    _write_hook(tmp_path, "#!/bin/bash\nexit 2\n")
    assert run_verification_hook("change-x", tmp_path) == "error"


def test_hook_runner_receives_change_name_arg(tmp_path):
    _write_hook(
        tmp_path,
        "#!/bin/bash\n[ \"$1\" = \"good-change\" ] && exit 0 || exit 1\n",
    )
    assert run_verification_hook("good-change", tmp_path) == "passed"
    assert run_verification_hook("bad-change", tmp_path) == "failed"


def test_hook_runner_timeout_returns_error(tmp_path):
    _write_hook(tmp_path, "#!/bin/bash\nsleep 5\n")
    assert run_verification_hook("change-x", tmp_path, timeout=1) == "error"


def test_cache_key_differs_per_hook_path(tmp_path):
    hook_a = tmp_path / "tools" / "a.sh"
    hook_a.parent.mkdir(exist_ok=True)
    hook_b = tmp_path / "tools" / "b.sh"
    hook_a.touch()
    hook_b.touch()
    assert cache_key("c", tmp_path, hook_a) != cache_key("c", tmp_path, hook_b)


def test_cache_key_stable_across_calls(tmp_path):
    hook = tmp_path / "tools" / "verify_change.sh"
    hook.parent.mkdir(exist_ok=True)
    hook.touch()
    assert cache_key("c", tmp_path, hook) == cache_key("c", tmp_path, hook)
