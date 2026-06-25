## ADDED Requirements

### Requirement: interaction-modes-three-modes
The system SHALL support three interaction modes: `loop`, `menu`, `hybrid` (default).

- **Loop mode**: Fully autonomous. Skips all human-in-loop nodes except on error.
- **Menu mode**: Fully manual. Every decision point displays a menu.
- **Hybrid mode**: Automatic for routine operations; manual at configured key nodes.

#### Scenario: Loop mode runs autonomously
- **WHEN** `mode: loop` is configured
- **THEN** no human input is requested except on error
- **AND** workflow completes without user intervention (in success case)

#### Scenario: Menu mode pauses at every decision
- **WHEN** `mode: menu` is configured
- **THEN** loop pauses and shows menu at every decision point

#### Scenario: Hybrid mode pauses at configured nodes
- **WHEN** `mode: hybrid` is configured
- **THEN** loop pauses only at nodes listed in `human_nodes` config
- **AND** routine operations proceed automatically

### Requirement: interaction-modes-runtime-switch
The system SHALL allow mode switching at runtime via parameter, overriding config file.

#### Scenario: Runtime override
- **WHEN** user invokes loop engine with `--mode menu`
- **AND** `loop.yaml` specifies `mode: hybrid`
- **THEN** menu mode is used for this invocation

### Requirement: human-in-loop-nodes-registry
The system SHALL provide a registry of 7 key human-in-loop node types.

Node types: `arch.adr_create`, `arch.roadmap_define`, `plan.change_select`, `plan.propose_confirm`, `ship.archive_confirm`, `ship.cleanup_confirm`, `ship.execute_error`.

#### Scenario: Node triggered
- **WHEN** loop reaches a configured node
- **THEN** the node's verification mode is invoked

### Requirement: human-in-loop-verification-modes
Each human-in-loop node SHALL support one of three verification modes: `human`, `multi_model`, `script`.

#### Scenario: Human verification
- **WHEN** node has `verification: human`
- **THEN** menu is displayed and user input is required

#### Scenario: Multi-model verification
- **WHEN** node has `verification: multi_model`
- **THEN** Tribunal is invoked (from `v2-advanced-features`)

#### Scenario: Script verification
- **WHEN** node has `verification: script`
- **THEN** configured Python script is run and its exit code determines pass/fail
