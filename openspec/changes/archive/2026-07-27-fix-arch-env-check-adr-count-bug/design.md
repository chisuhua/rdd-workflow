# fix-arch-env-check-adr-count-bug — Design

## Root Cause

`arch_env_check.sh` line 90 wraps the full path including glob in double quotes, preventing bash from expanding `*`:

```bash
ADR_COUNT=$(ls -d "$PROJECT_ROOT/$DISCOVERED_ADR_DIR/$DISCOVERED_ADR_PATTERN" 2>/dev/null | wc -l)
```

`$DISCOVERED_ADR_PATTERN` = `ADR-*.md`, the `*` is inside `""` → treated as literal → `ls` finds nothing → count = 0.

## Fix

Move closing quote before the glob:

```bash
ADR_COUNT=$(ls -d "$PROJECT_ROOT/$DISCOVERED_ADR_DIR/"$DISCOVERED_ADR_PATTERN 2>/dev/null | wc -l)
```

Consistent with `arch_done_gate.sh` quoting style. Lines 92, 93 already correct.
