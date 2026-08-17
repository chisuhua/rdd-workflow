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