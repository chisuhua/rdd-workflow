# skills/_lib/deps_iteration_sync.sh
# Step 6 of deps.md: sync iteration.json from deps-analysis.json (P3-4d).
# Replaces a 97-line inline PYEOF heredoc with a thin wrapper around
# deps_output.py + iteration.py. The markdown-fallback regex parsing
# was extracted into deps_output.parse_markdown_fallback() and is
# covered by Python unit tests (tests/unit/test_deps_output.py).
#
# Functions exported:
#   - deps_iteration_sync
#       Reads deps-analysis.json (preferred) or parses .deps-output.md
#       fallback, refreshes deps-analysis.json (updated_at), then
#       syncs iteration.json. Graceful exit 0 on any failure (per
#       original contract — deps main flow must not be blocked).
#
# Behavior preserved from inline version:
#   - Prefer deps-analysis.json; fall back to markdown parse if missing
#   - Always rewrite deps-analysis.json (update timestamp)
#   - Graceful exit 0 on any failure (non-fatal)
#   - Print source label: '来源: JSON' or '来源: MARKDOWN-FALLBACK'
#   - Markdown fallback marks records confidence='low'
#   - ImportError -> exit 0 (silent skip)
#   - .deps-output.md missing -> exit 0 (silent skip)

# deps_iteration_sync
deps_iteration_sync() {
  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

  PROJECT_ROOT="$PROJECT_ROOT" python3 <<'PYEOF'
import os, sys
try:
    from skills._lib import deps_output as do_mod
    from skills._lib import iteration as it_mod
except ImportError as e:
    print(f"⚠️  deps_output/iteration 模块不可用, 跳过同步: {e}", file=sys.stderr)
    sys.exit(0)

project_root = os.environ["PROJECT_ROOT"]

analysis = do_mod.load_analysis(project_root)
parsed_from = "JSON"

if analysis is None:
    md_path = os.path.join(project_root, ".rddf", "state", ".deps-output.md")
    if not os.path.exists(md_path):
        print("⏭️  deps-output.md 不存在, 跳过 iteration 同步", file=sys.stderr)
        sys.exit(0)
    records = do_mod.parse_markdown_fallback(project_root)
    if not records:
        print("⏭️  markdown fallback 无 change records, 跳过", file=sys.stderr)
        sys.exit(0)
    parsed_from = "MARKDOWN-FALLBACK"
    analysis = do_mod.build_analysis(records, fallback=True)

try:
    do_mod.write_analysis(project_root, analysis)
    print(f"✅ deps-analysis.json: {len(analysis['changes'])} 个 change (来源: {parsed_from})")
except Exception as e:
    print(f"⚠️  写 deps-analysis.json 失败 (非致命): {e}", file=sys.stderr)

try:
    count = do_mod.sync_iteration_from_analysis(project_root, it_mod)
    if count > 0:
        print(f"✅ iteration.json: 已同步 {count} 个 change 的 deps 信息")
    else:
        print("⏭️  iteration.json: 无需同步")
except Exception as e:
    print(f"⚠️  iteration.json 同步失败 (deps 主流程仍成功): {e}", file=sys.stderr)
    sys.exit(0)
PYEOF
}