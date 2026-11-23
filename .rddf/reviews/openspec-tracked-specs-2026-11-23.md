# openspec 契约面入库 + validate 门 —— 台账（2026-11-23）

## 背景

对齐审查发现三项**已批准但未执行**的 P0 债务（互为前提）：

1. 6 份 **4 行空壳 spec**（归档 delta 生成失败的残留）⇒ `openspec validate --all` **ERROR = 6**
2. `.gitignore` 仍是 `openspec/` 整树排除 ⇒ 159 份 spec **无 git 保护**、内容级守卫在 CI 上 skip
3. CI **没有** `openspec validate` 门

## 处置

### P0-1 删 6 份空壳（用户已批准「6 份全删」）

| spec | 行数 | 归档 delta | 归档 AC |
|---|---|---|---|
| `add-guide-polling-loop-implementation` | 4 | ❌ 无 | 20（原文仍在归档 proposal 的 `## Acceptance`） |
| `add-stage-guide-e2e-cross-process-coverage` | 4 | ❌ 无 | 9（同上） |
| `complete-guide-orchestrator-flow` | 4 | ❌ 无 | 0 |
| `wave3-opencode-session-injection` | 4 | ❌ 无 | 0 |
| `wave3-phase-heartbeat-progressing` | 4 | ❌ 无 | 0 |
| `wave3-rddf-session-show-events` | 4 | ❌ 无 | 0 |

- 删除前备份到 `/tmp/opencode/deleted-empty-specs/`（`openspec/` gitignored ⇒ 无 git 回滚凭据）
- **判据**：4 行 = 一句 `Auto-derived from …` 占位 + `## ADDED Requirements` 头；无归档 delta ⇒ 内容从未写入过；主题被 `e2e-test-infrastructure` / `orchestrator-output` 等覆盖
- **结果**：`openspec validate --all` ERROR **6 → 0**；issue **204 → 198**；spec 份数 **165 → 159**
- **配套**：`tests/unit/test_v4_residue_check.py` 的 `files_scanned` 冻结常量 **165 → 159**（hits/blocks/files 不变 —— 空壳不含 stage token）

### P0-2 方案 B：只跟踪契约面

`.gitignore`：
```diff
-# rdd-workflow: git.openspec_tracked=false — keep openspec/ out of git
-openspec/
+# rdd-workflow: git.openspec_tracked=false — keep the *archive* out of git.
+# ADR-0036 (2026-11-17 修订) 把该开关限定为「归档路径」维度 ⇒ 只排除 openspec/changes/，
+# openspec/specs/ + config.yaml 是可跟踪的契约面（CI 上 openspec validate 需要它们）。
+openspec/changes/
+# 归档生成的 schema 副本：CLI 有内建 defaultSchema，无需入库（避免与上游 schema 漂移）。
+openspec/schemas/
```

入库：`openspec/config.yaml` + `openspec/specs/**` = **160 文件 / 14804 行 / 1.1M**

**为什么不改 `project.yaml`**：`git.openspec_tracked: false` 的语义是「**归档路径**不跟踪」（ADR-0036 修订 2026-11-17）。方案 B 下 `openspec/changes/` 仍不跟踪 ⇒ 归档仍不 commit（`_lib/archive.sh:1003-1004` / `:1297-1298`）⇒ **`false` 依然正确**。

### P0-2 配套：工具链判定从「整树」放宽到「两种形态」

原实现硬编码了「`openspec/` 整树不跟踪」假设，方案 B 下会误报 WARNING。改两处：

**`_lib/env_checks.sh::_check_gitignore`**

| | 改前 | 改后 |
|---|---|---|
| 判定 | 只认 `openspec/` | 认 `openspec/` **或** `openspec/changes/`（允许尾斜杠） |
| 缺失提示 | 「openspec/ not in .gitignore」 | 「neither 'openspec/' nor 'openspec/changes/'」 |
| 混合状态探测 | `git ls-files openspec/` | `git ls-files openspec/changes/`（方案 B 下 specs 本就该被跟踪 ⇒ 原口径必误报） |
| auto-fix 追加 | `openspec/`（整树） | `openspec/changes/`（精确表达「只管归档路径」） |
| auto-fix guard | `! grep -qxF 'openspec/'` | 进入分支的前提已是「两种形态都缺」⇒ 不再需要 |
| 反向不一致 | 只查 `openspec/` | 两种形态任一存在即报（`tracked=true` 却排除归档路径同样矛盾） |

