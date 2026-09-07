## Why

The current `rdd-verifier` skill (v1.0, per ADR-0034) outsources LLM-based acceptance criteria verification to a separate `ac-verifier` sub-skill, which in turn shells out to an external Python process (`ac_verifier.py`) that calls one of four LLM provider SDKs (`openai`, `anthropic`, `ollama`, `minimax`). This split creates five concrete problems:

1. **Configuration sprawl.** Users must set `AC_LLM_PROVIDER`, `AC_LLM_BASE_URL`, `AC_LLM_API_KEY`, `AC_LLM_MODEL`, `AC_LLM_TIMEOUT`, `AC_LLM_MAX_RETRIES`, `AC_LLM_MOCK`, `SKIP_AC_VERIFICATION`, plus the provider-specific base URL for `minimax`. None of these are needed when the executing AI agent IS the LLM.
2. **External Python dependency.** The `ac-verifier/scripts/{ac_verifier.sh,ac_verifier.py}` + 4 `llm_providers/*.py` modules must be present, up-to-date, and reachable from `$PROJECT_ROOT/skills/ac-verifier/scripts/ac_verifier.sh`. Every `_lib/cli/rdd_verify_cmd.py`, `_lib/cli/ac_verify_cmd.py`, `_lib/archive.sh`, and `skills/rdd-verifier/scripts/run_verification.sh` invocation depends on this path existing.
3. **SoC violation between documentation and execution.** The actual LLM prompt template (`_SYSTEM_PROMPT_TEMPLATE`) and verdict JSON schema (`_VERDICT_SCHEMA`) live inside Python source, not inside the skill that conceptually owns verification. Future LLM behavior changes require modifying Python instead of the skill instruction.
4. **Two-layer failure mode.** Errors can originate in the shell wrapper, the Python entry point, the LLM provider SDK, OR the AI agent itself. Exit code 3 was overloaded to mean "ac-verifier internal error" without distinguishing among these sources.
5. **Mock gymnastics in CI.** CI must set `AC_LLM_MOCK=yes` and pick a `_MOCK_SCENARIO` to test the verifier path. The mock itself is a 5-scenario canned-response module (`ac_verifier_mocks.py`) that must stay synchronized with real LLM behavior.

The executing AI agent in OpenCode (or any AI assistant running this skill) **already is an LLM**. The verification work can be done directly by the agent using its built-in reasoning, reading proposal.md and code through the agent's normal tools, and writing verdict JSON through normal file writes. No external LLM provider configuration, no Python wrapper, no mock layer.

## What Changes

- **Inline the LLM verification protocol into `skills/rdd-verifier/SKILL.md`.** Replace every reference to "ac-verifier subprocess" with an inline "LLM Verification Protocol" section that instructs the executing AI agent to perform AC verification directly using its own tools (Read, Grep, Glob, Bash, codegraph_explore).
- **Mark `skills/ac-verifier/SKILL.md` as deprecated.** Set `user-invocable: false`, add a deprecation notice banner, and document the migration path. Keep `ac-verifier/scripts/*` as a thin backward-compatibility shim for `rddf ac-verify` and `_lib/archive.sh` fallback for one to two release cycles, then remove.
- **Remove `AC_LLM_*` environment variables from the rdd-verifier contract.** The new SKILL.md requires no LLM provider env vars because the executing agent is the LLM. `STRICT_AC_GATE` and `SKIP_AC_VERIFICATION` remain as gate-level escape hatches but are no longer tied to ac-verifier internals.
- **Reassign exit code 3 semantics.** From "ac-verifier internal error (provider/API key)" to "LLM verification error (agent context overflow, all tool calls failed, or unrecoverable LLM reasoning failure)".
- **Rewrite `_lib/cli/rdd_verify_cmd.py` to drop the default runner** that shells out to `ac-verifier/scripts/ac_verifier.sh`. The CLI now produces a structured shell invocation context that the executing agent reads from `.rddf/state/rdd-verify-context.json` and acts on directly per the SKILL.md protocol. (Or, for simpler implementations: keep `rddf rdd-verify` as a thin scan-and-stage helper and let the agent do the LLM work.)
- **Update `_lib/archive.sh::archive_gate_check`** to consume the canonical verifier cache (already present from ADR-0034) without falling back to `ac-verifier/scripts/ac_verifier.sh`. Cache-hit and cache-miss paths both use the SHA-bound cache; the fallback path is removed in favor of `SKIP_RDD_VERIFIER=yes` + audited bypass (already implemented per fix-rdd-verifier-lifecycle-dashboard).
- **Update `skills/rdd-verifier/scripts/run_verification.sh`** to either be removed (agent does verification per SKILL.md) or be rewritten as a thin wrapper that writes the cache and audit log without spawning an LLM subprocess.
- **Rewrite or deprecate the ac-verifier unit and integration test suites.** `tests/unit/test_ac_verifier*.py` (parse_acs, parse_verdict, build_agent_prompt, invoke_ai_agent) become either obsolete (parse_acs and verdict schema now live in SKILL.md) or migrate into `tests/unit/test_rdd_verifier_protocol.py`. `tests/integration/test_ac_verifier_*.bats` and `tests/integration/test_ac_verifier_skill.bats` are deprecated and replaced by `tests/integration/test_rdd_verifier_self_contained.bats` that exercises the inlined protocol against fixture proposals.
- **Update documentation.** `AGENTS.md` table row for `rdd-verifier` changes from "批量调 ac-verifier" to "self-contained LLM verification (inlined in SKILL.md)". `README.md` reflects the new architecture. `docs/superpowers/specs/2026-08-26-rdd-verifier-design.md` and `docs/superpowers/specs/2026-08-17-ac-verifier-skill-design.md` are annotated with a v2.0 update note.

