---
name: ac-verifier
description: ⚠️ DEPRECATED — replaced by `rdd-verifier` v2.0 which self-contains LLM verification. Thin shim kept for backward compatibility (1-2 release cycles); new code MUST use `rdd-verifier` directly.
license: MIT
compatibility: requires openspec CLI v1.3.1+, Python 3.11+, ANTHROPIC_API_KEY or OPENAI_API_KEY
metadata:
  author: rdd-workflow
  version: 1.0
  evolved-from: ""
  user-invocable: false  # deprecated, use rdd-verifier
  deprecated:
    deprecated_in: "rdd-verifier v2.0 (2026-09-07, per ADR-0045)"
    deprecated_by: "skills/rdd-verifier/SKILL.md"
    reason: "rdd-verifier v2.0 self-contains LLM verification (ADR-0045) — no longer needs to shell out to this skill"
    removal_target: "next minor release after 2.0"
    migration: "Replace skill_use('ac-verifier', '<name>') with skill_use('rdd-verifier', '<name>')"
---

# ⚠️ DEPRECATED — Use `rdd-verifier` instead

> **This skill is deprecated as of rdd-verifier v2.0 (2026-09-07, per ADR-0045).**
>
> `rdd-verifier` v2.0 **no longer calls this skill** (per ADR-0045 inline-ac-verifier-into-rdd-verifier). LLM verification logic has been inlined into the rdd-verifier SKILL.md instruction block (see `skills/rdd-verifier/SKILL.md` § "LLM Verification Protocol"). The executing AI agent IS the LLM — no external provider config needed.
>
> **This skill is kept as a thin backward-compatibility shim** for `rddf ac-verify` CLI users and `_lib/archive.sh::archive_gate_check` fallback path. **It will be removed in the next minor release after 2.0**.
>
> **New code MUST use `rdd-verifier` directly.**

## Migration

| Old (this skill) | New (rdd-verifier v2.0) |
|---|---|
| `skill_use("ac-verifier", "<name>")` | `skill_use("rdd-verifier", "<name>")` |
| `rddf ac-verify <name>` | `rddf rdd-verify <name>` (auto-redirect) |
| `AC_LLM_PROVIDER=openai` | not needed (agent IS the LLM) |
| `AC_LLM_API_KEY=...` | not needed |
| `AC_LLM_MOCK=yes` | not needed |
| Exit 3 = "ac-verifier internal error" | Exit 3 = "LLM verification error" |

See `skills/rdd-verifier/SKILL.md` for full v2.0 design.

---

# AC Verifier Skill (v1.0, deprecated — kept for backward compat)

> ⚠️ 以下文档保留用于向后兼容。**新代码请使用 `rdd-verifier`。**

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

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `STRICT_AC_GATE` | no | `no` | Promote AC fail → archive blocker |
| `SKIP_AC_VERIFICATION` | no | `no` | Skip AI verification entirely (exit 2) |
| `AC_LLM_MOCK` | no | `no` | `yes` → use mock LLM (testing only). Short-circuits before provider dispatch. |
| `AC_LLM_PROVIDER` | yes (if not mocking) | — | `openai` \| `anthropic` \| `ollama` \| `minimax` |
| `AC_LLM_BASE_URL` | yes for `minimax` | provider-specific | Endpoint URL (no trailing slash) |
| `AC_LLM_API_KEY` | yes | — | API key (set via env, never commit) |
| `AC_LLM_MODEL` | no | provider-specific | Model name |
| `AC_LLM_TIMEOUT` | no | `60` | Seconds per LLM call |
| `AC_LLM_MAX_RETRIES` | no | `3` | Retries on 429/5xx/network with exponential backoff (1s/2s/4s) |

## Provider Configuration

### Provider-specific defaults

| Provider | base_url | model |
|----------|----------|-------|
| `openai` | `https://api.openai.com` | `gpt-4o-mini` |
| `anthropic` | `https://api.anthropic.com` | `claude-3-5-haiku-20241022` |
| `ollama` | `http://localhost:11434` | `llama3.1` |
| `minimax` | `""` ⚠️ **must set `AC_LLM_BASE_URL`** | `MiniMax-M3` |

### Examples

```bash
# OpenAI
export AC_LLM_PROVIDER=openai
export AC_LLM_API_KEY="<your-openai-key>"  # set in env, not committed
ac_verifier.sh my-change

# Anthropic
export AC_LLM_PROVIDER=anthropic
export AC_LLM_API_KEY="<your-anthropic-key>"
ac_verifier.sh my-change

# Local Ollama (no API key needed)
export AC_LLM_PROVIDER=ollama
export AC_LLM_API_KEY=ollama  # required by base class; Ollama ignores it
ac_verifier.sh my-change

# MiniMax (placeholder — requires real endpoint)
export AC_LLM_PROVIDER=minimax
export AC_LLM_BASE_URL="<minimax-endpoint>"
export AC_LLM_API_KEY="<your-key>"
ac_verifier.sh my-change

# Mock mode (testing only)
export AC_LLM_MOCK=yes
ac_verifier.sh my-change
```

### Security notes

- **Never** hardcode API keys; always set via environment variables
- MiniMax's empty `default_base_url` forces explicit configuration — prevents silent calls to wrong endpoints
- CI must default to mock mode (`AC_LLM_MOCK=yes`); real provider live tests require explicit opt-in

## Audit Log

Each non-dry-run invocation appends a JSONL entry to `.rddf/state/.ac-verification.jsonl`:

```json
{"ts": "2026-08-17T...", "change_name": "...", "exit_code": 1, "verdict": [...]}
```

## See Also

- Spec: `docs/superpowers/specs/2026-08-17-ac-verifier-skill-design.md`
- Audit log: `.rddf/state/.ac-verification.jsonl`