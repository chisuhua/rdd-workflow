#!/usr/bin/env bash
# roadmap migrate: 9-step atomic workflow.
# Per add-hierarchical-roadmap-structure (additive to skills/roadmap/ skill).
#
# Steps: preflight → parse main → plan slice → dry-run → backup → execute → validate → archive hint → rollback hint
#
# Per Metis review (commit before this version):
#   - removed `set +e` (per-command error check with || { echo ❌; exit 1 })
#   - awk extracts phase|theme in single pass (not hardcoded TBD)
#   - backup covers 3 files: roadmap.md + tasks.md (current change) + .arch-handoff.json
#   - Step 7 has 5 content assertions (AUTO-INDEX sentinel, ≥1 phase fragment, frontmatter id, root is stub, handoff v2 hint)
#
# Usage:
#   roadmap-migrate --dry-run                    # preview slice
#   roadmap-migrate --execute --yes              # apply
#   roadmap-migrate --rollback <backup-dir> --yes  # undo

set -euo pipefail

PROJECT_ROOT="${RDDF_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
FRAGMENTS_DIR=".rddf/roadmap"
MAIN_DOC=".rddf/roadmap.md"
ROOT_ROADMAP="roadmap.md"
HANDOFF_FILE=".rddf/state/.arch-handoff.json"
BACKUP_PREFIX=".rddf/.roadmap-migrate-backup"
CHANGE_NAME="${CHANGE_NAME:-}"

# Parse args
DRY_RUN=true
EXECUTE=false
ROLLBACK=""
BACKUP_DIR=""
ASSUME_YES=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=true; EXECUTE=false ;;
        --execute) DRY_RUN=false; EXECUTE=true ;;
        --rollback) ROLLBACK="$2"; shift ;;
        --backup-dir) BACKUP_DIR="$2"; shift ;;
        --yes) ASSUME_YES=true ;;
        *) echo "Unknown arg: $1" >&2; exit 2 ;;
    esac
    shift
done

cd "$PROJECT_ROOT"

# --- Step 9: Rollback path (early) ---
if [ -n "$ROLLBACK" ]; then
    if [ ! -d "$ROLLBACK" ]; then
        echo "❌ Rollback dir not found: $ROLLBACK" >&2
        exit 1
    fi
    echo "🔙 Rolling back from $ROLLBACK ..."
    # Restore root roadmap.md
    if [ -f "$ROLLBACK/roadmap.md" ]; then
        cp "$ROLLBACK/roadmap.md" "$ROOT_ROADMAP"
    fi
    # Restore tasks.md (current change)
    if [ -n "$CHANGE_NAME" ] && [ -f "$ROLLBACK/tasks.md" ]; then
        cp "$ROLLBACK/tasks.md" "openspec/changes/$CHANGE_NAME/tasks.md" 2>/dev/null || true
    fi
    # Restore handoff
    if [ -f "$ROLLBACK/.arch-handoff.json" ] 2>/dev/null && [ -f "$HANDOFF_FILE" ]; then
        cp "$ROLLBACK/.arch-handoff.json" "$HANDOFF_FILE" 2>/dev/null || true
    fi
    # Remove new structure
    rm -rf ".rddf/roadmap" ".rddf/roadmap.md" 2>/dev/null || true
    echo "✅ Rollback complete"
    exit 0
fi

# --- Step 1: Preflight ---
if [ ! -f "$ROOT_ROADMAP" ]; then
    echo "❌ Root $ROOT_ROADMAP not found; cannot migrate" >&2
    exit 1
fi
if [ -d "$FRAGMENTS_DIR" ] && [ -n "$(ls -A "$FRAGMENTS_DIR" 2>/dev/null | grep -v '^\.gitkeep$')" ]; then
    echo "⚠️  $FRAGMENTS_DIR already exists with content; aborting to avoid overwrite" >&2
    exit 1
fi

