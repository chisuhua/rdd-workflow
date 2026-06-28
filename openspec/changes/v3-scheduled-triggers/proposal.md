## Why

ADR-0009 is currently a **placeholder** reserved as "编号占位，v2.1 候选". Its scope was intentionally deferred when v2.0 was released: scheduled (cron-like) loop execution and event-driven triggers (file changes, webhooks, git events) were deemed too large to fit into the v2.0 window but valuable enough to keep the ADR number reserved.

Without scheduled/event triggers, the Loop engine (ADR-0004) can only react to **manually triggered** scans. Continuous-integration-style workflows, time-based maintenance loops, and reactive pipelines triggered by external systems (webhooks, git pushes, file watchers) cannot be expressed. The v3.0 roadmap places this ADR as a foundational automation primitive.

## What Changes

- **Cron-style scheduled triggers**: Periodic loop execution via cron expression syntax (e.g. nightly ADR audit, weekly archive cleanup)
- **Event-driven triggers**: File-system events, git events (push/tag/branch), and generic webhook receivers feeding the Loop engine's `match_actions`
- **Trigger registry & deduplication**: Central registry of registered triggers with overlap-detection so multiple triggers cannot double-fire on the same event
- **Loop-engine integration**: Trigger firings appear as detection inputs alongside existing `detect_pending_changes` / `detect_worktrees`, reusing `match_actions` dispatch logic
- **Safety rails**: Configurable per-trigger rate limits, manual override (`--trigger-off`), persistent state file for crash recovery of in-flight triggers
