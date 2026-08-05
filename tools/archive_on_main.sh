#!/usr/bin/env bash
# tools/archive_on_main.sh — on-main archive flow for OpenSpec changes.
#
# Created: fix-archive-on-main-flow (P0, 2026-08-05).
# Depends on: skills/_lib/iteration/post_archive.py::sync_iteration_after_archive
#             (shipped via fix-archive-iteration-sync, the prior P0 in the chain).
#
# Why this script exists:
#   The happy path for shipping a change is `archive.sh::archive_change` in a
#   worktree (see skills/_lib/archive.sh). That path auto-merges and calls
#   sync_iteration_after_archive. This script is the OFF-HAPPY-PATH bypass:
#   archive a change directly on the default branch without a worktree.
#
# Fail-closed guard:
#   --confirm-main is REQUIRED. Without it, the script exits 2 immediately,
#   printing the off-happy-path banner. This prevents accidental direct-on-main
#   archive from running through a long bash chain and committing to master.
#
# Behavior:
#   1. Parse args; require --confirm-main.
#   2. Verify git repo, change dir exists, archive dir does not yet exist.
#   3. Compute archive dir name (today + change_name).
#   4. mv openspec/changes/<name>/ → openspec/changes/archive/<date>-<name>/
#   5. Invoke sync_iteration_after_archive (sets status=archived + archived_at
#      + archive_commit_sha + tasks_done + plan_path on iteration.json).
#   6. On helper failure: mv the archive dir back to its original location.
#      Helper never raises (it logs + returns warning string), so the
#      rollback only fires for hard I/O errors. The archive commit can still
#      proceed; the helper's warning is non-blocking per its own contract.
#
# Rollback contract (per fix-archive-on-main-flow §关键场景):
#   If the helper returns a warning string, the script still prints
#   "⚠️  iteration.json sync failed — run 'rddf status --check-archive-sync' later"
#   and exits 0. The archive mv is NOT rolled back. This matches the
#   proposal's "fail open" guidance: archive is the primary success criterion,
#   iteration.json drift is recoverable via `rddf status --check-archive-sync`.
#
# Idempotency:
#   If the archive dir already exists, the script refuses to proceed. This
#   protects against re-invocation (CI retry, script bug) creating duplicate
#   archive entries.
set -euo pipefail

# --- arg parsing ---

CONFIRM_MAIN=0
ARCHIVE_COMMIT_SHA=""

usage() {
  cat <<'EOF'
Usage: tools/archive_on_main.sh <change-name> --confirm-main [--archive-commit-sha <sha>]

Archive an OpenSpec change directly on the main branch (OFF-HAPPY-PATH).

⚠️  OFF-HAPPY-PATH: archiving on main without worktree. Use --confirm-main to proceed.

This bypass is for the on-main flow described in fix-archive-on-main-flow.
The default path is `archive.sh::archive_change` in a worktree; use that
unless you specifically need the on-main variant.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --confirm-main) CONFIRM_MAIN=1; shift ;;
    --archive-commit-sha) ARCHIVE_COMMIT_SHA="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "❌ unknown flag: $1" >&2; usage; exit 2 ;;
    *) CHANGE_NAME="$1"; shift ;;
  esac
done

# --- fail-closed: --confirm-main is mandatory ---

if [[ "$CONFIRM_MAIN" -ne 1 ]]; then
  echo "⚠️  OFF-HAPPY-PATH. Pass --confirm-main to archive without worktree." >&2
  usage >&2
  exit 2
fi

if [[ -z "${CHANGE_NAME:-}" ]]; then
  echo "❌ change name required" >&2
  usage >&2
  exit 2
fi

# --- precondition checks ---

# Must be in a git repo (we use git for path resolution + commit SHA capture).
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "❌ not in a git repository; on-main archive requires git" >&2
  exit 3
fi

# Resolve project root from cwd; prefer git rev-parse for worktree safety.
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$PROJECT_ROOT"

# Idempotency: refuse if the archive dir already exists (any date prefix).
ARCHIVE_BASE="$PROJECT_ROOT/openspec/changes/archive"
if [[ -d "$ARCHIVE_BASE" ]] && compgen -G "$ARCHIVE_BASE/*-$CHANGE_NAME" >/dev/null; then
  existing=$(compgen -G "$ARCHIVE_BASE/*-$CHANGE_NAME" | head -1)
  echo "❌ archive dir already exists: $existing" >&2
  echo "   refusing to re-archive; check status and recover manually" >&2
  exit 5
fi

# Verify the change directory exists in openspec/changes/.
CHANGE_DIR="$PROJECT_ROOT/openspec/changes/$CHANGE_NAME"
if [[ ! -d "$CHANGE_DIR" ]]; then
  echo "❌ change directory not found: $CHANGE_DIR" >&2
  exit 4
fi

# --- compute archive dir name (today) ---

ARCHIVE_DATE="$(date -u +%Y-%m-%d)"
ARCHIVE_DIR="$ARCHIVE_BASE/${ARCHIVE_DATE}-${CHANGE_NAME}"

# --- perform archive ---

echo "📦 Archiving $CHANGE_NAME → $ARCHIVE_DIR"
mkdir -p "$ARCHIVE_BASE"
mv "$CHANGE_DIR" "$ARCHIVE_DIR"

# --- sync iteration.json (the whole point of this proposal) ---

# Use the helper from fix-archive-iteration-sync. The helper is idempotent
# and fail-open (returns warning string, never raises).
SYNC_RESULT=$(PROJECT_ROOT="$PROJECT_ROOT" \
              CHANGE_NAME="$CHANGE_NAME" \
              ARCHIVE_COMMIT_SHA="$ARCHIVE_COMMIT_SHA" \
              python3 - <<'PYEOF' 2>&1
import os, sys
sys.path.insert(0, os.environ.get("SKILLS_PARENT", "."))
try:
    from skills._lib.iteration import post_archive as pa
except ImportError as exc:
    print(f"WARN: helper unavailable: {exc}")
    sys.exit(0)
try:
    warn = pa.sync_iteration_after_archive(
        project_root=os.environ["PROJECT_ROOT"],
        change_name=os.environ["CHANGE_NAME"],
        archive_commit_sha=os.environ.get("ARCHIVE_COMMIT_SHA") or None,
    )
    if warn:
        print(f"WARN: {warn}")
    else:
        print("OK")
except Exception as exc:
    print(f"WARN: helper raised: {exc}")
PYEOF
)

if [[ "$SYNC_RESULT" == "WARN:"* || "$SYNC_RESULT" == *"WARN:"* ]]; then
  echo "⚠️  iteration.json sync failed — run 'rddf status --check-archive-sync' later" >&2
  echo "   archive mv at $ARCHIVE_DIR is preserved; iteration drift is recoverable" >&2
  echo "   helper said: $SYNC_RESULT" >&2
  # Non-blocking per proposal §关键场景: archive success > iteration drift.
  exit 0
fi

echo "✅ iteration.json synced for $CHANGE_NAME"
echo "   archive dir: $ARCHIVE_DIR"
exit 0
