"""skills/_lib/ 只能是 shim 层：不得残留完整副本。"""
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SHIM_DIR = REPO_ROOT / "skills" / "_lib"

MAX_SHIM_PY_LINES = 50

# 显式豁免清单：>50 行的 .py 必须登记在此，且每项都要有理由。
# 逐项理由见 design.md Decision 7。
_ALLOWED_LARGE_FILES = {
    "iteration/__init__.py": "运行时必需：path-widening __path__ + 完整 re-export；"
                              "全局安装下 skills._lib.iteration 只能靠它解析",
    "gh_repo_detect.py": "Known Residual：完整实现住在 shim 层（同类病），"
                         "迁移方案同 resolver；本次不搬，显式登记",
}
# 豁免清单的规模上界 —— 新增豁免必须发生一次显式的人工复审。
_MAX_ALLOWLIST_ENTRIES = 3


def test_no_json_in_shim_layer():
    """JSON 无法 identity-merge —— 副本目录必须整体删除。"""
    assert list(SHIM_DIR.rglob("*.json")) == [], \
        f"skills/_lib/ 下不得有 JSON 副本：{list(SHIM_DIR.rglob('*.json'))}"


def test_no_large_python_files_in_shim_layer():
    """超过阈值的 .py 必须命中显式豁免清单（豁免项需带理由）。"""
    offenders = []
    for p in SHIM_DIR.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        rel = str(p.relative_to(SHIM_DIR))
        if len(p.read_text(encoding="utf-8").splitlines()) <= MAX_SHIM_PY_LINES:
            continue
        if rel not in _ALLOWED_LARGE_FILES:
            offenders.append(f"{rel}（未登记豁免）")
    assert offenders == [], offenders


def test_allowlist_entries_exist_and_have_reason():
    """豁免清单不得悬空：每项都要存在且带非空理由。"""
    for rel, reason in _ALLOWED_LARGE_FILES.items():
        assert (SHIM_DIR / rel).is_file(), f"豁免项不存在：{rel}"
        assert reason.strip(), f"豁免项缺理由：{rel}"


def test_allowlist_does_not_grow_silently():
    """豁免清单有规模上界 —— 否则它会变成「什么都往里塞」的逃逸口。"""
    assert len(_ALLOWED_LARGE_FILES) <= _MAX_ALLOWLIST_ENTRIES, (
        f"豁免清单已超过上界 {_MAX_ALLOWLIST_ENTRIES}："
        f"{sorted(_ALLOWED_LARGE_FILES)}"
    )


def test_no_stale_schema_path_reference():
    """不得再引用已删除的 skills/_lib/schemas/。

    注意：`skills/rdd-doctor/scripts/checks/state_schema_check.py` 的 docstring 里
    原本有一句解释「用真 _lib/schemas/，不是 shim 的 skills/_lib/schemas/」——
    那句**也要一起改掉**（见 File Map 的 EDIT 行），否则本守卫永远红。
    """
    hits = []
    for p in (REPO_ROOT / "skills").rglob("*"):
        if p.is_file() and p.suffix in {".py", ".sh", ".md"} and "__pycache__" not in p.parts:
            if "skills/_lib/schemas/" in p.read_text(encoding="utf-8", errors="ignore"):
                hits.append(str(p.relative_to(REPO_ROOT)))
    assert hits == [], hits


def test_no_proxy_to_missing_directory():
    """skills/*.py 代理不得指向不存在的目录。"""
    offenders = []
    for p in (REPO_ROOT / "skills").glob("*.py"):
        text = p.read_text(encoding="utf-8")
        for marker in ("__path__ = [__import__('os').path.join(__import__('os').path.dirname(__file__), '",):
            if marker not in text:
                continue
            target = text.split(marker, 1)[1].split("'", 1)[0]
            if not (REPO_ROOT / "skills" / target).is_dir():
                offenders.append(f"{p.name} -> {target}")
    assert offenders == [], offenders


def test_shim_schema_dir_is_not_importable(monkeypatch):
    """skills/_lib/schemas/ 已删除 → 隔离全局回落后必须不可 import。

    不 monkeypatch 掉 `skills._lib.__path__` 的全局回落路径时，
    在装了全局 skill 的机器上该 import 会**解析成功**（拿到全局副本）→ 断言不稳定。
    """
    import importlib
    import sys

    import skills._lib as shim_pkg

    monkeypatch.setattr(shim_pkg, "__path__", [str(SHIM_DIR)])
    sys.modules.pop("skills._lib.schemas", None)
    with pytest.raises(ImportError):
        importlib.import_module("skills._lib.schemas")


def test_all_canonical_schemas_parse():
    """canonical schema 必须是合法 JSON。"""
    bad = []
    for p in sorted((REPO_ROOT / "_lib" / "schemas").glob("*.json")):
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            bad.append(f"{p.name}: {e}")
    assert bad == [], bad


def test_three_live_schemas_are_canonical():
    """3 个只在副本目录存在的活契约必须已搬进 canonical。"""
    for name in ("populate_state_schema.json",
                 "populate_supplementary_schema.json",
                 "rfc_draft_schema.json"):
        assert (REPO_ROOT / "_lib" / "schemas" / name).is_file(), name
        assert not (SHIM_DIR / "schemas" / name).exists(), name


def test_canonical_declares_fields_the_runtime_writes():
    """canonical schema 必须声明运行时实际写入的字段。

    两个真实 bug 的回归守卫：
    - `iteration_schema.json` 缺 `cross_repo_dependencies` → 该 schema 是
      `additionalProperties: false`，而运行时 `_lib/iteration/__init__.py:174`
      （v6→v7 迁移）**每个 change 都写这个字段** → 校验必失败。
    - `sessions_schema.json` 缺 `$defs.Session.properties.metrics`（v3）→
      既有测试 `test_session_metrics.py` 钉住该字段。
    """
    iteration = json.loads(
        (REPO_ROOT / "_lib" / "schemas" / "iteration_schema.json").read_text(encoding="utf-8")
    )
    change_props = iteration["properties"]["changes"]["items"]["properties"]
    assert "cross_repo_dependencies" in change_props, (
        "iteration_schema.json 缺 cross_repo_dependencies —— 运行时每个 change 都写它，"
        "且该 schema 是 additionalProperties: false → 校验必失败"
    )

    sessions = json.loads(
        (REPO_ROOT / "_lib" / "schemas" / "sessions_schema.json").read_text(encoding="utf-8")
    )
    session_props = sessions["$defs"]["Session"]["properties"]
    assert "metrics" in session_props, "sessions_schema.json 缺 $defs.Session.properties.metrics"
    assert "last_seen_offset" in session_props["goal"]["properties"], (
        "sessions_schema.json 缺 goal.last_seen_offset（doctor 的 state 检查引用它）"
    )


def test_no_duplicate_top_level_keys_in_canonical_schemas():
    """重复键：后写覆盖先写，解析器不报错但语义已丢。"""
    def _reject_duplicates(pairs):
        seen = set()
        for key, _value in pairs:
            if key in seen:
                raise ValueError(f"duplicate top-level key: {key}")
            seen.add(key)
        return dict(pairs)

    offenders = []
    for p in sorted((REPO_ROOT / "_lib" / "schemas").glob("*.json")):
        try:
            json.loads(p.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicates)
        except ValueError as e:
            offenders.append(f"{p.name}: {e}")
    assert offenders == [], offenders
