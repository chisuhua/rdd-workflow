## ADDED Requirements

### Requirement: Cross-repo dependency graph generation

The system SHALL generate a dependency graph across multiple Spoke repositories by scanning their `iteration.json` files.

#### Scenario: Generate cross-repo dependency graph from multiple Spokes
- **WHEN** user runs `rddf deps cross-repo --spokes "org/repo-frontend,org/repo-backend"`
- **THEN** system reads `iteration.json` from each Spoke's default branch
- **AND** extracts all changes with status `proposed` or `in_progress`
- **AND** identifies `cross_repo_dependencies` field entries
- **AND** generates unified Mermaid dependency graph

#### Scenario: Handle Spoke with no cross-repo dependencies
- **WHEN** a Spoke repository has no `cross_repo_dependencies` in its `iteration.json`
- **THEN** that Spoke's changes are treated as independent (no edges in graph)
- **AND** they appear as standalone nodes in the Mermaid output

#### Scenario: Handle missing or inaccessible Spoke repository
- **WHEN** a Spoke repository cannot be cloned or accessed
- **THEN** system logs warning with repository URL
- **AND** skips that Spoke in graph generation
- **AND** continues with accessible Spokes
- **AND** reports total Spokes skipped in summary

---

### Requirement: Kahn topology sorting with cycle detection

The system SHALL produce a topological ordering of changes that respects dependency constraints, detecting cycles before sorting.

#### Scenario: Linear dependency chain (A → B → C)
- **WHEN** repo-frontend/auth-v2-impl depends on repo-backend/auth-v2-publish
- **AND** repo-backend/auth-v2-publish depends on repo-infra/base
- **THEN** topology sort produces wave order: `repo-infra/base`, `repo-backend/auth-v2-publish`, `repo-frontend/auth-v2-impl`
- **AND** no cycle is reported

#### Scenario: Parallel independent changes
- **WHEN** repo-frontend/checkout-v3 has no dependencies
- **AND** repo-infra/storage-v3 has no dependencies
- **THEN** both appear in same wave (Wave 1)
- **AND** can be executed in parallel

#### Scenario: Circular dependency detection
- **WHEN** A depends on B, B depends on C, and C depends on A
- **THEN** system detects cycle: `A → B → C → A`
- **AND** reports cycle members: `A, B, C`
- **AND** aborts topology sort
- **AND** outputs error: "Circular dependency detected between: A, B, C"

#### Scenario: Self-referencing dependency
- **WHEN** a change lists itself as a dependency
- **THEN** system treats it as cycle of length 1
- **AND** reports error with self-referencing change name

---

### Requirement: ETA Lv1/Lv2/Lv3 fallback with missing velocity cache

The system SHALL estimate completion days using three-level fallback strategy when velocity cache is unavailable.

#### Scenario: Lv1 ETA with valid velocity cache
- **WHEN** `~/.rddf/state/.velocity-cache.json` exists with TTL ≤ 7 days
- **AND** contains historical average of 2.5 days per task
- **AND** target change has 4 unchecked tasks
- **THEN** ETA = 4 × 2.5 = 10 days
- **AND** `eta_evidence` records `{"source": "Lv1_auto", "velocity_cache_ttl_hours": 168}`

#### Scenario: Lv1 fallback to Lv2 when velocity cache expired
- **WHEN** velocity cache TTL > 7 days (expired)
- **THEN** Lv1 returns `null`
- **AND** system falls back to Lv2 (proposal frontmatter `eta` field)
- **AND** `eta_evidence` records `{"source": "Lv2_frontmatter", "lv1_fallback_reason": "cache_expired"}`

#### Scenario: Lv2 fallback to Lv3 when no frontmatter ETA
- **WHEN** proposal.md has no `eta` frontmatter field
- **THEN** Lv2 returns `null`
- **AND** system falls back to Lv3 (manual `--set-eta` or PR comment)
- **AND** `eta_evidence` records `{"source": "Lv3_manual", "lv2_fallback_reason": "no_frontmatter"}`

#### Scenario: All ETA sources unavailable
- **WHEN** velocity cache missing, no frontmatter ETA, no manual ETA set
- **THEN** ETA displays as "ETA 未知（请补充）"
- **AND** `eta_evidence` records `{"source": "null", "all_sources_exhausted": true}`
- **AND** this does NOT block dependency decisions

#### Scenario: ETA deviation >50% triggers warning
- **WHEN** calculated ETA differs from actual by >50%
- **THEN** system logs warning: "ETA 偏差 >50%，建议更新速率缓存"
- **AND** suggests running `rddf velocity --update`

---

### Requirement: Dependency cache for cross-repo lookups

The system SHALL cache cross-repo dependency lookups to avoid repeated remote fetches.

#### Scenario: Cache hit within TTL
- **WHEN** `.rddf/state/.cross-repo-deps-cache.json` exists with TTL ≤ 24 hours
- **AND** cached data matches requested Spoke list
- **THEN** system returns cached dependency graph
- **AND** skips re-fetching `iteration.json` from Spokes

#### Scenario: Cache miss or expired
- **WHEN** cache missing or TTL > 24 hours
- **THEN** system fetches fresh `iteration.json` from each Spoke
- **AND** rebuilds dependency graph
- **AND** writes updated cache with fresh TTL

#### Scenario: Force refresh cache
- **WHEN** user passes `--force-refresh` flag
- **THEN** system ignores cache
- **AND** re-fetches all Spoke data
- **AND** updates cache

---

### Requirement: Hub dependency issue creation

The system SHALL create `[Dependency]` labeled Issues in Hub repository to track cross-repo blockers.

