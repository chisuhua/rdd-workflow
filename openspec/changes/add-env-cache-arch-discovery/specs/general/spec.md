## ADDED Requirements

### Requirement: general-add-env-cache-arch-discovery
The system SHALL persist auto-discovered third-party project artifact paths (ADR directory, roadmap path, architecture directory, ADR pattern) into `.env-cache.json` on first `rdd-env-check` run, and downstream consumers SHALL prefer this cache over the default convention.

#### Scenario: First run captures discovered paths
- **WHEN** `rdd-env-check` runs in a project with a custom ADR directory (e.g. `documentation/decisions`) and a non-default pattern (e.g. `RFC-*.md`)
- **AND** `.env-cache.json` does not exist (cache miss) or `cache.branch` differs from the current branch
- **THEN** env-check invokes `discover-arch-artifacts.sh::discover_all()`
- **AND** `.env-cache.json` records `discovered_adr_dir`, `discovered_roadmap_path`, `discovered_architecture_dir`, `discovered_adr_pattern`
- **AND** downstream consumers (`_read_arch_handoff_paths()` in `gate.py` and `detectors.py`) read the cache and use the discovered paths instead of hardcoded defaults

#### Scenario: Cache hit avoids re-scan
- **WHEN** `.env-cache.json` exists within TTL (3600s) and `cache.branch` matches `git branch --show-current`
- **THEN** env-check does NOT invoke `discover-arch-artifacts.sh` again
- **AND** consumers read `discovered_*` fields directly from cache

#### Scenario: Branch switch invalidates cache
- **WHEN** `cache.branch` differs from the current branch
- **THEN** env-check invalidates the existing cache
- **AND** runs `discover_all()` against the new branch state
- **AND** rewrites `.env-cache.json` with updated `branch` and `discovered_*` fields

#### Scenario: SKIP_AUTO_DISCOVERY opt-out preserves old behavior
- **WHEN** `SKIP_AUTO_DISCOVERY=yes` is set in the environment
- **THEN** env-check does NOT invoke `discover-arch-artifacts.sh`
- **AND** does NOT modify any `discovered_*` fields in cache
- **AND** prints `✅ Skip discovery (SKIP_AUTO_DISCOVERY=yes)` as visible confirmation

#### Scenario: Old 10-field cache files remain backward-compatible
- **WHEN** a pre-existing `.env-cache.json` (created before this change) lacks `discovered_*` fields
- **THEN** `_read_arch_handoff_paths()` returns the hardcoded default values for missing fields
- **AND** does NOT throw any exception
- **AND** behaves identically to the pre-change implementation for those fields

#### Scenario: Read-side fallback priority is env-cache > handoff > default
- **WHEN** `_read_arch_handoff_paths()` is called
- **THEN** it reads `discovered_adr_dir` (and 3 siblings) from `.env-cache.json` first
- **IF** any discovered field is absent or empty, it falls back to `.arch-handoff.json`
- **IF** handoff is also absent, it falls back to the hardcoded default (`docs/adr` / `roadmap.md` / `docs/architecture` / `ADR-*.md`)

#### Scenario: Discovery cache miss path is fast
- **WHEN** env-check runs in cold cache mode on a third-party project
- **THEN** the cache miss + discover + persist path completes in under 200ms
- **AND** does NOT invoke any `git` or `openspec` subprocess (pure filesystem walk)