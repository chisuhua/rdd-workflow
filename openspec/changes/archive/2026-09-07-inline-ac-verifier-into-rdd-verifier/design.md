## Context

The `rdd-verifier` skill was introduced in v1.0 (2026-08-26, ADR-0034) as the 5th phase of the OpenSpec workflow, batch-verifying acceptance criteria after `guide-ship` execution and before archive. It was explicitly designed to **reuse `ac-verifier` as the LLM backend**, with `_lib/verifier/classify.py` and `_lib/verifier/cache.py` providing the orchestration layer (failure classification, SHA-bound cache) and `ac-verifier/scripts/ac_verifier.py` providing the LLM call.

The architectural split between orchestration (rdd-verifier) and execution (ac-verifier) was justified by an Oracle review at the time: "separation of concerns — orchestration handles state machine and routing; ac-verifier handles LLM call semantics". The reviewer assigned 82/100 and noted the SoC alignment as a strength.

Six weeks later (2026-09-07), the practical cost of the split has become visible:

1. The LLM call layer (`ac-verifier`) requires users to configure `AC_LLM_PROVIDER`, `AC_LLM_BASE_URL`, `AC_LLM_API_KEY`, `AC_LLM_MODEL`, `AC_LLM_TIMEOUT`, `AC_LLM_MAX_RETRIES`, `AC_LLM_MOCK`. None of these are needed when the executing AI agent is itself the LLM.
2. The actual verification prompt and verdict JSON schema are buried inside `_SYSTEM_PROMPT_TEMPLATE` and `_VERDICT_SCHEMA` in `skills/ac-verifier/scripts/ac_verifier.py`. Changes to the verification protocol require Python source edits instead of skill instruction edits.
3. The ac-verifier sub-skill is invoked from 6 distinct places: `_lib/cli/rdd_verify_cmd.py`, `_lib/cli/ac_verify_cmd.py`, `_lib/archive.sh`, `skills/rdd-verifier/scripts/run_verification.sh`, plus integration test suites. Each invocation site has to handle the shell-to-Python bridge and the env var forwarding.
4. Mock testing requires `_MOCK_SCENARIO` selection in CI, with `ac_verifier_mocks.py` providing 5 canned LLM responses that must stay synchronized with real LLM behavior.

The executing AI agent in OpenCode (or any AI assistant running `skill_use("rdd-verifier")`) is already an LLM with file-system tools, grep, glob, code graph search, and bash. It can perform AC verification directly using these tools, write the verdict JSON, write the cache, and write the audit log — without any external Python wrapper.

## Goals / Non-Goals

**Goals:**

- Move the LLM verification protocol (AC extraction rules, prompt template, verdict JSON schema, reasoning-keyword contract, persistence protocol) into `skills/rdd-verifier/SKILL.md` as a single source of truth.
- Eliminate all `AC_LLM_*` environment variables from the rdd-verifier workflow contract.
- Eliminate the external `ac-verifier` Python dependency from the rdd-verifier execution path.
- Preserve all data-layer contracts: SHA-bound verdict cache schema v2, per-change verifier loop state, heuristic classification, audit log format, exit codes 0/1/2/4.
- Provide a clear deprecation path for `rddf ac-verify`, the `ac-verifier` skill, and the `AC_LLM_*` environment variables.
- Preserve backward compatibility for at least one release cycle: `rddf ac-verify` continues to work as a thin shim that delegates to rdd-verifier.

**Non-Goals:**

- Do not change the SHA-bound verdict cache schema. Caches written by ac-verifier must remain readable by rdd-verifier and vice versa.
- Do not change the `_lib/verifier/classify.py` heuristic or the keyword sets. The new agent-driven verdict just needs to embed the same keywords in the reasoning field.
- Do not change the per-change verifier loop state format (`verifier_loop_schema.json` v2).
- Do not change the iteration schema or the per-change verification object added by `fix-rdd-verifier-lifecycle-dashboard`.
- Do not remove `ac-verifier/scripts/*` files in this change; they remain as a deprecated thin shim.
- Do not change the archive gate cache lookup logic; only the fallback to ac-verifier subprocess is removed.
- Do not retroactively rewrite existing verdict caches.

## Decisions

### 1. Inline the LLM Verification Protocol into rdd-verifier SKILL.md

Reasoning: The executing AI agent IS the LLM. There is no technical reason to ship the verification prompt as a separate Python module. Inline documentation is more discoverable, easier to update, and removes a layer of indirection.

