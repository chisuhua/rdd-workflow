"""Regression test for fix-rddf-init-broken-layout Bug A.

Ensures __main__.py uses os.environ.setdefault for RDDF_PROJECT_ROOT so
user-supplied values (e.g. from nested rdd-workflow projects like PTX-EMU)
are not silently overwritten.
"""
import importlib.util
import os
import sys
from pathlib import Path

import pytest


def _load_main_module():
    """Load _lib/cli/__main__.py and run its main() entrypoint with a safe subcommand."""
    project_root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "_rddf_main_for_test", project_root / "_lib" / "cli" / "__main__.py"
    )
    module = importlib.util.module_from_spec(spec)
    # Prevent the module from running its top-level main() block during import.
    sys.modules["_rddf_main_for_test"] = module
    spec.loader.exec_module(module)
    # Exercise the code path that sets RDDF_PROJECT_ROOT (line 154).
    module.main(["version"])
    return module


def test_setdefault_preserves_user_rddf_project_root(monkeypatch):
    """User-supplied RDDF_PROJECT_ROOT must not be overwritten by __main__.py."""
    project_root = Path(__file__).resolve().parents[2]
    # Pre-set a custom value to simulate user input (e.g. PTX-EMU)
    monkeypatch.setenv("RDDF_PROJECT_ROOT", "/custom/source/PTX-EMU")
    monkeypatch.syspath_prepend(str(project_root))
    # Clear any cached import so the module's top-level code runs fresh
    sys.modules.pop("_rddf_main_for_test", None)
    _load_main_module()
    # The user's value must survive execution of the CLI entrypoint
    assert os.environ["RDDF_PROJECT_ROOT"] == "/custom/source/PTX-EMU"
