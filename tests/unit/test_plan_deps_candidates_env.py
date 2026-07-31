# tests/unit/test_plan_deps_candidates_env.py
import importlib
import importlib.util
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from skills.guide_plan.scripts import plan_deps_candidates_env  # noqa: E402


def test_spec_none_raises_import_error(monkeypatch, tmp_path):
    """When spec_from_file_location returns None, raise ImportError with target path."""
    calls = {}

    def fake_spec_from_file_location(name, path):
        calls["path"] = path
        return None  # simulate load failure

    monkeypatch.setattr(
        importlib.util, "spec_from_file_location", fake_spec_from_file_location
    )
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))

    with pytest.raises(ImportError) as excinfo:
        plan_deps_candidates_env.main()

    assert "plan_deps_candidates" in str(excinfo.value)
    assert "skills" in str(excinfo.value)  # includes target path


def test_spec_ok_executes_generate(monkeypatch, tmp_path):
    """When spec loads successfully, generate_deps_candidates is invoked."""
    called = {}

    class FakeLoader(importlib.abc.Loader):
        def create_module(self, spec):
            return None  # default module creation

        def exec_module(self, mod):
            mod.generate_deps_candidates = lambda root: called.update(root=root)

    def fake_spec_from_file_location(name, path):
        loader = FakeLoader()
        spec = importlib.util.spec_from_loader(name, loader)
        spec.origin = path
        return spec

    monkeypatch.setattr(
        importlib.util, "spec_from_file_location", fake_spec_from_file_location
    )
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))

    plan_deps_candidates_env.main()

    assert called.get("root") == str(tmp_path)
