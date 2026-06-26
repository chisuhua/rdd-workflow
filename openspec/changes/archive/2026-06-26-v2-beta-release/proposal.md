## Why

Phase 5 ships v2.0.0-beta to npm, collects real-world feedback, and fixes critical issues found in beta testing. Without this change, all the prior phases (v2-core-foundation through v2-migration-and-tests) have no public release. This is the change that transitions v2.0 from "draft architecture" to "shipped product with user feedback loop."

## What Changes

- **Modify** `package.json` — bump version to `2.0.0-beta`
- **Add** `CHANGELOG.md` — release notes for v2.0.0-beta
- **Add** GitHub Issue templates (bug report, feature request) for beta feedback
- **Add** Performance optimizations: state vector caching, event log batch writes, detector/action timing
- **Add** Beta feedback collection mechanism (GitHub Issues label `beta-feedback`)
- **Modify** `docs/migration/v1-to-v2.md` — add "Beta Release Notes" section

## Capabilities

### New Capabilities
- `beta-release`: v2.0.0-beta npm release with changelog
- `feedback-collection`: GitHub Issue templates and metrics collection
- `performance-optimization`: caching and batch write optimizations

### Modified Capabilities
- None

## Impact

- **New files**: ~200 lines (CHANGELOG.md ~100, Issue templates ~100)
- **Modified files**: package.json (version bump), migration doc (additions)
- **Dependencies**: None
- **Compatibility**: Beta version is explicitly unstable; v1.x users should stay on 1.x
- **Risk**: Low — release process is well-understood; performance optimizations are isolated
- **Source**: v2-implementation-plan.md § Phase 5 (P5-T1 ~ P5-T3)
