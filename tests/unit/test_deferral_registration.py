"""Deferral statements must carry a registration target.

Background (add-deferral-registration-guard):「另案立项」is a legitimate way to
close work, but without a registration target the deferred defect has **no debt
entry** — it can be deferred forever and nobody sees it coming back (two
defects recurred twice after being closed with a bare「另案」).

The convention (single source: `_lib/deferral_registration.py`):

    另案（已登记：<improvement-slug>）   ← the debt is an improvement
    另案（backlog：<topic>）             ← the debt is a backlog placeholder
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from _lib.deferral_registration import (  # noqa: E402
    BACKLOG_FORM,
    DEFERRAL_PHRASES,
    REGISTERED_FORM,
    load_exemptions,
    scan_project,
    scan_text,
    stale_exemptions,
)


def _project(tmp_path, files: dict[str, str], exemptions: list[str] | None = None):
    for rel, body in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    if exemptions is not None:
        exc = tmp_path / ".rddf" / "deferral-exemptions.txt"
        exc.parent.mkdir(parents=True, exist_ok=True)
        exc.write_text("".join(f"{e}\n" for e in exemptions), encoding="utf-8")
    return tmp_path


# --- AC1: the three fixtures -------------------------------------------------


def test_compliant_deferral_is_not_reported(tmp_path):
    root = _project(tmp_path, {
        ".rddf/improvements/fix-a.md": "见 [fix-b](fix-b.md) 的另案（已登记：fix-b）记录。\n",
    })
    findings = scan_project(str(root))
    assert findings == [], findings


def test_bare_deferral_is_reported_with_file_and_line(tmp_path):
    root = _project(tmp_path, {
        ".rddf/improvements/fix-a.md": "第一行\n这个缺陷另案处理。\n",
    })
    findings = scan_project(str(root))
    assert len(findings) == 1, findings
    assert findings[0].path == ".rddf/improvements/fix-a.md"
    assert findings[0].line == 2
    assert findings[0].phrase == "另案"


def test_backlog_placeholder_is_accepted(tmp_path):
    root = _project(tmp_path, {
        ".rddf/improvements/fix-a.md": "另案（backlog：缓存层失效）处理。\n",
    })
    assert scan_project(str(root)) == []


def test_every_managed_phrase_is_detected(tmp_path):
    for phrase in DEFERRAL_PHRASES:
        findings = scan_text(f"这里{phrase}处理。\n", "x.md")
        assert len(findings) == 1, (phrase, findings)


# --- AC2: the exemption list silences registered noise -----------------------


def test_exempted_file_produces_no_finding(tmp_path):
    root = _project(tmp_path, {
        ".rddf/improvements/old.md": "这个缺陷另案处理。\n",
    }, exemptions=[".rddf/improvements/old.md"])
    assert scan_project(str(root)) == []
    assert load_exemptions(str(root)) == [".rddf/improvements/old.md"]


def test_unexempted_file_is_still_reported(tmp_path):
    root = _project(tmp_path, {
        ".rddf/improvements/old.md": "这个缺陷另案处理。\n",
        ".rddf/improvements/new.md": "另一个缺陷另案处理。\n",
    }, exemptions=[".rddf/improvements/old.md"])
    findings = scan_project(str(root))
    assert len(findings) == 1
    assert findings[0].path == ".rddf/improvements/new.md"


# --- AC3: the convention text is greppable and complete ----------------------


def test_convention_doc_contains_every_anchor():
    doc = (Path(PROJECT_ROOT) / "docs/architecture/deferral-registration.md").read_text(
        encoding="utf-8")
    for phrase in DEFERRAL_PHRASES:
        assert phrase in doc, phrase
    assert REGISTERED_FORM in doc, REGISTERED_FORM
    assert BACKLOG_FORM in doc, BACKLOG_FORM


def test_convention_doc_points_at_the_single_source():
    doc = (Path(PROJECT_ROOT) / "docs/architecture/deferral-registration.md").read_text(
        encoding="utf-8")
    assert "_lib/deferral_registration.py" in doc


def test_phrase_list_has_one_definition_point():
    lib_root = Path(PROJECT_ROOT) / "_lib"
    offenders = [
        str(path.relative_to(PROJECT_ROOT))
        for path in lib_root.rglob("*.py")
        if path.name != "deferral_registration.py"
        and re.search(r"DEFERRAL_PHRASES\s*=", path.read_text(encoding="utf-8"))
    ]
    assert offenders == [], offenders


# --- AC4: the detection surfaces do not overlap -------------------------------


def test_review_debt_surface_is_not_touched(tmp_path):
    """Code comments are `review-debt`'s business — this scan is documents only."""
    root = _project(tmp_path, {
        "_lib/some.py": "# TODO(x): 这个缺陷另案处理\n",
        ".rddf/improvements/fix-a.md": "这个缺陷另案处理。\n",
    })
    findings = scan_project(str(root))
    assert [f.path for f in findings] == [".rddf/improvements/fix-a.md"]


