## Implementation Tasks

### Phase 1: P1 verdict 完整性校验（oracle 风险1）

- [ ] 1. Add `validate_verdict_completeness(verdict, acs) -> tuple[valid, problems]` in `_lib/verifier/protocol.py`. Checks: array length == len(acs), ac_id set equality (no missing, no unknown, no duplicate). Returns problems as list of "<ac_id>: <reason>". Pure function.
- [ ] 2. In `_lib/cli/rdd_verify_cmd.py::run_one_change`, call `validate_verdict_completeness` on the verdict before `verdict_cache()` write. If problems exist: log to audit, mark `state="failed"` with `failed_acs=["<completeness-failure>"]`, skip cache write. Add unit test `test_run_one_change_incomplete_verdict_marks_failed`.
- [ ] 3. In `_lib/cli/rdd_verify_cmd.py::run_one_change`, call `validate_verdict_completeness` on cached verdict (cache-hit path). If problems: log warning, treat cache as stale (force re-run). Add unit test `test_run_one_change_stale_incomplete_cache_triggers_rerun`.
- [ ] 4. In `_lib/archive.sh::archive_gate_check`, after cache read + cache_hit check, invoke `_lib/cli/rdd_verify_cmd.py::validate_verdict_completeness_via_subprocess` (Python helper exposed via `_lib/cli/__init__.py`) to verify cache verdict. Fail closed if problems. Use env-var passing (Oracle C1) per AGENTS.md common-pitfall #18.

### Phase 2: P2 schema 严格化（oracle 风险2）

- [ ] 5. Update `VERDICT_ITEM_SCHEMA` in `_lib/verifier/protocol.py`: `evidence` minItems=1, `reasoning` minLength=1, `status` enum unchanged.
- [ ] 6. Update `validate_verdict_items` to enforce: `pass`/`partial` paths require evidence non-empty; `fail`/`partial` paths require reasoning non-empty AND contains at least one drift/gap keyword (use `DRIFT_KEYWORDS + GAP_KEYWORDS`).
- [ ] 7. Add unit tests: `test_validate_verdict_items_pass_requires_evidence`, `test_validate_verdict_items_fail_requires_keyword`, `test_validate_verdict_items_partial_requires_evidence`, `test_validate_verdict_items_partial_requires_keyword`.
- [ ] 8. Update `skills/rdd-verifier/SKILL.md` § "LLM Verification Protocol" Step 3 with explicit "evidence minItems=1, fail reasoning must contain drift/gap keyword" callout.

### Phase 3: P2 卫生（oracle 风险3）

- [ ] 9. Fix `_lib/cli/rdd_verify_cmd.py:332` import: replace `from skills._lib.verifier.discovery import discover_archived` with `from _lib.verifier.discovery import discover_archived`. AGENTS.md rule 25.
- [ ] 10. Mark `_default_runner = _stage_context_runner` alias as deprecated-for-removal: add docstring `"""Deprecated alias for _stage_context_runner; will be removed in next minor release per ADR-0045 shim close."""`. Add TODO comment for `remove-ac-verifier-completely` change.
- [ ] 11. Update `_lib/cli/__init__.py` route comment to reference deprecation timeline.

### Phase 4: P2 exit-2 语义统一（oracle 风险4）

- [ ] 12. In `_lib/cli/rdd_verify_cmd.py::run_one_change`, change exit_code=2 mapping: `vstate="pending"` (was "skipped"), `route="pending-agent"` (was "halted"). Skip verdict_cache write. Write audit `pending` event.
- [ ] 13. In `_lib/cli/rdd_verify_cmd.py::aggregate_exit`, verify `pending` keeps score 0 (already in priority dict — verify and add unit test).
- [ ] 14. Add unit test `test_run_one_change_exit2_maps_to_pending` and `test_aggregate_exit_pending_does_not_block`.
- [ ] 15. Update `openspec/specs/verifier-archive-gate/spec.md` scenario "STRICT_AC_GATE absent permits bypass" wording for v2.0 semantics (cached pending → bypass permitted).

### Phase 5: P3 健壮性（oracle 风险5）

- [ ] 16. In `_lib/verifier/protocol.py::stage_verification_context`, change `out.write_text(...)` to temp-file + atomic rename (`tmp.replace(out)`).
- [ ] 17. In `_lib/verifier/cache.py::read_verdict_cache`, add schema_version fail-closed: if `schema_version != 2` (missing/1/unknown), return None. Add module docstring note: "v1 was ac-verifier era, deprecated by ADR-0034, superseded by ADR-0045; reads fail-closed."
- [ ] 18. In `_lib/verifier/protocol.py::validate_verdict_items`, change jsonschema ImportError fallback to log warning + return problems list with single entry "schema validator unavailable; structural-only check passed (or failed)" — never silently accept. Add unit test for jsonschema-unavailable path.
- [ ] 19. Add unit tests for schema_version compat: `test_read_verdict_cache_v1_returns_none`, `test_read_verdict_cache_unknown_version_returns_none`, `test_read_verdict_cache_missing_version_returns_none`.

