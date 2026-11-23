# sync-agents-md-five-stage Specification

## Purpose
Regenerate the AGENTS.md feature-fragments sentinel block from the on-disk roadmap
fragments, so the agent-facing context file never drifts from
`.rddf/roadmap/features/`. Invoked by `rddf roadmap --update-agent-md`; the block is
regenerated in place and the surrounding content is left intact.
## Requirements
### Requirement: sync-agents-md-five-stage

`rddf roadmap --update-agent-md` SHALL rewrite the block delimited by
`<!-- AUTO: feature fragments start -->` and `<!-- AUTO: feature fragments end -->`
in `AGENTS.md` from the on-disk roadmap fragments. Content outside that block SHALL be
preserved; whitespace immediately adjacent to the block MAY be normalized.

#### Scenario: the sentinel block is rewritten from the on-disk fragments

- **WHEN** `rddf roadmap --update-agent-md` runs
- **THEN** the text between the two AUTO sentinels SHALL be regenerated from the
  on-disk feature fragments
- **AND** a fragment added since the last run SHALL appear in the regenerated block

#### Scenario: content outside the sentinel block is preserved

- **WHEN** `rddf roadmap --update-agent-md` runs
- **THEN** every section before and after the sentinel block SHALL still be present
- **AND** whitespace immediately adjacent to the block MAY be normalized

#### Scenario: the rewrite is idempotent

- **WHEN** `rddf roadmap --update-agent-md` runs twice with unchanged input
- **THEN** the second run SHALL NOT change the generated block
- **AND** the sentinel count in the file SHALL remain 1

#### Scenario: a missing fragments directory fails loudly

- **WHEN** `rddf roadmap --update-agent-md` runs and the fragments directory is absent
- **THEN** the command SHALL exit non-zero
- **AND** it SHALL NOT write a partial block

