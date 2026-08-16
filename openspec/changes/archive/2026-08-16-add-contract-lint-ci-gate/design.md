---
SCOPE: shared
STATUS: PROPOSED
---

## Context

`rdd-workflow` currently lacks **contract consistency checking** between Hub repositories
(containing shared OpenAPI/Protobuf contracts) and Spoke repositories (containing local
implementations). This leads to:

1. Spoke A modifies implementation without syncing Hub contract → contract drift
2. Hub contract updated but Spoke repos don't pull → integration failures
3. AI-generated code inconsistent with existing contracts → type errors

The existing `skills/_lib/validate_delta_targets.py` validates **spec structure** (MODIFIED/RENAMED
targets in spec.md), but does not check **runtime contract-vs-implementation consistency**.

## Goals / Non-Goals

**Goals:**
- Add `rddf contract-check` CLI with OpenAPI/Protobuf diff capability
- Provide severity classification (Breaking-Change / Non-Breaking / New-Contract)
- Support `STRICT_CONTRACT_GATE=yes` for hard blocking on Breaking-Change
- Implement cache and offline mode for Hub-unreachable scenarios
- Provide Spoke CI workflow template for PR integration
- Add unit tests for 6 key paths

**Non-Goals:**
- Hub CI detailed configuration (belongs to Hub repo itself)
- Non-OpenAPI/Protobuf format support (OpenAPI 2.x, GraphQL, JSON Schema only - future ADR)
- Automatic enforcement of external repo CI (Hub/Spoke CI is manual gate)
- Replacement of Spoke repo's own CI (contract lint is supplementary)

## Decisions

### Decision 1: Separate Python module (contract_diff.py) + CLI wrapper

The implementation is split into:

```
skills/_lib/contract_diff.py    # Core diff engine (DiffEngine class)
skills/cli/contract_check.py    # rddf contract-check CLI (argparse wrapper)
```

**Rationale**: Separation allows:
- `contract_diff.py` to be imported by other Python code (guide-ship hooks, tests)
- CLI to handle I/O (argument parsing, output formatting) separately
- Easy unit testing of `DiffEngine` without CLI overhead

### Decision 2: Use openapi-diff library for OpenAPI comparison

For OpenAPI contracts, use the `openapi-diff` library (external dependency).

**Alternatives considered:**
- Custom diff implementation: Rejected - complex and error-prone
- `swagger-diff`: Less maintained than openapi-diff

**Installation**: `pip install openapi-diff` in requirements.txt

### Decision 3: Three-tier severity model

Use exactly three severity levels (not two, not four):

| Level | Meaning | STRICT_CONTRACT_GATE action |
|-------|---------|---------------------------|
| `Breaking-Change` | API incompatible | Block |
| `Non-Breaking` | Backward-compatible | Warn (exit 0) |
| `New-Contract` | New in Hub only | Warn (exit 0) |

**Rationale**: Three levels match OpenAPI Diff's semantic classification and are
sufficient for contract linting. Four levels (adding "Removed") adds complexity
without value.

### Decision 4: Cache file stored in .rddf/state/.contract-cache.json

Cache location: `<repo-root>/.rddf/state/.contract-cache.json`

**Schema**:
```json
{
  "contracts": {
    "<contract-name>": {
      "sha": "<sha256>",
      "fetched_at": "<ISO8601>",
      "hub_owner": "<owner>",
      "local_path": "<relative-path>"
    }
  }
}
```

**Rationale**: Using `.rddf/state/` (already gitignored) keeps cache isolated from
source code. SHA256 provides content-addressable caching.

### Decision 5: Offline mode uses local cache + warning

When Hub is unreachable:

1. Check `.contract-cache.json` for cached SHA
2. If SHA matches local file → use cache silently
3. If SHA mismatch or missing → warn and use local file
4. Never block on Hub unavailability

**Rationale**: Matches the "fail open" principle for network dependencies. Hub CI
already handles Hub-side notifications; Spoke should not be blocked by Hub downtime.