**`skills/rdd-doctor/scripts/checks/gitignore_check.py`** —— 同款改动（`_gitignore_has_entry` → `_gitignore_entries` 返回 `(has_whole, has_changes)`；`_openspec_files_tracked` → `_archive_files_tracked` 只查 `openspec/changes/`）。

### P0-3 CI 严格 validate 门

`.github/workflows/test.yml` 新增（放在既有 `Spec validation gate` 之后）：

```yaml
- name: Spec contract validation gate (openspec validate --all)
  run: |
    OUT="$(openspec validate --all 2>&1)" || true
    ERRORS="$(printf '%s\n' "$OUT" | grep -c '\[ERROR\]')" || true
    printf '%s\n' "$OUT" | tail -1
    echo "ERROR count: ${ERRORS:-0}"
    if [ "${ERRORS:-0}" -ne 0 ]; then
      echo "❌ openspec validate --all reported ${ERRORS} ERROR(s):"
      printf '%s\n' "$OUT" | grep '\[ERROR\]'
      exit 1
    fi
    echo "✅ openspec validate --all: 0 ERROR"
```

- **严格口径**：ERROR 必须 0；WARNING 放行（136 份 `## Purpose` 占位属已知 tail）
- **与既有门的分工**：既有 `Spec validation gate (baseline + delta targets)` 循环 `openspec/changes/*/` —— CI 上 `changes/` 被 ignore ⇒ **空跑**；新门读 `openspec/specs/`（已入库）⇒ 真的能跑

## 审查链

| 轮 | 结论 | 处置 |
|---|---|---|
| 1 | **APPROVE_WITH_CONDITIONS**（0 BLOCKER + 2 SHOULD_FIX + 2 NIT）；`mergeable: yes` / `scope_exceeded: false` | 2 SF + 2 NIT **全部采纳并实施** |

### 第 1 轮处置

| # | finding | 处置 |
|---|---|---|
| **SF-1** | **方案 B 的真实失效模式未被覆盖**：`tracked=false` + 只挡 `openspec/changes/`，但 `openspec/specs/` 在盘上却 untracked（用户照抄新 gitignore 却忘 `git add`）⇒ 两工具均静默 `PROTECTED=yes`，随后 CI 门因 fresh checkout 无 `openspec/specs/` 而 skip ⇒ **方案 B 的「CI 牙齿」静默归零** | **两侧都补非阻塞提示**：`_check_gitignore` 在「只挡归档 + specs 存在未跟踪」时打一行 hint（`PROTECTED` 结论不变）；doctor 的 gitignore category 报 **INFO**（`0 WARNING · 1 INFO` ⇒ exit 1 但非 CRITICAL）。本仓 specs 已跟踪 ⇒ 不触发 |
| **SF-2** | 文档同步遗漏 3 处 | `skills/rdd-env-check/SKILL.md` 表格改为「两种合法形态」+ auto-fix 行改 `openspec/changes/`；`skills/rdd-doctor/SKILL.md` 的 category 行补两形态 + INFO；`docs/adr/ADR-0061:157` 末句「本仓 `openspec/` 被 gitignore」→「`openspec/changes/` 被 gitignore（`openspec/specs/` 自 2026-11-23 起已入库）」（**描述性措辞更正，无决策变更**） |
| **NIT-1** | `test.sh` 的 CLI 缺失 skip 无安装指引 | 补 `npm install -g @fission-ai/openspec   # CI 固定 1.14.3` |
| **NIT-2** | 6 份空壳的回滚凭据在 `/tmp`（易失） | 台账注明「若 /tmp 被清**无需恢复**：只有 4 行模板句，可由归档 proposal 重建，不承载独立契约」 |

### 第 1 轮 focus 结论（critic 原文要点）

