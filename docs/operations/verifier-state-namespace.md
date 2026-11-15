# Verifier 状态命名空间（`.rddf/state/verifier/`）—— 运维手册

| 字段 | 值 |
|---|---|
| 日期 | 2026-11-15 |
| 适用 | `rdd-verifier` skill 的 6 个状态文件（verdict cache / loop state / audit log / staged context） |
| 决策来源 | `docs/adr/ADR-0034-rdd-verifier-verify-phase-architecture.md` §11（收拢修订） |
| 变更来源 | `openspec/changes/archive/2026-11-14-consolidate-verifier-state/`、`…/2026-11-15-verifier-owns-block-guard/` |

---

## 0. 一句话

`.rddf/state/verifier/` 是 **verifier 状态的唯一命名空间**；所有 verifier 状态文件都在这里，
**别再往 `.rddf/state/` 根下加**。

---

## 1. 症状（什么时候需要看这份）

| 症状 | 含义 |
|---|---|
| 归档门（`archive_gate_check`）报「no valid verdict cache」，但你**确实**跑过 `rddf rdd-verify` | cache 写到了**别处**（多半是旧路径），见 §5 |
| 委派出去的 **verifier 后端**写状态文件被 `Permission denied` | 它的 `scope` 少了 `.rddf/state/verifier`（**这是派发侧的问题，不是故障**） |
| 想给 verifier 加一条新的状态文件 | 见 §3（**清单要同步改两处**，否则 CI 会红） |
| `rddf rdd-verify` 启动时打印了 `📦 moved legacy verifier state → …` | 一次性搬迁在起作用（见 §4），**正常** |

---

## 2. 命名空间与 6 条路径

| # | 路径 | 谁写 | 是什么 |
|---|---|---|---|
| 1 | `.rddf/state/verifier/<name>.json` | skill | per-change loop state（重试计数 / 分类历史 / halt 原因） |
| 2 | `.rddf/state/verifier/<name>.audit.jsonl` | skill | per-change 审计（running/failed/halted/bypassed/archive-ready） |
| 3 | `.rddf/state/verifier/.ac-verdict-*.json` | skill（Step 5）/ `archive_gate_check` fallback | SHA 绑定的 verdict cache（**归档门的输入**） |
| 4 | `.rddf/state/verifier/.ac-verification.jsonl` | skill（Step 5） | 共享验证审计（append-only） |
| 5 | `.rddf/state/verifier/.ac-verifier-blocked.jsonl` | skill（halted 分支） | halted 验证审计 |
| 6 | `.rddf/state/verifier/rdd-verify-context-<name>.json` | `run_verification.sh` / `stage_verification_context` | 暂存的验证上下文（proposal 路径 / AC 列表 / cache 与 audit 路径） |

> ⚠ 2026-11-14 之前，第 3–6 项躺在 `.rddf/state/` **根下**（`.ac-verdict-*.json` 等）——
> 那就是「verifier 后端写不进去」的根因（写集上限是**目录**级）。现在已收拢。

---

## 3. 要加一条 verifier 状态路径 ⇒ 改两处 + 跑一条测试

**清单的单一真源**是 `_lib/verifier/state_paths.py::SKILL_OWNS_PATHS`；
`skills/rdd-verifier/SKILL.md` 的 `owns:` 块由它**渲染**（逐字副本），
`tests/unit/test_verifier_owns_block.py` 断言二者**逐字一致**。

### 步骤

```bash
cd <rdd-workflow 仓>

# ① 改清单（唯一真源）
#    编辑 _lib/verifier/state_paths.py 的 SKILL_OWNS_PATHS（顺序 = SKILL.md 里的顺序）

# ② 重新渲染 SKILL.md 的 owns: 块（逐字替换那一段）
python3 - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, ".")
from _lib.verifier.state_paths import render_owns_block

p = Path("skills/rdd-verifier/SKILL.md")
s = p.read_text(encoding="utf-8")
start = s.index("    owns:")
end = s.index("    not_owns:", start)
block = "\n".join(["    owns:", render_owns_block()])
p.write_text(s[:start] + block + "\n" + s[end:], encoding="utf-8")
print("SKILL.md 的 owns: 块已重渲染")
PY

# ③ 跑守卫（清单 ↔ SKILL.md ↔ 代码产出路径 三方一致）
python3 -m pytest tests/unit/test_verifier_owns_block.py -q

# ④ 若代码侧也新增了写这个文件的逻辑 ⇒ 在同一批里补一条断言：
#    代码实际产出的路径必须落在 owns 模式内（见该测试文件的 test_every_produced_path_matches_an_owns_pattern）
```