### Decision 6: STRICT_CONTRACT_GATE as environment variable (not CLI flag)

`STRICT_CONTRACT_GATE=yes` is an environment variable, not `--strict-gate` flag.

**Rationale**:
- CLI flags are per-invocation; env vars can be set in CI configuration
- Aligns with existing `STRICT_DESIGN_GATE=yes` pattern in rdd-workflow
- Reduces CLI complexity

### Decision 7: CLI output formats (Markdown default, JSON opt-in)

Default output is human-readable Markdown with emoji:
```
✅ Interface paths match (12 endpoints)
⚠️ Non-Breaking: POST /v2/login has new optional field 'device_fingerprint'
❌ Breaking-Change: GET /v2/user/profile missing required field 'email_verified'
```

`--format json` outputs machine-readable JSON for CI integration.

**Rationale**: Markdown is readable in terminal and GitHub Actions logs. JSON is
needed for programmatic parsing.

### Decision 8: Spoke CI workflow is template only (not auto-installed)

The `.github/workflows/contract-lint.yml` is:
- Provided as a documentation template in `docs/contract-conventions.md`
- NOT auto-installed by `rddf contract-check` or any skill

**Rationale**: Each Spoke repo has its own CI configuration. Auto-installing
workflows would be intrusive. The template serves as a reference implementation.

## Architecture

### Files Created

```
skills/_lib/contract_diff.py       # DiffEngine + format_output()
skills/cli/contract_check.py        # rddf contract-check CLI entry point
docs/contract-conventions.md        # Spoke repo contract implementation guide
.github/workflows/contract-lint.yml # Spoke CI template (in docs/)
tests/unit/test_contract_diff.py    # 6 test scenarios
```

### CLI Integration

```
rddf contract-check --contract X --impl Y [--strict|--warn-only|--diff-only] [--format json|markdown]
```

### guide-ship Integration

In `guide-ship` Phase 2 execute:
```bash
# Optional contract check step
if [ -n "$CONTRACT_CHECK_ENABLED" ]; then
    rddf contract-check --all --format json > .rddf/state/contract-check.json
    if [ "$STRICT_CONTRACT_GATE" = "yes" ]; then
        # Block on Breaking-Change
        python3 -c "import json; r=json.load(open('.rddf/state/contract-check.json')); exit(1 if r['severity']=='Breaking-Change' else 0)"
    fi
fi
```

## Risks / Trade-offs

| # | Risk | Mitigation |
|---|------|------------|
| 1 | openapi-diff library changes API | Pin version in requirements.txt; unit tests catch breakage |
| 2 | Protobuf comparison is complex | v1 uses basic field comparison only; advanced service comparison v2 |
| 3 | Cache file grows unbounded | TTL-based eviction (future enhancement) |
| 4 | Spoke CI not enforced | Template is opt-in; documentation explains value |
| 5 | Hub-offline causes stale cache | SHA validation on each run; warning if SHA mismatch |
| 6 | validate_delta_targets.py scope confusion | This change adds contract-diff.py, not modifying validate_delta_targets.py |

## Reconciliation with validate_delta_targets.py

The existing `skills/_lib/validate_delta_targets.py` validates:
- spec.md MODIFIED/RENAMED targets exist in `openspec/specs/`
- Baseline claims in `.openspec.yaml` are verifiable

The new `skills/_lib/contract_diff.py` validates:
- Runtime contract-vs-implementation consistency
- No dependency between the two modules

They serve different purposes and do not overlap.

## Verification

```bash
# Unit tests
cd /workspace/project/rdd-workflow
pip install -r requirements.txt
python3 -m pytest tests/unit/test_contract_diff.py -v

# CLI smoke test
rddf contract-check --help

# Integration test (requires test contracts)
rddf contract-check --contract tests/fixtures/auth-v2.yaml --impl tests/fixtures/auth_impl.py --warn-only
```
