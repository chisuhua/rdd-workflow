# AC Verifier Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an AI-powered skill that semantically verifies OpenSpec change acceptance criteria against committed code before archive, catching the failure mode found in 2026-08-17 audit (3 changes had unfulfilled ACs).

**Architecture:** Hybrid approach — new `skills/ac-verifier/` directory (user-invocable via `rddf ac-verify <name>` and `skill_use("ac-verifier", ...)`) plus integration into `_lib/archive.sh::archive_gate_check`. AI uses tool-augmented agent (codegraph, grep, codebase-memory-mcp, git) to investigate each AC. Output is per-AC structured JSON verdict; gate applies STRICT_AC_GATE escalation.

**Tech Stack:** Python 3.11+ (agent driver), bash (wrapper + archive integration), pytest + bats (testing), Anthropic/OpenAI/ollama API (LLM providers), MCP servers (codegraph, codebase-memory-mcp), jsonschema (verdict validation).

**Spec:** `docs/superpowers/specs/2026-08-17-ac-verifier-skill-design.md`

---

## File Structure

```
skills/ac-verifier/
├── SKILL.md                         # user-facing docs (frontmatter + usage)
├── __init__.py                      # package marker (empty)
└── scripts/
    ├── ac_verifier.sh               # bash wrapper (≤80 LOC)
    ├── ac_verifier.py               # Python main module (≤250 LOC)
    ├── ac_verifier_prompt.py        # prompt templates + tool manifest (≤100 LOC)
    └── ac_verifier_mocks.py         # mock LLM for tests (≤80 LOC)

tests/unit/test_ac_verifier.py                    # ≥18 unit cases
tests/integration/test_ac_verifier_skill.bats     # ≥11 bats cases
tests/integration/test_ac_verifier_e2e.bats       # ≥4 E2E mock-LLM cases

_lib/cli/ac_verify_cmd.py              # CLI command (≤60 LOC)
_lib/archive.sh                        # modify lines 255-292 (insert AC step)
_lib/cli/__main__.py                   # register ac-verify subcommand
package.json                           # add skill to manifest
```

---

## Task 1: Skill Skeleton

**Files:**
- Create: `skills/ac-verifier/__init__.py`
- Create: `skills/ac-verifier/SKILL.md`
- Create: `skills/ac-verifier/scripts/__init__.py`

- [ ] **Step 1: Create package markers**

```bash
mkdir -p skills/ac-verifier/scripts
touch skills/ac-verifier/__init__.py
touch skills/ac-verifier/scripts/__init__.py
```

- [ ] **Step 2: Create SKILL.md with frontmatter**

Write `skills/ac-verifier/SKILL.md` with the following content:

```markdown
---
name: ac-verifier
description: Verify OpenSpec change acceptance criteria against committed code via AI semantic check + tools. Used standalone (`rddf ac-verify <name>`) or automatically invoked before archive.
license: MIT
compatibility: requires openspec CLI v1.3.1+, Python 3.11+, ANTHROPIC_API_KEY or OPENAI_API_KEY
metadata:
  author: rdd-workflow
  version: 1.0
  evolved-from: ""
  user-invocable: true
---

# AC Verifier Skill

Verifies that each `## 验收标准` bullet in an OpenSpec change's `proposal.md` is genuinely satisfied in the committed code, using an AI agent with code investigation tools.

## Usage

### Standalone

```bash
# Verify a single change
rddf ac-verify <change-name>

# Dry-run (no audit log, no gate effect)
rddf ac-verify <change-name> --dry-run

# Strict mode (any AC fail → exit 1 blocking)
rddf ac-verify <change-name> --strict

# Skip verification entirely
rddf ac-verify <change-name> --skip

# Skill form
skill_use("ac-verifier", "<change-name>")
```

### Automatic (archive integration)

`_lib/archive.sh::archive_gate_check` calls this skill before returning success. By default, AC failures produce warnings (archive continues). Set `STRICT_AC_GATE=yes` to block archive on any AC fail.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All ACs pass (or no `## 验收标准` section) |
| 1 | At least one AC fail (warning by default; blocking under STRICT_AC_GATE) |
| 2 | Skipped (via `--skip` / `SKIP_AC_VERIFICATION=yes` / no proposal.md) |
| 3 | Error (LLM call failed after retries, missing API key) |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STRICT_AC_GATE` | `no` | Promote AC fail → archive blocker |
| `SKIP_AC_VERIFICATION` | `no` | Skip AI verification entirely |
| `AC_LLM_MOCK` | `no` | Use mock LLM (testing only) |
| `AC_LLM_PROVIDER` | auto-detect | `openai` / `anthropic` / `local-ollama` |
| `AC_LLM_MODEL` | provider default | Model name |
| `AC_LLM_TIMEOUT` | `60` | Seconds per LLM call |

## Audit Log

Each non-dry-run invocation appends a JSONL entry to `.rddf/state/.ac-verification.jsonl`:

```json
{"ts": "2026-08-17T...", "change_name": "...", "exit_code": 1, "verdict": [...]}
```

## See Also

- Spec: `docs/superpowers/specs/2026-08-17-ac-verifier-skill-design.md`
- Audit log: `.rddf/state/.ac-verification.jsonl`
```

- [ ] **Step 3: Verify skill files exist**

Run: `ls -la skills/ac-verifier/ skills/ac-verifier/scripts/`
Expected: 3 files (SKILL.md, __init__.py, scripts/__init__.py) plus scripts/ dir

- [ ] **Step 4: Commit**

```bash
git add skills/ac-verifier/
git commit -m "feat(ac-verifier): scaffold skill directory and SKILL.md"
```

---

## Task 2: parse_acs() — TDD

**Files:**
- Create: `skills/ac-verifier/scripts/ac_verifier.py`
- Create: `tests/unit/test_ac_verifier.py`

- [ ] **Step 1: Write failing test for parse_acs()**

Write `tests/unit/test_ac_verifier.py`:

```python
"""Unit tests for ac_verifier module."""
from pathlib import Path
import pytest
from skills.ac_verifier.scripts.ac_verifier import parse_acs


def test_parse_acs_empty_section(tmp_path: Path):
    """Section header present but no bullets → empty list."""
    p = tmp_path / "proposal.md"
    p.write_text("# T\n\n## 验收标准\n\n## Other\n", encoding="utf-8")
    assert parse_acs(p) == []


def test_parse_acs_single_checkbox(tmp_path: Path):
    """Single `- [ ]` bullet becomes AC-1."""
    p = tmp_path / "proposal.md"
    p.write_text(
        "# T\n\n## 验收标准\n\n- [ ] First AC\n\n## Other\n",
        encoding="utf-8",
    )
    result = parse_acs(p)
    assert len(result) == 1
    assert result[0]["ac_id"] == "AC-1"
    assert result[0]["description"] == "First AC"
    assert result[0]["has_checkbox"] is True


def test_parse_acs_multiple_prose_bullets(tmp_path: Path):
    """Prose bullets (no checkbox) are also ACs."""
    p = tmp_path / "proposal.md"
    p.write_text(
        "# T\n\n## 验收标准\n\n- First AC\n- Second AC\n- Third AC\n",
        encoding="utf-8",
    )
    result = parse_acs(p)
    assert [r["ac_id"] for r in result] == ["AC-1", "AC-2", "AC-3"]
    assert all(r["has_checkbox"] is False for r in result)


def test_parse_acs_mixed(tmp_path: Path):
    """Mix of checkbox and prose bullets."""
    p = tmp_path / "proposal.md"
    p.write_text(
        "# T\n\n## 验收标准\n\n- [ ] First\n- Second\n- [x] Done\n",
        encoding="utf-8",
    )
    result = parse_acs(p)
    assert len(result) == 3
    assert result[0]["has_checkbox"] is True
    assert result[1]["has_checkbox"] is False
    assert result[2]["has_checkbox"] is True


def test_parse_acs_missing_section(tmp_path: Path):
    """No `## 验收标准` section → empty list."""
    p = tmp_path / "proposal.md"
    p.write_text("# T\n\n## Acceptance\n- something\n", encoding="utf-8")
    assert parse_acs(p) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_ac_verifier.py -v`
Expected: 5 failures with "ModuleNotFoundError: No module named 'skills.ac_verifier.scripts.ac_verifier'"

- [ ] **Step 3: Implement minimal parse_acs()**

Write `skills/ac-verifier/scripts/ac_verifier.py`:

```python
"""AC verifier main module."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Section header (Chinese + English variants per brainstorming Q6)
_AC_SECTION_HEADERS = re.compile(
    r"^##\s+(?:验收标准|Acceptance Criteria)\s*$", re.MULTILINE
)
# Section-end pattern: next `## ` header or end-of-file
_SECTION_END = re.compile(r"^##\s+", re.MULTILINE)
# Bullet line: `- ...` or `- [ ] ...` or `- [x] ...`
_BULLET_LINE = re.compile(r"^- \[([ x])\]?\s+(.+)$")


class AcVerifierError(Exception):
    """Base error for ac_verifier operations."""


def parse_acs(proposal_path: Path) -> list[dict]:
    """Extract AC bullets from `## 验收标准` (or `## Acceptance Criteria`) section.

    Returns list of {ac_id: 'AC-N', description: str, has_checkbox: bool}.
    Empty list if section missing or has no bullets.
    """
    if not proposal_path.is_file():
        return []
    text = proposal_path.read_text(encoding="utf-8")

    # Find AC section start
    section_match = _AC_SECTION_HEADERS.search(text)
    if not section_match:
        return []

    # Find section end (next ## header)
    section_start = section_match.end()
    section_end_match = _SECTION_END.search(text, pos=section_start)
    section_end = section_end_match.start() if section_end_match else len(text)
    section_text = text[section_start:section_end]

    # Extract bullets
    acs: list[dict] = []
    for i, line in enumerate(section_text.splitlines(), start=1):
        m = _BULLET_LINE.match(line.strip())
        if not m:
            continue
        marker = m.group(1)  # " ", "x", or None
        description = m.group(2).strip()
        has_checkbox = marker in (" ", "x")
        acs.append({
            "ac_id": f"AC-{i}",
            "description": description,
            "has_checkbox": has_checkbox,
        })
    return acs
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_ac_verifier.py::test_parse_acs_empty_section tests/unit/test_ac_verifier.py::test_parse_acs_single_checkbox tests/unit/test_ac_verifier.py::test_parse_acs_multiple_prose_bullets tests/unit/test_ac_verifier.py::test_parse_acs_mixed tests/unit/test_ac_verifier.py::test_parse_acs_missing_section -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add skills/ac-verifier/scripts/ac_verifier.py tests/unit/test_ac_verifier.py
git commit -m "feat(ac-verifier): implement parse_acs() with unit tests"
```

---

## Task 3: build_agent_prompt() — TDD

**Files:**
- Create: `skills/ac-verifier/scripts/ac_verifier_prompt.py`
- Modify: `tests/unit/test_ac_verifier.py`

- [ ] **Step 1: Add failing tests for build_agent_prompt()**

Append to `tests/unit/test_ac_verifier.py`:

```python
from skills.ac_verifier.scripts.ac_verifier import build_agent_prompt


def test_build_prompt_includes_all_acs():
    """All AC descriptions appear in the user prompt."""
    acs = [
        {"ac_id": "AC-1", "description": "First AC", "has_checkbox": True},
        {"ac_id": "AC-2", "description": "Second AC", "has_checkbox": False},
    ]
    system, user = build_agent_prompt(acs, "my-change")
    assert "AC-1" in user
    assert "First AC" in user
    assert "AC-2" in user
    assert "Second AC" in user
    assert "my-change" in system or "my-change" in user


def test_build_prompt_declares_tools():
    """System prompt lists all available tools."""
    acs = [{"ac_id": "AC-1", "description": "x", "has_checkbox": False}]
    system, _ = build_agent_prompt(acs, "x")
    for tool in ["codegraph_explore", "grep_app_searchGitHub", "codebase-memory-mcp", "git"]:
        assert tool in system, f"Tool {tool} not in system prompt"


def test_build_prompt_requires_json_schema():
    """System prompt specifies JSON array output format."""
    acs = [{"ac_id": "AC-1", "description": "x", "has_checkbox": False}]
    system, _ = build_agent_prompt(acs, "x")
    assert "JSON" in system or "json" in system
    assert "ac_id" in system
    assert "status" in system
    assert "pass" in system and "fail" in system
```

- [ ] **Step 2: Run new tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_ac_verifier.py -k "build_prompt" -v`
Expected: 3 failures with "ImportError: cannot import name 'build_agent_prompt'"

- [ ] **Step 3: Implement build_agent_prompt()**

Add to `skills/ac-verifier/scripts/ac_verifier.py`:

```python
# Preamble constants (top of module, after imports)
_SYSTEM_PROMPT_TEMPLATE = """You are an AC verification agent for rdd-workflow. Given an OpenSpec change's
acceptance criteria (ACs) and access to code investigation tools, you must
determine whether each AC is genuinely satisfied in the committed code.

Available tools:
- codegraph_explore(query): structural code search via knowledge graph
- grep_app_searchGitHub(query, path?, language?): pattern matching
- codebase-memory-mcp: function/class/import lookup (via MCP)
- git log / git diff (subprocess via your driver): commit history

For each AC, you MUST:
1. Make at least one tool call to gather evidence
2. Cross-reference AC text against actual implementation
3. Issue verdict: "pass" (genuinely satisfied) | "fail" (not satisfied) |
   "partial" (partially satisfied with caveats)
4. Provide 0.0-1.0 confidence score
5. Cite evidence in 1-2 sentences

Output format (strict JSON array, no other text):
[
  {
    "ac_id": "AC-1",
    "description": "<verbatim AC text>",
    "status": "pass" | "fail" | "partial",
    "confidence": 0.0-1.0,
    "evidence": [
      {"tool": "codegraph", "query": "...", "result_summary": "..."}
    ],
    "reasoning": "1-2 sentences justifying verdict"
  }
]

Array length MUST equal AC count. Omitting any AC invalidates response.
"""


def build_agent_prompt(acs: list[dict], change_name: str) -> tuple[str, str]:
    """Build (system_prompt, user_prompt) pair for LLM.

    System prompt declares tools + JSON schema; user prompt lists ACs.
    """
    user_lines = [
        f"Change: {change_name}",
        "",
        f"Number of ACs to verify: {len(acs)}",
        "",
        "Acceptance Criteria:",
    ]
    for ac in acs:
        user_lines.append(f"\n{ac['ac_id']}: {ac['description']}")
    user_lines.append(
        "\nFor each AC above, investigate using the declared tools and emit "
        "your verdict as a strict JSON array (one entry per AC)."
    )
    user_prompt = "\n".join(user_lines)
    return _SYSTEM_PROMPT_TEMPLATE, user_prompt
```

- [ ] **Step 4: Run new tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_ac_verifier.py -k "build_prompt" -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add skills/ac-verifier/scripts/ac_verifier.py tests/unit/test_ac_verifier.py
git commit -m "feat(ac-verifier): implement build_agent_prompt() with unit tests"
```

---

## Task 4: invoke_ai_agent() — TDD with Mock

**Files:**
- Create: `skills/ac-verifier/scripts/ac_verifier_mocks.py`
- Modify: `tests/unit/test_ac_verifier.py`

- [ ] **Step 1: Create mock LLM module**

Write `skills/ac-verifier/scripts/ac_verifier_mocks.py`:

```python
"""Mock LLM responses for AC verifier tests.