def test_defer_state_field_is_not_a_deferral_wording():
    """The proposal deferral STATUS field (`已推迟` / `deferred`) is a different thing."""
    assert "已推迟" not in DEFERRAL_PHRASES
    assert "deferred" not in DEFERRAL_PHRASES
    assert scan_text("状态: 已推迟（2026-11-20）\n", "x.md") == []


# --- AC6: stale exemptions are surfaced --------------------------------------


def test_stale_exemption_is_detected(tmp_path):
    root = _project(tmp_path, {
        ".rddf/improvements/old.md": "这条记录里没有任何 deferral 措辞。\n",
    }, exemptions=[".rddf/improvements/old.md"])
    assert stale_exemptions(str(root)) == [".rddf/improvements/old.md"]


def test_missing_exempted_file_is_stale(tmp_path):
    root = _project(tmp_path, {}, exemptions=[".rddf/improvements/gone.md"])
    assert stale_exemptions(str(root)) == [".rddf/improvements/gone.md"]


def test_live_exemption_is_not_stale(tmp_path):
    root = _project(tmp_path, {
        ".rddf/improvements/old.md": "这个缺陷另案处理。\n",
    }, exemptions=[".rddf/improvements/old.md"])
    assert stale_exemptions(str(root)) == []


# --- AC1 at the doctor-category level -----------------------------------------


def _run_category(project_root: str):
    import sys as _sys

    checks_dir = Path(PROJECT_ROOT) / "skills/rdd-doctor/scripts"
    for extra in (str(checks_dir), str(Path(PROJECT_ROOT) / "skills/rdd-doctor/scripts")):
        if extra not in _sys.path:
            _sys.path.insert(0, extra)
    from checks.deferral_registration_check import run

    return run(project_root)


def test_doctor_category_reports_unregistered_deferral(tmp_path):
    root = _project(tmp_path, {
        ".rddf/improvements/fix-a.md": "第一行\n这个缺陷另案处理。\n",
    })
    findings = _run_category(str(root))
    assert len(findings) == 1, findings
    assert findings[0].category == "deferral-registration"
    assert findings[0].file == ".rddf/improvements/fix-a.md"
    assert findings[0].line == 2
    assert "登记目标" in findings[0].fix_hint


def test_doctor_category_is_silent_for_exempted_noise(tmp_path):
    root = _project(tmp_path, {
        ".rddf/improvements/old.md": "这个缺陷另案处理。\n",
    }, exemptions=[".rddf/improvements/old.md"])
    assert _run_category(str(root)) == []


def test_doctor_category_reports_stale_exemptions(tmp_path):
    root = _project(tmp_path, {
        ".rddf/improvements/old.md": "这里没有任何 deferral 措辞。\n",
    }, exemptions=[".rddf/improvements/old.md"])
    findings = _run_category(str(root))
    assert len(findings) == 1, findings
    assert "可清理" in findings[0].fix_hint
