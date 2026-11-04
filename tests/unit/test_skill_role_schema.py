"""Tests for the skill role frontmatter contract (ADR-0028).

`role.boundaries.owns` / `not_owns` are path lists consumed by external
agents (e.g. the opencode build-agent role matrix). A parenthetical note
inside the string makes the entry unusable as a glob — the note becomes
part of the path.

Contract:
  - entries are bare globs (no `(...)` notes)
  - the `<name>` / `<change>` placeholders are equivalent
  - every shipped skill frontmatter validates against the schema
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import jsonschema
import pytest
import yaml

SCHEMA_PATH = Path("_lib/schemas/skill_role_schema.json")
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
SKILLS_DIR = Path("skills")


def _role(owns, not_owns=("x",)):
    return {
        "title": "T",
        "perspective": "p",
        "boundaries": {
            "owns": list(owns),
            "not_owns": list(not_owns),
            "human_involvement": "low",
        },
    }


def test_owns_with_parenthetical_note_is_rejected():
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            _role(["openspec/changes/<name>/proposal.md (per ADR-0025)"]), SCHEMA
        )


def test_not_owns_with_parenthetical_note_is_rejected():
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            _role(["a.md"], not_owns=["b.md (rdd-quick owns)"]), SCHEMA
        )


@pytest.mark.parametrize(
    "entry",
    [
        "openspec/changes/<name>/{tasks,design}.md",
        "docs/adr/ADR-*.md",
        ".rddf/wt/<name>/",
        "openspec/specs/<name>/spec.md",
        ".rddf/plans/quick-*.md",
    ],
)
def test_valid_globs_are_accepted(entry):
    jsonschema.validate(_role([entry]), SCHEMA)


def _frontmatters():
    for p in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        text = p.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue
        try:
            data = yaml.safe_load(text.split("---\n", 2)[1])
        except yaml.YAMLError:
            continue
        role = (data or {}).get("role")
        if role:
            yield p.parent.name, role


def test_all_shipped_skill_frontmatters_pass_schema():
    roles = list(_frontmatters())
    assert roles, "no skill frontmatter with a role: block found"
    for name, role in roles:
        jsonschema.validate(role, SCHEMA)


def test_no_skill_owns_entry_contains_parentheses():
    """Guards the contract without relying on the schema being loaded."""
    offenders = []
    for name, role in _frontmatters():
        for key in ("owns", "not_owns"):
            for entry in role["boundaries"].get(key, []):
                if re.search(r"[()]", entry):
                    offenders.append(f"{name}.{key}: {entry}")
    assert not offenders, f"parenthetical notes found: {offenders}"


def test_placeholders_are_consistent():
    """`<change>` and `<name>` are equivalent — a mixed vocabulary defeats
    automated path matching."""
    offenders = []
    for name, role in _frontmatters():
        for key in ("owns", "not_owns"):
            for entry in role["boundaries"].get(key, []):
                if "<change>" in entry:
                    offenders.append(f"{name}.{key}: {entry}")
    assert not offenders, f"non-canonical placeholder found: {offenders}"
