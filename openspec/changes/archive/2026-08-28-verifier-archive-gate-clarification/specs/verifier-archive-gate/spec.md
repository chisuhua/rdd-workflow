# Verifier-Archive Gate Boundary Capability

## ADDED Requirements

### Requirement: ADR-0035 documents verifier/archive dual-track boundary

The system SHALL create `docs/adr/ADR-0035-verifier-archive-gate-boundary.md` documenting the boundary between `rdd-verifier` (5th phase, default-required) and `archive_gate_check` (in-archive fallback) per ADR-0034 §5.

The ADR SHALL cover 4 scenarios: standard (rdd-verifier), fallback (archive_gate_check inlined ac-verifier), halted (verifier triggered max_loops, exit 4), and on-main mode (tools/archive_on_main.sh bypass).

#### Scenario: ADR-0035 enumerated scenarios

- **WHEN** reviewer reads ADR-0035
- **THEN** all 4 scenarios are explicitly enumerated
- **AND** the trade-off between token savings (skip verifier) and lost failure-loop capability is documented

### Requirement: STRICT_AC_GATE escalation token

When `STRICT_AC_GATE=yes`, the `SKIP_RDD_VERIFIER=yes` bypass SHALL be ignored and treated as fatal error (refuses to archive).

#### Scenario: STRICT_AC_GATE blocks bypass

- **WHEN** user sets `STRICT_AC_GATE=yes` and `SKIP_RDD_VERIFIER=yes`
- **THEN** `archive_gate_check` rejects the bypass
- **AND** emits "🚫 STRICT_AC_GATE active; SKIP_RDD_VERIFIER bypass refused" error

#### Scenario: STRICT_AC_GATE absent permits bypass

- **WHEN** only `SKIP_RDD_VERIFIER=yes` is set (default STRICT_AC_GATE=no)
- **THEN** archive proceeds via fallback ac-verifier path
- **AND** cache is written with `ran_by=archive_gate_check` field

### Requirement: archive_gate_check top-of-file reference

The `_lib/archive.sh::archive_gate_check` function SHALL have a top comment referencing ADR-0035 §1 so future maintainers understand the dual-track design.

#### Scenario: archive_gate_check header cites ADR-0035

- **WHEN** developer reads the first 20 lines of `_lib/archive.sh`
- **THEN** the comment SHALL contain "ADR-0035" or "verifier-archive-gate boundary"
