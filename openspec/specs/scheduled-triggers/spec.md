# scheduled-triggers Specification

## Purpose
TBD - created by archiving change v3-scheduled-triggers. Update Purpose after archive.
## Requirements
### Requirement: scheduled-loop-triggers
The system SHALL accept cron-expression-based scheduled triggers that invoke the Loop engine on a periodic schedule, independent of any user action.

#### Scenario: cron trigger fires Loop engine
- **WHEN** a trigger is registered with expression `0 2 * * *` (daily at 02:00)
- **THEN** at the scheduled wall-clock time the Loop engine SHALL execute a full scan-detect-act cycle
- **AND** the firing SHALL be recorded in the event log with trigger id and expression

### Requirement: event-driven-triggers
The system SHALL accept event-driven triggers (file system events, git events, webhooks) that invoke the Loop engine when a matching event arrives.

#### Scenario: webhook triggers Loop
- **WHEN** a webhook receiver registers for `git.push` events on branch `main`
- **AND** a push to `main` is received
- **THEN** the Loop engine SHALL execute a scan-detect-act cycle
- **AND** the trigger id and event payload SHALL be recorded in the event log

### Requirement: trigger-registry-and-deduplication
The system SHALL maintain a central trigger registry and SHALL deduplicate overlapping triggers so that a single event does not cause duplicate Loop-engine invocations.

#### Scenario: overlapping triggers deduplicated
- **WHEN** two triggers both match the same incoming event
- **THEN** the Loop engine SHALL execute the scan-detect-act cycle exactly once for that event
- **AND** both trigger ids SHALL be recorded in the event log entry

