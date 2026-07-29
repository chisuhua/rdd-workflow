# Fix scan-state integer comparison — wc -l newline pollution 技术设计

## 设计目标

修复 `scan-state.sh` 及 `skills/` 下所有脚本中 `$() | wc -l` 赋值可能因换行符污染导致 `integer expression expected` 错误的问题。统一使用 `| tr -d '[:space:]'` 对 `wc -l` 输出做防御性清理。

## 根因分析

`wc -l` 输出格式为 `"<count>\n"`。在 bash 的 `$(...)` 命令替换中，**尾部换行符**会被剥离，所以正常情况下 `FS_ACTIVE_COUNT=$(cmd | wc -l)` 的值是纯数字。

但在某些场景下（管道组合、`|| echo 0` fallback 交互、shell 版本差异），`wc -l` 输出可能包含**非尾部的空白字符**或**多行输出**，导致：
- `[ "$FS_ACTIVE_COUNT" -eq 0 ]` 报错 `integer expression expected`
- `[ "$DETACHED" -gt 0 ]` 类似

**具体触发场景**：当 `ls -d openspec/changes/*/` 匹配到路径但 `grep -v archive/` 过滤掉所有行时，`wc -l` 输出 `0`，但后续 `|| echo 0` 在某些 shell 中也会执行（因 `ls -d` 返回非零），导致双输出 `0\n0`。

## 修复策略

### 统一模式

对所有 `$() | wc -l` 赋值追加 `| tr -d '[:space:]'` 管道：

```bash
# 修复前
FS_ACTIVE_COUNT=$(cmd | wc -l)

# 修复后
FS_ACTIVE_COUNT=$(cmd | wc -l | tr -d '[:space:]')
```

`tr -d '[:space:]'` 移除所有空白字符（换行符、空格、制表符），确保输出仅为纯数字字符串。

### 特殊处理

对于已有 `|| echo 0` fallback 的模式，`| tr -d '[:space:]'` 确保 fallback 的输出也经过清理：

```bash
# 修复前
FS_ACTIVE_COUNT=$(cmd | wc -l || echo 0)

# 修复后
FS_ACTIVE_COUNT=$(cmd | wc -l | tr -d '[:space:]' || echo 0)
```

注意：`tr -d '[:space:]'` 对 `echo 0` 的输出（`0\n`）同样安全，因为 `$(...)` 会剥离尾部换行，`tr -d '[:space:]'` 确保任何残留空白都被移除。

## 受影响文件清单

### 直接修复（脚本文件）

| 文件 | 行号 | 变量 | 当前写法 | 修复方式 |
|------|------|------|---------|---------|
| `skills/guide/scripts/scan-state.sh` | 95 | `FS_ACTIVE_COUNT` | `... \| wc -l \|\| echo 0` | 追加 `\| tr -d '[:space:]'` |
| `skills/guide/scripts/scan-state.sh` | 127 | `DETACHED` | `... \| wc -l` | 追加 `\| tr -d '[:space:]'` |
| `skills/guide-arch/scripts/arch_env_check.sh` | 91 | `ADR_COUNT` | `... \| wc -l` | 追加 `\| tr -d '[:space:]'` |
| `skills/guide-arch/scripts/arch_env_check.sh` | 93 | `GAP_COUNT` | `... \| wc -l` | 追加 `\| tr -d '[:space:]'` |
| `skills/guide-arch/scripts/arch_env_check.sh` | 94 | `ACTIVE_CHANGES` | `... \| wc -l` | 追加 `\| tr -d '[:space:]'` |
| `skills/guide-arch/scripts/arch_gap_analysis.sh` | 73 | `GAP_COUNT` | `$("$GAP_DOCS" \| wc -l)` | 追加 `\| tr -d '[:space:]'` |
| `skills/guide-plan/scripts/plan_done_gate.sh` | 91 | `CHANGE_COUNT` | `... \| wc -l` | 追加 `\| tr -d '[:space:]'` |
| `skills/guide-plan/scripts/plan_intake.sh` | 22 | `archived_count` | `... \| wc -l` | 追加 `\| tr -d '[:space:]'` |
| `skills/guide-ship/scripts/ship_done.sh` | 23 | `REMAINING` | `... \| wc -l` | 追加 `\| tr -d '[:space:]'` |
| `skills/guide-ship/scripts/ship_done.sh` | 25 | `REMAINING_WT` | `... \| wc -l` | 追加 `\| tr -d '[:space:]'` |
| `skills/guide-ship/scripts/ship_plan.sh` | 181 | `existing_wt` | `... \| wc -l \|\| echo 0` | 追加 `\| tr -d '[:space:]'` |
| `skills/guide-ship/scripts/ship_plan.sh` | 184 | `total_changes` | `... \| wc -l \|\| echo 0` | 追加 `\| tr -d '[:space:]'` |

### 需修复的 SKILL.md 内联代码

| 文件 | 行号 | 变量 | 修复方式 |
|------|------|------|---------|
| `skills/guide-arch/SKILL.md` | 173 | `ADR_COUNT` | `... \| wc -l` → `... \| wc -l \| tr -d '[:space:]'` |
| `skills/guide-ship/SKILL.md` | 209 | `WORKTREE_COUNT` | `... \| wc -l \|\| echo 0` → 追加 `\| tr -d '[:space:]'` |
| `skills/roadmap/SKILL.md` | 211 | `ADR_COUNT` | `... \| wc -l` → `... \| wc -l \| tr -d '[:space:]'` |

### 无需修复（安全模式）

| 文件 | 行号 | 原因 |
|------|------|------|
| `skills/guide-ship/SKILL.md` | 378, 388 | 使用 `wc -l < file` 输入重定向（无 `$(...)` 包装，直接 `$()` 赋值但输出不含换行符问题） |
| `skills/guide-arch/SKILL.md` | 378 | 仅用于 `echo` 显示，不参与算术比较 |
| `skills/guide-arch/scripts/arch_done_gate.sh` | 43 | **已修复**：已有 `\| tr -d ' '` |
| `skills/guide-arch/scripts/arch_proposal_review.sh` | 270 | 使用 `wc -l < file` 输入重定向 |
| `skills/INSTALL.md` | 196 | 仅用于 `echo` 显示，不参与算术比较 |

## 回归风险

### 风险 1：`tr -d '[:space:]'` 在管道中不可用

`tr` 是 POSIX 标准工具，在所有 Unix 系统上可用。风险极低。

**缓解**：如果 `tr` 不可用，bash 原生 `${var//[[:space:]]/}` 可作为备选。但使用 `tr` 更简洁且不影响 `set -euo pipefail`。

### 风险 2：`set -euo pipefail` 兼容性

所有目标脚本已使用 `set -euo pipefail` 或 `set -eo pipefail`。`tr -d` 在输入为空时返回 0，不会触发 `set -e`。

### 风险 3：误修 `wc -l < file` 安全模式

已确认 `wc -l < file` 模式是安全的（shell 直接读取文件，不会产生多行输出），不在修复范围内。

## 验收标准

1. `scan_state` 执行时无 `integer expression expected` 错误
2. 所有 `$() | wc -l` 赋值的变量均为纯数字字符串
3. 现有 bats 测试全部通过
4. 新增 bats 测试验证 `FS_ACTIVE_COUNT` 在边缘情况下的行为