### Phase 6: Oracle 推荐 5 个补测

- [ ] 20. Add `test_run_one_change_staged_to_pending_mapping`: mock runner returns `{"staged": True, "context_path": "..."}` → assert state="pending", route="pending-agent", NO verdict_cache write, audit `pending` event written.
- [ ] 21. Add `test_validate_verdict_items_required_fields_missing` (no `confidence`/`status` → problems non-empty).
- [ ] 22. Add `test_validate_verdict_completeness_three_scenarios` (length mismatch, unknown ac_id, duplicate ac_id).
- [ ] 23. Add `test_zero_ac_context_pass_through`: build_verification_context for proposal with `## 验收标准\n(no bullets)` → ac_count=0; cmd_rdd_verify --stage exits 0 with pass-through message.
- [ ] 24. Add integration bats `test_rdd_verifier_self_contained.bats` case "agent writes incomplete verdict (1 of N ACs)" → assert rdd-verify marks failed, NO archive pass-through. Place in `tests/integration/test_archive_gate_no_ac_fallback.bats` for archive-gate path coverage.

### Phase 7: 跨阶段 follow-up 调度（oracle Q3）

- [ ] 25. Add `_lib/planner_*.py::scan_deprecated_skills(skills_dir)` helper: read `skills/<name>/SKILL.md` frontmatter, extract `metadata.deprecated` or `user-invocable: false`, return list of `{name, reason, removal_target, migration}`. Add `_lib/planner_*.py` test.
- [ ] 26. Integrate scan_deprecated_skills into propose stage (Planner Phase 1): surface deprecated skill list as suggestion in proposal-suggestions.md (not blocking). Add unit test for output format.
- [ ] 27. Schedule `remove-ac-verifier-completely` change in `proposal-approved.md` with manual_deps `[inline-ac-verifier-into-rdd-verifier, verifier-v2-hardening]`. The skeleton change tasks.md: delete `skills/ac-verifier/` + scripts + providers + mocks; remove `_default_runner` alias; ac-verify CLI route → friendly error; strip deprecation banners from test files; post-removal regression bats.
- [ ] 28. Add `openspec/changes/remove-ac-verifier-completely/` directory (skeleton only — not full propose, just registration). Tasks.md stub with `manual_deps: [inline-ac-verifier-into-rdd-verifier, verifier-v2-hardening]`.
- [ ] 29. Create `docs/superpowers/specs/verifier-protocol-template.md`: 5-section template spec documenting "SKILL.md § Protocol + `_lib/<phase>/protocol.py` data layer + staged context + agent writeback + SHA cache + fail-closed gate" shared pattern. Includes naming convention for staged context files (`rdd-<phase>-context-<change>.json`), cache schema v2 consistency requirements, fail-closed gate semantics.
- [ ] 30. Add cross-stage follow-up items to `proposal-approved.md`: (a) audit `propose_quality_check.py` for external LLM/hook coupling; (b) audit `arch_quality_gate.py` for same; (c) first application of `verifier-protocol-template` (rdd-arch gap analysis) — as future change candidates.

### Phase 8: 文档与 ADR

- [ ] 31. Append "v2.0 closure fix addendum" to `docs/adr/ADR-0045-inline-ac-verifier-into-rdd-verifier.md` referencing this change and the oracle review.
- [ ] 32. Update `openspec/specs/verifier-lifecycle/spec.md`: add Scenario "verdict completeness is enforced" covering `validate_verdict_completeness` + cache- fail-closed on incomplete. Add Scenario "evidence non-empty required for pass/fail".
- [ ] 33. Update `openspec/specs/verifier-archive-gate/spec.md`: add Scenario "incomplete verdict cache fails archive gate" (P1 closure).
- [ ] 34. Update `AGENTS.md` `rdd-verifier` row: note `_default_runner` scheduled for removal in next minor per `remove-ac-verifier-completely`.
- [ ] 35. Add `CHANGELOG.md` entry for this change under `## Unreleased`.

### Phase 10: Final Validation

- [ ] 36. Run `./test.sh --full --regression` before archive. Verify 0 new bats failures. Pre-existing pytest failures must remain unchanged (verified via git stash + diff).
- [ ] 37. Verify `validate_verdict_completeness` is called in both `run_one_change` and `archive_gate_check` paths (grep + unit test coverage).
- [ ] 38. Verify `_lib/cli/rdd_verify_cmd.py` has no `from skills._lib` imports remaining (only `_lib.*`).
- [ ] 39. Verify `read_verdict_cache` rejects schema_version != 2 with None (unit test confirms).
- [ ] 40. Verify `openspec/specs/verifier-protocol-template.md` exists and is referenced from proposal-approved.md follow-up.