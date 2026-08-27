#!/usr/bin/env bash
# reconcile-iteration.sh — 一性脚本: scan openspec/changes/archive/ 找出已 archive 的 changes,
# reconcile .rddf/state/iteration.json 中对应条目的 status 为 'archived' + tasks_done=tasks_total。
# Per reconcile-iteration-after-change proposal.
# 配套: .rddf/state/.before-reconcile/iteration.json.before-reconcile-<date>

set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
ITERATION_FILE="$PROJECT_ROOT/.rddf/state/iteration.json"
ARCHIVE_DIR="$PROJECT_ROOT/openspec/changes/archive"
BACKUP_BASE="$PROJECT_ROOT/.rddf/state/.before-reconcile"
TIMESTAMP=$(date -u +%Y-%m-%d)
BACKUP_FILE="$BACKUP_BASE/iteration.json.before-reconcile-$TIMESTAMP"
DRY_RUN="${DRY_RUN:-no}"

usage() {
  cat <<USAGE
Usage: PROJECT_ROOT=/path bash reconcile-iteration.sh [--dry-run]

环境变量:
  PROJECT_ROOT  项目根目录 (默认: git toplevel)
  DRY_RUN=yes   仅预览不写

效果:
  1. 扫描 $ARCHIVE_DIR/<date>-<name>/ 中所有 archive 的 changes
  2. 对每个 change,如 .rddf/state/iteration.json 中存在且 status != 'archived',
     更新 status='archived',tasks_done=tasks_total
  3. 写前先备份 iteration.json 到 $BACKUP_FILE
  4. atomic write 保护
  5. 输出 reconcile report
USAGE
}

case "${1:-}" in
  --dry-run) DRY_RUN=yes ;;
  -h|--help) usage; exit 0 ;;
  "") : ;;
  *) echo "unknown arg: $1" >&2; usage; exit 1 ;;
esac

if [ ! -f "$ITERATION_FILE" ]; then
  echo "❌ iteration.json 不存在: $ITERATION_FILE" >&2
  exit 1
fi

if [ ! -d "$ARCHIVE_DIR" ]; then
  echo "❌ archive 目录不存在: $ARCHIVE_DIR" >&2
  exit 1
fi

# 备份
mkdir -p "$BACKUP_BASE"
if [ "$DRY_RUN" = "yes" ]; then
  echo "[DRY-RUN] would backup to $BACKUP_FILE"
else
  cp "$ITERATION_FILE" "$BACKUP_FILE"
  echo "✅ backup: $BACKUP_FILE"
fi

# 收集 archive 后的 change 名: 目录名格式 YYYY-MM-DD-<name>
# 例: 2026-08-27-sync-package-skills-to-disk → sync-package-skills-to-disk
mapfile -t ARCHIVED < <(find "$ARCHIVE_DIR" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null \
  | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}-' \
  | sed -E 's/^[0-9]{4}-[0-9]{2}-[0-9]{2}-//' \
  | sort -u)

if [ "${#ARCHIVED[@]}" -eq 0 ]; then
  echo "⚠️  archive dir 为空 (或命名不符),无需 reconcile"
  exit 0
fi

echo "🔍 发现 ${#ARCHIVED[@]} 个已 archive change(s):"
for name in "${ARCHIVED[@]}"; do echo "  - $name"; done

# 读取 iteration.json
ITER_DATA=$(cat "$ITERATION_FILE")

# Use file-based exchange (more robust than env arrays)
ARCHIVED_FILE="$BACKUP_BASE/.archived-names.tmp"
printf '%s\n' "${ARCHIVED[@]}" > "$ARCHIVED_FILE"
trap 'rm -f "$ARCHIVED_FILE"' EXIT

ARCHIVED_FILE="$ARCHIVED_FILE" \
ITERATION_FILE="$ITERATION_FILE" \
DRY_RUN="$DRY_RUN" \
  python3 - <<'PYEOF'
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path

iter_path = os.environ["ITERATION_FILE"]
archived_file = os.environ["ARCHIVED_FILE"]
dry = os.environ.get("DRY_RUN", "no") == "yes"

with open(iter_path, encoding="utf-8") as f:
    data = json.load(f)

with open(archived_file) as f:
    archived_names = {line.strip() for line in f if line.strip()}

updated = []
unchanged = []
missing = []

for c in data.get("changes", []):
    name = c.get("name")
    if name not in archived_names:
        continue
    if c.get("status") == "archived":
        unchanged.append(name)
        continue
    old_status = c.get("status")
    total = c.get("tasks_total", 0)
    c["status"] = "archived"
    c["tasks_done"] = total
    c["archived_at"] = datetime.now(timezone.utc).isoformat()
    updated.append((name, old_status, total))

# Build new file (atomic write)
new_data = dict(data)
new_data["updated_at"] = datetime.now(timezone.utc).isoformat()
new_data["changes"] = list(data.get("changes", []))

if dry:
    print(f"[DRY-RUN] would update {len(updated)} entries, {len(unchanged)} already archived")
    for name, old, total in updated:
        print(f"  {name}: status {old} -> archived, tasks_done={total}")
    sys.exit(0)

# atomic write: tmp + rename
tmp = iter_path + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(new_data, f, indent=2, ensure_ascii=False)
os.replace(tmp, iter_path)

print(f"✅ reconciled {len(updated)} entries ({len(unchanged)} already archived)")
for name, old, total in updated:
    print(f"  {name}: status {old} -> archived, tasks_done={total}")
PYEOF

echo ""
echo "📊 reconcile report:"
echo "  archive changes scanned: ${#ARCHIVED[@]}"
echo "  iteration.json updated: $(jq -r --arg n "${ARCHIVED[*]}" '
    (.changes // []) | map(select(.name as $x | ($n | split(" ") | index($x)))) |
    map(select(.status=="archived")) | length
  ' "$ITERATION_FILE")"
echo "  backup: $BACKUP_FILE"
echo ""
echo "💡 下一步: 验证 'rddf rdd-verify --dry-run' 不再 empty queue"