# --- Step 2: Parse main roadmap.md ---
# Per Metis: extract phase id + theme in single awk pass.
# Supports TWO formats (both observed in real rdd-workflow roadmap.md):
#   1. Table row: | phase-N | theme | status | started | done |
#   2. Heading:   ### Phase N: theme  (or ## Phase N: theme)
# Output: "phase-N|theme" per line (preserves all phases, including duplicates across roadmap versions)
PHASE_THEME_MAP=$(awk '
    function extract_digit(s,   i, c, num) {
        for (i = 1; i <= length(s); i++) {
            c = substr(s, i, 1)
            if (c ~ /[0-9]/) {
                num = c
                while ((i + 1) <= length(s) && substr(s, i + 1, 1) ~ /[0-9]/) {
                    i++
                    num = num substr(s, i, 1)
                }
                return num
            }
        }
        return ""
    }
    /^\| phase-/ {
        # Format 1: pipe-delimited table row
        n = split($0, parts, "|")
        if (n >= 4) {
            gsub(/^ +| +$/, "", parts[2]); gsub(/^ +| +$/, "", parts[3])
            if (parts[2] != "") print parts[2] "|" parts[3]
        }
        next
    }
    /^###? Phase [0-9]+:/ {
        # Format 2: markdown heading "### Phase N: theme" or "## Phase N: theme"
        n = split($0, parts, ":")
        if (n < 2) next
        num = extract_digit(parts[1])
        if (num == "") next
        theme = parts[2]
        for (k = 3; k <= n; k++) theme = theme ":" parts[k]
        gsub(/^ +| +$/, "", theme)
        print "phase-" num "|" theme
    }
' "$ROOT_ROADMAP")

PHASE_COUNT=$(echo "$PHASE_THEME_MAP" | grep -c '.' || true)
if [ "$PHASE_COUNT" -eq 0 ]; then
    echo "⚠️  No phase rows found in $ROOT_ROADMAP phase skeleton table" >&2
    echo "    (Format expected: | phase-N | theme | status | ... |)" >&2
    exit 1
fi

# --- Step 3: Plan slice ---
echo "📋 Migration plan:"
echo "$PHASE_THEME_MAP" | while IFS='|' read -r pid theme; do
    [ -z "$pid" ] && continue
    echo "  - phases/$pid.md (theme: ${theme:-TBD})"
done
echo "  - $MAIN_DOC (rewritten with AUTO-INDEX)"
echo "  - $ROOT_ROADMAP (rewritten as 1-paragraph stub)"

# --- Step 4: Dry-run output ---
if [ "$DRY_RUN" = true ]; then
    echo ""
    echo "🔍 Dry-run only — no files modified"
    echo "  Run with --execute --yes to apply"
    exit 0
fi

# --- Step 5: Backup ---
if [ "$ASSUME_YES" != true ]; then
    echo "❌ Refusing to --execute without --yes" >&2
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="${BACKUP_DIR:-$BACKUP_PREFIX-$TIMESTAMP}"
mkdir -p "$BACKUP_DIR" || { echo "❌ mkdir backup failed" >&2; exit 1; }

# Backup 3 files (per Metis: ensures full rollback including task progress + handoff version)
cp "$ROOT_ROADMAP" "$BACKUP_DIR/roadmap.md" || { echo "❌ backup roadmap failed" >&2; exit 1; }

CHANGE_TASKS=""
if [ -n "$CHANGE_NAME" ] && [ -f "openspec/changes/$CHANGE_NAME/tasks.md" ]; then
    cp "openspec/changes/$CHANGE_NAME/tasks.md" "$BACKUP_DIR/tasks.md" || true
    CHANGE_TASKS="openspec/changes/$CHANGE_NAME/tasks.md"
fi

if [ -f "$HANDOFF_FILE" ]; then
    cp "$HANDOFF_FILE" "$BACKUP_DIR/.arch-handoff.json" || true
fi

echo "💾 Backup: $BACKUP_DIR (roadmap.md${CHANGE_TASKS:+, tasks.md}${HANDOFF_FILE:+, handoff})"

# Git tag if in repo
if git rev-parse --git-dir >/dev/null 2>&1; then
    git tag "pre-roadmap-migrate-$TIMESTAMP" 2>/dev/null || true
fi

# --- Step 6: Execute (per Metis: no set +e; per-command error check) ---
mkdir -p "$FRAGMENTS_DIR/phases" "$FRAGMENTS_DIR/features" "$FRAGMENTS_DIR/archive" \
    || { echo "❌ mkdir fragments failed; rolling back" >&2; exit 1; }

# Write per-phase fragments with theme from root roadmap.md (not hardcoded TBD)
echo "$PHASE_THEME_MAP" | while IFS='|' read -r phase_id phase_theme; do
    [ -z "$phase_id" ] && continue
    [ -z "$phase_theme" ] && phase_theme="(migrated from root roadmap.md)"
    cat > "$FRAGMENTS_DIR/phases/$phase_id.md" <<EOF || { echo "❌ fragment write failed for $phase_id; rolling back" >&2; exit 1; }
---
id: $phase_id
kind: phase
status: active
phase_refs: []
主题: $phase_theme
---

## $phase_id content (migrated from root roadmap.md)
EOF
done

# Write main doc (phase table from original + AUTO-INDEX sentinel)
cat > "$MAIN_DOC" <<'MAINEOF' || { echo "❌ main doc write failed; rolling back" >&2; exit 1; }
# Roadmap

## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
MAINEOF
# Per Metis review + root roadmap format discovery: support both table-row
# and heading formats. Use the same dual-format parser as Step 2 so main doc
# phase table is non-empty even when source uses "### Phase N: title" headings.
awk '
    /^\| phase-/ { print; next }
    /^###? Phase [0-9]+:/ {
        n = split($0, parts, ":")
        if (n < 2) next
        for (i = 1; i <= length(parts[1]); i++) {
            c = substr(parts[1], i, 1)
            if (c ~ /[0-9]/) {
                num = c
                while ((i + 1) <= length(parts[1]) && substr(parts[1], i + 1, 1) ~ /[0-9]/) {
                    i++
                    num = num substr(parts[1], i, 1)
                }
                break
            }
        }
        if (num == "") next
        theme = parts[2]
        for (k = 3; k <= n; k++) theme = theme ":" parts[k]
        gsub(/^ +| +$/, "", theme)
        print "| phase-" num " | " theme " | active | | |"
    }
' "$ROOT_ROADMAP" | sort -u >> "$MAIN_DOC"
cat >> "$MAIN_DOC" <<'MAINEOF'

<!-- AUTO-INDEX -->
MAINEOF

# Rewrite root roadmap.md as stub
cat > "$ROOT_ROADMAP" <<'STUBEOF' || { echo "❌ root stub write failed; rolling back" >&2; exit 1; }
# Roadmap (deprecated pointer)

本文件已迁移，详见 `.rddf/roadmap.md`。

保留为 stub 是为了不破坏外部文档链接与 ADR-0016 默认 fallback。
STUBEOF

# --- Step 7: Validate (per Metis: 5 content assertions) ---
VALIDATION_FAILED=0

# 7.1: Main doc has AUTO-INDEX sentinel
if ! grep -q "<!-- AUTO-INDEX -->" "$MAIN_DOC"; then
    echo "❌ Validation: $MAIN_DOC missing AUTO-INDEX sentinel" >&2
    VALIDATION_FAILED=1
fi

# 7.2: At least 1 phase fragment exists (prevents empty migration)
if [ -z "$(ls -A "$FRAGMENTS_DIR/phases" 2>/dev/null | grep -v '^\.gitkeep$')" ]; then
    echo "❌ Validation: no phase fragments created (PHASES empty? awk parsing failed?)" >&2
    VALIDATION_FAILED=1
fi

# 7.3: Each phase fragment has id in frontmatter
for frag in "$FRAGMENTS_DIR/phases"/*.md; do
    [ -f "$frag" ] || continue
    if ! grep -q "^id: " "$frag"; then
        echo "❌ Validation: $frag missing frontmatter id" >&2
        VALIDATION_FAILED=1
    fi
done

# 7.4: Root roadmap.md is now the stub
if ! grep -q "本文件已迁移" "$ROOT_ROADMAP"; then
    echo "❌ Validation: root roadmap.md not rewritten as stub" >&2
    VALIDATION_FAILED=1
fi

# 7.5: handoff bump to v2 hint (informational, not blocking — actual bump is Task 8.3)
if [ -f "$HANDOFF_FILE" ]; then
    if ! grep -q '"version": 2' "$HANDOFF_FILE"; then
        echo "⚠️  Handoff still v1 (bump to v2 must run separately in Task 8.3 / write_arch_handoff.py)" >&2
    fi
fi

if [ "$VALIDATION_FAILED" -ne 0 ]; then
    echo "❌ Post-migration validation failed; rolling back" >&2
    # Rollback root + tasks + handoff
    cp "$BACKUP_DIR/roadmap.md" "$ROOT_ROADMAP" || true
    [ -n "$CHANGE_TASKS" ] && [ -f "$BACKUP_DIR/tasks.md" ] && cp "$BACKUP_DIR/tasks.md" "$CHANGE_TASKS" || true
    [ -f "$BACKUP_DIR/.arch-handoff.json" ] && cp "$BACKUP_DIR/.arch-handoff.json" "$HANDOFF_FILE" || true
    rm -rf "$FRAGMENTS_DIR" "$MAIN_DOC" || true
    exit 1
fi

# --- Step 8: Archive hint ---
echo ""
echo "✅ Migration complete"
echo "  Backup: $BACKUP_DIR"
echo "  Tag: pre-roadmap-migrate-$TIMESTAMP"
echo "  ℹ️  Consider archiving the old (pre-migration) commit if you no longer need its history"
echo "  ℹ️  Run: $0 --rollback $BACKUP_DIR --yes  to undo"
echo "  ℹ️  Run: rddf roadmap validate-fragments  to verify fragment refs"
exit 0