- **A（`openspec_tracked: false` 语义）**：**成立**。全部读者只消费 project.yaml 值，且都落在「归档路径」或「波次」维度；**没有任何代码用泛型 `git ls-files openspec/` 推断 tracked 模式**（仅剩两处已改为 `openspec/changes/` 的查询）。`project.yaml` 不改是正确决策。
- **B（放宽判定的严密性）**：正则无误（`grep -x` 全行锚定 ⇒ `openspec/changes/?` 不匹配 `openspec/changes-archive/`）；bash 与 Python 两处实现**逐条等价**；唯一漏洞 = SF-1。
- **C（auto-fix 行为变更）**：**正确取舍** —— ADR-0036 修订后开关语义就是「归档路径」，回退为追加 `openspec/` 会把 P0 债务复制到每个未来项目；「`git add -A` 把 specs 推上去」是方案 B 的**意图本身**，非副作用。
- **D（删 6 份空壳）**：**安全**。4 行占位（无 Scenario、无 delta）+ validate 基线稳定 ⇒ 足以支撑「从未写入」；29 条 AC 原文在归档 proposal 完好；同主题契约由 `cross-container-event-bus`（polling）/ `e2e-test-infrastructure` / `orchestrator-output` 承载 ⇒ **现行契约未丢**（删的是历史记录不是契约）。
- **E（CI 门 vs 本地门）**：**可接受**。本地 skip 的两条前置正是「贡献者环境不完整」场景；严格口径对新增缺 `## Purpose` 的 spec 会 ERROR 假红 —— 这是用户显式批准的口径（探针已验证）。

## 验证

| 项 | 改前 | 改后 |
|---|---|---|
| `openspec validate --all` ERROR | 6 | **0** |
| `openspec validate --all` issue 总数 | 204 | **198** |
| spec 份数 | 165 | **159** |
| `_check_gitignore`（本仓） | PROTECTED=no（改 .gitignore 前） | **PROTECTED=yes** |
| doctor `--category gitignore`（本仓） | — | **All 1 categories OK** |
| `test_gitignore_protection.bats` | 9 例 | **20 例全绿**（新增 11：部分排除形态 ×3、auto-fix 不误伤 ×1、缺两种形态提示 ×1、SF-1 的 specs 未跟踪 hint ×3、doctor 部分排除 ×2、doctor INFO ×1） |
| CI 门负向验证 | — | 注入缺 `## Purpose` 的探针 spec ⇒ **ERROR count 1** ⇒ 门 exit 1 ✓；删探针后 0 |
| `pytest tests/unit/` | — | **3537 passed, 3 skipped** |
| `ruff check skills/_lib/` | 绿 | **绿** |
| 相关 bats（gitignore + archive_gate_tracked_false + rdd_doctor） | — | **36 例全绿** |
| `./test.sh --full --regression` | — | **GATE_RC=0**（`✅ ALL PASSED`；未评估 **0** · 已知失败 **10** = 基线 · **新增失败 0**） |

## 回滚凭据

- 6 份空壳原文：`/tmp/opencode/deleted-empty-specs/`（⚠️ 易失路径）。若已被清理，**无需恢复**：
  内容只有 `## ADDED Requirements` 头 + 一句 `Auto-derived from .rddf/improvements/<name>.md per ADR-0025 D1/D2 + rdd-builder Phase 0 approve.` 模板句，
  4 行可由归档 proposal 重建，且它们不承载任何独立契约（见「处置」表的归档 delta / AC 列）。
- spec 改前全树：`/tmp/opencode/specs-baseline-b5/`（165 份，含已删的 6 份）
- `.gitignore` / `env_checks.sh` / `gitignore_check.py` / `test.sh` / CI / 测试 / ADR-0061 末句 / 两份 SKILL.md：`git diff`（均 tracked）

## 范围外（本 change 不处置）

1. **`openspec/schemas/` 是否入库** —— 现选「不入库」（CLI 有内建 defaultSchema；避免与上游漂移）。若日后需要 schema 演化可审计，单独改。
2. **136 份 `## Purpose` 占位** —— 已知 tail，不在本 change。
3. **架构文档 / 治理面文档漂移**（`skills-and-handoff.md` handoff 族、`MULTI-AGENT-DESIGN.md` 计数、`build.md` 表内漏项）—— 属对齐审查的 P1，另立项。
