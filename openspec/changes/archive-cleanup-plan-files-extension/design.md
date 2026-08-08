# Design — archive-cleanup-plan-files-extension

## 1. 背景与目标

`post-archive-cleanup-hook`（P0，2026-08-06 落地）已经覆盖 `.rddf/plans/` 与 `.rddf/state/*.tmp` 残留,
但 `add-rdd-doctor-skill` 的 archive 走 `merge → openspec archive` 路径时（**不是** `archive_change_for_mode → cleanup_plan_file`）,
6 类 change artifact 留在 working tree 不被 helper 覆盖:

- `openspec/changes/<name>/.openspec.yaml`
- `openspec/changes/<name>/design.md`
- `openspec/changes/<name>/proposal.md`
- `openspec/changes/<name>/roadmap-meta.yaml`
- `openspec/changes/<name>/specs/<cap>/spec.md`
- `openspec/changes/<name>/tasks.md`

残留让 `./test.sh --full` 多报 6 项 `D` status 噪音，并触发 `rdd-doctor` 的 state-category 警告。

**目标**: 扩展 `_WHITELIST_DELETED_PATTERNS` 包含 `openspec/changes/`，并在 `git rm` 前防御性检查
`openspec/changes/archive/<date>-<name>/` 存在（防止误删活跃 change）。

## 2. 设计概述

### 2.1 核心扩展

```bash
# _lib/post_archive_cleanup.sh 当前:
_WHITELIST_DELETED_PATTERNS=(
  ".rddf/plans/"
  ".rddf/state/.arch-handoff.json.tmp"
  ".rddf/state/.plan-handoff.json.tmp"
)

# 扩展后:
_WHITELIST_DELETED_PATTERNS=(
  ".rddf/plans/"
  ".rddf/state/.arch-handoff.json.tmp"
  ".rddf/state/.plan-handoff.json.tmp"
  "openspec/changes/"   # ← NEW
)
```

### 2.2 防御性 archive-presence 检查

在 `post_archive_cleanup` 主循环中,当 `x y` 模式为 ` D`（worktree deleted, not staged）,
且 path 匹配 `openspec/changes/` 前缀, **且** `path` 不以 `openspec/changes/archive/` 开头时,
额外验证 `openspec/changes/archive/<date>-<name>/` 存在:

```bash
# 伪代码 (实际写入按现有 pattern 风格)
case "$path" in
  openspec/changes/archive/*) ;;  # 跳过 archive/ 自身
  openspec/changes/*)
    # 提取 <name> (path 第 3 段)
    name=$(echo "$path" | cut -d/ -f3)
    # 检查 archive/<date>-<name>/ 存在
    if ! compgen -G "openspec/changes/archive/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-$name" > /dev/null; then
      echo "⚠️  skip $path (no archive/<date>-$name/)" >&2
      continue
    fi
    deleted_to_rm+=("$path")
    ;;
esac
```

### 2.3 手工入口 `--include-change-artifacts`

扩展 `scripts/cleanup-plan-files.sh` 接受新 flag:

```bash
# 新 flag 行为
case "$1" in
  --include-change-artifacts)
    INCLUDE_CHANGES=1
    shift
    ;;
esac

# 在 main logic 中追加:
if [ "${INCLUDE_CHANGES:-0}" = "1" ]; then
  for dir in openspec/changes/*/; do
    name=$(basename "$dir")
    [ "$name" = "archive" ] && continue
    # 防御: 必须存在 archive/<date>-<name>
    if ! compgen -G "openspec/changes/archive/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-$name" > /dev/null; then
      echo "⏭️  skip $name (no archive)"
      continue
    fi
    # 列出 6 类 artifact
    count=$(find "$dir" -maxdepth 2 -type f 2>/dev/null | wc -l)
    echo "  $name: $count files"
  done
  read -r -p "确认清理? [y/N]: " confirm
  if [ "$confirm" = "y" ]; then
    git rm -r openspec/changes/*/  # except archive/
  fi
fi
```

## 3. 影响面与回归风险

### 3.1 正面影响

- ✅ 工作树残留 6 项 `D` 噪音清零
- ✅ `./test.sh --full` 减少 6 项 report_regression 噪音
- ✅ `rdd-doctor --category state` 不再报 stale handoff 警告
- ✅ 真正意义的 idempotent: archive 完成后 working tree 完全 clean

### 3.2 防御性测试

**MUST**: 添加 3 个 e2e 测试防止 archive-presence 检查失效:

| Test | 场景 | 期望 |
|------|------|------|
| `test_post_archive_cleanup_blocks_active_change` | 活跃 change (无 archive/) | 不删, 警告 |
| `test_post_archive_cleanup_handles_archive_in_archive` | archive/ 下残留 | 不删 (跳 self) |
| `test_post_archive_cleanup_e2e_worktree_mode` | 完整 worktree-mode archive flow | 残留清零, 1 commit |

### 3.3 概率极低但 MUST 防御

| 缺陷 | 防御手段 |
|------|---------|
| archive-presence 检查的 compgen glob 失败 | 8 个 unit tests 覆盖 4 种 edge case (空, 1 个, 多个, 错误日期格式) |
| `git rm -f` 对 worktree-NX 标记文件失败 | 现有 `_WHITELIST_DELETED_PATTERNS` 单元测试已覆盖 |
| `cleanup-plan-files.sh --include-change-artifacts` 误删活跃 change | 内部 archive-presence 检查 + 交互式确认 |

## 4. 验证矩阵

执行顺序（保证可重放）:

```bash
# 1. 单元测试 (8 个新 bats)
bats tests/integration/test_post_archive_cleanup.bats

# 2. e2e (3 个)
bats tests/integration/test_post_archive_cleanup_e2e.bats

# 3. 回归 (9 个现有 case 不破)
bats tests/integration/test_archive_cleanup_plan_files.bats

# 4. 全量
./test.sh --full --regression
```

## 5. Out of Scope (再次明确)

**不做**:

- ❌ 不修改 `archive-cleanup-plan-files` 现有 scope (.rddf/plans/ 清理)
- ❌ 不清理 `openspec/changes/archive/` 自身
- ❌ 不动 `.rddf/plans/<name>.md` 的逻辑 (前序改进负责)
- ❌ 不修改 `tests/KNOWN_FAILURES.txt` (保持 baseline 隔离)
- ❌ 不引入新的 spec 名称 (沿用 `post-archive-cleanup-hook`, 不创建 `archive-cleanup-artifacts`)
