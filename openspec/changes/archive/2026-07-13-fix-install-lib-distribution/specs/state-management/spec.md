---
SCOPE: shared
STATUS: PROPOSED
DATE: 2026-07-13
CHANGE: fix-install-lib-distribution
RELATED: sync-workflow-contracts (unblocks Decision 1 A-flip); add-rddf-session (rddf-session skill ship); feature-management (feature skill ship)
RELATED_INCIDENT: 2026-07-13 Oracle consultation surfaced that feature.md and rddf-session.md declare depends-on _lib modules that are not distributed by install.sh / INSTALL.md
---

# Capability: state-management

> Add install-time contract for `skills/_lib/*.py` distribution so that skills declaring `depends-on` on `_lib` modules (notably `feature.md` and `rddf-session.md`) actually work for users who install via npm or the INSTALL skill.

> **Status**: Spec delta (PROPOSED). Locks the install distribution contract introduced by change `fix-install-lib-distribution`.

## ADDED Requirements

### Requirement: install-distributes-lib-modules

The system SHALL distribute `skills/_lib/*.py` and `skills/_lib/schemas/*.json` runtime modules when `install.sh` or `skills/INSTALL.md` is invoked, so that any user-facing skill declaring `depends-on` on a `_lib` module can import it post-install.

#### Scenario: install.sh copies _lib Python modules

- **WHEN** `install.sh` is invoked
- **AND** `$PACKAGE_DIR/skills/_lib` exists
- **THEN** the install script SHALL copy `*.py` files under `skills/_lib/` to the target's `.opencode/skills/rdd-workflow/skills/_lib/`
- **AND** the install script SHALL copy `*.json` files under `skills/_lib/schemas/` to the target's `.opencode/skills/rdd-workflow/skills/_lib/schemas/`
- **AND** the target's `skills/__init__.py` and `skills/_lib/__init__.py` SHALL exist as Python package markers

#### Scenario: install.sh excludes dev-only subdirectories

- **WHEN** `install.sh` traverses `$PACKAGE_DIR/skills/_lib`
- **THEN** it SHALL prune the following subdirectories before copy:
  - `__pycache__/` (Python bytecode cache, host-pollution source)
  - `plugins/` (extension points for detectors/actions; dev-only, currently README.md only)
  - `schedulers/` (LoopEngine cron/fs/git/webhook schedulers; v3 candidate, not enabled in production skills)
- **AND** the install SHALL NOT copy any file under those directories

#### Scenario: skills/INSTALL.md mirrors install.sh behavior

- **WHEN** `skills/INSTALL.md` Step 3 (复制所有子技能) is executed by an AI assistant
- **THEN** it SHALL also copy `skills/_lib/*.py` and `skills/_lib/schemas/*.json`
- **AND** it SHALL exclude `__pycache__/` / `plugins/` / `schedulers/`
- **AND** it SHALL emit a one-line note telling the user to ensure project root is on `sys.path` for `from skills._lib.X import Y` to resolve

#### Scenario: depends-on declaration resolves post-install

- **WHEN** a user installs via `install.sh` or `skills/INSTALL.md`
- **AND** the installed `skills/feature.md` declares `depends-on: [iteration, deps_output]`
- **AND** the installed `skills/rddf-session.md` declares `depends-on: [rddf_session]`
- **THEN** `python3 -c "from skills._lib.iteration import save"` SHALL succeed without ModuleNotFoundError
- **AND** `python3 -c "from skills._lib.rddf_session import RddfSessionCoordinator"` SHALL succeed

### Requirement: install-skills-list-stays-in-sync

The system SHALL prevent `package.json::skills[]` (the source of truth for npm publish surface) from drifting out of sync with `skills/*.md` files on disk and with `skills/INSTALL.md` description text.

#### Scenario: INSTALL.md fallback string lists all current skills

- **WHEN** the source `package.json::skills[]` contains N entries
- **THEN** `skills/INSTALL.md` L115 and L118 fallback strings SHALL contain the same N names
- **OR** `skills/INSTALL.md` SHALL derive the list dynamically from `package.json` via `python3 -c "import json; ..."` so the fallback can never disagree with upstream

#### Scenario: INSTALL.md description does not enumerate skill names

- **WHEN** `skills/INSTALL.md` description field is read
- **THEN** it SHALL NOT contain a comma-/slash-separated enumeration of skill names inside a parenthetical
- **AND** it SHALL state the skill count numerically (matching `len(skills/*.md)`)
- **AND** the claimed count SHALL match the actual number of `.md` files under `skills/`

#### Scenario: anti-drift test catches _lib distribution drift

- **WHEN** a contributor removes `skills/_lib/*.py` from `install.sh` or `skills/INSTALL.md` copy logic
- **AND** CI runs `bats tests/integration/test_install_lib_distribution.bats`
- **THEN** the test SHALL exit 1
- **AND** stderr SHALL identify which surface (install.sh vs INSTALL.md) lost the `_lib` copy step

#### Scenario: anti-drift test catches __init__.py removal

- **WHEN** a contributor deletes `skills/__init__.py` or `skills/_lib/__init__.py`
- **AND** CI runs `bats tests/integration/test_install_lib_distribution.bats`
- **THEN** the test SHALL exit 1
- **AND** stderr SHALL identify which marker file is missing

#### Scenario: anti-drift test catches __pycache__ pollution

- **WHEN** `install.sh` or `skills/INSTALL.md` copy logic loses its `__pycache__/` prune
- **AND** CI runs `bats tests/integration/test_install_lib_distribution.bats`
- **THEN** the test SHALL exit 1
- **AND** stderr SHALL mention `__pycache__` is no longer excluded

## MODIFIED Requirements

(none — this change adds a new contract surface without modifying existing state-management requirements)

## REMOVED Requirements

(none)

## RENAMED Requirements

(none)