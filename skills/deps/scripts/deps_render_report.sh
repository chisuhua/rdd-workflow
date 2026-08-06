# _lib/deps_render_report.sh
# Bash wrapper for deps.md Step 5 (P0-3 extraction).
# Delegates to _lib/deps_output.py::render_markdown_report which
# encapsulates the 160-line inline bash block from deps.md lines 483-642.
#
# Functions exported:
#   - render_deps_report
#       Reads environment variables (PROJECT_ROOT, CANDIDATES, DEPS_OUTPUT,
#       AI_RESULT_FILE, ROADMAP_CURRENT_PHASE) and writes the complete
#       .rddf/state/.deps-output.md report.
#
# Environment variables (set by caller in deps.md Step 5):
#   PROJECT_ROOT          - project root path
#   CANDIDATES            - space-separated list of candidate change names
#   DEPS_OUTPUT           - output file path (typically .rddf/state/.deps-output.md)
#   AI_RESULT_FILE        - optional path to .rddf/state/.deps-ai-result.json
#   ROADMAP_CURRENT_PHASE - optional current phase for out-of-phase detection
#
# Behavior preserved from inline version (deps.md lines 483-642):
# - mkdir -p for .rddf/state/ before writing
# - All output sections (header, mermaid, precheck, status, recommended, conflicts, AI)
# - Fallback to "AI 语义分析未启用" when no AI file
# - Graceful JSON parse failure on malformed AI file

# render_deps_report
render_deps_report() {
  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  DEPS_OUTPUT="${DEPS_OUTPUT:-$PROJECT_ROOT/.rddf/state/.deps-output.md}"

  mkdir -p "$(dirname "$DEPS_OUTPUT")"

  # Convert CANDIDATES string to Python list format (comma-separated,
  # avoids adjacent-string concat bug: 'a' 'b' 'c' != ['a','b','c'])
  local candidates_py
  candidates_py=$(PY_CANDIDATES="$CANDIDATES" python3 -c '
import json, os, shlex
cands = shlex.split(os.environ.get("PY_CANDIDATES", ""))
print(json.dumps(cands))
' 2>/dev/null)
  # If CANDIDATES is empty, fall back to reading deps-candidates.json
  if [ -z "$CANDIDATES" ]; then
    local deps_input="$PROJECT_ROOT/.rddf/state/.deps-candidates.json"
    CANDIDATES=$(python3 -c "import json; d=json.load(open('$deps_input')); print(' '.join(d.get('candidates',[])))" 2>/dev/null)
    if [ -z "$CANDIDATES" ]; then
      candidates_py="[]"
    else
      # fallback 读取成功后重新计算 candidates_py（原实现漏掉此行）
      candidates_py=$(PY_CANDIDATES="$CANDIDATES" python3 -c '
import json, os, shlex
cands = shlex.split(os.environ.get("PY_CANDIDATES", ""))
print(json.dumps(cands))
' 2>/dev/null)
    fi
  fi

  PROJECT_ROOT="$PROJECT_ROOT" \
  AI_RESULT_FILE="$AI_RESULT_FILE" \
  ROADMAP_CURRENT_PHASE="$ROADMAP_CURRENT_PHASE" \
  CANDIDATES_PY="$candidates_py" \
  python3 <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["PROJECT_ROOT"])
from skills.deps.scripts import deps_output as do

project_root = os.environ["PROJECT_ROOT"]
candidates_str = os.environ.get("CANDIDATES_PY", "[]")
# Parse the Python list literal
candidates = eval(candidates_str)  # safe — we built the string ourselves
ai_result_file = os.environ.get("AI_RESULT_FILE") or None
ai_result_file = ai_result_file if ai_result_file else None
roadmap_current_phase = os.environ.get("ROADMAP_CURRENT_PHASE") or None
roadmap_current_phase = roadmap_current_phase if roadmap_current_phase else None

output = do.render_markdown_report(
    candidates=candidates,
    project_root=project_root,
    ai_result_file=ai_result_file,
    roadmap_current_phase=roadmap_current_phase,
)

deps_output = os.environ.get("DEPS_OUTPUT", f"{project_root}/.rddf/state/.deps-output.md")
with open(deps_output, "w") as f:
    f.write(output)
    f.write("\n")
PYEOF

  echo "✅ 依赖分析报告已写入: $DEPS_OUTPUT"
}