**Decision:** The new SKILL.md adds a "LLM Verification Protocol" section (estimated 150 lines) that contains:

- **AC extraction rules** — regex for `## 验收标准` / `## Acceptance Criteria` headers, three bullet formats (`- ...`, `- [ ] ...`, `- [x] ...`), edge cases (missing section, empty bullets).
- **Evidence collection protocol** — tool priority chain (Read > Grep > Glob > codegraph_explore > Bash), per-AC minimum one tool call, three documented anti-patterns.
- **Verdict JSON schema** — strict array, length equals AC count, `ac_id`/`description`/`status`/`confidence`/`evidence`/`reasoning` fields, schema validation in the agent's response.
- **Reasoning-keyword contract** — drift keywords (`exists but`/`discrepan`/`mismatch`/`differs from ac`) checked first, gap keywords (`not implement`/`missing`/`absent`/`todo: implement`) second, conservative default `implementation_gap`.
- **Persistence protocol** — write `.rddf/state/.ac-verdict-<change>.json` (cache schema v2) and append to `.rddf/state/.ac-verification.jsonl` (audit log schema v1).
- **Exit code semantics** — 0 pass, 1 fail, 2 no-ACs, 3 LLM error, 4 halted (unchanged 0/1/2/4; 3 redefined).

**Alternatives considered:**

- *Keep ac-verifier as a thin Python wrapper, just remove AC_LLM_PROVIDER* — rejected because it still leaves the prompt in Python and keeps the shell-to-Python bridge complexity.
- *Move the prompt to a separate `prompts/verify.md` file referenced by SKILL.md* — rejected because it creates a second source of truth. The SKILL.md instruction block is the right place for an instruction-driven verification protocol.

### 2. Reassign exit code 3 from "ac-verifier internal error" to "LLM verification error"

Reasoning: v1.0 exit 3 meant "external LLM provider returned an error". In v2.0 the only way to fail with an "LLM error" is if the executing agent itself fails (context overflow, all tool calls failed, JSON parse of own output failed). The new semantics is documented in the SKILL.md exit code table.

**Alternatives considered:**

- *Add a new exit code (e.g., exit 5) for "agent failure"* — rejected because the caller-action mapping becomes ambiguous (1=route to plan/ship, 4=halted). Keeping the existing 4-slot contract simplifies integration.
- *Treat agent failure as halt immediately (exit 4)* — rejected because halt implies exhausted retry budget. An agent that fails on first try should not consume a retry loop slot.

### 3. Remove `ac-verifier` subprocess invocation from `_lib/archive.sh`

Reasoning: The archive gate already consumes the canonical SHA-bound verdict cache written by either rdd-verifier or the historical ac-verifier fallback. With rdd-verifier writing the cache directly, the fallback is no longer needed for new flows. Historical ac-verifier-written caches remain readable by the unchanged `_lib/verifier/cache.py::is_cache_fresh`.

**Decision:** Remove lines 397-470 of `_lib/archive.sh` that invoke `ac-verifier/scripts/ac_verifier.sh`. Keep the cache lookup logic (lines ~397-440 range). If the cache is missing or stale, the archive gate fails closed unless `SKIP_RDD_VERIFIER=yes` + `RDDF_VERIFIER_BYPASS_REASON` is set (the audited bypass path from `fix-rdd-verifier-lifecycle-dashboard`).

**Alternatives considered:**

- *Keep ac-verifier fallback for archive_gate_check only* — rejected because the dual-path is what created the original audit (4 scenarios in `verifier-archive-gate-clarification`). One canonical path is cleaner.

### 4. Drop the default verifier runner in `_lib/cli/rdd_verify_cmd.py`

Reasoning: v1.0's `default_runner()` function (lines 132-136) shells out to `ac-verifier/scripts/ac_verifier.sh` and parses its JSON output. In v2.0, the LLM work is done by the agent reading the SKILL.md, so the runner becomes a scan-and-stage helper instead of a LLM invocation.

**Decision:** Replace `default_runner()` with `stage_runner_context()` that writes a JSON context file at `.rddf/state/rdd-verify-context-<change>.json` describing what the agent should verify (proposal.md path, AC list, cache path, audit log path, expected verdict schema). The agent reads the context and writes the verdict JSON + cache + audit log directly. The CLI then re-reads the cache and produces the exit code.

**Alternatives considered:**

- *Delete `rddf rdd-verify` CLI entirely; rely on agent skill_use only* — rejected because the CLI provides the scan/discovery logic and exit code aggregation that an interactive skill cannot easily express.
- *Keep `default_runner()` calling ac-verifier.sh as a fallback* — rejected because the whole point of v2.0 is to remove that dependency.

