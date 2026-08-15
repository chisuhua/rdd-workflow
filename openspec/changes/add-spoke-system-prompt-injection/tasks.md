# add-spoke-system-prompt-injection Tasks

## Implementation Tasks

- [ ] Create `skills/spoke-system-prompt-injection/SKILL.md` — skill definition for spoke-system-prompt-injection
- [ ] Create `skills/spoke-system-prompt-injection/templates/cursor.cursorrules` — Cursor `.cursorrules.cross-repo-hub` template
- [ ] Create `skills/spoke-system-prompt-injection/templates/cline.clinerules` — Cline `.clinerules.cross-repo-hub` template
- [ ] Create `skills/spoke-system-prompt-injection/templates/continue.rules.md` — Continue `.continue/rules/cross-repo-hub.md` template
- [ ] Create `skills/spoke-system-prompt-injection/templates/copilot.instructions.md` — GitHub Copilot `.github/copilot-instructions.md` template
- [ ] Create `skills/spoke-system-prompt-injection/templates/claude.CLAUDE.md` — Claude Code `CLAUDE.md` template
- [ ] Create `skills/spoke-system-prompt-injection/inject.md` — canonical protocol content with `protocol_version: 1.0`, containing RFC initiation, RFC review, sync, and auto-approval prohibition
- [ ] Create `skills/spoke-system-prompt-injection/scripts/deploy.sh` — deployment script with `--tools`, `--uninstall`, `--status` flags and tool detection
- [ ] Create `skills/spoke-system-prompt-injection/scripts/deploy.sh` idempotency logic using `<!-- RDD-HUB-PROTOCOL-START -->` marker detection
- [ ] Create `skills/spoke-system-prompt-injection/scripts/deploy.sh` backup logic creating `{filename}.bak.YYYYMMDD` before modification
- [ ] Create `skills/spoke-system-prompt-injection/scripts/deploy.sh` uninstall logic removing bounded protocol block and restoring from backup
- [ ] Create `skills/spoke-system-prompt-injection/scripts/deploy.sh` multi-tool support with comma-separated `--tools` list
- [ ] Add `--spoke-init` subcommand to `install.sh` invoking `deploy.sh --tools all` (or specified tools)
- [ ] Add `--spoke-init --tools` flag to `install.sh` to pass tool list to `deploy.sh`
- [ ] Add `docs/spoke-system-prompt.md` — user-facing documentation for Spoke AI protocol injection
- [ ] Create `tests/integration/test_spoke_injection.bats` with deploy test case
- [ ] Create `tests/integration/test_spoke_injection.bats` with idempotent re-run test case
- [ ] Create `tests/integration/test_spoke_injection.bats` with multi-tool deployment test case
- [ ] Create `tests/integration/test_spoke_injection.bats` with uninstall test case
- [ ] Create `tests/integration/test_spoke_injection.bats` with backup creation test case
- [ ] Verify all five templates contain equivalent protocol semantics (RFC initiation, review, sync, prohibition)
- [ ] Verify `deploy.sh --tools cursor` appends Hub protocol to `.cursorrules` successfully
- [ ] Verify running `deploy.sh` twice produces identical output (no duplicate injection)
- [ ] Verify `--uninstall` removes protocol block and restores from backup
- [ ] Verify `install.sh --spoke-init` runs successfully in a new project
- [ ] Update README §跨项目协同 chapter with Spoke 接入指南 referencing deploy.sh usage
