"""rdd-quick 的历史文件必须落在 <项目根>/.rddf/state/ 下。"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
APPEND = REPO_ROOT / "skills/rdd-quick/scripts/append_history.py"


def test_append_history_has_no_walk_up_heuristic():
    """禁止「按目录名特征向上搜索」——那正是本 bug 的成因。

    口径不是「文本里不能出现 is_dir()」：合法的固定深度锚点（parents[N]）
    只用于 import 引导，可以保留。要禁的是「循环 + 特征目录探测」的组合。
    """
    text = APPEND.read_text(encoding="utf-8")
    has_loop = re.search(r"for\s+\w+\s+in\s+range\s*\(", text) is not None
    has_probe = re.search(r"is_dir\(\)|exists\(\)", text) is not None
    assert not (has_loop and has_probe), "不得用『向上循环 + 探测特征目录』推导项目根"


def test_append_history_uses_canonical_resolver():
    text = APPEND.read_text(encoding="utf-8")
    assert "resolve_project_root" in text


def test_history_path_is_under_project_root_state_dir():
    text = APPEND.read_text(encoding="utf-8")
    assert '"state"' in text and ".quick-history.jsonl" in text
