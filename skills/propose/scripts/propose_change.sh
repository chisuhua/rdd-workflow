# skills/_lib/propose_change.sh
# Bash wrapper for propose.md Phase 4 (P0-1 extraction).
# Encapsulates 5 Python helpers in _lib/propose_change.py:
#   - set_suggestion_status
#   - create_skeleton_change
#   - update_roadmap_meta
#   - update_roadmap_state
#   - update_iteration_proposed
#
# Functions exported:
#   - propose_create_change <name> --skeleton <phase> <category> <priority>
#       Skeleton branch: writes minimal proposal.md + roadmap-meta.yaml,
#       updates iteration.json (status=planned). Matches original skeleton
#       branch at propose.md lines 486-551.
#
#   - propose_finalize_change <name> <phase> <category> <priority> <valid_categories>
#       Full create finalization: writes roadmap-meta.yaml, updates
#       roadmap-state.json, updates iteration.json (status=proposed).
#       Matches original full branch at propose.md lines 617-760.
#       Note: openspec new change + baseline validation (lines 553-575)
#       are NOT extracted — they remain in propose.md inline because they
#       orchestrate external openspec CLI calls.
#       The artifact creation loop at lines 580-608 (HALF-IMPLEMENTED
#       pseudo-code) is preserved as-is in propose.md.

# propose_create_change <name> --skeleton <phase> <category> <priority>
propose_create_change() {
  local name="$1"
  local mode="$2"
  local current_phase="$3"
  local category="$4"
  local priority="$5"

  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

  if [ "$mode" = "--skeleton" ]; then
    PROJECT_ROOT="$PROJECT_ROOT" python3 <<PYEOF
import os, sys
sys.path.insert(0, os.environ["PROJECT_ROOT"])
from skills.propose.scripts import propose_change as pc
kwargs = dict(
    project_root=os.environ["PROJECT_ROOT"],
    name="$name",
    current_phase="$current_phase",
    category="$category",
    priority="$priority",
)
pf = os.environ.get("PARENT_FEATURE") or None
if pf is not None:
    kwargs["parent_feature"] = pf
result = pc.create_skeleton_change(**kwargs)
if not result:
    sys.exit(1)
PYEOF
  fi
}

# propose_finalize_change <name> <phase> <category> <priority> <valid_categories>
propose_finalize_change() {
  local name="$1"
  local current_phase="$2"
  local category="$3"
  local priority="$4"
  local valid_categories="$5"

  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

  PROJECT_ROOT="$PROJECT_ROOT" CURRENT_PHASE="$current_phase" \
    VALID_CATEGORIES="$valid_categories" \
    PARENT_FEATURE="${PARENT_FEATURE:-}" \
    python3 <<PYEOF
import os, sys
sys.path.insert(0, os.environ["PROJECT_ROOT"])
from skills.propose.scripts import propose_change as pc
project_root = os.environ["PROJECT_ROOT"]
current_phase = os.environ["CURRENT_PHASE"]
valid_categories = os.environ.get("VALID_CATEGORIES", "")
pf = os.environ.get("PARENT_FEATURE") or None
meta_kwargs = dict(
    project_root=project_root,
    name="$name",
    current_phase=current_phase,
    change_category="$category",
    priority="$priority",
    valid_categories=valid_categories,
)
if pf is not None:
    meta_kwargs["parent_feature"] = pf
pc.update_roadmap_meta(**meta_kwargs)
pc.update_roadmap_state(
    project_root=project_root,
    name="$name",
    change_phase=current_phase,
    change_category="$category",
)
iter_kwargs = dict(
    project_root=project_root,
    name="$name",
    phase=current_phase,
    category="$category",
    priority="$priority",
)
if pf is not None:
    iter_kwargs["parent_feature"] = pf
pc.update_iteration_proposed(**iter_kwargs)
PYEOF
}