## Capabilities

### New Capabilities

- **Self-contained LLM verification.** `rdd-verifier` v2.0 instructs the executing AI agent to verify acceptance criteria using its built-in tools, with no external LLM provider configuration. The verification prompt, verdict JSON schema, AC extraction rules, and persistence protocol all live inside `skills/rdd-verifier/SKILL.md` as a single source of truth.
- **Direct agent reasoning with reasoning-keyword contract.** The agent's verdict reasoning MUST contain one of the documented drift or gap keywords so the existing `_lib/verifier/classify.py::classify_failure` heuristic continues to work without modification. The contract is documented in the SKILL.md "LLM Verification Protocol" section.
- **Migration path from ac-verifier.** A documented migration table in the rdd-verifier SKILL.md and a deprecation notice at the top of the ac-verifier SKILL.md guide users from `rddf ac-verify` to `rddf rdd-verify`.

### Modified Capabilities

- **`rdd-verifier` (verifier-lifecycle).** Phase 5 of the OpenSpec workflow becomes self-contained. The phase no longer depends on a separate ac-verifier skill and no longer requires `AC_LLM_*` environment variables. Exit code 3 semantics shift from "external provider error" to "agent reasoning/tool failure".
- **`archive_gate_check` (verifier-archive-gate).** The fallback path that shells out to `ac-verifier/scripts/ac_verifier.sh` is removed. Archive gate consumes only the canonical SHA-bound verdict cache. A cache miss with no fallback is treated as a hard gate failure that requires `SKIP_RDD_VERIFIER=yes` + `RDDF_VERIFIER_BYPASS_REASON` to bypass.
- **`ac-verifier` (ac-verifier, deprecated).** Marked deprecated. `user-invocable: false`. Kept as a thin shim for `rddf ac-verify` CLI and `_lib/archive.sh` for one to two release cycles. All new code MUST use `rdd-verifier` directly.

## Impact

Affected code:

- `skills/rdd-verifier/SKILL.md` — rewrite to inline LLM Verification Protocol
- `skills/ac-verifier/SKILL.md` — add deprecation notice
- `_lib/cli/rdd_verify_cmd.py` — drop default runner that shells out to ac-verifier
- `_lib/cli/ac_verify_cmd.py` — convert to thin shim that delegates to rdd_verify_cmd
- `_lib/archive.sh` — remove fallback `ac-verifier/scripts/ac_verifier.sh` invocation
- `skills/rdd-verifier/scripts/run_verification.sh` — rewrite or delete (agent does verification per SKILL.md)
- `skills/ac-verifier/scripts/ac_verifier.{sh,py}` and `llm_providers/*.py` — kept as shim for 1-2 versions
- `tests/unit/test_ac_verifier*.py` — replaced by `tests/unit/test_rdd_verifier_protocol.py`
- `tests/integration/test_ac_verifier_*.bats` — replaced by `tests/integration/test_rdd_verifier_self_contained.bats`
- `AGENTS.md` — update rdd-verifier description
- `README.md` — update architecture diagram
- `docs/superpowers/specs/2026-08-26-rdd-verifier-design.md` — annotate v2.0 update
- New ADR: `docs/adr/ADR-0045-deprecate-ac-verifier.md`

Backward compatibility:

- `rddf ac-verify <change>` continues to work for at least one release cycle, shimming through to rdd-verifier internally.
- The SHA-bound verdict cache schema v2 is unchanged. Existing caches remain valid and reusable.
- `_lib/verifier/classify.py::classify_failure` and `_lib/verifier/cache.py::verdict_cache` are unchanged (the heuristic still consumes the same verdict JSON shape; the cache writer is now called from a different source).
- `_lib/verifier/{branch,archive_gate,scan_state}.py` remain unchanged.

Migration for users:

- Replace `skill_use("ac-verifier", "<name>")` with `skill_use("rdd-verifier", "<name>")` or `skill_use("rdd-verifier")` for the batch flow.
- Delete `AC_LLM_*` exports from CI and shell profiles.
- `STRICT_AC_GATE` retains its gate-promotion semantics but now blocks on rdd-verifier verdict (not ac-verifier verdict).
