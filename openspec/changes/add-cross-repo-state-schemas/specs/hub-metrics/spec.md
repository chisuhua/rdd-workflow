# hub-metrics: Specifications

> Source: `_lib/schemas/hub_metrics_schema.json` v1
> Change: add-cross-repo-state-schemas

## ADDED Requirements

### Requirement: Hub aggregate metrics storage

The system SHALL store aggregate metrics for Hub-and-Spoke 3-month review.

#### Scenario: Record spoke connection count
- **WHEN** metrics are aggregated
- **THEN** `spokes_connected` counts repos actively connected (synced within 30 days)
- **AND** `last_updated` records aggregation time

#### Scenario: Track RFC statistics
- **WHEN** RFC stats are updated
- **THEN** `rfc_stats.total` counts all RFCs created
- **AND** `rfc_stats.by_status` tracks counts per status (Draft/RFC/In-Review/Approved/Rejected/Blocked)
- **AND** `rfc_stats.avg_decision_days` provides average time to decision

#### Scenario: Record stale RFC count
- **WHEN** RFCs with no comment for >5 days are identified
- **THEN** `rfc_stats.stale_rfc_count` records the count

---

### Requirement: Hub health tracking

The system SHALL track hub health indicators and audit anomalies.

#### Scenario: Track audit anomalies
- **WHEN** anomaly events in `.cross-repo-audit.jsonl` are counted
- **THEN** `audit_anomalies` reflects count of `decision=block` failures

#### Scenario: Record hub health indicators
- **WHEN** hub health is assessed
- **THEN** `hub_health.branch_protection_enabled` indicates protection status
- **AND** `hub_health.maintainer_count` tracks active maintainers
- **AND** `hub_health.last_security_audit` records the date

---

### Requirement: Hub metrics validation

Hub metrics entries MUST pass schema validation.

#### Scenario: Valid RFC stats structure
- **GIVEN** `rfc_stats` with required fields `total`, `by_status`, `avg_decision_days`
- **WHEN** schema validation runs
- **THEN** the entry passes validation

#### Scenario: Valid by_status structure
- **GIVEN** `rfc_stats.by_status` with keys Draft/RFC/In-Review/Approved/Rejected/Blocked
- **WHEN** schema validation runs
- **THEN** validation passes (additionalProperties: false)

#### Scenario: Invalid spoke connection count
- **GIVEN** `spokes_connected` is negative
- **WHEN** schema validation runs
- **THEN** validation fails with minimum constraint error

---

### Requirement: Hub metrics file structure

The `.rddf/state/.hub-metrics.json` file SHALL contain version and metrics aggregates.

#### Scenario: File contains required top-level fields
- **WHEN** the metrics file is read
- **THEN** it contains `version` (const: 1), `last_updated`, `spokes_connected`, and `rfc_stats`

#### Scenario: Optional hub_health section
- **WHEN** hub health data is available
- **THEN** `hub_health` object may be present with optional fields
- **AND** `audit_anomalies` may be recorded
