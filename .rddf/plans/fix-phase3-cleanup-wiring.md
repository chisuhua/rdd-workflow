# fix-phase3-cleanup-wiring Implementation Plan

**Goal:** `_lib/post_archive_cleanup.sh` 是一个**库**（155 行只有函数定义、无脚本入口）。被 `bash` 直接执行时它什么都不做且 exit 0 —— 这个失败模式在 `phase3_archive.sh:101` 上真实发生过（归档后 `improvement-approved.md` 未同步，doctor 报 `proposal-section` CRITICAL）。修法不是加功能，而是**把静默换成显式**。

**Architecture:** ① 库末尾加最小守卫：被当脚本执行 ⇒ stderr 说明 + `exit 2`；② `source ... 2>/dev/null || true` 的静默吞错改为显式 WARN（不改变退出码，与 `archive.sh:725` 的 `|| true` 语义一致）；③ 用 e2e 钉住「正确的调用方式确实会同步 `improvement-approved.md`」。

**范围外**：`phase3_archive.sh` 侧的调用点已由 `fix-worktree-archive-path` 删除（该 change 归档时实测确认）；cleanup 的 deleted/whitelist 清理清单；键名参数解析。

---

## File Structure

| File | 类型 | Responsibility |
|---|---|---|
| `_lib/post_archive_cleanup.sh` | 改 | 末尾加「直接执行 ⇒ exit 2」守卫；`source` 失败改为 stderr WARN |
| `tests/integration/test_post_archive_cleanup_guard.bats` | 新 | 直接执行 ⇒ exit 2 + 说明；source 缺失 ⇒ WARN；正确调用 ⇒ 同步 `improvement-approved.md`（e2e） |

### Task 1: 库被直接执行时 fail loud

- [ ] **Step 1: 写失败测试**

```bash
@test "cleanup: executing the library directly fails loudly" {
    run bash "$REPO_ROOT/_lib/post_archive_cleanup.sh" "$TMP" demo
    [ "$status" -eq 2 ]
    [[ "$output" == *"library"* || "$output" == *"库"* ]]
}
```

- [ ] **Step 2: 确认变红**：当前 exit 0、零输出。
- [ ] **Step 3: 实现**：文件末尾加

```bash
# Executed directly (not sourced)? Say so instead of silently doing nothing.
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  echo "❌ post_archive_cleanup.sh is a library, not a script." >&2
  echo "   source it, then call: post_archive_cleanup <project_root> <change_name>" >&2
  exit 2
fi
```

- [ ] **Step 4: 确认变绿** + `bash -n`。

### Task 2: `source` 失败改为显式 WARN

- [ ] **Step 1: 写失败测试**：fixture 无 `_lib/state.sh` ⇒ 调用后 stderr 含 WARN，退出码不变（0）。
- [ ] **Step 2: 确认变红**（当前静默）。
- [ ] **Step 3: 实现**：

```bash
  if [ -f "$project_root/_lib/state.sh" ]; then
    # shellcheck source=/dev/null
    if ! source "$project_root/_lib/state.sh"; then
      echo "⚠️  post_archive_cleanup: failed to source _lib/state.sh — skipping proposal sync" >&2
    fi
  else
    echo "⚠️  post_archive_cleanup: _lib/state.sh missing — skipping proposal sync" >&2
  fi
```

- [ ] **Step 4: 确认变绿**。

### Task 3: e2e —— 正确调用确实同步 `improvement-approved.md`

- [ ] fixture：`improvement-approved.md`（`## 已批准提案` 段含一行）+ `openspec/changes/archive/2026-01-01-demo/` 存在 ⇒ `source` 后调 `post_archive_cleanup <root> demo` ⇒ 该行出现在「已实施」段。
- [ ] 断言幂等：重复调用不产生重复行。

### Task 4: 全量回归 + 遗留清扫

```bash
bats tests/integration/test_post_archive_cleanup_guard.bats tests/integration/test_post_archive_cleanup*.bats
./test.sh --bats --regression     # 在主仓跑（已知 11 / 新增 0 是当前基线）
bash skills/rdd-doctor/scripts/doctor.sh
```
