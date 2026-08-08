#!/usr/bin/env bash
# scripts/cleanup-plan-files.sh
#
# Manual entry for archive cleanup. Two modes:
#   (default)        — scan .rddf/plans/ for orphan plan files (no corresponding active change)
#   --include-change-artifacts — scan openspec/changes/<name>/ for 6-residue after archive
#
# Usage:
#   bash scripts/cleanup-plan-files.sh                       # scan .rddf/plans/ orphans
#   bash scripts/cleanup-plan-files.sh --include-change-artifacts  # scan openspec/changes/ residue
#
# Both modes are interactive: lists candidates, requires 'y' confirmation before git rm.
# Idempotent: returns 0 if no candidates found.

set -uo pipefail

# Defaults: only clean .rddf/plans/ orphans
INCLUDE_CHANGES=0

for arg in "$@"; do
  case "$arg" in
    --include-change-artifacts) INCLUDE_CHANGES=1 ;;
    --help|-h)
      grep -E "^#( |!)" "$0" | sed 's/^#//' | head -20
      exit 0
      ;;
  esac
done

# Resolve project root from script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
PROJECT_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$PROJECT_ROOT" || { echo "❌ cannot cd to $PROJECT_ROOT" >&2; exit 1; }

scan_plan_orphans() {
  local count=0
  for plan in .rddf/plans/*.md; do
    [ -f "$plan" ] || continue
    local name=$(basename "$plan" .md)
    if [ -d "openspec/changes/$name" ]; then
      continue
    fi
    if compgen -G "openspec/changes/archive/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-$name" > /dev/null; then
      continue
    fi
    echo "  $name"
    count=$((count + 1))
  done
  return $count
}

scan_change_residue() {
  local count=0
  for dir in openspec/changes/*/; do
    [ -d "$dir" ] || continue
    local name=$(basename "$dir")
    [ "$name" = "archive" ] && continue
    if ! compgen -G "openspec/changes/archive/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-$name" > /dev/null; then
      echo "  ⏭️  $name (no archive, skip)"
      continue
    fi
    local residue=$(git status --porcelain 2>/dev/null | grep -c " D openspec/changes/$name/" || true)
    if [ "$residue" -gt 0 ]; then
      echo "  $name: $residue residue files"
      count=$((count + 1))
    fi
  done
  return $count
}

print_header() {
  echo "📋 archive cleanup scan"
  echo "   project: $PROJECT_ROOT"
  echo "   mode: $1"
  echo ""
}

if [ "$INCLUDE_CHANGES" = "1" ]; then
  print_header "--include-change-artifacts (scan openspec/changes/<name>/ residue)"
  echo "🔍 Scanning for 6-residue in openspec/changes/<name>/..."
  echo ""
  candidates=$(scan_change_residue)
  count=$?
  echo "$candidates"
  echo ""
  if [ "$count" -eq 0 ]; then
    echo "✅ No residue found. Working tree clean."
    exit 0
  fi
  read -r -p "确认清理 $count 个 change dir 的残留? [y/N]: " confirm
  if [ "$confirm" = "y" ]; then
    for dir in openspec/changes/*/; do
      [ -d "$dir" ] || continue
      local name=$(basename "$dir")
      [ "$name" = "archive" ] && continue
      if compgen -G "openspec/changes/archive/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-$name" > /dev/null; then
        git rm -r "$dir" 1>/dev/null && echo "🧹 cleaned: $dir"
      fi
    done
    echo "✅ Done. (Not auto-committed — manual review recommended.)"
  else
    echo "⏭️  Cancelled."
  fi
else
  print_header "default (scan .rddf/plans/ orphans)"
  echo "🔍 Scanning for orphan plan files..."
  echo ""
  candidates=$(scan_plan_orphans)
  count=$?
  echo "$candidates"
  echo ""
  if [ "$count" -eq 0 ]; then
    echo "✅ No orphan plan files found."
    exit 0
  fi
  read -r -p "确认清理 $count 个孤立计划文件? [y/N]: " confirm
  if [ "$confirm" = "y" ]; then
    for plan in .rddf/plans/*.md; do
      [ -f "$plan" ] || continue
      local name=$(basename "$plan" .md)
      if [ -d "openspec/changes/$name" ]; then continue; fi
      if compgen -G "openspec/changes/archive/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-$name" > /dev/null; then continue; fi
      git rm -f "$plan" 1>/dev/null && echo "🧹 cleaned: $plan"
    done
    echo "✅ Done. (Not auto-committed — manual review recommended.)"
  else
    echo "⏭️  Cancelled."
  fi
fi
