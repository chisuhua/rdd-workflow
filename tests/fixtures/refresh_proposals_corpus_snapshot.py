"""刷新语料 golden snapshot（AC4）—— **新增 improvement 后必须同 PR 运行**。

用法：
    python3 tests/fixtures/refresh_proposals_corpus_snapshot.py

产物：`tests/fixtures/proposals_corpus_snapshot.json`
- ``generated_at``：刷新时刻
- ``corpus_count``：**动态**语料计数（不得写死）
- ``shape_labels``：全语料的形态标签汇总
- ``items[name]``：每份 improvement 的形态标签 + 生成物 sha256（指纹，体积 ~60KB）
"""
from __future__ import annotations

import datetime
import hashlib
import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_SCRIPT = ROOT / "skills" / "rdd-builder" / "scripts" / "generate_full_proposal.py"
_spec = importlib.util.spec_from_file_location("gen_fp_refresh", _SCRIPT)
gen_fp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen_fp)

SNAPSHOT = ROOT / "tests" / "fixtures" / "proposals_corpus_snapshot.json"
IMPROVEMENTS = sorted((ROOT / ".rddf" / "improvements").glob("*.md"))


def _what_changes(text: str) -> str:
    marker = "## What Changes"
    if marker not in text:
        return ""
    rest = text.split(marker, 1)[1]
    for stop in ("\n## Capabilities", "\n## Impact", "\n## Acceptance"):
        if stop in rest:
            rest = rest.split(stop, 1)[0]
    return rest.strip()


def main() -> int:
    items: dict[str, dict] = {}
    totals = {"table_row": 0, "bullet": 0, "numbered": 0, "other": 0}
    for path in IMPROVEMENTS:
        md = path.read_text(encoding="utf-8")
        out = gen_fp.generate_full_proposal(path.stem, md)
        labels = gen_fp.shape_labels(md)
        for k, v in labels.items():
            totals[k] += v
        items[path.stem] = {
            "labels": labels,
            "sha256": hashlib.sha256(out.encode("utf-8")).hexdigest(),
        }
    data = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "corpus_count": len(IMPROVEMENTS),
        "shape_labels": totals,
        "items": items,
    }
    SNAPSHOT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"snapshot refreshed: {len(IMPROVEMENTS)} improvements → {SNAPSHOT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
