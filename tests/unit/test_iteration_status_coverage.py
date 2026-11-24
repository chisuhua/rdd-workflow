"""change 状态的**两个词汇域**完整性守卫。

背景（fix-rddf-status-icon-coverage）：

仓库里 change 状态有**两个互不相同**的词汇域，各有各的真源：

- **iteration.json 域**（状态写进 ``iteration.json``，由 ``rddf dashboard`` /
  ``rddf iteration`` / ``rddf guide`` 渲染）
  ⇒ 真源 = ``_lib/schemas/iteration_schema.json`` 的 ``status`` enum
  ⇒ 派生：``_lib/iteration/schema.py::_VALID_STATUSES``、
  ``_lib/dashboard/renderer.py::_STATUS_ICON`` / ``_STATUS_ICON_PLAIN``
- **disk-derived 域**（状态由磁盘推导，**不写** ``iteration.json``）
  ⇒ 真源 = ``_lib/cli/status_cmd.py::_disk_change_status()`` 的值域 ∪
  {``archived``, ``unknown``}
  ⇒ 派生：``_lib/cli/status_cmd.py::_STATUS_ICON``

初版把 schema enum 当成唯一真源、要求所有表都 ⊇ enum —— **错的**：
``rddf status`` 不读 iteration.json（见 ``status_cmd`` 的模块 docstring），
它的表服务的是 disk-derived 词汇（含 ``committed``，**不在** enum 内）。

本文件锁住两域各自的完整性 + 跨域公共部分的一致性，以及
「``archived_partial`` 在每一处 archived 过滤点都被识别」这条口径。

⚠️ ``_lib/schemas/iteration_schema.json`` 是 **tracked** 的 ⇒ 本守卫在 CI 上
**有牙齿**（与扫 ``openspec/`` 的守卫不同 —— 那个在 CI 上是空转的）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from _lib.cli.status_cmd import _STATUS_ICON as STATUS_CMD_ICON
from _lib.dashboard.renderer import _STATUS_ICON as RENDERER_ICON
from _lib.dashboard.renderer import _STATUS_ICON_PLAIN as RENDERER_ICON_PLAIN
from _lib.iteration.schema import _VALID_STATUSES

REPO_ROOT = Path(__file__).resolve().parents[2]

SCHEMA_PATH = REPO_ROOT / "_lib" / "schemas" / "iteration_schema.json"

#: iteration.json 域的真源 —— schema 的 status enum。
ITERATION_STATUS_ENUM = tuple(
    json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    ["properties"]["changes"]["items"]["properties"]["status"]["enum"]
)

#: disk-derived 域的真源 —— `_disk_change_status()` 的返回值
#: （``in_worktree`` / ``committed`` / ``completed`` / ``planned``）+ ``status_cmd.py`` 里硬编码的
#: ``archived`` + ``.get(status, "?")`` 的兜底 ``unknown``。
#:
#: ``unknown`` 是**防御键**：当前渲染路径产不出它（status 不读 iteration.json），
#: 但删掉会让将来的这个状态渲染成 ``?``。
#: ``completed`` 由「tasks.md 全勾」推出（``_tasks_complete``）—— 在
#: ``openspec/`` 被 gitignore 的仓里 ``committed`` 探针永远命中不了，
#: 没有这一条则已完成的 change 会被报成 ``planned``。
DISK_DERIVED_STATUSES = {
    "planned",
    "in_worktree",
    "completed",
    "archived",
    "committed",
    "unknown",
}

#: 两域的交集 —— 跨表一致性只对这组断言（emoji 表 vs emoji 表）。
OVERLAP_STATUSES = ("planned", "in_worktree", "archived")


# ---------------------------------------------------------------------------
# ① iteration.json 域：store 的写校验集合 == schema enum
# ---------------------------------------------------------------------------
def test_valid_statuses_matches_schema_enum() -> None:
    assert set(_VALID_STATUSES) == set(ITERATION_STATUS_ENUM), (
        "_lib/iteration/schema.py::_VALID_STATUSES drifted from the schema enum: "
        f"only-in-code={sorted(set(_VALID_STATUSES) - set(ITERATION_STATUS_ENUM))} "
        f"only-in-schema={sorted(set(ITERATION_STATUS_ENUM) - set(_VALID_STATUSES))}"
    )
    assert len(_VALID_STATUSES) == len(set(_VALID_STATUSES)), "duplicate status in _VALID_STATUSES"


# ---------------------------------------------------------------------------
# ②③ iteration.json 域：两张 dashboard 图标表覆盖 enum，且每个值非空
# ---------------------------------------------------------------------------
def test_renderer_icons_cover_schema_enum() -> None:
    for label, table in (
        ("_STATUS_ICON", RENDERER_ICON),
        ("_STATUS_ICON_PLAIN", RENDERER_ICON_PLAIN),
    ):
        missing = sorted(set(ITERATION_STATUS_ENUM) - set(table))
        assert not missing, f"dashboard/renderer.py::{label} misses statuses: {missing}"
        for status in ITERATION_STATUS_ENUM:
            assert str(table[status]).strip(), (
                f"dashboard/renderer.py::{label}[{status!r}] is empty"
            )


# ---------------------------------------------------------------------------
# ④ disk-derived 域：键集**恰好**等于该域的词汇集
# ---------------------------------------------------------------------------
def test_status_cmd_icon_keys_match_disk_derived_vocabulary() -> None:
    """不多（死键 —— 永远不会被 ``.get()`` 命中）不少（会渲染成 ``?``）。"""
    assert set(STATUS_CMD_ICON) == DISK_DERIVED_STATUSES, (
        "_lib/cli/status_cmd.py::_STATUS_ICON drifted from the disk-derived "
        f"vocabulary: extra={sorted(set(STATUS_CMD_ICON) - DISK_DERIVED_STATUSES)} "
        f"missing={sorted(DISK_DERIVED_STATUSES - set(STATUS_CMD_ICON))}"
    )
    for status, icon in STATUS_CMD_ICON.items():
        assert str(icon).strip(), f"status_cmd.py::_STATUS_ICON[{status!r}] is empty"


# ---------------------------------------------------------------------------
# ⑤ 跨域公共部分：同一状态在两张 emoji 表里给出相同图标
# ---------------------------------------------------------------------------
def test_overlap_statuses_share_the_same_emoji() -> None:
    for status in OVERLAP_STATUSES:
        assert STATUS_CMD_ICON[status] == RENDERER_ICON[status], (
            f"status {status!r} renders as {STATUS_CMD_ICON[status]!r} in "
            f"status_cmd.py but {RENDERER_ICON[status]!r} in dashboard/renderer.py"
        )


# ---------------------------------------------------------------------------
# ⑥ archived 口径：`archived_partial` 在每一处 archived 过滤点都被识别
# ---------------------------------------------------------------------------
_ARCHIVED_LITERAL = re.compile(r'==\s*"archived"|!=\s*"archived"')

#: 明确**不改**的 3 处 —— 每条都带理由（改口径前先看这里）。
_ARCHIVED_LITERAL_EXEMPT = (
    (
        "_lib/cli/status_cmd.py",
        re.compile(r'^\s*if status == "archived":'),
        "disk-derived domain — `rddf status` never reads iteration.json",
    ),
    (
        "_lib/iteration/repair.py",
        re.compile(r'existing\.get\("status"\) != "archived"'),
        "the archived_partial -> archived upgrade direction is intentional",
    ),
    (
        "_lib/roadmap_state.py",
        re.compile(r'frag\.status == "archived"'),
        "`frag.status` is a feature-fragment status, not a change status",
    ),
)


def _archived_literal_sites() -> list[tuple[str, int, str]]:
    """全仓 ``== "archived"`` / ``!= "archived"`` 的字面比较点。"""
    out: list[tuple[str, int, str]] = []
    roots = [REPO_ROOT / "_lib", REPO_ROOT / "skills"]
    files: list[Path] = []
    for root in roots:
        files.extend(p for p in root.rglob("*.py") if "__pycache__" not in str(p))
        files.extend(p for p in root.rglob("*.sh") if "__pycache__" not in str(p))
    for path in sorted(files):
        rel = str(path.relative_to(REPO_ROOT))
        for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
            if not _ARCHIVED_LITERAL.search(line):
                continue
            if "archived_partial" in line:
                continue
            out.append((rel, lineno, line))
    return out


def test_every_archived_literal_site_recognises_archived_partial() -> None:
    """每一处 archived 字面比较都必须同时识别 ``archived_partial``（或被显式豁免）。"""
    unaligned = []
    for rel, lineno, line in _archived_literal_sites():
        exempt = any(
            path == rel and pattern.search(line)
            for path, pattern, _reason in _ARCHIVED_LITERAL_EXEMPT
        )
        if exempt:
            continue
        unaligned.append(f"{rel}:{lineno}: {line.strip()}")
    assert not unaligned, (
        "archived filters that do not recognise 'archived_partial' "
        "(schema allows it):\n  " + "\n  ".join(unaligned)
    )


def test_exempt_list_is_still_accurate() -> None:
    """豁免清单里的每一条都必须**仍然存在**（否则豁免就该删掉）。"""
    for path, pattern, reason in _ARCHIVED_LITERAL_EXEMPT:
        target = REPO_ROOT / path
        assert target.is_file(), f"exempt path no longer exists: {path} ({reason})"
        hits = [
            line
            for line in target.read_text(errors="ignore").splitlines()
            if pattern.search(line) and "archived_partial" not in line
        ]
        assert hits, f"exempt no longer matches in {path}: {pattern.pattern} ({reason})"
