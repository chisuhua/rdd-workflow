## 1. Beta Release Preparation (P5-T1)

- [ ] 1.1 Update `package.json` version to `2.0.0-beta`
- [ ] 1.2 Add v2.0 skills to package.json: `guide-arch`, `guide-plan`, `guide-ship`, `loop`
- [ ] 1.3 Write `CHANGELOG.md` with: new features, breaking changes, known issues, migration guide link
- [ ] 1.4 Performance optimization: state vector caching
- [ ] 1.5 Performance optimization: event log batch writes
- [ ] 1.6 Performance optimization: detector/action execution timing
- [ ] 1.7 Verify `npm install spec-workflow@2.0.0-beta` succeeds in clean environment
- [ ] 1.8 Verify release notes are complete and reviewed
- [ ] 1.9 Verify performance metrics (read/write latency < 10ms)

## 2. User Feedback Collection (P5-T2)

- [ ] 2.1 Create GitHub Issue template: bug-report.md
- [ ] 2.2 Create GitHub Issue template: feature-request.md
- [ ] 2.3 Create GitHub Issue template: beta-feedback.md
- [ ] 2.4 Add `beta-feedback` label for tracking
- [ ] 2.5 Document feedback channels in CHANGELOG and README
- [ ] 2.6 Set up monitoring: installation success rate, first-run success rate, error report frequency
- [ ] 2.7 Collect performance data: loop engine execution time, state vector read/write latency, event log query time

## 3. Critical Issue Fixes (P5-T3)

- [ ] 3.1 Prioritize issues: P0 (blocking, data loss), P1 (functional defects), P2 (UX issues)
- [ ] 3.2 For each P0 issue: reproduce, write failing test, fix, regression test
- [ ] 3.3 For each P1 issue: assess impact, fix in order of frequency
- [ ] 3.4 P2 issues: collect, defer to v2.0.0 stable
- [ ] 3.5 Release patches as `2.0.0-beta.N` for each P0 fix
- [ ] 3.6 Update CHANGELOG with each patch release

## 4. Beta Phase Close-Out

- [ ] 4.1 Verify all P0 issues from beta are fixed
- [ ] 4.2 Verify ≥ 5 users have provided feedback
- [ ] 4.3 Compile feedback summary for v2.0.0 stable planning
- [ ] 4.4 Update `docs/migration/v1-to-v2.md` with "Beta Release Notes" section
- [ ] 4.5 Communicate stable release timeline to beta users
