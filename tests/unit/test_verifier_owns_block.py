"""The skill's `owns:` block must match the code that writes those files.

Per `consolidate-verifier-state`: `skills/rdd-verifier/SKILL.md` declared
**4** paths while the skill actually wrote **6** (`.ac-verifier-blocked.jsonl`
and `rdd-verify-context-<name>.json` were written but never declared) — a
manifest that can silently under-report its own write surface.

This module ties the manifest to the code:

  1. `SKILL.md` contains `_lib/verifier/state_paths.py::render_owns_block()`
     **byte for byte** (same repo ⇒ CI can check it — the cross-repo half
     remains manual, see the opencode-side `VERIFIER_OWNS_PATHS`);
  2. every path the code produces matches one of the owns patterns;
  3. the legacy (pre-consolidation) locations are **not** owned any more.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _lib.verifier.audit import _audit_path  # noqa: E402
from _lib.verifier.cache import (  # noqa: E402
    audit_log_path,
    blocked_audit_log_path,
    verdict_cache_path,
    verify_context_path,
)
from _lib.verifier.loop_state import _state_path  # noqa: E402
from _lib.verifier.state_paths import (  # noqa: E402
    SKILL_OWNS_PATHS,
    matches_any_owns,
    render_owns_block,
)

SKILL_MD = Path(__file__).resolve().parents[2] / "skills" / "rdd-verifier" / "SKILL.md"


def test_skill_md_owns_block_matches_canonical_byte_for_byte():
    text = SKILL_MD.read_text(encoding="utf-8")
    block = render_owns_block()
    assert block in text, (
        "SKILL.md 的 owns: 块与 _lib/verifier/state_paths.py 不一致 —— "
        "以 render_owns_block() 为准（改代码时同批改 SKILL.md）"
    )
    assert text.count(block) == 1, "owns: 块在 SKILL.md 里应恰好出现一次"


def test_owns_block_lists_exactly_six_paths():
    assert len(SKILL_OWNS_PATHS) == 6
    # 六项都在 `.rddf/state/verifier/` 命名空间内（收拢的硬判据）
    for p in SKILL_OWNS_PATHS:
        assert p.startswith(".rddf/state/verifier/"), p


def test_every_produced_path_matches_an_owns_pattern():
    root = Path("/tmp/proj")
    produced = [
        verdict_cache_path(root, "ch-x"),
        audit_log_path(root),
        blocked_audit_log_path(root),
        verify_context_path(root, "ch-x"),
        _state_path(root, "ch-x"),
        _audit_path(root, "ch-x"),
    ]
    for path in produced:
        rel = path.relative_to(root)
        assert matches_any_owns(rel), f"{rel} 不在 owns 集合内"


def test_legacy_root_locations_are_not_owned():
    """收拢前的根下路径**不再**是 owns 的一部分（它们已被搬进命名空间）。"""
    for legacy in (
        ".rddf/state/.ac-verdict-ch-x.json",
        ".rddf/state/.ac-verification.jsonl",
        ".rddf/state/.ac-verifier-blocked.jsonl",
        ".rddf/state/rdd-verify-context-ch-x.json",
    ):
        assert not matches_any_owns(legacy), legacy


def test_manifest_owns_count_is_six():
    """SKILL.md 的 owns 列表**逐项**就是这六条（防止清单被悄悄增删）。"""
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.index("    owns:")
    end = text.index("    not_owns:", start)
    listed = [line.strip() for line in text[start:end].splitlines() if line.strip().startswith("- ")]
    assert len(listed) == 6, f"owns 应有 6 项，实际 {len(listed)}"
    for item in listed:
        path = item.strip("- ").strip('"')
        assert path in SKILL_OWNS_PATHS, f"owns 里出现清单外的路径: {path}"
