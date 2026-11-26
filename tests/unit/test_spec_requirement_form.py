"""spec 的**形态**守卫 —— 防「自动生成的 Requirement 退化形态」回流。

背景（`rewrite-register-change-in-iteration-spec` 试点）：

``openspec/specs/**`` 里有一批 spec 的 Requirement 是 change 的 AC 机械搬过来的，
形态退化有四种：

1. **Requirement 名无语义** —— ``### Requirement: acceptance-3``
   （名是 AC 序号，读者无法从名字判断这条讲什么）
2. **正文被截断 ⇒ 语义丢失** —— 「SHALL … 不再返回.」（宾语被切掉）
3. **Scenario 名被截断** —— ``#### Scenario: 同场景下 … sync_iteration_after_archi``
4. **Scenario 的 WHEN 恒真** —— ``- **WHEN** the change is applied``
   （对**任何** change 都成立 ⇒ Scenario 零判别力）

第 4 条比「零信息」更危险：读者会以为读到了一条真契约。

本文件用**tracked 的清单** ``tests/unit/spec_form_compliant.json`` 记录哪些 spec 已经整改：

- **清单自身的完整性**（schema / 无重复 / 两段不交 / 并集 == 已知全集）
  ⇒ **CI 上可判**（清单是 tracked 的）⇒ 「有人从 pending 删掉却不 promote 到 compliant」
  这类**清单停滞**会立刻红。
- **已整改 spec 的形态**（判据 ①②）
  ⇒ 需要 ``openspec/specs/`` 存在 ⇒ ``openspec/`` 整树 gitignore ⇒ **CI 上 skip**
  （与 ``requires_general_spec`` / ``requires_spec_requirement_form`` 同款）。

⚠️ 因此本守卫对「清单完整性」有 CI 牙齿，对「spec 内容」只有本地牙齿。
这是 ``openspec/`` 不跟踪这一既有立场的必然结果，不是本守卫的设计缺陷。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SPECS_DIR = REPO_ROOT / "openspec" / "specs"
MANIFEST_PATH = REPO_ROOT / "tests" / "unit" / "spec_form_compliant.json"

#: `acceptance-N` 形态的 Requirement 所在的**已知全集**（12 份）。
#: 这是一个**有界集合**（不是目录构成计数）—— 它只随「本系列是否又新增一份」而变，
#: 不随每次加文件而变 ⇒ 冻结它是安全的。
ACCEPTANCE_FORM_SPECS = (
    "env-bootstrap",
    "fix-bats-per-file-timeout",
    "fix-flow-drift-batch-1",
    "fix-p3-verifier-gate",
    "fix-phase3-cleanup-wiring",
    "fix-script-project-root-anchoring",
    "fix-skill-post-install-discoverability",
    "fix-worktree-archive-path",
    "objective-tracking",
    "rddf-layout-manifest",
    "register-change-in-iteration",
    "rfc-rddf-project-yaml-config-i10",
)

# 判据 ①②③ 的**单一真源**在 `_lib/spec_requirement_form.py`（2026-11-27 上移）：
# 生成器（`generate_full_proposal.generate_spec_delta()`）在产出前必须引用**同一份**判据，
# 否则「守卫改 A、生成器仍按 B 判」⇒ 退化形态持续流入归档期（每次归档手工重写）。
# ⇒ 本文件只**引用**判据，不再自己定义（AC10：两处实现 = 漂移）。
from _lib.spec_requirement_form import (  # noqa: E402
    DEGRADED_REQUIREMENT_NAME as _DEGRADED_REQUIREMENT_NAME,
    MEANINGLESS_REQUIREMENT as _MEANINGLESS_REQUIREMENT,
    TAUTOLOGICAL_WHEN as _TAUTOLOGICAL_WHEN,
)

requires_specs_dir = pytest.mark.skipif(
    not SPECS_DIR.is_dir(),
    reason="openspec/ is gitignored (local-only artifacts): no openspec/specs/ here",
)


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 清单自身的完整性 —— **CI 上可判**（清单是 tracked 的）
# ---------------------------------------------------------------------------
def test_manifest_covers_the_whole_acceptance_form_class() -> None:
    m = _manifest()
    assert m["schema"] == "spec-form-compliant-v1", m["schema"]

    compliant = list(m["compliant"])
    pending = list(m["pending"])

    assert len(compliant) == len(set(compliant)), f"duplicate in compliant: {compliant}"
    assert len(pending) == len(set(pending)), f"duplicate in pending: {pending}"
    assert not set(compliant) & set(pending), (
        f"spec listed in both compliant and pending: {sorted(set(compliant) & set(pending))}"
    )
    assert compliant, "compliant list is empty — the series stalled"

    covered = set(compliant) | set(pending)
    assert covered == set(ACCEPTANCE_FORM_SPECS), (
        "compliant ∪ pending must equal the known `acceptance-N` class exactly; "
        f"missing={sorted(set(ACCEPTANCE_FORM_SPECS) - covered)} "
        f"unknown={sorted(covered - set(ACCEPTANCE_FORM_SPECS))}"
    )
    assert m["class_total"] == len(ACCEPTANCE_FORM_SPECS), m["class_total"]


def test_manifest_compliant_is_monotonic_in_history() -> None:
    """`compliant` 只能增长 —— 靠 git 历史判定（`git show <HEAD>:file`）。"""
    import subprocess

    try:
        prev = subprocess.run(
            ["git", "show", "HEAD:tests/unit/spec_form_compliant.json"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("no git history for the manifest (fresh checkout?)")

    old = json.loads(prev)
    old_compliant = set(old.get("compliant", []))
    new_compliant = set(_manifest()["compliant"])
    dropped = sorted(old_compliant - new_compliant)
    assert not dropped, (
        f"compliant list shrank — a spec was un-promoted: {dropped}. "
        "The series is 'promote only'; retiring a spec must happen via the spec "
        "itself, not by dropping it from the manifest."
    )


# ---------------------------------------------------------------------------
# 已整改 spec 的形态 —— 需要 `openspec/specs/`（CI 上 skip）
# ---------------------------------------------------------------------------
@requires_specs_dir
def test_compliant_specs_have_no_acceptance_form_requirements() -> None:
    """判据 ①：已整改的 spec 不得再有 `acceptance-N` Requirement 名。"""
    offenders = []
    for name in _manifest()["compliant"]:
        spec = SPECS_DIR / name / "spec.md"
        if not spec.is_file():
            offenders.append(f"{name}: spec.md missing")
            continue
        for m in _MEANINGLESS_REQUIREMENT.finditer(spec.read_text(encoding="utf-8")):
            offenders.append(f"{name}:{spec.read_text(encoding='utf-8')[: m.start()].count(chr(10)) + 1}: {m.group(0).strip()}")
    assert not offenders, (
        "semantics-less requirement names remain:\n  " + "\n  ".join(offenders)
    )


@requires_specs_dir
def test_compliant_specs_have_no_tautological_scenario_when() -> None:
    """判据 ②：已整改的 spec 不得再有恒真的 Scenario WHEN。"""
    offenders = []
    for name in _manifest()["compliant"]:
        spec = SPECS_DIR / name / "spec.md"
        if not spec.is_file():
            continue
        text = spec.read_text(encoding="utf-8")
        for m in _TAUTOLOGICAL_WHEN.finditer(text):
            offenders.append(f"{name}:{text[: m.start()].count(chr(10)) + 1}: {m.group(0).strip()}")
    assert not offenders, (
        "tautological Scenario WHEN clauses remain:\n  " + "\n  ".join(offenders)
    )


@requires_specs_dir
def test_pending_specs_still_declare_the_acceptance_form() -> None:
    """清单里的 `pending` 必须**确实**还是 acceptance-N 形态。

    否则清单腐化了（spec 已整改却没 promote，或 spec 被删/改名）。
    """
    offenders = []
    for name in _manifest()["pending"]:
        spec = SPECS_DIR / name / "spec.md"
        if not spec.is_file():
            offenders.append(f"{name}: spec.md missing")
            continue
        if not _MEANINGLESS_REQUIREMENT.search(spec.read_text(encoding="utf-8")):
            offenders.append(
                f"{name}: no `acceptance-N` requirement left — promote it to compliant"
            )
    assert not offenders, (
        "pending list is stale:\n  " + "\n  ".join(offenders)
    )


@requires_specs_dir
def test_no_spec_anywhere_uses_a_degraded_requirement_form() -> None:
    """**全仓**扫描 —— 不依赖清单。

    上面那些判据都是**清单级**的：`compliant` / `pending` 只覆盖 `ACCEPTANCE_FORM_SPECS`
    那个**有界集合**（12 份）⇒ 第 13 份退化 spec 不咬，CI 上更没有牙齿
    （`openspec/` 整树 gitignore ⇒ 内容级判据在 CI 上 skip）。

    本判据扫 `openspec/specs/**` 的**每一份** spec ⇒ 任何新引入的退化形态立刻红
    （本地）。它同时覆盖两种命名：

    - `acceptance-N`（AC 序号名）
    - `capability-N`（**同一退化族的另一种命名** —— 见上面的教训 ⑦ 注释）
    """
    offenders = []
    for spec in sorted(SPECS_DIR.glob("*/spec.md")):
        text = spec.read_text(encoding="utf-8")
        rel = spec.relative_to(REPO_ROOT)
        for pattern in (_DEGRADED_REQUIREMENT_NAME, _TAUTOLOGICAL_WHEN):
            for m in pattern.finditer(text):
                line = text[: m.start()].count("\n") + 1
                offenders.append(f"{rel}:{line}: {m.group(0).strip()}")
    assert not offenders, (
        "degraded Requirement form found under openspec/specs/:\n  "
        + "\n  ".join(offenders)
        + "\n\nFix: give the Requirement a semantic name and make its WHEN "
        "discriminating (see .rddf/reviews/rewrite-acceptance-form-batch-5-2026-11-23.md)."
    )



def test_generator_and_guard_share_one_predicate_source() -> None:
    """单一真源（AC10）：守卫与生成器引用**同一份**判据 ⇒ 复制第二份即红。

    背景：生成器仍在产出被本守卫拒绝的形态（`acceptance-N` / 恒真 WHEN）⇒ 生成器必须
    能引用同一份判据；两处各写一份 ⇒ 必然漂移（本守卫改 A、生成器仍按 B 判）。
    """
    from _lib import spec_requirement_form as shared

    assert _DEGRADED_REQUIREMENT_NAME.pattern == shared.DEGRADED_REQUIREMENT_NAME.pattern
    assert _TAUTOLOGICAL_WHEN.pattern == shared.TAUTOLOGICAL_WHEN.pattern
    assert _MEANINGLESS_REQUIREMENT.pattern == shared.MEANINGLESS_REQUIREMENT.pattern
