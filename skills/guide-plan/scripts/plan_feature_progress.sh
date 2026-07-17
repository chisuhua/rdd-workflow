#!/usr/bin/env bash
# skills/_lib/plan_feature_progress.sh — extracted from guide-plan.md L263-L297
# Exports: show_feature_progress()
#
# Shows per-feature progress via iteration.feature_progress (derived from change name prefix).
# Sorts features by completion ratio (unfinished first).

show_feature_progress() {
  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  export PROJECT_ROOT

  echo ""
  echo "📌 Feature 进度:"
  PY_PROJECT_ROOT="$PROJECT_ROOT" python3 <<'PYEOF' 2>/dev/null
import os, sys
try:
    from skills._lib import iteration as it
    d = it.load(os.environ.get("PY_PROJECT_ROOT", "."))
    progress = it.feature_progress(d)
except Exception:
    progress = {}

if not progress:
    print("  (无 multi-change feature)")
else:
    sorted_features = sorted(progress.items(), key=lambda kv: (kv[1][0] / kv[1][1]) if kv[1][1] > 0 else 0)
    for feature, (done, total) in sorted_features:
        if total == 0:
            continue
        if done == total:
            marker = "✅"
            note = "所有 sub-change 已归档"
        elif done == 0:
            marker = "⏳"
            note = f"尚未归档 ({total} 个子 change)"
        else:
            marker = "⚙️"
            remaining = total - done
            note = f"还有 {remaining} 个 sub-change 未归档"
        print(f"  {marker} {feature}: {done}/{total} {note}")
PYEOF
}