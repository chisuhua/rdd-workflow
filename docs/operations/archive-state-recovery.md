# Archive State Recovery Guide

## 症状

当 `iteration.json` 与 `openspec/changes/archive/` 实际状态不一致时,`rddf status` 会显示不一致的视图:

```bash
$ rddf status
📋 planned  harden-archive-iteration-sync   # 但 openspec/changes/archive/2026-08-16-harden-archive-iteration-sync/ 已存在
```

## 手动修复 (3 步)

1. **运行 reconcile**:
   ```bash
   bash skills/_lib/archive.sh reconcile .
   ```

2. **验证**:
   ```bash
   rddf status | grep harden-archive-iteration-sync
   # 应显示 📦 archived
   ```

3. **如果 iteration.json 被修改,提交**:
   ```bash
   git add .rddf/state/iteration.json
   git commit -m "fix(iteration): reconcile stale archive entries"
   ```

## Opt-out

设置 `FORCE_ITERATION_BACKFILL=no` 关闭 archive 主流程的自动 reconciliation:

```bash
FORCE_ITERATION_BACKFILL=no bash skills/guide-ship/scripts/ship_archive.sh
```

## 快速验证

```bash
# 一行命令: 检测 stale planned + 已存在 archive dir 的 change
comm -12 \
  <(rddf status --json | jq -r '.changes[] | select(.status=="planned") | .name' | sort) \
  <(ls openspec/changes/archive/ | sed 's/^[0-9-]*//' | sort -u) | \
  while read -r name; do [ -d "openspec/changes/archive"/*-"$name" ] && echo "STALE: $name"; done
```

如输出任何 STALE 行,运行 reconcile。