## Context

The advanced features in v2.0 (ADR-0008 Tribunal, ADR-0006 Memory, ADR-0010 Sessions) transform spec-workflow from a static workflow tool into a learning, self-correcting system. The Tribunal provides quality assurance through multi-agent cross-validation. The Memory system enables resumption of interrupted work and configuration optimization. The Session manager coordinates multiple related workflow runs. These features all consume the loop engine, state vector, and event log from the previous changes.

The Tribunal design follows a weighted voting model: `final_score = exec_score * 0.4 + review_score * 0.6`. Pass condition: `final_score >= 0.8 AND both pass AND conflict < 0.4`. The heavier weight on review reflects that the Reviewer agent has more domain context and is more conservative.

## Goals / Non-Goals

**Goals:**
- Provide multi-agent verification with confidence-weighted scoring
- Sanitize sensitive data before cross-agent invocation
- Persist execution history for learning and recovery
- Coordinate multiple related sessions (v2.0 sequential, v2.1 parallel)
- Define standard agent roles (Planner/Executor/Verifier)

**Non-Goals:**
- True multi-process parallel execution (v2.1)
- ML-based config recommendation (use heuristic similarity instead)
- Cross-session shared memory (each session has its own memory)
- Replacing human reviewers entirely (Tribunal supplements, doesn't replace)

## Decisions

### Decision 1: Weighted scoring 0.4 exec / 0.6 review

- **Why**: Reviewer agent has more domain context; heavier weight reflects lower false-positive rate
- **Alternative**: Equal weight (0.5/0.5)
- **Rejected**: Equal weight doesn't reflect agent specialization

### Decision 2: Sanitization is mandatory, not opt-in

- **Why**: API keys in code are common; accidental disclosure is catastrophic
- **Alternative**: Opt-in with explicit user config
- **Rejected**: Opt-in allows accidents; mandatory prevents them

### Decision 3: Memory uses heuristic similarity, not ML

- **Why**: Heuristic (goal string match + config match) is debuggable and fast. ML adds dependency and opacity.
- **Alternative**: Embedding-based similarity (sentence-transformers)
- **Rejected**: Adds heavy dependency for marginal accuracy gain

### Decision 4: Session v2.0 is sequential, v2.1 adds parallel

- **Why**: v2.0 prioritizes stability over features. True parallel needs careful synchronization.
- **Alternative**: Ship parallel in v2.0
- **Rejected**: Parallel coordination is complex; better to ship sequential and learn

## Risks / Trade-offs

- **Risk**: Tribunal invocation may fail if oh-my-opencode CLI unavailable
  - **Mitigation**: Graceful degradation to single-agent verification with warning
- **Risk**: Sanitizer may miss new sensitive patterns
  - **Mitigation**: Maintain whitelist of common patterns; document how to extend
- **Risk**: Memory may grow unboundedly
  - **Mitigation**: Provide archive command; cap at 10K records by default
- **Trade-off**: Tribunal adds latency (~30s per verification) — accepted for higher quality
- **Trade-off**: Session coordination complexity vs independent runs — chose coordination for related-workflow benefits
