"""Generate the machine census of retired-stage names in adopted specs.

The census is the **tracked** artifact of ``fix-spec-residue-guard``: in this
repo ``openspec/`` is gitignored, so spec edits produce no diff at all — the
census ledger is the only thing that lands in git.

Design decisions (see the change's ``proposal.md`` → 「与草案的偏离」):

* **No cross-ledger merge.** Earlier batches' ledgers store context-fragment
  tokens and truncated titles with duplicate keys, so any join is either lossy
  or ambiguous.  Sign-off records stay in those ledgers; this file is the
  backlog list, and ``disposition`` is always ``unset`` until Phase 1 signs a
  row off.
* **Only unexempted hits.** A hit carrying ``<!-- v4-residue:allow=<code> -->``
  is somebody's explicit judgement — it does not belong in the backlog.
* **Byte-identical on re-run.** Rows are sorted by
  ``(file, line, matched_token)`` and the header carries no timestamp, so
  ``diff`` between two runs is empty.

Usage::

    python3 skills/rdd-doctor/scripts/gen_spec_residue_census.py \\
        --out .rddf/reviews/spec-residue-census-2026-11-20-full.md
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from spec_residue_scan import RETIRED_TOKENS, scan_specs  # noqa: E402

COLUMNS: Tuple[str, ...] = (
    "file",
    "line",
    "requirement_title",
    "matched_token",
    "category",
    "disposition",
    "owner",
    "signoff",
    "date",
)

#: Batches already signed off by hand; their rows still appear here as backlog
#: because the machine cannot know a judgement happened (see module docstring).
PRIOR_LEDGERS: Tuple[str, ...] = (
    ".rddf/reviews/spec-residue-census-2026-11-20.md",
    ".rddf/reviews/spec-residue-census-2026-11-20-batch2.md",
)

#: The specs those two ledgers cover.
PRIOR_SPECS: Tuple[str, ...] = (
    # batch 1 (13)
    "add-strict-human-approval",
    "apply-adr-0051-skill-description-convention-bulk-rewrite",
    "approved-proposal-parsing",
    "cross-container-event-bus",
    "design-content-review",
    "project-setup-check",
    "proposal-lifecycle-sync",
    "rddf-session",
    "roadmap-feature-fragment",
    "ship-done-orphan-cleanup",
    "skill-role-model",
    "three-phase-skills",
    "workflow-design-phase",
    # batch 2 (5)
    "iterative-plan-fill",
    "plan-intake-bootstrap",
    "post-archive-cleanup-hook",
    "rddf-session-auto-archive",
    "verifier-v2-hardening",
)

_CALIBRATION = ((True, True), (True, False), (False, True), (False, False))


def _cell(value: object) -> str:
    """Markdown table cell — escape pipes, collapse newlines."""
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _hub_managed(project_root: Path) -> set:
    """Capability names written by ``sync_hub`` (report-only, never fixed here).

    ``skills/sync-hub/scripts/sync_hub.py`` materialises
    ``openspec/specs/<contract>/spec.md`` from the Hub, so editing those specs
    would be overwritten upstream.  The set is read from
    ``.rddf/config/*hub*.y*ml`` when such a config exists; a project without a
    Hub config has no hub-managed capability.
    """
    names: set = set()
    cfg_dir = project_root / ".rddf" / "config"
    if not cfg_dir.is_dir():
        return names
    for cfg in sorted(cfg_dir.iterdir()):
        if "hub" not in cfg.name.lower():
            continue
        if cfg.suffix.lower() not in (".yaml", ".yml", ".json"):
            continue
        try:
            text = cfg.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if cfg.suffix.lower() == ".json":
            import json

            try:
                data = json.loads(text)
            except ValueError:
                continue
        else:
            try:
                import yaml

                data = yaml.safe_load(text) or {}
            except Exception:
                continue
        contracts = data.get("contracts") if isinstance(data, dict) else None
        if isinstance(contracts, list):
            names.update(str(c) for c in contracts)
        elif isinstance(contracts, dict):
            names.update(str(c) for c in contracts)
    return names


def build_census(project_root: Path) -> str:
    """Render the census markdown for ``project_root``."""
    root = Path(project_root)
    result = scan_specs(root)                       # frozen 口径: True × True
    hub = _hub_managed(root)

    rows: List[Dict[str, str]] = []
    for hit in result.hits:
        if hit.category:                            # explicitly exempted
            continue
        cap = Path(hit.file).parent.name
        disposition = "excluded(hub-managed)" if cap in hub else "unset"
        rows.append({
            "file": hit.file,
            "line": str(hit.line),
            "requirement_title": hit.requirement_title,
            "matched_token": hit.matched_token,
            "category": "unclassified",
            "disposition": disposition,
            "owner": "",
            "signoff": "",
            "date": "",
        })
    rows.sort(key=lambda r: (r["file"], int(r["line"]), r["matched_token"]))

    combo_rows: List[Sequence[str]] = []
    for code_block_in, title_in in _CALIBRATION:
        res = scan_specs(root, code_block_in=code_block_in, title_in=title_in)
        combo_rows.append((
            f"`{code_block_in}` × `{title_in}`"
            + (" ← 选定（冻结）" if code_block_in and title_in else ""),
            str(len(res.hits)),
            str(len(res.blocks())),
            str(len({h.file for h in res.hits})),
        ))

    prior_rows = [r for r in rows if Path(r["file"]).parent.name in PRIOR_SPECS]
    prior_lines = len({(r["file"], r["line"]) for r in prior_rows})
    unset_rows = sum(1 for r in rows if r["disposition"] == "unset")

    out: List[str] = []
    out.append("# spec 残留普查台账（机器生成）")
    out.append("")
    out.append("> 生成器：`skills/rdd-doctor/scripts/gen_spec_residue_census.py` — **不要手编辑本文件**。")
    out.append("> 台账 = **清理待办清单**（`disposition=unset` 的行归零 = Phase 1 的完成判据）+ 可复算基线 + 证据。")
    out.append("> 签批记录的权威落点**不是这里** —— 见下方「既有签批」段。")
    out.append("")
    out.append("## 口径（冻结常量）")
    out.append("")
    out.append("扫描根 `openspec/specs/*/spec.md`（恰为一层，非递归；**不扫** `openspec/changes/**`）。")
    out.append("normative 段 = `### Requirement:` 标题+正文 / `#### Scenario:` 标题+正文 / 正文内 fenced code block；")
    out.append("**不含** `## Purpose` 等散文段。命中按**块**归类。")
    out.append("")
    out.append("词边界：`(?<![\\w-])(guide-arch|guide-design|guide-plan|guide-ship|guide-spec|ac-verifier)(?![\\w-])`")
    out.append("（token 后不得再跟 `-`，否则 `guide-plan-quick-finish` 这类**提案名**会被前缀命中）。")
    out.append("")
    out.append("| `code_block_in` × `title_in` | 命中处数 | 命中块数 | 命中 spec 份数 |")
    out.append("|---|---|---|---|")
    for combo in combo_rows:
        out.append("| " + " | ".join(combo) + " |")
    out.append("")
    out.append("## 基线（选定口径）")
    out.append("")
    out.append(f"- 扫描 spec 文件：**{result.files_scanned}** 份")
    out.append(f"- 命中实例：**{len(result.hits)}** 处（其中未被豁免 **{len(rows)}** 处）")
    out.append(f"- 命中块：**{len(result.blocks())}** 块")
    out.append(f"- 命中 spec：**{len({h.file for h in result.hits})}** 份")
    out.append(f"- `stale allow`（过期豁免）：**{len(result.stale_allows)}** 处")
    out.append("")
    if not result.checked_anything:
        out.append("> ⚠️ **checked 0** —— 未扫描到任何 spec 文件（`openspec/specs/` 不存在或为空）。")
        out.append("> 这**不等于 clean**：干净 clone 上没有 `openspec/`，静默通过就是假通过。")
        out.append("")
    out.append("## 既有签批（不由本台账合并）")
    out.append("")
    out.append("| 批次 | 台账 | 覆盖 spec |")
    out.append("|---|---|---|")
    out.append("| 第一批（13 份 / 34 处） | `" + PRIOR_LEDGERS[0] + "` | 见该文件 |")
    out.append("| 第二批（5 份 / 37 处） | `" + PRIOR_LEDGERS[1] + "` | 见该文件 |")
    out.append("")
    if prior_rows:
        out.append(f"这 {len(PRIOR_SPECS)} 份当前仍有 **{prior_lines}** 个命中行（{len(prior_rows)} 条实例），"
                   "在本台账里以 `disposition=unset` 出现 ——")
        out.append("机器无法知道人工签批发生过，**Phase 1 必须逐行重新对齐**并由标注消除它们。")
        out.append("")
        out.append("⚠️ **不得**把这 18 份统一标 `allow=history`：`RETIRED` 的保留原文才是 history；")
        out.append("`PARTIAL` 的仍生效子句若含旧名 ⇒ **真实 delta**；`KEEP` 取旧台账 `category` 对应的 code。")
    else:
        out.append(f"这 {len(PRIOR_SPECS)} 份已**全部处置完毕**（0 个命中行）—— 逐行判定与标注见")
        out.append("`.rddf/reviews/spec-residue-align-18-2026-11-20.md`（change `align-spec-residue-prior-18`）。")
    out.append("")
    out.append("## 残留清单")
    out.append("")
    if rows:
        out.append("| " + " | ".join(COLUMNS) + " |")
        out.append("|" + "|".join(["---"] * len(COLUMNS)) + "|")
        for r in rows:
            out.append("| " + " | ".join(_cell(r[c]) for c in COLUMNS) + " |")
    else:
        out.append("（无 —— `disposition=unset` 的行已归零）")
    out.append("")
    out.append("## 合计")
    out.append("")
    out.append(f"- `disposition=unset`：**{unset_rows}** 条命中记录（Phase 1 的待办量）")
    out.append(f"- 已登记豁免（标注）：**{sum(1 for h in result.hits if h.category)}** 处")
    out.append("- 命中 token 分布：")
    counts: Dict[str, int] = {}
    for r in rows:
        counts[r["matched_token"]] = counts.get(r["matched_token"], 0) + 1
    for token in RETIRED_TOKENS:
        if token in counts:
            out.append(f"  - `{token}`: {counts[token]}")
    out.append("")
    return "\n".join(out)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, help="output markdown path")
    parser.add_argument(
        "--project-root",
        default=os.environ.get("RDDF_PROJECT_ROOT", "."),
        help="project root (default: $RDDF_PROJECT_ROOT or '.')",
    )
    args = parser.parse_args(argv)

    root = Path(args.project_root).resolve()
    text = build_census(root)
    out = Path(args.out)
    if not out.is_absolute():
        out = root / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
