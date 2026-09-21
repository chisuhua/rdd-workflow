# Auto-Fix Decision Table (Phase 4)

Per [ADR-0053 §Decision D3](../adr/ADR-0053-rdd-env-bootstrap-orchestrator.md), the auto-fix whitelist is **fixed** to only two categories. Any finding outside this whitelist is **never** auto-executable — the user must explicitly review and confirm.

## Whitelist

| Finding category | Auto-fixable? | Command | Risk | AC |
|---|---|---|---|---|
| `ai-context-bootstrap: 未部署` | ✅ | `rddf setup ai-context --yes` | Low (idempotent sentinel) | AC-6 |
| `ai-context-bootstrap: 块已陈旧` | ✅ | `rddf setup ai-context --yes` | Low (force overwrite sentinel) | AC-6 |
| `ai-context-bootstrap` (other) | ❌ | output suggestion | Medium | — |
| `gitignore: openspec/ 缺失` | ❌ | output suggestion | Medium (affects git behavior) | — |
| `docs-consistency: ADR drift` | ❌ | output suggestion + rebuild hint | Medium (affects doc sync) | — |
| `bypass-audit: bypass > 阈值` | ❌ | output audit report | High (needs human review) | — |
| `orphan-gates: gate 失效` | ❌ | output diagnosis | High (affects phase safety) | — |
| `migration-residue` | ❌ | output checklist | Medium (affects schema consistency) | — |
| Anything else | ❌ | output finding | High | — |

## Safety principle

Any fix that would modify any of the following is **NOT** auto-fixable:

- `.gitignore` (e.g., `openspec/` ignore rule)
- Tracked files in git
- `.rddf/state/*.json` (except the orchestrator's own report `.env-bootstrap-report.json`)
- Public API surface (per rdd-doctor's own `--fix` rejection in Improvement §用户洞察)

User must explicitly confirm via the Phase 4 prompt OR run with `--auto-fix --yes` after reviewing the report.

## Idempotency contract

Per AC-6 reviewer note: `rddf setup ai-context --yes` is idempotent:

| Run | Behavior |
|---|---|
| First run | creates `AGENTS.md` (or appends to existing config file) with Layer 0 sentinel block |
| Repeat run | detects sentinel, no-op |
| Stale detection | regenerates the block if drift detected |

This idempotency is what makes auto-fix safe — running env-bootstrap twice produces the same end state.

## Future expansion

- `--fix-rules <yaml>` user-customizable whitelist (Out of Scope for v1.0)
- Cross-project federation (Out of Scope)
- Integration with `rddf-hub-bootstrap` for Hub repo guided init (Out of Scope)
