## Context

The v2.0 loop engine (ADR-0004) is the AI-native execution model. v1.x uses a state machine where the user manually progresses through phases. v2.0 uses a loop that automatically iterates until a goal is achieved, with human-in-the-loop nodes at key decision points. The state vector (from `v2-core-foundation`) provides persistent state; the gate mechanism validates transitions; this change adds the engine that drives iteration.

Three interaction modes (ADR-0002) allow users to choose their preferred autonomy level: Loop (fully autonomous, suitable for CI/CD), Menu (fully manual, suitable for learning/debugging), and Hybrid (default, automatic for routine operations, manual for key decisions).

## Goals / Non-Goals

**Goals:**
- Provide a safe, observable loop cycle that drives the workflow forward
- Support three interaction modes with runtime switching
- Provide 7 key human-in-loop nodes with configurable verification modes
- Run a design-first phase before the loop starts to confirm goal, verification, and control parameters
- Generate real-time ASCII flowcharts for observability

**Non-Goals:**
- Implementing the Tribunal (that's `v2-advanced-features`)
- Implementing Memory / Session management (that's `v2-advanced-features`)
- Multi-process parallel execution (that's `v2-advanced-features` / v2.1)
- Replacing v1.x phase progression (loop engine runs in parallel, not replacement)

## Decisions

### Decision 1: 5 building blocks, not a generic AST

- **Why**: 5 blocks map directly to ADR-0004's model (verify_goal / scan_state / generate_plan / execute_plan / verify_results). Generic AST would require a meta-language.
- **Rejected**: AST would add complexity without proportional benefit for current use cases.

### Decision 2: Safety mechanisms enforced at engine level, not action level

- **Why**: Centralized enforcement ensures no action can bypass. Distributed enforcement (each action enforcing its own safety) would be inconsistent.
- **Rejected**: Per-action enforcement duplicates code and risks inconsistency.

### Decision 3: Detectors and actions are pluggable but with sensible defaults

- **Why**: 8 detectors + 7 actions cover v1.x workflows out of the box; users can extend without writing from scratch.
- **Alternative**: Require user to register all detectors/actions
- **Rejected**: High friction for common cases.

### Decision 4: Human-in-loop nodes are config-driven, not hardcoded

- **Why**: Different users/orgs need different human checkpoints. Config-driven allows per-project customization.
- **Rejected**: Hardcoded nodes would force one-size-fits-all.

## Risks / Trade-offs

- **Risk**: Loop could run unboundedly without safety mechanisms
  - **Mitigation**: Hard caps (max_iterations=100 default, max_retries=3), oscillation detection (5 same states in 5 iterations triggers stop), circuit breaker (3 consecutive failures)
- **Risk**: Actions may take longer than expected
  - **Mitigation**: Per-action 30-minute timeout, configurable
- **Risk**: Detector/Action plugin quality varies
  - **Mitigation**: Document plugin API thoroughly; provide reference implementations
- **Trade-off**: Loop engine complexity vs v1.x state machine simplicity — chose loop for AI-native benefits, accepting higher complexity
