## Implementation Tasks

### Phase 0: SKILL.md Documentation Layer (already completed 2026-09-07)

- [x] 1. Rewrite `skills/rdd-verifier/SKILL.md` to v2.0. Inline "LLM Verification Protocol" section with AC extraction rules, evidence collection protocol, verdict JSON schema, reasoning-keyword contract, persistence protocol, and exit code table. Remove all references to `ac-verifier` subprocess invocation. Remove `AC_LLM_*` environment variables from the contract. Add frontmatter `version: 2.0`, `user-invocable: true`, `deprecated-relation.deprecates: skills/ac-verifier/SKILL.md`. Add "Migration from v1.0" table.
- [x] 2. Mark `skills/ac-verifier/SKILL.md` as deprecated. Set frontmatter `user-invocable: false`. Add `metadata.deprecated` block with `deprecated_in`, `deprecated_by`, `reason`, `removal_target`, `migration`. Add ⚠️ DEPRECATED banner at top of document with migration table.

### Phase 1: Skill Architecture Cleanup

- [x] 3. Update `skills/rdd-verifier/scripts/run_verification.sh`. Replace ac-verifier subprocess invocation with agent-context-stage pattern. The script writes a JSON context file at `.rddf/state/rdd-verify-context-<change>.json` describing what the agent should verify (proposal.md path, AC list, cache path, audit log path, expected verdict schema). Drop the inline Python that wraps `_lib/verifier/cache.py::verdict_cache`. Add tests for context file shape.
- [x] 4. Delete or annotate `skills/ac-verifier/scripts/ac_verifier.sh` and `skills/ac-verifier/scripts/ac_verifier.py`. Add a top-of-file deprecation comment block referencing rdd-verifier v2.0 and pointing to the migration path. Do NOT delete the file yet (shim period).
- [x] 5. Mark `skills/ac-verifier/scripts/llm_providers/*.py` as deprecated (4 files: openai.py, anthropic.py, ollama.py, minimax.py). Each file gets a deprecation docstring and a `DeprecationWarning` on import. Keep behavior unchanged for one release cycle.

### Phase 2: CLI Layer Refactor

- [x] 6. Rewrite `_lib/cli/rdd_verify_cmd.py::default_runner` (lines 132-136). Replace shell-out to ac-verifier with `stage_runner_context(change)` that writes the context JSON file. The CLI no longer invokes an LLM; the agent does that by reading the context file. Keep the cache-hit path unchanged.
- [x] 7. Convert `_lib/cli/ac_verify_cmd.py` to a thin shim. The CLI entry point reads `<change>`, optionally `--dry-run`, and delegates to `_lib/cli/rdd_verify_cmd.py::cmd_rdd_verify(<change> --single)`. Keep exit codes mapped 0/1/2/3. Add deprecation banner at top of file.
- [x] 8. Update `_lib/cli/__init__.py` (line 79 `"ac-verify": "skills._lib.cli.ac_verify_cmd:cmd_ac_verify"`) with a comment noting the entry is deprecated but retained for backward compatibility.

### Phase 3: Archive Gate Cleanup

- [x] 9. Remove ac-verifier subprocess invocation from `_lib/archive.sh::archive_gate_check` (lines 397-470). Keep the cache lookup logic. If cache is missing or stale, fail closed unless `SKIP_RDD_VERIFIER=yes` + `RDDF_VERIFIER_BYPASS_REASON` is set (audited bypass path already exists from `fix-rdd-verifier-lifecycle-dashboard`). Update line 402 comment that references `ac-verifier/scripts/ac_verifier.sh`.
- [x] 10. Add tests covering: cache hit (archive succeeds), cache stale (archive fails with clear message), cache missing + `SKIP_RDD_VERIFIER=yes` + reason set (archive succeeds with bypass), cache missing + bypass unset (archive fails closed). Place tests in `tests/integration/test_archive_gate_no_ac_fallback.bats`.

### Phase 4: Test Suite Migration

- [x] 11. Add `tests/unit/test_rdd_verifier_protocol.py`. Cover AC extraction regex (3 bullet formats), verdict JSON schema validation, reasoning keyword embedding requirement, cache file v2 schema write/read, audit log JSONL append semantics. Source fixtures from `tests/fixtures/rdd-verifier-protocol/`.
- [x] 12. Add `tests/integration/test_rdd_verifier_self_contained.bats`. Exercise the full pipeline: write fixture proposal.md → invoke scan_queue → invoke the new run_verification.sh context-staging → simulate agent verdict writeback → verify cache and audit log shape. At least 4 test cases: all-pass, one-fail-classified-gap, one-fail-classified-drift, no-AC pass-through.
- [x] 13. Mark `tests/unit/test_ac_verifier_providers.py`, `tests/unit/test_ac_verifier.py`, `tests/unit/test_ac_verdict_cache_schema.py` as deprecated (add `# DEPRECATED: see test_rdd_verifier_protocol.py per ADR-0045` at top). Do not delete in this change.
- [x] 14. Mark `tests/integration/test_ac_verifier_skill.bats`, `tests/integration/test_ac_verifier_http_live.bats`, `tests/integration/test_ac_verifier_e2e.bats` as deprecated. Each gets a top-of-file deprecation banner. Do not delete in this change.

### Phase 5: Documentation and ADR

- [x] 15. Create `docs/adr/ADR-0045-inline-ac-verifier-into-rdd-verifier.md` documenting the v1.0 → v2.0 transition rationale, preserved contracts, changed contracts, and superseded sections of ADR-0034.
- [x] 16. Update `AGENTS.md` table row for `rdd-verifier` (line 94): change "批量调 ac-verifier, 启发式分类 AC pass/fail, 失败回 plan/ship" to "self-contained LLM verification (LLM Verification Protocol in SKILL.md), 启发式分类, 失败回 plan/ship".
- [x] 17. Update `README.md` table row for `rdd-verifier` (line 96): change "批量 AC 验证 + 启发式分类 + 失败回 plan/ship" to "self-contained AC verification (inlined LLM protocol in SKILL.md) + 启发式分类 + 失败回 plan/ship". Update architecture diagram if present.
- [x] 18. Update `docs/superpowers/specs/2026-08-26-rdd-verifier-design.md` with a v2.0 addendum at the top: "Superseded sections: §State Machine Step 2a-c (ac-verifier subprocess removed). See ADR-0045 for the new architecture. v1.0 design preserved below for historical reference."
- [x] 19. Annotate `docs/superpowers/specs/2026-08-17-ac-verifier-skill-design.md` with a deprecation notice at the top: "DEPRECATED 2026-09-07 per ADR-0045. Replaced by `skills/rdd-verifier/SKILL.md` v2.0 LLM Verification Protocol. See ADR-0045 for migration path."

### Phase 6: Final Validation

- [x] 20. Run repository-mandated `./test.sh --full --regression` before archive. Record any pre-existing baseline failures separately from new failures (per `add-full-regression-gate`).
- [x] 21. Verify no remaining `AC_LLM_*` references in skills/ or _lib/ outside of `ac-verifier/scripts/` (which are kept as shim).
- [x] 22. Verify no remaining `ac-verifier/scripts/ac_verifier.sh` invocations outside `_lib/cli/ac_verify_cmd.py` (shim) and `tests/integration/test_ac_verifier_*.bats` (deprecated tests).
- [x] 23. Update `openspec/specs/verifier-lifecycle/spec.md` to reflect the new architecture: replace "THEN it invokes ac-verifier" with "THEN the agent performs LLM verification per the LLM Verification Protocol in skills/rdd-verifier/SKILL.md".
