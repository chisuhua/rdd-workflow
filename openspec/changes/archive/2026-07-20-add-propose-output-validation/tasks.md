## Tasks

### [1/4] Create propose_quality_check.py module
- [ ] Write 5 check functions in skills/propose/scripts/propose_quality_check.py
  - [ ] check_proposal_length(proposal_path) - min 500 chars, strip skeleton boilerplate
  - [ ] check_adr_references(proposal_path) - regex ADR-\d{4}, >=1 match
  - [ ] check_scope_sections(proposal_path) - In Scope + Out of Scope substrings
  - [ ] check_roadmap_alignment(name, project_root) - name in roadmap.md
  - [ ] check_tasks_completeness(tasks_path) - regex ^\s*-\s*\[ \], >=2 matches
- [ ] Add run_all_checks(name, project_root) aggregator
- [ ] Add __main__ CLI entry supporting --change <name> and --strict flags
- [ ] Honor STRICT_PROPOSE_GATE=yes env var (CLI --strict takes precedence)

### [2/4] Write unit tests
- [ ] Create tests/unit/test_propose_quality_check.py
- [ ] Cover all 5 check functions with pass/fail cases
- [ ] Cover edge cases: missing file, empty file, skeleton boilerplate, strict-mode exit code
- [ ] Follow pattern from tests/unit/test_deps_output.py (tmp_path fixtures, direct imports)

### [3/4] Verify and commit
- [ ] Run `python3 -m pytest tests/unit/test_propose_quality_check.py -q --tb=short`
- [ ] Run `python3 -m pytest tests/unit/ -q --tb=short` (full unit suite, no regressions)
- [ ] Stage only this change's files (not pre-existing working tree changes)
- [ ] Commit with message: `feat(propose): add propose_quality_check.py with 5 quality checks + STRICT_PROPOSE_GATE`

### [4/4] Update iteration.json
- [ ] Add or update change entry with status=proposed
