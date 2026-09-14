#!/usr/bin/env python3
"""A-layer e2e helper for reflect_engine.

Invokes ReflectEngine.analyze() against a fake project root and prints a
1-line JSON envelope to stdout for bats assertions.

Design: docs/superpowers/specs/2026-09-14-reflect-e2e-coverage-design.md §2.0
Oracle C1 safe: ALL inputs via env vars, no shell interpolation.

Required env vars:
  REFLECT_PROJECT_ROOT  absolute path to fake project root
  REPO_ROOT             absolute path to rdd-workflow repo (sys.path root)
  REFLECT_PHASE         one of {arch, plan, ship, design}

Optional env vars:
  REFLECT_FAILURES_JSON JSON array of failure dicts (default '[]')
                        Each dict: {type, gate?, step?, error, retry?, max_retries?}
  REFLECT_DRAFT         '1' → also call engine.draft_issue(result) and include
                        the draft envelope (only when action == propose_issue)

Output: single line of JSON with shape:
  {"action": "<action>",
   "fingerprint": "<fp>",
   "reason": "<reason>",
   "matched_source"?: "<source>",
   "matched_name"?:   "<name>",
   "draft"?: {"title", "target_repo", "labels", "body_has_analysis"}}

Exit code: 0 on success, 1 on missing env vars, 2 on engine exception.
"""
import json
import os
import sys


def _die(msg: str, code: int = 1) -> None:
    sys.stderr.write(f"reflect_invoke: {msg}\n")
    sys.exit(code)


def _get_required(name: str) -> str:
    val: str | None = os.environ.get(name)
    if not val:
        _die(f"missing required env var: {name}")
    assert val is not None  # narrow for strict type checkers
    return val


def main() -> None:
    root = _get_required("REFLECT_PROJECT_ROOT")
    repo_root = _get_required("REPO_ROOT")
    phase = _get_required("REFLECT_PHASE")

    # Inject repo root into sys.path so `from _lib.reflect_engine import ...`
    # resolves (canonical per P1-1b identity-merge).
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    failures_raw: str = os.environ.get("REFLECT_FAILURES_JSON", "[]")
    failures: list
    try:
        failures = json.loads(failures_raw)
    except json.JSONDecodeError as e:
        _die(f"REFLECT_FAILURES_JSON is not valid JSON: {e}", code=2)
        return  # unreachable; satisfies strict type checker
    if not isinstance(failures, list):
        _die("REFLECT_FAILURES_JSON must be a JSON array", code=2)
        return

    try:
        from _lib.reflect_engine import ReflectEngine  # noqa: E402
    except Exception as e:  # pragma: no cover - import error surfaces here
        _die(f"failed to import ReflectEngine: {e}", code=2)
        return

    try:
        engine = ReflectEngine(phase=phase, project_root=root, timeout=10)
        result = engine.analyze(failures=failures)
    except Exception as e:  # pragma: no cover - engine error surfaces here
        _die(f"engine.analyze raised: {e}", code=2)
        return

    out: dict = {
        "action": result.action,
        "fingerprint": result.fingerprint,
        "reason": result.reason,
    }
    if result.matched_improvement:
        out["matched_source"] = result.matched_improvement.get("source")
        out["matched_name"] = result.matched_improvement.get("matched_name")

    draft_flag = os.environ.get("REFLECT_DRAFT", "")
    if draft_flag == "1" and result.action == "propose_issue":
        draft = engine.draft_issue(result)
        out["draft"] = {
            "title": draft.title,
            "target_repo": draft.target_repo,
            "labels": list(draft.labels),
            "body_has_analysis": "## Reflection Analysis" in draft.body,
        }

    print(json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    main()
