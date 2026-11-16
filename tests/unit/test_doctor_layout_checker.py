"""Unit tests for the doctor `layout` checker.

The checker must never let a missing manifest surface as a CRITICAL finding:
doctor_main.py's aggregator turns any checker exception into a CRITICAL, and
this category's contract is "never CRITICAL" (so `rddf doctor` cannot exit 2
because of layout drift in a third-party project).
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "rdd-doctor" / "scripts"))

from checks.layout_check import run  # noqa: E402
from doctor_render import Severity  # noqa: E402


def test_missing_manifest_degrades_to_warning(tmp_path, monkeypatch):
    """When the manifest cannot be imported, report WARNING — never CRITICAL."""
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "_lib.core.rddf_layout":
            raise ImportError("no _lib in this deployment")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.delitem(sys.modules, "_lib.core.rddf_layout", raising=False)

    findings = run(project_root=tmp_path)
    assert findings, "manifest 不可用时必须给出 finding，而不是静默"
    for f in findings:
        assert f.severity is not Severity.CRITICAL
        assert f.category == "layout.unavailable"


def test_missing_rddf_dir_yields_no_findings(tmp_path):
    """A project without .rddf/ has nothing to diagnose."""
    assert run(project_root=tmp_path) == []