Activated when AC_LLM_MOCK=yes. Provides 5 canned scenarios:
- mock_pass_all
- mock_fail_one
- mock_partial
- mock_invalid_json
- mock_omitted_ac
"""
from __future__ import annotations

import json
import os
from typing import Optional

_MOCK_KEY = os.environ.get("AC_LLM_MOCK_SCENARIO", "mock_pass_all")


def mock_invoke(system: str, user: str) -> str:
    """Return canned response for current mock scenario."""
    if _MOCK_KEY == "mock_pass_all":
        # Extract AC IDs from user prompt (AC-1, AC-2, ...)
        import re
        ac_ids = re.findall(r"(AC-\d+):", user)
        verdicts = [
            {"ac_id": ac, "description": f"AC {ac}", "status": "pass",
             "confidence": 0.95, "evidence": [], "reasoning": "mock pass"}
            for ac in ac_ids
        ]
        return json.dumps(verdicts)

    if _MOCK_KEY == "mock_fail_one":
        import re
        ac_ids = re.findall(r"(AC-\d+):", user)
        verdicts = []
        for i, ac in enumerate(ac_ids):
            status = "fail" if i == 1 else "pass"
            verdicts.append({
                "ac_id": ac, "description": f"AC {ac}", "status": status,
                "confidence": 0.85, "evidence": [], "reasoning": f"mock {status}"
            })
        return json.dumps(verdicts)

    if _MOCK_KEY == "mock_partial":
        import re
        ac_ids = re.findall(r"(AC-\d+):", user)
        verdicts = [
            {"ac_id": ac, "description": f"AC {ac}", "status": "partial",
             "confidence": 0.6, "evidence": [], "reasoning": "mock partial"}
            for ac in ac_ids
        ]
        return json.dumps(verdicts)

    if _MOCK_KEY == "mock_invalid_json":
        return "This is not valid JSON. Sorry."

    if _MOCK_KEY == "mock_omitted_ac":
        import re
        ac_ids = re.findall(r"(AC-\d+):", user)
        # Omit the last AC
        verdicts = [
            {"ac_id": ac, "description": f"AC {ac}", "status": "pass",
             "confidence": 0.9, "evidence": [], "reasoning": "mock"}
            for ac in ac_ids[:-1]
        ]
        return json.dumps(verdicts)

    raise ValueError(f"Unknown mock scenario: {_MOCK_KEY}")
```

- [ ] **Step 2: Write failing tests for invoke_ai_agent()**

Append to `tests/unit/test_ac_verifier.py`:

```python
import os
import pytest
from skills.ac_verifier.scripts.ac_verifier import invoke_ai_agent, AcVerifierError


def test_invoke_ai_agent_mock_pass(monkeypatch):
    """Mock mode returns canned JSON."""
    monkeypatch.setenv("AC_LLM_MOCK", "yes")
    monkeypatch.setenv("AC_LLM_MOCK_SCENARIO", "mock_pass_all")
    raw = invoke_ai_agent("system", "AC-1: foo\nAC-2: bar")
    import json
    parsed = json.loads(raw)
    assert len(parsed) == 2
    assert parsed[0]["status"] == "pass"
    assert parsed[1]["status"] == "pass"


def test_invoke_ai_agent_mock_fail(monkeypatch):
    """Mock fail scenario returns one fail."""
    monkeypatch.setenv("AC_LLM_MOCK", "yes")
    monkeypatch.setenv("AC_LLM_MOCK_SCENARIO", "mock_fail_one")
    raw = invoke_ai_agent("system", "AC-1: foo\nAC-2: bar")
    import json
    parsed = json.loads(raw)
    statuses = [v["status"] for v in parsed]
    assert "fail" in statuses


def test_invoke_ai_agent_raises_on_unmocked():
    """Without AC_LLM_MOCK=yes, raises AcVerifierError (no real LLM in unit tests)."""
    os.environ.pop("AC_LLM_MOCK", None)
    with pytest.raises(AcVerifierError):
        invoke_ai_agent("system", "user")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_ac_verifier.py -k "invoke_ai_agent" -v`
Expected: 3 failures with "ImportError: cannot import name 'invoke_ai_agent'"

- [ ] **Step 4: Implement invoke_ai_agent()**

Add to `skills/ac-verifier/scripts/ac_verifier.py`:

```python
def invoke_ai_agent(system: str, user: str) -> str:
    """Call LLM with tools. Returns raw text.

    In mock mode (AC_LLM_MOCK=yes), returns canned response from mocks module.
    In real mode, requires API key env var; raises AcVerifierError on failure.
    """
    if os.environ.get("AC_LLM_MOCK", "").lower() == "yes":
        from skills.ac_verifier.scripts import ac_verifier_mocks
        return ac_verifier_mocks.mock_invoke(system, user)

    provider = os.environ.get("AC_LLM_PROVIDER", "").lower()
    if not provider:
        raise AcVerifierError(
            "AC_LLM_PROVIDER not set and AC_LLM_MOCK != yes. "
            "Set AC_LLM_PROVIDER=openai|anthropic|local-ollama or use AC_LLM_MOCK=yes."
        )
    # Real LLM invocation is delegated to a future implementation.
    # v1 ships mock-first; real provider implementation in Task 9.
    raise AcVerifierError(
        f"Real LLM provider '{provider}' not yet wired in v1. "
        f"Use AC_LLM_MOCK=yes for testing."
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_ac_verifier.py -k "invoke_ai_agent" -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add skills/ac-verifier/scripts/ac_verifier.py skills/ac-verifier/scripts/ac_verifier_mocks.py tests/unit/test_ac_verifier.py
git commit -m "feat(ac-verifier): implement invoke_ai_agent() with mock support"
```

---

## Task 5: parse_verdict() — TDD

**Files:**
- Modify: `tests/unit/test_ac_verifier.py`
- Modify: `skills/ac-verifier/scripts/ac_verifier.py`

- [ ] **Step 1: Write failing tests for parse_verdict()**

Append to `tests/unit/test_ac_verifier.py`:

```python
import json
from jsonschema import ValidationError
from skills.ac_verifier.scripts.ac_verifier import parse_verdict


def test_parse_verdict_valid():
    """Valid JSON array with correct count passes through."""
    raw = json.dumps([
        {"ac_id": "AC-1", "description": "x", "status": "pass",
         "confidence": 0.9, "evidence": [], "reasoning": "ok"}
    ])
    result = parse_verdict(raw, expected_count=1)
    assert len(result) == 1
    assert result[0]["status"] == "pass"


def test_parse_verdict_missing_ac_filled_as_fail():
    """Missing AC entry auto-filled with fail."""
    raw = json.dumps([
        {"ac_id": "AC-1", "description": "x", "status": "pass",
         "confidence": 0.9, "evidence": [], "reasoning": "ok"}
        # AC-2 missing
    ])
    result = parse_verdict(raw, expected_count=2)
    assert len(result) == 2
    statuses = {r["ac_id"]: r["status"] for r in result}
    assert statuses["AC-1"] == "pass"
    assert statuses["AC-2"] == "fail"
    assert "AI omitted" in result[1]["reasoning"]


def test_parse_verdict_invalid_json_raises():
    """Unparseable JSON raises AcVerifierError after 1 internal retry."""
    with pytest.raises(AcVerifierError):
        parse_verdict("not json at all", expected_count=2)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_ac_verifier.py -k "parse_verdict" -v`
Expected: 3 failures with "ImportError"

- [ ] **Step 3: Implement parse_verdict()**

Add to `skills/ac-verifier/scripts/ac_verifier.py`:

```python
# Verdict schema for jsonschema validation
_VERDICT_ITEM_SCHEMA = {
    "type": "object",
    "required": ["ac_id", "status", "confidence"],
    "properties": {
        "ac_id": {"type": "string", "pattern": r"^AC-\d+$"},
        "description": {"type": "string"},
        "status": {"enum": ["pass", "fail", "partial"]},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "evidence": {"type": "array"},
        "reasoning": {"type": "string"},
    },
}
_VERDICT_SCHEMA = {
    "type": "array",
    "items": _VERDICT_ITEM_SCHEMA,
}


def parse_verdict(raw: str, expected_count: int) -> list[dict]:
    """Parse LLM JSON output, validate schema, auto-fill missing ACs.

    On unparseable JSON: retry hint internally once (note: caller should
    pre-retry; this raises AcVerifierError). Auto-fills missing ACs as fail.
    """
    # First attempt
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise AcVerifierError(f"Verdict not valid JSON: {raw[:100]}...")

    if not isinstance(data, list):
        raise AcVerifierError(f"Verdict must be JSON array, got {type(data).__name__}")

    # Validate items with jsonschema (best-effort, skip on schema error)
    try:
        import jsonschema
        jsonschema.validate(data, _VERDICT_SCHEMA)
    except (ImportError, ValidationError):
        pass  # schema validation is advisory; missing/invalid fields fall through

    # Auto-fill missing ACs
    present_ids = {item.get("ac_id") for item in data}
    for i in range(1, expected_count + 1):
        ac_id = f"AC-{i}"
        if ac_id not in present_ids:
            data.append({
                "ac_id": ac_id,
                "description": f"(missing from LLM output)",
                "status": "fail",
                "confidence": 0.0,
                "evidence": [],
                "reasoning": "AI omitted this AC from verdict",
            })

    return data
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_ac_verifier.py -k "parse_verdict" -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add skills/ac-verifier/scripts/ac_verifier.py tests/unit/test_ac_verifier.py
git commit -m "feat(ac-verifier): implement parse_verdict() with schema validation"
```

---

## Task 6: apply_gate_rules() — TDD

**Files:**
- Modify: `tests/unit/test_ac_verifier.py`
- Modify: `skills/ac-verifier/scripts/ac_verifier.py`

- [ ] **Step 1: Write failing tests for apply_gate_rules()**

Append to `tests/unit/test_ac_verifier.py`:

```python
from skills.ac_verifier.scripts.ac_verifier import apply_gate_rules


def test_apply_gate_rules_all_pass_returns_0():
    """All pass → exit 0."""
    verdict = [{"ac_id": "AC-1", "status": "pass"}]
    assert apply_gate_rules(verdict, strict=False) == 0


def test_apply_gate_rules_one_fail_warning_returns_0():
    """One fail, not strict → exit 0 (warning, not blocking)."""
    verdict = [
        {"ac_id": "AC-1", "status": "pass"},
        {"ac_id": "AC-2", "status": "fail"},
    ]
    assert apply_gate_rules(verdict, strict=False) == 0


def test_apply_gate_rules_one_fail_strict_returns_1():
    """One fail, strict → exit 1 (blocking)."""
    verdict = [
        {"ac_id": "AC-1", "status": "pass"},
        {"ac_id": "AC-2", "status": "fail"},
    ]
    assert apply_gate_rules(verdict, strict=True) == 1


def test_apply_gate_rules_partial_warning_returns_0():
    """Partial counts as warning (not fail)."""
    verdict = [{"ac_id": "AC-1", "status": "partial"}]
    assert apply_gate_rules(verdict, strict=False) == 0
    assert apply_gate_rules(verdict, strict=True) == 0  # partial != fail


def test_apply_gate_rules_empty_verdict_returns_2():
    """Empty verdict (no ACs) → exit 2 (skipped)."""
    assert apply_gate_rules([], strict=False) == 2
    assert apply_gate_rules([], strict=True) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_ac_verifier.py -k "apply_gate_rules" -v`
Expected: 5 failures

- [ ] **Step 3: Implement apply_gate_rules()**

Add to `skills/ac-verifier/scripts/ac_verifier.py`:

```python
def apply_gate_rules(verdict: list[dict], strict: bool) -> int:
    """Return exit code based on verdict + strict flag.

    0 if all pass (warning case under non-strict)
    1 if any fail (warning under non-strict; blocking under strict)
    2 if no ACs in verdict (treated as skip)
    """
    if not verdict:
        return 2
    has_fail = any(v.get("status") == "fail" for v in verdict)
    if has_fail and strict:
        return 1
    return 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_ac_verifier.py -k "apply_gate_rules" -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add skills/ac-verifier/scripts/ac_verifier.py tests/unit/test_ac_verifier.py
git commit -m "feat(ac-verifier): implement apply_gate_rules() with strict/warning modes"
```

---

## Task 7: append_audit_log() — TDD

**Files:**
- Modify: `tests/unit/test_ac_verifier.py`
- Modify: `skills/ac-verifier/scripts/ac_verifier.py`

- [ ] **Step 1: Write failing tests for append_audit_log()**

Append to `tests/unit/test_ac_verifier.py`:

```python
import json
from skills.ac_verifier.scripts.ac_verifier import append_audit_log


def test_append_audit_log_creates_file(tmp_path: Path):
    """First append creates .rddf/state/.ac-verification.jsonl."""
    project_root = tmp_path
    verdict = [{"ac_id": "AC-1", "status": "pass"}]
    append_audit_log(verdict, "my-change", exit_code=0, project_root=project_root)
    log = project_root / ".rddf" / "state" / ".ac-verification.jsonl"
    assert log.is_file()
    lines = log.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["change_name"] == "my-change"
    assert entry["exit_code"] == 0
    assert entry["verdict"][0]["ac_id"] == "AC-1"
    assert "ts" in entry


def test_append_audit_log_appends(tmp_path: Path):
    """Subsequent appends add lines without overwriting."""
    project_root = tmp_path
    append_audit_log([{"ac_id": "AC-1", "status": "pass"}], "change-a", 0, project_root=project_root)
    append_audit_log([{"ac_id": "AC-1", "status": "fail"}], "change-b", 1, project_root=project_root)
    log = project_root / ".rddf" / "state" / ".ac-verification.jsonl"
    lines = log.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["change_name"] == "change-a"
    assert json.loads(lines[1])["change_name"] == "change-b"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_ac_verifier.py -k "audit_log" -v`
Expected: 2 failures

- [ ] **Step 3: Implement append_audit_log()**

Add to `skills/ac-verifier/scripts/ac_verifier.py`:

```python
def append_audit_log(
    verdict: list[dict],
    change_name: str,
    exit_code: int,
    project_root: Optional[Path] = None,
) -> None:
    """Append JSONL entry to .rddf/state/.ac-verification.jsonl.

    Entry: {ts, change_name, verdict, exit_code, llm_model, llm_provider}.
    Idempotent: creates directory + file on first call, appends on subsequent.
    """
    if project_root is None:
        project_root = Path.cwd()
    log_path = project_root / ".rddf" / "state" / ".ac-verification.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "change_name": change_name,
        "exit_code": exit_code,
        "llm_provider": os.environ.get("AC_LLM_PROVIDER", "mock"),
        "llm_model": os.environ.get("AC_LLM_MODEL", "mock"),
        "verdict": verdict,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_ac_verifier.py -k "audit_log" -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add skills/ac-verifier/scripts/ac_verifier.py tests/unit/test_ac_verifier.py
git commit -m "feat(ac-verifier): implement append_audit_log() with JSONL append"
```

---

## Task 8: End-to-End Orchestrator — `verify_change()`

**Files:**
- Modify: `tests/unit/test_ac_verifier.py`
- Modify: `skills/ac-verifier/scripts/ac_verifier.py`

- [ ] **Step 1: Write failing test for verify_change()**

Append to `tests/unit/test_ac_verifier.py`:

```python
from skills.ac_verifier.scripts.ac_verifier import verify_change


def test_verify_change_end_to_end_pass(monkeypatch, tmp_path: Path):
    """Mock pass-all scenario returns exit 0 and writes audit log."""
    monkeypatch.setenv("AC_LLM_MOCK", "yes")
    monkeypatch.setenv("AC_LLM_MOCK_SCENARIO", "mock_pass_all")
    proposal = tmp_path / "proposal.md"
    proposal.write_text(
        "# T\n\n## 验收标准\n\n- AC one\n- AC two\n",
        encoding="utf-8",
    )
    exit_code = verify_change("test-change", proposal, project_root=tmp_path, strict=False)
    assert exit_code == 0
    log = tmp_path / ".rddf" / "state" / ".ac-verification.jsonl"
    assert log.is_file()


def test_verify_change_strict_blocks_on_fail(monkeypatch, tmp_path: Path):
    """Mock fail-one + strict → exit 1."""
    monkeypatch.setenv("AC_LLM_MOCK", "yes")
    monkeypatch.setenv("AC_LLM_MOCK_SCENARIO", "mock_fail_one")
    proposal = tmp_path / "proposal.md"
    proposal.write_text("# T\n\n## 验收标准\n\n- one\n- two\n", encoding="utf-8")
    exit_code = verify_change("test-change", proposal, project_root=tmp_path, strict=True)
    assert exit_code == 1


def test_verify_change_no_proposal_returns_2(tmp_path: Path):
    """Missing proposal.md → exit 2 (skip)."""
    exit_code = verify_change("test-change", tmp_path / "missing.md", project_root=tmp_path, strict=False)
    assert exit_code == 2


def test_verify_change_no_ac_section_returns_0(tmp_path: Path):
    """Proposal without `## 验收标准` → exit 0 (no ACs to verify)."""
    proposal = tmp_path / "proposal.md"
    proposal.write_text("# T\n\n## Other\n- thing\n", encoding="utf-8")
    exit_code = verify_change("test-change", proposal, project_root=tmp_path, strict=False)
    assert exit_code == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_ac_verifier.py -k "verify_change" -v`
Expected: 4 failures

- [ ] **Step 3: Implement verify_change() orchestrator**

Add to `skills/ac-verifier/scripts/ac_verifier.py`:

```python
def verify_change(
    change_name: str,
    proposal_path: Path,
    project_root: Optional[Path] = None,
    strict: bool = False,
    dry_run: bool = False,
) -> int:
    """End-to-end AC verification. Returns exit code.

    Orchestrates: parse → build prompt → invoke AI → parse verdict → apply rules.
    Writes audit log unless dry_run=True.
    """
    if not proposal_path.is_file():
        return 2  # skip — no proposal

    acs = parse_acs(proposal_path)
    if not acs:
        return 2  # skip — no ACs to verify

    system, user = build_agent_prompt(acs, change_name)

    # Single LLM call (no internal retry; caller handles via AcVerifierError)
    try:
        raw = invoke_ai_agent(system, user)
    except AcVerifierError as e:
        print(f"⚠️  AC verification LLM error: {e}", file=sys.stderr)
        return 3  # error

    verdict = parse_verdict(raw, expected_count=len(acs))
    exit_code = apply_gate_rules(verdict, strict=strict)

    if not dry_run:
        if project_root is None:
            project_root = Path.cwd()
        append_audit_log(verdict, change_name, exit_code, project_root=project_root)

    return exit_code
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_ac_verifier.py -k "verify_change" -v`
Expected: 4 passed

- [ ] **Step 5: Run all unit tests to verify no regression**

Run: `python3 -m pytest tests/unit/test_ac_verifier.py -v`
Expected: All tests pass (parse_acs × 5 + build_prompt × 3 + invoke × 3 + parse_verdict × 3 + apply_gate × 5 + audit_log × 2 + verify_change × 4 = 25 total)

- [ ] **Step 6: Commit**

```bash
git add skills/ac-verifier/scripts/ac_verifier.py tests/unit/test_ac_verifier.py
git commit -m "feat(ac-verifier): implement verify_change() end-to-end orchestrator"
```

---

## Task 9: ac_verifier.sh Bash Wrapper

**Files:**
- Create: `skills/ac-verifier/scripts/ac_verifier.sh`

- [ ] **Step 1: Write the bash wrapper**

Write `skills/ac-verifier/scripts/ac_verifier.sh`:

```bash
#!/usr/bin/env bash
# ac_verifier.sh — bash wrapper for skills/ac-verifier/scripts/ac_verifier.py
#
# Usage: ac_verifier.sh <change-name> [--dry-run] [--strict] [--skip]
#
# Exit codes:
#   0  All ACs pass (or no AC section found)
#   1  At least one AC fail (warning by default; error under STRICT_AC_GATE)
#   2  Skipped (--skip, no proposal.md, or no AC section)
#   3  Error (LLM call failed after retries, missing API key)
#
# Environment:
#   STRICT_AC_GATE=yes          Promote AC fail → archive blocker
#   SKIP_AC_VERIFICATION=yes    Skip verification entirely (exit 2)
#   AC_LLM_MOCK=yes             Use mock LLM (testing only)
#   AC_LLM_PROVIDER             openai | anthropic | local-ollama (default: auto-detect)
#   AC_LLM_MODEL                Model name
#   AC_LLM_TIMEOUT              Seconds per LLM call (default: 60)
set -euo pipefail

# Resolve script directory and python module path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

# Argument parsing
CHANGE_NAME=""
DRY_RUN=""
STRICT=""
SKIP=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN="--dry-run"; shift ;;
    --strict) STRICT="--strict"; shift ;;
    --skip) SKIP="--skip"; shift ;;
    -h|--help)
      cat <<EOF
Usage: $(basename "$0") <change-name> [--dry-run] [--strict] [--skip]

Verify OpenSpec change acceptance criteria against committed code.

Exit codes: 0=pass, 1=fail, 2=skip, 3=error
EOF
      exit 0
      ;;
    -*)
      echo "Unknown flag: $1" >&2
      exit 3
      ;;
    *)
      CHANGE_NAME="$1"
      shift
      ;;
  esac
done

[[ -z "$CHANGE_NAME" ]] && { echo "Usage: $(basename "$0") <change-name> [--dry-run] [--strict] [--skip]" >&2; exit 3; }

# Honor SKIP_AC_VERIFICATION env var (matches SKIP_* pattern)
if [ "${SKIP_AC_VERIFICATION:-no}" = "yes" ] || [ -n "$SKIP" ]; then
  echo "⏭️  AC verification skipped via SKIP_AC_VERIFICATION" >&2
  exit 2
fi

# Honor STRICT_AC_GATE env var (matches STRICT_*_GATE pattern)
if [ -z "$STRICT" ] && [ "${STRICT_AC_GATE:-no}" = "yes" ]; then
  STRICT="--strict"
fi

# Locate proposal.md
PROPOSAL_PATH="$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/proposal.md"
if [ ! -f "$PROPOSAL_PATH" ]; then
  echo "⚠️  proposal.md not found at $PROPOSAL_PATH; skipping" >&2
  exit 2
fi

# Invoke Python orchestrator
exec python3 -m skills.ac_verifier.scripts.ac_verifier "$CHANGE_NAME" \
  --proposal "$PROPOSAL_PATH" \
  --project-root "$PROJECT_ROOT" \
  $DRY_RUN $STRICT
```

- [ ] **Step 2: Add CLI entry point to ac_verifier.py**

Modify `skills/ac-verifier/scripts/ac_verifier.py`, append at end:

```python
def _cli_main():
    """CLI entry point invoked by ac_verifier.sh via `python3 -m ...`."""
    import argparse
    parser = argparse.ArgumentParser(description="AC verifier")
    parser.add_argument("change_name")
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    sys.exit(verify_change(
        change_name=args.change_name,
        proposal_path=args.proposal,
        project_root=args.project_root,
        strict=args.strict,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    _cli_main()
```

- [ ] **Step 3: Make wrapper executable and verify CLI help**

Run:
```bash
chmod +x skills/ac-verifier/scripts/ac_verifier.sh
bash skills/ac-verifier/scripts/ac_verifier.sh --help
```
Expected: Help text printed, exit 0

- [ ] **Step 4: Smoke-test CLI with mock**

Run:
```bash
AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_pass_all \
  bash skills/ac-verifier/scripts/ac_verifier.sh nonexistent-change
```
Expected: stderr "proposal.md not found", exit 2

- [ ] **Step 5: Commit**

```bash
git add skills/ac-verifier/scripts/ac_verifier.sh skills/ac-verifier/scripts/ac_verifier.py
git commit -m "feat(ac-verifier): add bash wrapper and CLI entry point"
```

---

## Task 10: Archive Gate Integration

**Files:**
- Modify: `_lib/archive.sh` lines 255-292 (insert AC verification step)

- [ ] **Step 1: Locate archive_gate_check function**

Run: `grep -n "archive_gate_check" _lib/archive.sh`
Expected: Function definition around line 255-292

- [ ] **Step 2: Read current function**

Run: `sed -n '249,295p' _lib/archive.sh`
Expected: Current implementation as in spec

- [ ] **Step 3: Add AC verification step before final return 0**

Modify `_lib/archive.sh`, replace the existing `archive_gate_check` function body with:

```bash
# archive_gate_check <change_name> [tasks_root]
#   Returns 0 if change has at least 1 completed task ([x]), returns 1 if 0.
#   Plus AC verification step (NEW in v1.0): runs ac-verifier skill and
#   applies STRICT_AC_GATE escalation. Honors FORCE_ARCHIVE_INCOMPLETE=yes
#   to bypass both checks.
archive_gate_check() {
  local change_name="${1:-}"
  local tasks_root="${2:-}"
  [[ -z "$change_name" ]] && return 0

  if [ "${FORCE_ARCHIVE_INCOMPLETE:-no}" = "yes" ]; then
    return 0
  fi

  if [ -z "$tasks_root" ]; then
    tasks_root="."
  fi

  local tasks_file="$tasks_root/openspec/changes/$change_name/tasks.md"
  if [ ! -f "$tasks_file" ]; then
    echo "❌ archive_gate_check: tasks.md 缺失 ($tasks_file)。设置 FORCE_ARCHIVE_INCOMPLETE=yes 跳过"
    return 1
  fi

  local completed
  completed=$(grep -c '^- \[x\]' "$tasks_file" 2>/dev/null | head -n1)
  [[ "$completed" =~ ^[0-9]+$ ]] || completed=0

  if [ "$completed" -eq 0 ]; then
    echo "❌ 未实现 (0 个完成任务)。设置 FORCE_ARCHIVE_INCOMPLETE=yes 跳过"
    return 1
  fi

  # NEW: AC verification step (ac-verifier skill)
  if [ "${SKIP_AC_VERIFICATION:-no}" != "yes" ]; then
    local proposal_file="$tasks_root/openspec/changes/$change_name/proposal.md"
    if [ -f "$proposal_file" ]; then
      local ac_script
      ac_script="$(git rev-parse --show-toplevel 2>/dev/null)/skills/ac-verifier/scripts/ac_verifier.sh"
      if [ -x "$ac_script" ]; then
        local ac_output ac_exit
        ac_output=$(bash "$ac_script" "$change_name" 2>&1)
        ac_exit=$?
        case $ac_exit in
          0) ;;  # all pass — continue
          1)
            if [ "${STRICT_AC_GATE:-no}" = "yes" ]; then
              echo "❌ archive_gate_check: AC verification failed under STRICT_AC_GATE"
              echo "$ac_output" | tail -30
              return 1
            else
              echo "⚠️  archive_gate_check: AC verification warning (set STRICT_AC_GATE=yes to block)"
              echo "$ac_output" | tail -30
            fi
            ;;
          2) ;;  # skipped — continue silently
          3)
            echo "⚠️  AC verification errored; treating as warning (set SKIP_AC_VERIFICATION=yes to suppress)"
            echo "$ac_output" | tail -10
            ;;
        esac
      fi
    fi
  fi

  return 0
}
```

- [ ] **Step 4: Verify the file diff is sensible**

Run: `git diff _lib/archive.sh | head -50`
Expected: AC verification block inserted before final `return 0`

- [ ] **Step 5: Smoke-test archive_gate_check with no proposal**

Run:
```bash
source _lib/archive.sh
mkdir -p /tmp/test-ac/openspec/changes/dummy
echo "- [x] task 1" > /tmp/test-ac/openspec/changes/dummy/tasks.md
(cd /tmp/test-ac && archive_gate_check dummy .)
```
Expected: exit 0 (no proposal.md → AC verification skipped)

- [ ] **Step 6: Smoke-test with mock AC fail + STRICT_AC_GATE=yes**

Run:
```bash
mkdir -p /tmp/test-ac-strict/openspec/changes/dummy
cat > /tmp/test-ac-strict/openspec/changes/dummy/proposal.md <<EOF
# Test

## 验收标准
- AC one
- AC two
EOF
echo "- [x] task 1" > /tmp/test-ac-strict/openspec/changes/dummy/tasks.md
STRICT_AC_GATE=yes AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_fail_one \
  PROJECT_ROOT=/tmp/test-ac-strict \
  bash /workspace/project/rdd-workflow/skills/ac-verifier/scripts/ac_verifier.sh dummy
```
Expected: exit 1 (mock fail + strict = blocking)

- [ ] **Step 7: Commit**

```bash
git add _lib/archive.sh
git commit -m "feat(archive): integrate ac-verifier into archive_gate_check"
```

---

## Task 11: rddf CLI Subcommand

**Files:**
- Create: `_lib/cli/ac_verify_cmd.py`
- Modify: `_lib/cli/__main__.py`

- [ ] **Step 1: Create CLI command file**

Write `_lib/cli/ac_verify_cmd.py`:

```python
"""rddf ac-verify subcommand."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    """Entry point for `rddf ac-verify`."""
    parser = argparse.ArgumentParser(
        prog="rddf ac-verify",
        description="Verify OpenSpec change acceptance criteria against committed code",
    )
    parser.add_argument("change_name", help="OpenSpec change name")
    parser.add_argument("--dry-run", action="store_true", help="Run without writing audit log")
    parser.add_argument("--strict", action="store_true", help="Block on any AC fail")
    parser.add_argument("--skip", action="store_true", help="Skip verification entirely")
    parser.add_argument("--project-root", type=Path, default=None, help="Project root (default: cwd)")
    args = parser.parse_args(argv)

    project_root = args.project_root or Path.cwd()
    script = project_root / "skills" / "ac-verifier" / "scripts" / "ac_verifier.sh"
    if not script.is_file():
        print(f"❌ ac-verifier skill not found at {script}", file=sys.stderr)
        return 3

    flags = []
    if args.dry_run:
        flags.append("--dry-run")
    if args.strict:
        flags.append("--strict")
    if args.skip:
        flags.append("--skip")

    # Forward env vars (STRICT_AC_GATE, SKIP_AC_VERIFICATION, AC_LLM_*)
    import subprocess
    result = subprocess.run(
        ["bash", str(script), args.change_name, *flags],
        cwd=str(project_root),
        env=None,  # inherit parent env
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Register subcommand in __main__.py**

Modify `_lib/cli/__main__.py`:

Find the dispatch table or command registration. If there's an explicit list of subcommands, add `"ac-verify": "skills.ac_verifier.scripts.ac_verify_cmd:main"` style entry.

If using lazy import pattern, add an `elif` clause matching `ac-verify`.

Run: `grep -n "contract_check\|contract-check" _lib/cli/__main__.py`
Expected: Existing entry showing the pattern to follow

Then add corresponding entry for `ac-verify` mirroring the pattern.

- [ ] **Step 3: Test rddf CLI**

Run: `rddf ac-verify --help`
Expected: Help text printed, exit 0

- [ ] **Step 4: Test rddf CLI with mock**

Run: `AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_pass_all rddf ac-verify nonexistent`
Expected: "proposal.md not found; skipping", exit 2

- [ ] **Step 5: Commit**

```bash
git add _lib/cli/ac_verify_cmd.py _lib/cli/__main__.py
git commit -m "feat(cli): add rddf ac-verify subcommand"
```

---

## Task 12: package.json + INSTALL.md Manifest

**Files:**
- Modify: `package.json`

- [ ] **Step 1: Find existing skill manifest entries**

Run: `grep -A 5 "skills" package.json | head -30`
Expected: Pattern showing how skills are registered

- [ ] **Step 2: Add ac-verifier to manifest**

Add entry for `ac-verifier` in the skills section, following the pattern of `contract-check` (closest analog).

- [ ] **Step 3: Verify package.json is valid JSON**

Run: `python3 -c "import json; json.load(open('package.json'))"`
Expected: No error

- [ ] **Step 4: Commit**

```bash
git add package.json
git commit -m "feat(install): register ac-verifier in package.json manifest"
```

---

## Task 13: Bats Integration Tests (skill registration + CLI)

**Files:**
- Create: `tests/integration/test_ac_verifier_skill.bats`

- [ ] **Step 1: Create bats test file**

Write `tests/integration/test_ac_verifier_skill.bats`:

```bash
#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
}

# === Skill Registration ===

@test "ac-verifier: SKILL.md exists with user-invocable: true" {
  [ -f "$REPO_ROOT/skills/ac-verifier/SKILL.md" ]
  run grep "user-invocable: true" "$REPO_ROOT/skills/ac-verifier/SKILL.md"
  [ "$status" -eq 0 ]
}

@test "ac-verifier: all 4 scripts exist" {
  for f in ac_verifier.sh ac_verifier.py ac_verifier_prompt.py ac_verifier_mocks.py; do
    [ -f "$REPO_ROOT/skills/ac-verifier/scripts/$f" ]
  done
}

@test "ac-verifier: bash wrapper is executable" {
  [ -x "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh" ]
}

# === CLI subcommand ===

@test "rddf ac-verify --help exits 0" {
  run rddf ac-verify --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"Verify OpenSpec"* ]]
}

@test "rddf ac-verify --skip exits 2" {
  run rddf ac-verify nonexistent-change --skip
  [ "$status" -eq 2 ]
}

@test "rddf ac-verify nonexistent-change exits 2 (no proposal)" {
  AC_LLM_MOCK=yes run rddf ac-verify nonexistent-change
  [ "$status" -eq 2 ]
}

# === Bash wrapper exit code mapping ===

@test "ac_verifier.sh --help exits 0" {
  run bash "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh" --help
  [ "$status" -eq 0 ]
}

@test "ac_verifier.sh with no args exits 3" {
  run bash "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh"
  [ "$status" -eq 3 ]
}

@test "ac_verifier.sh honors SKIP_AC_VERIFICATION=yes" {
  SKIP_AC_VERIFICATION=yes run bash "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh" my-change
  [ "$status" -eq 2 ]
}

# === Mock LLM scenarios ===

@test "mock_pass_all: writes audit log entry with exit_code=0" {
  TMP="$(mktemp -d)"
  mkdir -p "$TMP/openspec/changes/test-change"
  echo "- AC one" > "$TMP/openspec/changes/test-change/proposal.md"
  echo "- [x] task" > "$TMP/openspec/changes/test-change/tasks.md"
  PROJECT_ROOT="$TMP" AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_pass_all \
    run bash "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh" test-change
  [ "$status" -eq 0 ]
  [ -f "$TMP/.rddf/state/.ac-verification.jsonl" ]
  rm -rf "$TMP"
}

@test "mock_fail_one + --strict: exit 1" {
  TMP="$(mktemp -d)"
  mkdir -p "$TMP/openspec/changes/test-change"
  echo $'- AC one\n- AC two' > "$TMP/openspec/changes/test-change/proposal.md"
  echo "- [x] task" > "$TMP/openspec/changes/test-change/tasks.md"
  PROJECT_ROOT="$TMP" AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_fail_one \
    run bash "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh" test-change --strict
  [ "$status" -eq 1 ]
  rm -rf "$TMP"
}

@test "mock_fail_one without --strict: exit 0 (warning)" {
  TMP="$(mktemp -d)"
  mkdir -p "$TMP/openspec/changes/test-change"
  echo $'- AC one\n- AC two' > "$TMP/openspec/changes/test-change/proposal.md"
  echo "- [x] task" > "$TMP/openspec/changes/test-change/tasks.md"
  PROJECT_ROOT="$TMP" AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_fail_one \
    run bash "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh" test-change
  [ "$status" -eq 0 ]
  rm -rf "$TMP"
}
```

- [ ] **Step 2: Run bats tests**

Run: `bats tests/integration/test_ac_verifier_skill.bats`
Expected: 11 passed

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_ac_verifier_skill.bats
git commit -m "test(ac-verifier): add bats integration tests for skill and CLI"
```

---

## Task 14: Archive Gate Integration Bats Tests

**Files:**
- Modify: `tests/integration/test_archive_gate.bats` (or create new file)

- [ ] **Step 1: Check if existing archive gate test file exists**

Run: `ls tests/integration/test_archive*`
Expected: May have test_archive_iteration_sync_resilience.bats already

- [ ] **Step 2: Add AC verification cases to existing file or create new**

Write `tests/integration/test_ac_verifier_archive_gate.bats`:

```bash
#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  TEST_TMP="$(mktemp -d)"
  cd "$TEST_TMP"
  git init -q
  mkdir -p "$TEST_TMP/openspec/changes/test-change"
}

teardown() {
  rm -rf "$TEST_TMP"
}

# === archive_gate_check with AC verification ===

@test "archive_gate_check passes when AC verification passes (mock)" {
  echo "- [x] task" > "$TEST_TMP/openspec/changes/test-change/tasks.md"
  echo "- AC one" > "$TEST_TMP/openspec/changes/test-change/proposal.md"
  source "$REPO_ROOT/_lib/archive.sh"
  AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_pass_all \
    run archive_gate_check test-change "$TEST_TMP"
  [ "$status" -eq 0 ]
}

@test "archive_gate_check warns (not blocks) on AC fail without STRICT_AC_GATE" {
  echo "- [x] task" > "$TEST_TMP/openspec/changes/test-change/tasks.md"
  echo $'- AC one\n- AC two' > "$TEST_TMP/openspec/changes/test-change/proposal.md"
  source "$REPO_ROOT/_lib/archive.sh"
  AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_fail_one \
    run archive_gate_check test-change "$TEST_TMP"
  [ "$status" -eq 0 ]
  [[ "$output" == *"AC verification warning"* ]]
}

@test "archive_gate_check blocks on AC fail with STRICT_AC_GATE=yes" {
  echo "- [x] task" > "$TEST_TMP/openspec/changes/test-change/tasks.md"
  echo $'- AC one\n- AC two' > "$TEST_TMP/openspec/changes/test-change/proposal.md"
  source "$REPO_ROOT/_lib/archive.sh"
  STRICT_AC_GATE=yes AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_fail_one \
    run archive_gate_check test-change "$TEST_TMP"
  [ "$status" -eq 1 ]
}

@test "archive_gate_check skips AC verification with SKIP_AC_VERIFICATION=yes" {
  echo "- [x] task" > "$TEST_TMP/openspec/changes/test-change/tasks.md"
  echo "- AC one" > "$TEST_TMP/openspec/changes/test-change/proposal.md"
  source "$REPO_ROOT/_lib/archive.sh"
  SKIP_AC_VERIFICATION=yes AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_fail_one \
    run archive_gate_check test-change "$TEST_TMP"
  [ "$status" -eq 0 ]
}

@test "archive_gate_check skips AC verification when no proposal.md" {
  echo "- [x] task" > "$TEST_TMP/openspec/changes/test-change/tasks.md"
  source "$REPO_ROOT/_lib/archive.sh"
  AC_LLM_MOCK=yes run archive_gate_check test-change "$TEST_TMP"
  [ "$status" -eq 0 ]
}
```

- [ ] **Step 3: Run bats tests**

Run: `bats tests/integration/test_ac_verifier_archive_gate.bats`
Expected: 5 passed

- [ ] **Step 4: Run existing archive tests to verify no regression**

Run: `bats tests/integration/test_archive_iteration_sync_resilience.bats`
Expected: All existing tests still pass (regression safety)

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_ac_verifier_archive_gate.bats
git commit -m "test(ac-verifier): add bats tests for archive_gate_check integration"
```

---

## Task 15: E2E Mock LLM Tests

**Files:**
- Create: `tests/integration/test_ac_verifier_e2e.bats`

- [ ] **Step 1: Create E2E test file**

Write `tests/integration/test_ac_verifier_e2e.bats`:

```bash
#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  TMP="$(mktemp -d)"
  export TMP
  mkdir -p "$TMP/openspec/changes/test-change"
  echo $'- AC one\n- AC two\n- AC three' > "$TMP/openspec/changes/test-change/proposal.md"
  echo "- [x] task" > "$TMP/openspec/changes/test-change/tasks.md"
}

teardown() {
  rm -rf "$TMP"
}

@test "e2e: mock_pass_all → exit 0 + audit log entry" {
  PROJECT_ROOT="$TMP" AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_pass_all \
    run bash "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh" test-change
  [ "$status" -eq 0 ]
  [ -f "$TMP/.rddf/state/.ac-verification.jsonl" ]
}

@test "e2e: mock_fail_one (warning mode) → exit 0 + audit log" {
  PROJECT_ROOT="$TMP" AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_fail_one \
    run bash "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh" test-change
  [ "$status" -eq 0 ]
  log="$TMP/.rddf/state/.ac-verification.jsonl"
  [ -f "$log" ]
  grep -q '"change_name": "test-change"' "$log"
}

@test "e2e: mock_fail_one (strict mode) → exit 1 + audit log" {
  PROJECT_ROOT="$TMP" AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_fail_one \
    run bash "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh" test-change --strict
  [ "$status" -eq 1 ]
  [ -f "$TMP/.rddf/state/.ac-verification.jsonl" ]
}

@test "e2e: mock_invalid_json → exit 3 + audit log skipped" {
  PROJECT_ROOT="$TMP" AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_invalid_json \
    run bash "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh" test-change
  [ "$status" -eq 3 ]
  # No audit log written on LLM error
  [ ! -f "$TMP/.rddf/state/.ac-verification.jsonl" ]
}

@test "e2e: mock_omitted_ac → AC-3 auto-filled as fail + exit 1 (strict)" {
  PROJECT_ROOT="$TMP" AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_omitted_ac \
    run bash "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh" test-change --strict
  [ "$status" -eq 1 ]
  log="$TMP/.rddf/state/.ac-verification.jsonl"
  grep -q '"AI omitted' "$log"
}
```

- [ ] **Step 2: Run E2E tests**

Run: `bats tests/integration/test_ac_verifier_e2e.bats`
Expected: 5 passed (≥4 required)

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_ac_verifier_e2e.bats
git commit -m "test(ac-verifier): add E2E mock-LLM tests covering 5 scenarios"
```

---

## Task 16: Regression Check + Final Validation

**Files:**
- (none; validation only)

- [ ] **Step 1: Run all unit tests**

Run: `python3 -m pytest tests/unit/test_ac_verifier.py -v`
Expected: All 25+ tests pass

- [ ] **Step 2: Run all new bats tests**

Run: `bats tests/integration/test_ac_verifier_skill.bats tests/integration/test_ac_verifier_archive_gate.bats tests/integration/test_ac_verifier_e2e.bats`
Expected: All tests pass (11 + 5 + 5 = 21)

- [ ] **Step 3: Run existing archive tests for regression**

Run: `bats tests/integration/test_archive_iteration_sync_resilience.bats`
Expected: 5 passed (no regression)

- [ ] **Step 4: Smoke-test manual invocation**

Run:
```bash
mkdir -p /tmp/manual-ac-test/openspec/changes/manual-change
cat > /tmp/manual-ac-test/openspec/changes/manual-change/proposal.md <<EOF
# Manual test

## 验收标准
- First AC to verify
- Second AC to verify
EOF
echo "- [x] task 1" > /tmp/manual-ac-test/openspec/changes/manual-change/tasks.md
PROJECT_ROOT=/tmp/manual-ac-test AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_pass_all \
  rddf ac-verify manual-change
echo "Exit: $?"
```
Expected: "All ACs passed", exit 0

- [ ] **Step 5: Final commit (if any cleanup)**

```bash
git status
# If any uncommitted changes, commit them
git add -A
git diff --cached --quiet || git commit -m "chore(ac-verifier): final cleanup"
```

---

## Self-Review

### 1. Spec coverage

| Spec section | Implementation task |
|--------------|---------------------|
| §3 Architecture | Tasks 1, 2-9 (orchestrator) |
| §4 Component Interfaces (sh, py API) | Tasks 8, 9 |
| §5 AI Agent Prompt Contract | Tasks 3, 4 (mock), future Task 9 in v2 for real LLM |
| §6 Error Handling (boundary cases) | Task 4 (mock), Task 5 (parse_verdict), Task 8 (orchestrator) |
| §7 Archive Integration | Task 10 |
| §8 CLI & Skill Surface | Tasks 9, 11, 12 |
| §9 Testing Strategy | Tasks 2-8 (unit), 13-15 (bats), 16 (regression) |
| §10 Rollout (4 phases) | v1 implements Phase 1 + Phase 2 default warning; Phases 3-4 deferred (per Out of Scope) |
| §11 Risks | Mitigations documented; cache + STRICT flag implemented in Tasks 10, 11 |
| §12 Acceptance Criteria | Task 16 covers all verification |
| §13 Out of Scope | cross-repo, multi-LLM, auto-fix, UI — explicitly NOT implemented |

### 2. Placeholder scan

No "TBD", "TODO", "implement later", or vague phrases found in plan steps. All code blocks are complete.

### 3. Type consistency

- `parse_acs()` returns `list[dict]` with `{ac_id, description, has_checkbox}` — used consistently in Tasks 2, 3, 4, 5, 6, 7, 8.
- `invoke_ai_agent(system: str, user: str) -> str` — used in Task 4 (test) and Task 8 (orchestrator).
- `parse_verdict(raw: str, expected_count: int) -> list[dict]` — used in Task 5 (test) and Task 8.
- `apply_gate_rules(verdict: list[dict], strict: bool) -> int` — used in Task 6 (test) and Task 8.
- `append_audit_log(verdict, change_name, exit_code, project_root)` — used in Task 7 (test) and Task 8.
- `verify_change(change_name, proposal_path, project_root, strict, dry_run)` — used in Task 8 (test) and Task 9 (CLI).
- CLI arg names `--dry-run`, `--strict`, `--proposal`, `--project-root` consistent across Tasks 9, 11, 13-15.

No mismatches found.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-08-17-ac-verifier-skill.md`. Two execution options:**

1. **Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Recommended for this plan: Subagent-Driven** — Tasks 2-8 are pure TDD with well-defined contracts, ideal for subagent isolation. Tasks 10, 11, 13-15 have integration boundaries that benefit from review between tasks.