### 5. Mark ac-verifier deprecated, do not delete in this change

Reasoning: `_lib/archive.sh`, `rddf ac-verify`, and 3 integration test files (`test_ac_verifier_skill.bats`, `test_ac_verifier_http_live.bats`, `test_ac_verifier_e2e.bats`) still reference ac-verifier. Removing them in one change would create too large a blast radius.

**Decision:**

- `skills/ac-verifier/SKILL.md` gets `user-invocable: false` + deprecation notice banner + migration table at the top.
- `ac-verifier/scripts/*` files remain for one to two release cycles.
- `_lib/cli/ac_verify_cmd.py` becomes a thin shim that delegates to `_lib/cli/rdd_verify_cmd.py`.
- All integration tests continue to pass against the shim.
- A follow-up change (next minor release) removes ac-verifier entirely.

**Alternatives considered:**

- *Delete ac-verifier immediately* — rejected because the `_lib/archive.sh` fallback path is still used by users who archive directly without rdd-verifier, and breaking that flow is a regression.
- *Keep ac-verifier indefinitely as a stable public API* — rejected because it doubles the LLM-protocol maintenance surface; the next minor release should remove it.

### 6. New ADR-0045 records the deprecation

Reasoning: ADR-0034 documents the original ac-verifier-as-backend design. A new ADR-0045 records the v2.0 redesign and supersedes the relevant sections of ADR-0034.

**Decision:** Create `docs/adr/ADR-0045-inline-ac-verifier-into-rdd-verifier.md` that:

- Documents the v1.0 → v2.0 transition rationale.
- Lists the contracts that are preserved (cache schema, classifier heuristic, loop state).
- Lists the contracts that change (exit code 3 semantics, env var requirements).
- Supersedes ADR-0034 §"State Machine" Step 2a-c (which assumed ac-verifier invocation).
- Marks ADR-0034 §"Sub-Skills Referenced" `ac-verifier` row as deprecated.

## Risks / Trade-offs

1. **Prompt drift.** The verification prompt is now in a markdown file instead of a Python string. Markdown rendering of code blocks (especially nested backticks in JSON examples) may differ from how the agent reads it. **Mitigation:** test the inlined protocol against a known proposal + code fixture in `tests/integration/test_rdd_verifier_self_contained.bats` and assert the verdict JSON matches the expected schema.

2. **Loss of provider-specific retry logic.** ac-verifier had `AC_LLM_MAX_RETRIES` with exponential backoff for 429/5xx errors. The agent-driven verification relies on the agent's own retry semantics (OpenCode's built-in). **Mitigation:** Document that the agent is responsible for retry; if a user needs explicit retry control, they can re-invoke `rddf rdd-verify` after the agent fails.

3. **Loss of mock-based CI testing.** ac-verifier's `AC_LLM_MOCK=yes` + `_MOCK_SCENARIO` allowed CI to test verdict-handling logic deterministically. With agent-driven verification, CI cannot deterministically mock the verdict. **Mitigation:** Focus CI tests on the data-layer contracts (cache schema, classify heuristic, loop state) which are unchanged. End-to-end agent verification is exercised in a separate nightly run, not in CI.

4. **Backward compatibility window for `rddf ac-verify` users.** External scripts that shell out to `rddf ac-verify <change>` will continue to work via the shim, but the shim introduces a new JSON context file write/read round trip. **Mitigation:** Document the shim path in the rdd-verifier SKILL.md "Migration from v1.0" table. The shim is on the deprecation removal track for the next minor release.

5. **Agent context budget.** Reading a large proposal.md + grepping the entire codebase + writing the verdict JSON consumes significant agent context. For changes with many ACs (10+) this could approach context limits. **Mitigation:** The SKILL.md instructs the agent to use targeted Grep/Glob queries rather than bulk reads. Future improvement: add a per-change AC count cap in the queue scanner.

6. **Heuristic classifier assumes LLM-rendered reasoning.** `_lib/verifier/classify.py::classify_failure` looks for English keywords (`exists but`, `discrepan`, `missing`, etc.) in the reasoning field. If the agent writes the reasoning in Chinese (since the rest of the SKILL.md is bilingual), the classifier may default to `implementation_gap` conservatively, which is still the safe behavior. **Mitigation:** The SKILL.md now documents that reasoning MUST embed English keywords regardless of UI language. A future improvement could add multilingual keyword sets to the classifier.
