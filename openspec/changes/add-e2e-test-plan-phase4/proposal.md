# add-e2e-test-plan-phase4 (CI integration)

> Per `2026-09-08-e2e-test-plan-design.md` §5 + §9 Phase 4.

## What Changes

- **New**: `.github/workflows/e2e-nightly.yml` — nightly cron 02:00 UTC + workflow_dispatch, runs `./test.sh --e2e-agent` with `continue-on-error: true` for missing credentials
- **Extended**: `.github/workflows/test.yml` — added step `./test.sh --e2e-smoke` (A-layer CI 必跑)
- **Updated**: `README.md` "测试基础设施" section — layered e2e strategy (A/C/external) + references to 5 spec docs

## Acceptance

- AC-1: e2e-nightly.yml YAML valid + triggers nightly + manual
- AC-2: test.yml includes e2e-smoke step
- AC-3: README has e2e layered strategy section
- AC-4: OpenSpec archive completed

## Specs

D3 spec-delta 落 `openspec/specs/ci-e2e-integration/spec.md`。
