## Implementation Tasks

### Phase 1: Data Model + Core Logic (TDD)

- [x] 1.1 Add `AdrCodeVerification` dataclass to `skills/_lib/populate_lib.py` (fields: `adr_id`, `self_claim_version`, `code_symbols_found: list[str]`, `code_symbols_expected: list[str]`, `verification_status: Literal['confirmed','self-claim-only','placeholder-as-claimed','placeholder-but-exists']`, `has_discrepancy: bool`, `verified_at: str`, `mcp_used: bool`)
- [x] 1.2 Add `parse_symbols_from_adr_text(adr_text: str) -> list[str]` helper — regex for `` `func()` ``, `` `ClassName` ``, `` `module.py` ``, `def func`, `class Class`, `` `--flag``; filter code blocks
- [x] 1.3 Add `verify_adr_by_code(adr: AdrRecord, project_root: Path) -> AdrCodeVerification` — calls mcp first, fallback grep; applies 80% threshold for `confirmed`; populates all 4 statuses
- [x] 1.4 Add `verify_all_adrs(adrs: list[AdrRecord], project_root: Path) -> list[AdrCodeVerification]` — uses `concurrent.futures.ThreadPoolExecutor` (max 4 workers) to verify in parallel
- [x] 1.5 Add `load_supplementary_or_default(project_root: Path) -> dict[str, AdrCodeVerification]` — reads `.rddf/state/.populate-supplementary.json` or returns empty dict
- [x] 1.6 Add `save_supplementary(records: list[AdrCodeVerification], project_root: Path) -> None` — atomic write via `tempfile + os.replace`; validate against schema before write

### Phase 2: CLI Flag + Step 1.5 Orchestration (TDD)

- [x] 2.1 Modify `skills/_lib/populate.sh` (or wherever the CLI entry lives): add `--code-verify=off|on|strict` argparse-style flag parsing; default `off`
- [x] 2.2 Add Step 1.5 invocation in `populate.sh` between Step 1 (catalog) and Step 2 (fragment write): if `--code-verify=on|strict`, call `verify_all_adrs` → `save_supplementary`
- [x] 2.3 Add strict-mode exit-2 logic: if `any(r.has_discrepancy for r in records) and code_verify == 'strict'`, print discrepant ADR IDs to stderr and `exit 2`
- [x] 2.4 Add `--dry-run` integration: when set, `save_supplementary` is skipped (records printed to stdout for human review)
- [x] 2.5 Update `_format_adr_block` signature: add `verification: Optional[AdrCodeVerification] = None` parameter; when None, fall back to v1.0 marker

### Phase 3: Fragment Body Rendering (TDD)

- [x] 3.1 Add 4 badge formatters to `populate_lib.py`:
  - `_format_badge_confirmed(claim_version: str) -> str` → `*（已实施 v2.0.0+ + 代码验证）*`
  - `_format_badge_self_claim_only(claim_version: str) -> str` → `*（已实施 v2.0.0+ 仅自报）*`
  - `_format_badge_placeholder_but_exists() -> str` → `*（占位 + 代码已现 ⚠️）*`
  - `_format_badge_placeholder_as_claimed() -> str` → `*（占位 + 代码未现）*`
- [x] 3.2 Wire `_format_adr_block` to choose badge based on `verification.verification_status` when `--code-verify=on|strict`; v1.0 marker when off
- [x] 3.3 Verify `_format_adr_block` byte-identical output for `--code-verify=off` (regression test against `2b0991a` fragment body)

### Phase 4: Schema File

- [x] 4.1 Create `skills/_lib/schemas/populate_supplementary_schema.json` (v1) with fields: `version`, `generated_at`, `records[]` (each: `adr_id`, `self_claim_version`, `verification_status`, `code_symbols_found[]`, `code_symbols_expected[]`, `has_discrepancy`, `verified_at`, `mcp_used`)
- [x] 4.2 Add `version: 1` literal at top-level; consumers MUST reject `version: 0` or missing version field

### Phase 5: Unit Tests (≥8 cases)

- [x] 5.1 `test_verify_adr_by_code_confirmed` — ADR claims v2.0, code has 5/5 symbols → `confirmed`, `has_discrepancy=False`
- [x] 5.2 `test_verify_adr_by_code_self_claim_only` — ADR claims v2.0, code has 1/5 symbols (< 80%) → `self-claim-only`, `has_discrepancy=True`
- [x] 5.3 `test_verify_adr_by_code_placeholder_no_code` — ADR placeholder, code has 0 symbols → `placeholder-as-claimed`, `has_discrepancy=False`
- [x] 5.4 `test_verify_adr_by_code_placeholder_contradicts` — ADR placeholder, code has 1 symbol → `placeholder-but-exists`, `has_discrepancy=True`
- [x] 5.5 `test_parse_symbols_from_adr_text` — given sample ADR text, returns expected symbol list (filters code blocks, backtick patterns)
- [x] 5.6 `test_verify_all_adrs_parallel` — 5 ADRs verified, total wall-time < 2x single-ADR time (proves parallelism)
- [x] 5.7 `test_load_supplementary_or_default` — file missing → returns empty dict; file present → returns parsed records
- [x] 5.8 `test_supplementary_json_roundtrip` — write 3 records → read back → all fields match (validated against schema v1)
- [x] 5.9 `test_mcp_unavailable_falls_back_to_grep` — monkeypatch mcp check to fail; verify grep path executes and emits warning
- [x] 5.10 `test_strict_mode_exit_2_on_discrepancy` — set up discrepancy; call populate with `--code-verify=strict`; assert exit code 2 and stderr contains ADR ID

### Phase 6: Integration Tests (≥4 cases)

- [x] 6.1 `code-verify off: same output as v1.0` — run `populate-roadmap-from-arch --yes --code-verify=off`; diff against v1.0 fixture SHALL be empty
- [x] 6.2 `code-verify on: new badges appear` — run with `--code-verify=on`; fragment body SHALL contain all 4 badge types across the 4 ADRs in fixture set
- [x] 6.3 `code-verify strict: exit 2 on discrepancy` — set up fixture with 1 discrepancy; run with `--code-verify=strict`; assert exit code 2
- [x] 6.4 `code-verify on fallback: grep works without mcp` — set `RDD_NO_MCP=1` env var; run with `--code-verify=on`; assert warning emitted, supplementary.json still written, badges still rendered

### Phase 7: Documentation (SKILL.md)

- [x] 7.1 Update `skills/populate-roadmap-from-arch/SKILL.md` (or wherever the SKILL lives):
  - Add `--code-verify` / `--code-verify=strict` / `--no-code-verify` to CLI flag table
  - Update state-machine diagram to include Step 1.5
  - Add "已实施能力" badge legend (4 types)
  - Add "Known Limitations" entry: codebase-memory-mcp availability note
  - Add "Recommended CI Integration" section (no yml shipped, just guidance)
- [x] 7.2 Update `openspec/specs/populate-code-verification/spec.md` (already created in design phase) — leave as-is, this is the source of truth

### Phase 8: Verification & Cleanup

- [x] 8.1 Run `./test.sh --full --regression` — confirm no new failures vs `tests/KNOWN_FAILURES.txt` baseline
- [x] 8.2 Run `./test.sh --python --unit` — confirm new `tests/unit/test_populate_lib.py` ≥ 8 cases pass
- [x] 8.3 Run `bats tests/integration/test_populate_roadmap_from_arch.bats` — confirm ≥ 4 new cases pass
- [x] 8.4 Run `./test.sh --full --no-color | grep -E "FAIL|ERROR"` — confirm zero new failures
- [x] 8.5 (Manual) Verify `populate-roadmap-from-arch --code-verify=off` produces byte-identical output to v1.0 (`git diff` against `2b0991a` baseline empty)
- [x] 8.6 (Manual) Verify `populate-roadmap-from-arch --code-verify=on` writes `.rddf/state/.populate-supplementary.json` and renders 4 badge types in fragment body
- [x] 8.7 (Manual) Verify `populate-roadmap-from-arch --code-verify=strict` exits 2 on fixture with 1 discrepancy

### Out-of-Scope (deferred to follow-up proposals)

- CI workflow YAML for `--code-verify=strict`
- LLM-based semantic verification
- Cross-repo code verification (Hub handles per ADR-0030)
- Historical fragment backfill
- Modification to `rdd-doctor` roadmap-refs category