# gate-mechanism delta

## MODIFIED Requirements

### Requirement: gate-mechanism-plugin-api

The system SHALL allow extension via plugins loaded from `.rdd-workflow/plugins/`.

**All shell scripts that reference `_lib` shared libraries SHALL use `resolve_rdd_lib_dir()` to resolve the `_lib` directory path instead of hardcoded `$PROJECT_ROOT/skills/_lib/` paths.**

#### Scenario: Plugin registers custom check

- **WHEN** a plugin in `.rdd-workflow/plugins/` registers a gate check via `register_gate_check()`
- **THEN** the check SHALL be executed during the corresponding phase transition
- **AND** plugin scripts SHALL resolve `_lib` paths via `resolve_rdd_lib_dir()` when sourced from SKILL.md code blocks

#### Scenario: Global installation gate scripts

- **GIVEN** rdd-workflow is installed globally via `install.sh --global`
- **WHEN** gate-related shell scripts (e.g., `plan_done_gate.sh`, `arch_done_gate.sh`) execute
- **THEN** all `_lib` references SHALL resolve to `$HOME/.agents/skills/_lib/`
- **AND** cross-skill references (e.g., `propose/scripts/validate_baseline.py`) SHALL resolve via `resolve_rdd_skill_dir()`
