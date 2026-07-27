# fix-deps-render-empty-candidates — Design

## Root Cause

`deps_render_report.sh` expects `$CANDIDATES` env var. When deps.md's `mapfile -t CANDIDATES` array is not exported to the function (e.g., when called from guide-plan directly), `$CANDIDATES` is empty → `candidates_py="[]"` → report shows "候选 0".

## Fix

Add fallback: when `$CANDIDATES` is empty, read `.rddf/state/.deps-candidates.json`:

```bash
if [ -z "$CANDIDATES" ]; then
  CANDIDATES=$(python3 -c "import json; d=json.load(open('$PROJECT_ROOT/.rddf/state/.deps-candidates.json')); print(' '.join(d.get('candidates',[])))" 2>/dev/null)
fi
```

Env var takes priority (backward compat), JSON read failure → fallback to `[]`.
