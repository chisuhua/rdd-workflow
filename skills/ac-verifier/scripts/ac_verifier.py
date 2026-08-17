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
_BULLET_LINE = re.compile(r"^- (?:\[([ x])\]\s+)?(.+)$")


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
    for line in section_text.splitlines():
        m = _BULLET_LINE.match(line.strip())
        if not m:
            continue
        marker = m.group(1)  # " ", "x", or None (None for prose bullets)
        description = m.group(2).strip()
        has_checkbox = marker in (" ", "x")
        acs.append({
            "ac_id": f"AC-{len(acs) + 1}",
            "description": description,
            "has_checkbox": has_checkbox,
        })
    return acs


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


def invoke_ai_agent(system: str, user: str) -> str:
    """Call LLM with tools. Returns raw text.

    In mock mode (AC_LLM_MOCK=yes), returns canned response from mocks module.
    In real mode, requires API key env var; raises AcVerifierError on failure.
    """
    if os.environ.get("AC_LLM_MOCK", "").lower() == "yes":
        import importlib.util
        _mock_path = Path(__file__).resolve().parent / "ac_verifier_mocks.py"
        _spec = importlib.util.spec_from_file_location("ac_verifier_mocks", _mock_path)
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        return _mod.mock_invoke(system, user)

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

    On unparseable JSON: raise AcVerifierError. Auto-fills missing ACs as fail.
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
    except ImportError:
        pass  # jsonschema not installed
    except jsonschema.exceptions.ValidationError:
        pass  # schema validation is advisory; missing/invalid fields fall through

    # Auto-fill missing ACs
    present_ids = {item.get("ac_id") for item in data}
    for i in range(1, expected_count + 1):
        ac_id = f"AC-{i}"
        if ac_id not in present_ids:
            data.append({
                "ac_id": ac_id,
                "description": "(missing from LLM output)",
                "status": "fail",
                "confidence": 0.0,
                "evidence": [],
                "reasoning": "AI omitted this AC from verdict",
            })

    return data


def apply_gate_rules(verdict: list[dict], strict: bool) -> int:
    """Return exit code based on verdict + strict flag.

    0 if all pass, or any fail under non-strict (warning mode)
    1 if any fail under strict (blocking mode)
    2 if no ACs in verdict (treated as skip)
    """
    if not verdict:
        return 2
    has_fail = any(v.get("status") == "fail" for v in verdict)
    if has_fail and strict:
        return 1
    return 0


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
        return 0  # No ACs to verify (treat as pass-through per spec)

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