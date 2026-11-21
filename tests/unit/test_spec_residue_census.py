"""机器普查台账生成器 `gen_spec_residue_census.py`。

判据来源：change `fix-spec-residue-guard` 的 AC-8 / AC-15 / AC-17。
台账是**唯一 tracked 交付物**（本仓 `openspec/` 被 gitignore ⇒ spec 改动无 git diff）。
"""
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPTS_DIR = REPO_ROOT / "skills" / "rdd-doctor" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import gen_spec_residue_census as gen  # noqa: E402

COLUMNS = ("file", "line", "requirement_title", "matched_token",
           "category", "disposition", "owner", "signoff", "date")


def _spec(project_root: Path, name: str, body: str) -> None:
    d = project_root / "openspec" / "specs" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "spec.md").write_text(body, encoding="utf-8")


def _rows(text: str):
    """表内数据行 → 单元格列表（跳过分隔行与表头）。"""
    out = []
    for line in text.splitlines():
        if not line.startswith("| openspec/"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        out.append(cells)
    return out


def test_row_schema_has_all_columns(tmp_path):
    _spec(tmp_path, "demo", "### Requirement: r\nSHALL call `guide-ship`.\n")
    text = gen.build_census(tmp_path)
    header = [ln for ln in text.splitlines() if ln.startswith("| file |")][0]
    for col in COLUMNS:
        assert f" {col} " in header + " ", header
    rows = _rows(text)
    assert len(rows) == 1, rows
    assert len(rows[0]) == len(COLUMNS)


def test_only_unexempted_hits_appear(tmp_path):
    """AC-8：带 allow 标注的命中不进台账（那是人的判断，不是待办）。"""
    _spec(tmp_path, "demo",
          "### Requirement: a\nSHALL accept `guide-ship`.\n"
          "<!-- v4-residue:allow=enum -->\n\n"
          "### Requirement: b\nSHALL call `guide-plan`.\n")
    rows = _rows(gen.build_census(tmp_path))
    assert len(rows) == 1, rows
    assert rows[0][3] == "guide-plan"


def test_disposition_defaults_to_unset(tmp_path):
    """不合并既有签批 ⇒ 机器行恒为 unset（合并不可靠，见 proposal 偏离 2）。"""
    _spec(tmp_path, "demo", "### Requirement: r\nSHALL call `guide-ship`.\n")
    rows = _rows(gen.build_census(tmp_path))
    assert rows[0][5] == "unset"


def test_idempotent_byte_identical(tmp_path):
    """AC-8：同一输入跑两次 ⇒ 逐字节相同（台账 diff 才有意义）。"""
    for name in ("a", "b", "c"):
        _spec(tmp_path, name, f"### Requirement: {name}\nSHALL call `guide-ship`.\n")
    first = gen.build_census(tmp_path)
    second = gen.build_census(tmp_path)
    assert first == second


def test_rows_sorted_deterministically(tmp_path):
    for name in ("zeta", "alpha", "mid"):
        _spec(tmp_path, name, "### Requirement: r\nSHALL use `guide-arch` and `guide-plan`.\n")
    rows = _rows(gen.build_census(tmp_path))
    keys = [(r[0], int(r[1]), r[3]) for r in rows]
    assert keys == sorted(keys), keys


def test_header_points_at_prior_ledgers(tmp_path):
    """AC-17：头部写明第一批 / 第二批台账指针。

    两种形态都covered：仍有未处置行 ⇒ 带「不得统一 allow=history」的警告；
    已全部处置 ⇒ 指向 align-18 的逐行判定台账。
    """
    _spec(tmp_path, "demo", "### Requirement: r\nSHALL call `guide-ship`.\n")
    text = gen.build_census(tmp_path)
    for ledger in gen.PRIOR_LEDGERS:
        assert ledger in text, ledger
    if "disposition=unset` 出现" in text:
        assert "不得" in text and "allow=history" in text
    else:
        assert "全部处置完毕" in text and "spec-residue-align-18" in text


def test_prior_ledgers_and_batch_ledgers_untouched(tmp_path):
    """AC-8：生成器不读不写既有台账（同一目录里的旧台账字节不变）。"""
    reviews = tmp_path / ".rddf" / "reviews"
    reviews.mkdir(parents=True)
    prior = reviews / "spec-residue-census-2026-11-20.md"
    prior.write_text("# batch1\n| openspec/specs/a/spec.md | 1 | t | guide | x | RETIRED |\n",
                     encoding="utf-8")
    before = prior.read_bytes()

    _spec(tmp_path, "demo", "### Requirement: r\nSHALL call `guide-ship`.\n")
    out = reviews / "spec-residue-census-2026-11-20-full.md"
    out.write_text(gen.build_census(tmp_path), encoding="utf-8")

    assert prior.read_bytes() == before
    assert out.is_file()


def test_hub_managed_rows_marked_excluded(tmp_path):
    """AC-15：hub-managed capability 只报不修 ⇒ 标 excluded(hub-managed)。"""
    cfg = tmp_path / ".rddf" / "config"
    cfg.mkdir(parents=True)
    (cfg / "hub.yaml").write_text("contracts:\n  - demo\n", encoding="utf-8")
    _spec(tmp_path, "demo", "### Requirement: r\nSHALL call `guide-ship`.\n")
    rows = _rows(gen.build_census(tmp_path))
    assert rows[0][5] == "excluded(hub-managed)", rows


def test_no_hub_config_means_no_exclusion(tmp_path):
    _spec(tmp_path, "demo", "### Requirement: r\nSHALL call `guide-ship`.\n")
    assert _rows(gen.build_census(tmp_path))[0][5] == "unset"


def test_checked_zero_is_called_out(tmp_path):
    """AC-12 的同族判据：无 spec 时台账必须自报 checked 0，不得读成 clean。"""
    text = gen.build_census(tmp_path)
    assert "checked 0" in text
    assert "不等于 clean" in text


def _fence_section(text: str) -> str:
    return text.split("## 围栏式豁免清单", 1)[1].split("\n## ", 1)[0]


def test_fence_allow_listed_in_audit_section(tmp_path):
    """围栏式豁免必须进「围栏式豁免清单」—— 它与被豁免文本物理分离，不留记录就不可审计。"""
    _spec(tmp_path, "demo",
          "### Requirement: r\n\n```json\n"
          '{"route": "guide-ship|guide-plan"}\n'
          "```\n"
          "<!-- v4-residue:allow=enum -->\n")
    text = gen.build_census(tmp_path)
    assert _rows(text) == []                       # 已豁免 ⇒ 不是待办
    section = _fence_section(text)
    assert "`openspec/specs/demo/spec.md`" in section, section
    assert "`enum`" in section, section
    assert "guide-plan, guide-ship" in section, section


def test_fence_allow_section_says_none_when_empty(tmp_path):
    """没有围栏式豁免时该段也必须存在并明说「无」—— 空段与「没实现」无法区分。"""
    _spec(tmp_path, "demo", "### Requirement: r\nSHALL call `guide-ship`.\n")
    text = gen.build_census(tmp_path)
    assert "## 围栏式豁免清单" in text
    assert "全仓没有任何围栏式豁免" in _fence_section(text)


def test_cli_writes_file(tmp_path, capsys):
    _spec(tmp_path, "demo", "### Requirement: r\nSHALL call `guide-ship`.\n")
    out = tmp_path / "out.md"
    rc = gen.main(["--out", str(out), "--project-root", str(tmp_path)])
    assert rc == 0
    assert out.is_file()
    assert str(out) in capsys.readouterr().out


def test_baseline_numbers_present(tmp_path):
    """AC-2：头部记录 4 个口径组合的基线数字。"""
    _spec(tmp_path, "demo", "### Requirement: r\nSHALL call `guide-ship`.\n")
    text = gen.build_census(tmp_path)
    for combo in ("`True` × `True`", "`True` × `False`",
                  "`False` × `True`", "`False` × `False`"):
        assert combo in text, combo
    assert "扫描 spec 文件" in text
