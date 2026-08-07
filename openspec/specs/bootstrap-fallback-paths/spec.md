# bootstrap-fallback-paths Specification

## Purpose
TBD - created by archiving change fix-bootstrap-fallback-paths. Update Purpose after archive.
## Requirements
### Requirement: External projects use the installed global skill root
The workflow SHALL resolve the global skill root from `$HOME/.agents/skills/_lib/skill_root.sh` when a project-local skill root is absent.

#### Scenario: Project-local skill root is absent
- GIVEN an external git project with no `.opencode/_lib/skill_root.sh`
- AND the global install contains `~/.agents/skills/_lib/skill_root.sh`
- WHEN a phase helper executes its fallback bootstrap
- THEN the global resolver is loaded successfully

#### Scenario: Obsolete fallback is not used
- GIVEN the repository's runtime scripts and SKILL.md examples
- WHEN the bootstrap fallback paths are scanned
- THEN no supported surface references `$HOME/.agents/_lib/skill_root.sh`

