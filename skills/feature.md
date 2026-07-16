---
name: feature
description: View and manage features (groups of related changes). Provides summary table, Mermaid dependency graph, per-feature change status, and recommended wave execution order. Pure derived view from iteration.json + deps-analysis.json.
license: MIT
compatibility: Requires iteration.json (run `guide-plan` once first) and ideally deps-analysis.json (run `deps` first for full graph).
metadata:
  version: "2.0"
  author: sisyphus
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
export PROJECT_ROOT

SUBCOMMAND="${1:-summary}"
TARGET_NAME="${2:-}"

# Source all 4 subcommand helpers
_SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]:-$0}")"
if [ ! -f "$_SCRIPT_DIR/_lib/feature_summary.sh" ]; then
  # Piped execution (e.g., extracted-by-test): BASH_SOURCE is /dev/fd/N.
  if [ -n "${REPO_ROOT:-}" ] && [ -f "$REPO_ROOT/skills/_lib/feature_summary.sh" ]; then
    _SCRIPT_DIR="$REPO_ROOT/skills"
  else
    _SCRIPT_DIR="$PROJECT_ROOT/skills"
  fi
fi
source "$_SCRIPT_DIR/_lib/feature_summary.sh"
source "$_SCRIPT_DIR/_lib/feature_graph.sh"
source "$_SCRIPT_DIR/_lib/feature_status.sh"
source "$_SCRIPT_DIR/_lib/feature_order.sh"

case "$SUBCOMMAND" in
    summary|"")
        render_feature_summary
        ;;
    graph)
        render_feature_graph
        ;;
    status)
        if [ -z "$TARGET_NAME" ]; then
            echo "❌ usage: feature status <name>" >&2
            exit 2
        fi
        render_feature_status "$TARGET_NAME"
        ;;
    order)
        render_feature_order
        ;;
    *)
        echo "❌ unknown subcommand: $SUBCOMMAND" >&2
        echo "Usage: feature [summary|graph|status <name>|order]" >&2
        exit 2
        ;;
esac
```