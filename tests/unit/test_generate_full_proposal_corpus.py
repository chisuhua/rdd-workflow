"""语料 golden snapshot —— 全量 improvement 的生成结果**必须**与入库期望一致（AC4）。

为什么用「快照」而不是「差异白名单」：白名单若是**文件清单**，实施者可以在同一个 PR 里
把新差异加进白名单 ⇒ 判别力为零；快照是**期望值**，任何改动都会显式出现在 diff 里。

快照内容（每份 improvement）：
- ``sha256``：整份生成物的指纹（覆盖面 = 整份 proposal，**强于**只钉 What Changes 段）
- ``labels``：该 improvement 的**行首形态标签**（table_row / bullet / numbered / other）

⚠ **为什么不存整段文本**：全语料 300+ 份 × 整份 proposal ≈ 600KB（比仓内最大文件大 5 倍）。
指纹 + 形态标签已**完全**具备判别力（任一字节变化 ⇒ sha 变 ⇒ 红），而体积落在 ~60KB；
「哪几份变了」在快照 diff 里一目了然（每份一行）。

⚠ 语料会增长 ⇒ 新增 improvement 后**必须同 PR 刷新快照**
（`python3 tests/fixtures/refresh_proposals_corpus_snapshot.py`），否则本用例红。
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_SCRIPT = _ROOT / "skills" / "rdd-builder" / "scripts" / "generate_full_proposal.py"
_spec = importlib.util.spec_from_file_location("gen_fp_corpus", _SCRIPT)
gen_fp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen_fp)

_SNAPSHOT = _ROOT / "tests" / "fixtures" / "proposals_corpus_snapshot.json"
_IMPROVEMENTS = sorted((_ROOT / ".rddf" / "improvements").glob("*.md"))


def _what_changes(text: str) -> str:
    """取生成的 `## What Changes` 段（逐字）。"""
    marker = "## What Changes"
    if marker not in text:
        return ""
    rest = text.split(marker, 1)[1]
    for stop in ("\n## Capabilities", "\n## Impact", "\n## Acceptance"):
        if stop in rest:
            rest = rest.split(stop, 1)[0]
    return rest.strip()


def test_snapshot_metadata_is_dynamic() -> None:
    """快照元信息必须是**动态**的（语料计数随仓增长 ⇒ 不得写死）。"""
    data = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    assert data["corpus_count"] == len(_IMPROVEMENTS), (
        f"语料计数漂移：快照 {data['corpus_count']} vs 实测 {len(_IMPROVEMENTS)}"
        " ⇒ 新增 improvement 后必须同 PR 刷新快照"
    )
    assert data["generated_at"], "快照缺 generated_at"
    assert set(data["shape_labels"]) == {"table_row", "bullet", "numbered", "other"}


def test_generated_output_matches_golden_snapshot() -> None:
    """逐份比对：生成结果 == 入库期望（段 + 形态标签 + 指纹）。"""
    data = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    for path in _IMPROVEMENTS:
        md = path.read_text(encoding="utf-8")
        out = gen_fp.generate_full_proposal(path.stem, md)
        expected = data["items"].get(path.stem)
        assert expected is not None, (
            f"快照缺 {path.stem} ⇒ 同 PR 必须刷新快照"
            "（python3 tests/fixtures/refresh_proposals_corpus_snapshot.py）"
        )
        assert gen_fp.shape_labels(md) == expected["labels"], (
            f"{path.stem} 的形态标签与快照不一致"
        )
        digest = hashlib.sha256(out.encode("utf-8")).hexdigest()
        assert digest == expected["sha256"], f"{path.stem} 的生成物指纹与快照不一致"