#### Scenario: Auto-create Hub Issue on strong cross-repo dependency
- **WHEN** `guide-plan` detects strong dependency (cross_repo_dependencies.type = "strong")
- **AND** `STRICT_DEPS_GATE=yes`
- **THEN** system calls `rddf hub issue --deps`
- **AND** creates Hub Issue with:
  - Title: `[Dependency] {change_name} 等待 {depends_on}`
  - Body: Links to both changes, ETA info, wave assignment
  - Labels: `dependency`, `cross-repo`
  - Assignees: owners of the depends-on change

#### Scenario: Manual Hub Issue creation
- **WHEN** user runs `rddf hub issue --deps --from A --depends-on B --eta "5d"`
- **THEN** system creates Hub Issue with provided parameters
- **AND** outputs Issue URL

#### Scenario: Hub Issue updates existing dependency tracking
- **WHEN** dependency already tracked by existing Hub Issue
- **THEN** system updates existing Issue body/ETA
- **AND** does NOT create duplicate Issue

---

### Requirement: STRICT_DEPS_GATE mode for plan-done

The system SHALL block plan-done transition when cross-repo strong dependencies are unresolved.

#### Scenario: STRICT_DEPS_GATE blocks plan-done with unresolved strong deps
- **WHEN** `STRICT_DEPS_GATE=yes`
- **AND** current change has unresolved strong cross-repo dependencies
- **THEN** plan-done gate reports CRITICAL
- **AND** blocks progression to ship phase
- **AND** displays: "强依赖 {dep} 未解决，请等待或使用 SKIP_STRICT_DEPS_GATE=yes 绕过"

#### Scenario: STRICT_DEPS_GATE allows weak dependencies
- **WHEN** `STRICT_DEPS_GATE=yes`
- **AND** current change only has weak cross-repo dependencies
- **THEN** plan-done gate allows progression
- **AND** logs weak dependency as WARNING

#### Scenario: STRICT_DEPS_GATE disabled via env var
- **WHEN** `SKIP_STRICT_DEPS_GATE=yes`
- **THEN** plan-done gate skips cross-repo dependency check
- **AND** proceeds regardless of dependency state

---

### Requirement: Iteration v7 schema compatibility

The system SHALL upgrade iteration schema to v7 with `cross_repo_dependencies` field while maintaining backward compatibility.

#### Scenario: Read v6 iteration.json without cross_repo_dependencies
- **WHEN** loading `iteration.json` with version "6"
- **THEN** system treats all changes as independent
- **AND** `cross_repo_dependencies` field defaults to `[]`
- **AND** no migration required

#### Scenario: Write v7 iteration.json with cross_repo_dependencies
- **WHEN** saving new iteration state
- **THEN** system writes version "7"
- **AND** includes `cross_repo_dependencies` array per change

#### Scenario: Schema validation for cross_repo_dependencies entry
- **WHEN** validating entry: `{change: "name", type: "strong", depends_on: "org/repo#change"}`
- **THEN** `change` must be non-empty string
- **AND** `type` must be "strong" or "weak"
- **AND** `depends_on` must match format `org/repo#change-name`

---

### Requirement: Mermaid dependency graph output

The system SHALL generate Mermaid-formatted dependency graph for visualization.

#### Scenario: Independent changes grouped in subgraph
- **WHEN** changes have no cross-repo dependencies
- **THEN** they appear in `subgraph` block labeled by Spoke name
- **AND** independent changes within same Spoke also grouped

#### Scenario: Strong dependency rendered as solid arrow
- **WHEN** dependency type is "strong"
- **THEN** rendered as `A --> B` (solid arrow)

#### Scenario: Weak dependency rendered as dashed arrow
- **WHEN** dependency type is "weak"
- **THEN** rendered as `A -.-> B` (dashed arrow)

#### Scenario: Cycle detected renders error node
- **WHEN** circular dependency exists
- **THEN** renders `A --> B --> C --> A` in red
- **AND** adds `style cycle fill:#ffcccc` class

#### Scenario: Output includes ETA in tooltip
- **WHEN** rendering node for change X with ETA 5 days
- **THEN** renders as `X["change-name\nETA: 5d"]`

---

### Requirement: Unit and integration tests

The system SHALL provide comprehensive test coverage for cross-repo dependency functionality.

#### Scenario: Test Kahn topological sort
- **GIVEN** DAG: A→B, A→C, B→D, C→D
- **WHEN** topological_sort is called
- **THEN** returns [A, B, C, D] or [A, C, B, D]

#### Scenario: Test cycle detection on small cycle
- **WHEN** graph: X→Y→Z→X
- **THEN** detect_cycle returns [X, Y, Z]

#### Scenario: Test ETA fallback chain
- **GIVEN** no velocity cache, no frontmatter ETA
- **WHEN** calculate_eta(change) is called
- **THEN** returns Lv3 manual or null

#### Scenario: Test Spoke iteration.json parsing
- **WHEN** parse_spoke_iteration(json_content) is called
- **THEN** extracts changes with cross_repo_dependencies

#### Scenario: Test Hub Issue creation API call
- **WHEN** create_hub_issue(dep_info) is called
- **THEN** returns issue URL or raises HubError on failure

#### Scenario: Test Mermaid graph generation
- **WHEN** generate_mermaid(deps_graph) is called
- **THEN** outputs valid Mermaid syntax with correct node names

#### Scenario: Integration: Full cross-repo deps flow
- **WHEN** `rddf deps cross-repo --spokes "a/x,b/y"` is executed
- **THEN** returns 0
- **AND** outputs Mermaid graph to stdout
- **AND** cache file is created