### 跨仓提示

消费侧（`~/.config/opencode`，opencode 配置仓）有一份**同形**的清单
（`lib/delegate-core.ts::VERIFIER_OWNS_PATHS`），它决定**被派发的 verifier 后端**能写哪儿。
**改了一侧就要同步另一侧** —— 两侧清单应**逐字一致**（含占位符写法 `<name>`）。
跨仓核对命令见 opencode 仓的 **`docs/guard-authoring.md` §6.1**（耐久位置；会话级副本在
该仓 `.rddf/reviews/session-handoff-20261114.md` §7）。

---

## 4. 收拢后的一次性搬迁（自动）

`rddf rdd-verify` 启动时会调用 `_lib/verifier/cache.py::migrate_legacy_state()`，
把**根下**的遗留文件搬进命名空间：

| 动作 | 含义 |
|---|---|
| `📦 moved legacy verifier state → .rddf/state/verifier/<file>` | 已搬迁 |
| `📦 kept legacy verifier state (destination exists): <file>` | 目标已存在 ⇒ **不覆盖**（保守） |
| `⚠️ failed to migrate legacy verifier state: <file>` | 单个文件失败 ⇒ **只告警**，不阻断验证 |

- **只搬不读**：读路径**只认新路径**（旧路径的 cache 不会被读到 ⇒ 会被当作「无 cache」⇒ 需重跑一次验证）。
  这是有意的：**不做双路 fallback** —— 否则 bash 归档门与 python reader 可能对「cache 是否存在」给出不同答案。
- 搬迁是 **best-effort 的 housekeeping**：失败绝不影响验证结论。

手动搬迁（不跑 `rddf rdd-verify` 时）：

```bash
for f in .rddf/state/.ac-verdict-*.json .rddf/state/.ac-verification.jsonl \
         .rddf/state/.ac-verifier-blocked.jsonl .rddf/state/rdd-verify-context-*.json; do
  [ -e "$f" ] && mv "$f" .rddf/state/verifier/
done
```

---

## 5. 旧路径的兼容规则

| 场景 | 规则 |
|---|---|
| **新写入** | 一律写 `.rddf/state/verifier/` —— 旧路径**不再产生** |
| **读** | 只读新路径。旧路径的 cache **不会被读到** ⇒ 表现为「无 cache」⇒ 需重跑一次验证（**不会误判为通过**，是 fail-closed） |
| **存量未迁移的残留文件** | 只读不受影响（本仓不再写它们）；可按 §4 手动搬走 |
| **worktree 场景** | cache 在**主仓**的 `.rddf/state/verifier/` 下（归档门解析的是主仓根）—— 与 worktree 里的**不是同一个目录**，别以为文件丢了 |

---

## 6. 常见症状与处置

| 症状 | 原因 | 处置 |
|---|---|---|
| 归档门说「no valid verdict cache」，但 `ls .rddf/state/verifier/` 有文件 | **worktree** 场景：归档门看**主仓**，你在 worktree 里找 | 去主仓的 `.rddf/state/verifier/` 找；或把验证跑在主仓 |
| 归档门说「no valid verdict cache」，且两处都没有 | cache 在**旧路径**（收拢前） | 跑一次 `rddf rdd-verify`（会自动搬迁）；或按 §4 手动搬 |
| 后端写状态文件被 `Permission denied` | 派发的 `scope` 没含 `.rddf/state/verifier` | **派发侧**问题（消费侧 opencode 仓的 `role_class` 契约）—— 补 scope 后重派；不要改 skill 代码绕过 |
| `rdd-doctor` 看不到 halted 记录 | 记录还在旧路径 | 同上（搬迁） |

---

## 7. 相关文件

| 文件 | 作用 |
|---|---|
| `_lib/verifier/state_paths.py` | **owns 清单真源** + 规范块渲染器 + 模式匹配器 |
| `_lib/verifier/cache.py` | verdict cache 路径定义（`verdict_cache_path`）+ 遗留搬迁（`migrate_legacy_state`） |
| `_lib/verifier/protocol.py` | staged context 的写入（`verify_context_path`） |
| `_lib/verifier/loop_state.py` / `audit.py` | loop state / per-change audit 的路径 |
| `skills/rdd-verifier/SKILL.md` | skill 的 `owns:` 声明（**逐字投影**） |
| `tests/unit/test_verifier_owns_block.py` | 清单 ↔ SKILL.md ↔ 代码产出路径的三方一致性守卫 |
| `docs/adr/ADR-0034-…md` §11 | 决策与理由（storage ownership 的收拢修订） |
