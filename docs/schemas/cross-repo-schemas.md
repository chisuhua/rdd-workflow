# Cross-Repo Federation Schemas (v1)

> SSOT schema definitions for ADR-0030 Hub-and-Spoke Federation Architecture and 7 related proposals.
> All schemas are located in `_lib/schemas/` and validated via jsonschema Draft-7.

## 1. `cross_repo_pending_schema.json` v1

**Purpose**: Hub Issue pending status — tracks local proposals waiting for Hub approval.

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | integer (const:1) | ✓ | Schema version |
| `pending_issues` | array | ✓ | List of Hub Issues blocking local workflow gates |
| `last_updated` | date-time | ✓ | ISO-8601 |

## 2. `cross_repo_audit_schema.json` v1

**Purpose**: Cross-repo decision audit log — immutable record of all RFC propose/approve/reject events.

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | integer (const:1) | ✓ | Schema version |
| `timestamp` | date-time | ✓ | ISO-8601 |
| `proposal_name` | string | ✓ | Local proposal name (kebab-case) |
| `hub_issue` | string | ✓ | Hub Issue reference (e.g. `org/rdd-hub#42`) |
| `decision` | enum | ✓ | `initiate` / `approve` / `reject` / `block` / `defer` / `revoke` |
| `actor` | object | ✓ | Actor type (`human`/`ai-agent`/`ci-bot`) and id |

## 3. `mcp_trace_schema.json` v1

**Purpose**: MCP (Model Context Protocol) call trace — records all Spoke ↔ Hub MCP messages.

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | integer (const:1) | ✓ | Schema version |
| `timestamp` | date-time | ✓ | ISO-8601 |
| `direction` | enum | ✓ | `hub-to-spoke` / `spoke-to-hub` |
| `tool_name` | string | ✓ | MCP tool name (e.g. `hub_create_issue`) |
| `actor_repo` | string | ✓ | Repo making the call (e.g. `org/repo-frontend`) |
| `args_hash` | string | ✓ | SHA-256 hash of args (privacy-preserving) |
| `result_status` | enum | ✓ | `success` / `error` / `rate-limited` / `unauthorized` / `timeout` |

## 4. `contract_cache_schema.json` v1

**Purpose**: Contract version cache — local mirror of Hub contract versions and SHA-256 checksums.

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | integer (const:1) | ✓ | Schema version |
| `last_sync` | date-time | ✓ | ISO-8601 |
| `hub_repo` | string | | Hub repo reference (e.g. `org/rdd-hub`) |
| `hub_ref` | string | | Git ref synced from (e.g. `main`, `v1.2.0`) |
| `contracts` | array | ✓ | List of cached contracts |

## 5. `cross_repo_deps_cache_schema.json` v1

**Purpose**: Cross-repo dependency cache — cached cross-repo dependency graph scan results (TTL 3600s).

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | integer (const:1) | ✓ | Schema version |
| `cache_generated_at` | date-time | ✓ | ISO-8601 |
| `ttl_seconds` | integer | | Cache TTL in seconds (default 3600s) |
| `spokes` | array | ✓ | List of Spoke repos included in the scan |
| `dependency_graph` | object | ✓ | Nodes and edges of the dependency graph |

## 6. `hub_metrics_schema.json` v1

**Purpose**: Hub runtime metrics — aggregate statistics for Hub-and-Spoke 3-month review.

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | integer (const:1) | ✓ | Schema version |
| `last_updated` | date-time | ✓ | ISO-8601 |
| `spokes_connected` | integer | ✓ | Number of Spoke repos actively connected |
| `rfc_stats` | object | ✓ | RFC statistics (total, by_status, avg_decision_days) |
| `audit_anomalies` | integer | | Count of anomaly events in `.cross-repo-audit.jsonl` |
| `hub_health` | object | | Hub health metrics (branch protection, maintainer count) |

## Evolution Strategy

- **v1 (current)**: Immutable. Schema files are not modified once published.
- **v2 (future)**: For breaking changes:
  1. Create `_lib/schemas/<name>_schema_v2.json`
  2. Add `version: {"const": 2}`
  3. Retain v1 files for 6-month transition period
  4. `rdd-doctor --category state` warns about v1 files after transition

## Validation

- `tests/unit/test_cross_repo_schemas.py` covers 6 schemas × 3 validations (valid / invalid-field / missing-field)
- `rdd-doctor --category state` detects state file to schema alignment

## Related

- ADR-0016: Arch Artifact Discovery Contract
- ADR-0030: Hub-and-Spoke Federation Architecture
- ADR-0031: Human-in-Loop for Cross-Repo RFCs
