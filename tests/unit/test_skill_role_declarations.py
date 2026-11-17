"""Author-declaration tests for skill role boundaries.

ADR-0028 / `openspec/specs/skill-role-model/spec.md` established two rules:

  1. `role.boundaries.owns` MUST NOT list an artifact the skill does not
     produce (the `design.md` precedent: the builder phase skill's script
     never writes it, so owns must not claim it — but the SKILL.md body MUST
     say who authors it).
  2. `role.boundaries.owns` MUST match the "职责边界" section of the body.

Three paths are owned by the **opencode build-agent role layer**, not by any
rdd-workflow skill:

  - `.rddf/reviews/**`        — verification / review reports (verifier role,
                                 architect role)
  - `.rddf/config/arch-docs.json` — the architect role's scope config

rdd-workflow code never reads or writes them. So the skills must NOT claim
them in `owns` — and they MUST declare, in the body, that those paths are
authored by the agent role layer.

CHANGED 2026-11-17: added by the doc-alignment change (audit P1-2 / P1-3
re-scoped from "add to owns" to "declare the author in the body").
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RDD_VERIFIER_SKILL = PROJECT_ROOT / "skills" / "rdd-verifier" / "SKILL.md"
RDD_ARCH_SKILL = PROJECT_ROOT / "skills" / "rdd-arch" / "SKILL.md"

ROLE_LAYER_PATHS = [
    ".rddf/reviews/",
    ".rddf/config/arch-docs.json",
]


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, f"{path} has no YAML frontmatter"
    return yaml.safe_load(m.group(1))


def _owns(path: Path) -> list[str]:
    role = _frontmatter(path).get("role") or {}
    return list((role.get("boundaries") or {}).get("owns") or [])


def test_rdd_verifier_does_not_claim_role_layer_paths():
    """The verification report is the verifier *role's* product, not the skill's."""
    owns = _owns(RDD_VERIFIER_SKILL)
    assert not any(p.startswith(".rddf/reviews") for p in owns), owns
    assert ".rddf/config/arch-docs.json" not in owns, owns


def test_rdd_arch_does_not_claim_role_layer_paths():
    """`arch-docs.json` and ADR review reports belong to the architect role layer."""
    owns = _owns(RDD_ARCH_SKILL)
    assert not any(p.startswith(".rddf/reviews") for p in owns), owns
    assert not any(p.startswith(".rddf/config") for p in owns), owns


def test_rdd_verifier_declares_the_product_landing_point_author():
    """The body must say who writes the report — otherwise the two-layer model
    has no anchor on the skill side (the `design.md` precedent)."""
    text = RDD_VERIFIER_SKILL.read_text(encoding="utf-8")
    assert ".rddf/reviews/" in text, "rdd-verifier body never mentions the product landing point"
    # must attribute the authorship to the agent layer, not claim it itself
    assert re.search(r"(agent|角色层|executing|auditing)", text), \
        "rdd-verifier body does not attribute the report to the agent layer"


def test_rdd_arch_declares_the_role_layer_author():
    """rdd-arch body must declare that scope config / review reports are role-level."""
    text = RDD_ARCH_SKILL.read_text(encoding="utf-8")
    assert ".rddf/config/arch-docs.json" in text, \
        "rdd-arch body never mentions arch-docs.json"
    assert ".rddf/reviews/" in text, \
        "rdd-arch body never mentions the ADR review report landing point"
    assert re.search(r"(agent|角色层|role)", text), \
        "rdd-arch body does not attribute those paths to the agent role layer"
