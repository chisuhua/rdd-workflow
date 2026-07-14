---
name: feature
description: View and manage features (groups of related changes). Provides summary table, Mermaid dependency graph, per-feature change status, and recommended wave execution order. Pure derived view from iteration.json + deps-analysis.json.
license: MIT
compatibility: Requires iteration.json (run `guide-plan` once first) and ideally deps-analysis.json (run `deps` first for full graph).
metadata:
  version: "2.0"
  author: sisyphus
  version: "1.0"
  depends-on: [iteration, deps_output]
---

# OpenSpec Workflow — Feature Management

> **Pure derived view** — never mutates any change artifacts. Reads `iteration.json`
> and (optionally) `deps-analysis.json`, writes only the `feature_view` node back
> into `iteration.json`.

## Subcommands

```
skill_use("feature")              # default: summary table
skill_use("feature summary")      # same as above
skill_use("feature graph")        # Mermaid flowchart (feature-level topology)
skill_use("feature status <name>")# drill into one feature
skill_use("feature order")        # wave-grouped execution order
```

## Implementation (Bash)

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

SUBCOMMAND="${1:-summary}"
TARGET_NAME="${2:-}"

case "$SUBCOMMAND" in
    summary|"")
        python3 - <<'PYEOF'
import json, os, sys
from pathlib import Path
root = os.environ["PROJECT_ROOT"]
try:
    from skills._lib import feature_view as fv
except ImportError as e:
    print(f"❌ feature_view module unavailable: {e}", file=sys.stderr); sys.exit(2)
try:
    fv.update_iteration_feature_view(root)
except (fv.NoIterationError, fv.FileLockedError) as e:
    print(f"❌ {e}", file=sys.stderr); sys.exit(1)
data = json.loads(Path(f"{root}/.rddf/state/iteration.json").read_text())
features = data["feature_view"]["features"]
if not features:
    print("(no features — set parent_feature in proposal.md or use feature-<name>-<part> naming)")
    sys.exit(0)
print("| Feature | Status | Changes | Progress | Wave | Blocks | Blocked by |")
print("|---------|--------|---------|----------|------|--------|------------|")
for name in sorted(features):
    info = features[name]
    if name == "__ungrouped__":
        print(f"| **{name}** | ⚪ ungrouped | {info['change_count']} | — | — | — | — |")
        continue
    status_icon = {
        "blocked": "🔴", "in_progress": "🟡", "ready": "🟢", "done": "✅"
    }.get(info["status"], "⚪")
    blocks = ", ".join(info["blocks"]) or "—"
    blocked_by = ", ".join(info["depends_on"]) or "—"
    print(f"| {name} | {status_icon} {info['status']} | {info['change_count']} | "
          f"{info['archived_count']}/{info['change_count']} | {info['parallel_group']} | "
          f"{blocks} | {blocked_by} |")
PYEOF
        ;;
    graph)
        python3 - <<'PYEOF'
import json, os, sys
from pathlib import Path
root = os.environ["PROJECT_ROOT"]
try:
    from skills._lib import feature_view as fv
except ImportError as e:
    print(f"❌ feature_view module unavailable: {e}", file=sys.stderr); sys.exit(2)
try:
    fv.update_iteration_feature_view(root)
except (fv.NoIterationError, fv.FileLockedError) as e:
    print(f"❌ {e}", file=sys.stderr); sys.exit(1)
data = json.loads(Path(f"{root}/.rddf/state/iteration.json").read_text())
fv_node = data["feature_view"]
features = fv_node["features"]
edges = []
conflicts = []
seen = set()
for name, info in features.items():
    for b in info.get("blocks", []):
        e = (name, b, "hard")
        if e not in seen:
            edges.append(e); seen.add(e)
    for c in info.get("conflicts_with", []):
        pair = tuple(sorted([name, c]))
        if pair not in seen:
            conflicts.append(pair); seen.add(pair)
pg = {n: info["parallel_group"] for n, info in features.items()}
mermaid = fv.render_mermaid(features, edges, conflicts, pg)
print("```mermaid")
print(mermaid)
print("```")
if fv_node.get("__cycle_warning__"):
    print(f"\n⚠️ Cycle detected: {fv_node.get('__cycle_members__')}")
PYEOF
        ;;
    status)
        if [ -z "$TARGET_NAME" ]; then
            echo "❌ usage: feature status <name>"; exit 2
        fi
        python3 - "$TARGET_NAME" <<'PYEOF'
import json, os, sys
from pathlib import Path
root = os.environ["PROJECT_ROOT"]
target = sys.argv[1]
try:
    from skills._lib import feature_view as fv
except ImportError as e:
    print(f"❌ feature_view module unavailable: {e}", file=sys.stderr); sys.exit(2)
try:
    fv.update_iteration_feature_view(root)
except (fv.NoIterationError, fv.FileLockedError) as e:
    print(f"❌ {e}", file=sys.stderr); sys.exit(1)
data = json.loads(Path(f"{root}/.rddf/state/iteration.json").read_text())
info = data["feature_view"]["features"].get(target)
if info is None:
    names = sorted(data["feature_view"]["features"].keys())
    print(f"❌ feature '{target}' not found. Known: {names}", file=sys.stderr); sys.exit(1)
print(f"## {target}\n")
print(f"- **Status:** {info['status']}")
print(f"- **Rollup basis:** {info['rollup_basis']}")
print(f"- **Change count:** {info['change_count']} (archived: {info['archived_count']})")
print(f"- **Wave:** {info['parallel_group']}")
print(f"- **Blocks:** {', '.join(info['blocks']) or '—'}")
print(f"- **Blocked by:** {', '.join(info['depends_on']) or '—'}\n")
print("| Change | Status | Blocker | Phase | Category |")
print("|--------|--------|---------|-------|----------|")
all_changes = {c["name"]: c for c in data.get("changes", [])}
for n in info["change_names"]:
    c = all_changes.get(n, {})
    print(f"| {n} | {c.get('status', '—')} | {c.get('blocker') or '—'} | "
          f"{c.get('phase', '—')} | {c.get('category', '—')} |")
PYEOF
        ;;
    order)
        python3 - <<'PYEOF'
import json, os, sys
from pathlib import Path
root = os.environ["PROJECT_ROOT"]
try:
    from skills._lib import feature_view as fv
except ImportError as e:
    print(f"❌ feature_view module unavailable: {e}", file=sys.stderr); sys.exit(2)
try:
    fv.update_iteration_feature_view(root)
except (fv.NoIterationError, fv.FileLockedError) as e:
    print(f"❌ {e}", file=sys.stderr); sys.exit(1)
data = json.loads(Path(f"{root}/.rddf/state/iteration.json").read_text())
order = data["feature_view"].get("execution_order", [])
features = data["feature_view"]["features"]
if not order:
    print("(no features)"); sys.exit(0)
print("## Recommended execution order\n")
for i, wave in enumerate(order):
    if not wave: continue
    print(f"- **Wave {i}** (run in parallel):")
    for f in sorted(wave):
        info = features.get(f, {})
        print(f"  - {f} ({info.get('status', '—')} · {info.get('archived_count', 0)}/{info.get('change_count', 0)})")
PYEOF
        ;;
    *)
        echo "❌ unknown subcommand: $SUBCOMMAND" >&2
        echo "Usage: feature [summary|graph|status <name>|order]" >&2
        exit 2
        ;;
esac
```