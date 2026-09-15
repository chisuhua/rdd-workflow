---
name: rdd-verifier
description: |
  Stage 4 of v4 architecture (rdd-arch → rdd-planner → rdd-builder → rdd-verifier).
  AC verification + bounded retry loop (max 3 per ADR-0034).

  Invoke when canonical preconditions hold:
    1. rdd-builder P3 archive_gate_check triggered
    2. OpenSpec change has `## Acceptance` checkboxes to verify

  Default: self-contained LLM verification per ADR-0045 (executing AI agent IS the LLM).

  Boundary ownership: see role.boundaries.owns / not_owns.
license: MIT
compatibility: requires openspec CLI v1.3.1+, Python 3.11+, git 2.25+. No external LLM provider env vars needed — the executing AI agent IS the LLM.
metadata:
  author: rdd-workflow
  version: "2.0"
  evolved-from: "rdd-verifier skill v1.0 (2026-08-26); self-contained LLM verification per deprecate-ac-verifier"
  user-invocable: true
  deprecated-relation:
    deprecates: "skills/ac-verifier/SKILL.md"
    replacement: "This skill — ac-verifier is a deprecated thin wrapper"
role:
  title: "Verifier (验证治理者)"
  perspective: "5th phase state machine — guards archive by enforcing AC pass, classifies failures heuristically, routes loops back to plan/ship. High human involvement (AI classification + user confirm + failure routing decisions)."
  boundaries:
    owns:
      - ".rddf/state/verifier/<change>.json"
      - ".rddf/state/verifier/<change>.audit.jsonl"
      - ".rddf/state/.ac-verdict-*.json"
      - ".rddf/state/.ac-verification.jsonl"
    not_owns:
      - "openspec/changes/<name>/"
      - "docs/adr/ADR-*.md"
      - "skills/ac-verifier/"  # deprecated, do not invoke
    human_involvement: "high"
---

# OpenSpec 工作流 — rdd-verifier (5th Phase, v2.0 自包含验证)

本技能是 OpenSpec 工作流的**第 5 阶段**（验证回环），位于 `rdd-builder` 完成、`archive` 之前。

## v2.0 重大变更（自包含 LLM 验证）

**v1.0**：`rdd-verifier` 通过 bash 调用外部 `ac-verifier` 子技能 → 外部 Python 进程 → 外部 LLM provider SDK。需要 `AC_LLM_PROVIDER`/`AC_LLM_BASE_URL`/`AC_LLM_API_KEY` 等环境变量。

**v2.0（当前）**：`rdd-verifier` **不再调用 `ac-verifier`**。LLM 验证逻辑全部内联在本 SKILL.md 的指令块（"LLM Verification Protocol" 一节）。执行本 skill 的 AI agent **自身就是 LLM** — 它的推理就是验证过程。不需要任何外部 LLM provider 配置。

**核心变化总结**：

| 维度 | v1.0（已废弃） | v2.0（当前） |
|---|---|---|
| LLM 调用方 | 外部 Python 进程 `ac_verifier.py` | 执行本 skill 的 AI agent 自身 |
| LLM 客户端 | `llm_providers/{openai,anthropic,ollama,minimax}.py` | agent 内置（OpenCode/Anthropic/OpenAI 等任何） |
| Prompt 来源 | hardcode 在 `_SYSTEM_PROMPT_TEMPLATE` | 内联在本文档 "LLM Verification Protocol" 一节 |
| Env vars | `AC_LLM_PROVIDER`、`AC_LLM_BASE_URL`、`AC_LLM_API_KEY`、`AC_LLM_MOCK`... | 无（agent 自己有 LLM） |
| Mock 模式 | `AC_LLM_MOCK=yes` 走 mock LLM | 无（agent 推理无法 mock，由人类承担 mock 责任） |
| 失败诊断 | `Exit 3 = ac-verifier internal error` | `Exit 3 = LLM verification error`（agent 自身错误：上下文爆炸、工具失败等） |

**保留不变**：

- 5 阶段状态机（scan queue → per-change verify → classify → user confirm → route）
- SHA 指纹 verdict 缓存（与 `archive_gate_check` 共享）
- 启发式失败分类（implementation_gap vs proposal_drift）
- 失败回环 + 3 次上限（haled → audit log → 人工）
- 所有状态文件 schema（`.rddf/state/verifier/*.json`、`*.audit.jsonl`、`.ac-verdict-*.json`、`.ac-verification.jsonl`）
- 退出码 0/1/2/4 语义不变

**Deprecated**：`skills/ac-verifier/SKILL.md` 标记 deprecated，所有调用方（包括 `_lib/archive.sh` 和 `rddf ac-verify` CLI）将自动重定向到本 skill 的实现。

**职责边界**：

- **角色定义**：见 frontmatter `role:` 字段（ADR-0028）
- **拥有**：`role.boundaries.owns` 列出的状态文件
- **不拥有**：`openspec/changes/*/`（不修改提案本身）、`docs/adr/ADR-*.md`（不写 ADR）、`skills/ac-verifier/`（已废弃，不要触碰）
- **人工介入程度**：`high`（与 `rdd-arch` 同档）

---

## 调用方式

```bash
# 直接调用（CLI 形式）
rddf rdd-verify [--dry-run] [--max-changes N] [--loop]

# Skill 形式（交互式状态机）
skill_use("rdd-verifier")
```

**注意**：`rddf ac-verify` 已废弃，会自动重定向到 `rddf rdd-verify <change-name>`。直接调用 `skill_use("ac-verifier", "<change>")` 也已废弃。

---

## State Machine (State Diagram)

```
[ENTRY: rdd-builder done]
    ↓
[1] scan_queue.sh → list `in_worktree`/`completed` changes with `tasks_done == tasks_total > 0` from .rddf/state/iteration.json
    ↓ (queue = ["change-a", "change-b", ...])
[2] FOR EACH change (serial, max $RDDF_VERIFIER_MAX_CHANGES):
    ├─ [2a] Check SHA cache (.ac-verdict-<name>.json):
    │   ├─ cache_hit + SHA match → reuse verdict (no LLM call)
    │   ├─ cache_hit + SHA mismatch → "stale", re-run LLM verification
    │   └─ no cache → run LLM verification fresh
    │
    ├─ [2b] If verdict all PASS → mark loop_state.route="archive-ready"
    │
    └─ [2c] If any FAIL → classify_failure:
        ├─ implementation_gap → user_confirm → route="rdd-builder P2"
        │   (re-execute code in worktree → commit → re-enter verify)
        ├─ proposal_drift → user_confirm → route="rdd-builder P1"
        │   (rewrite proposal/specs → plan → ship → verify again)
        └─ ambiguous → default = implementation_gap (conservative)
            │
            └─ append_classification(loop_count += 1)
                ├─ loop_count < $RDDF_VERIFIER_MAX_LOOPS → route to plan/ship
                └─ loop_count >= $RDDF_VERIFIER_MAX_LOOPS → route="halted" + audit log
                    │
                    └─ [EXIT 4] halted: manual review needed
[3] ALL PASS → [EXIT 0] archive can proceed
```

---

## LLM Verification Protocol (v2.0 新增 — 核心)

**这是 v2.0 的核心新增节**：原 v1.0 把这段逻辑放在 `ac-verifier/scripts/ac_verifier.py` 的 `_SYSTEM_PROMPT_TEMPLATE` 里。v2.0 把它全部内联到本 SKILL.md，让 AI agent 直接执行。

### Step 1: 提取 AC（Acceptance Criteria）

从 `openspec/changes/<change-name>/proposal.md` 提取 AC 列表。

**段头匹配**（两种都支持，中英文）：

```regex
^##\s+(?:验收标准|Acceptance Criteria)\s*$
```

**段边界**：从匹配位置到下一个 `## ` 段头（或文件末尾）。

**Bullet 提取**（支持三种格式）：

| Markdown | 说明 |
|---|---|
| `- ...` | 普通 bullet |
| `- [ ] ...` | 未勾选 checkbox |
| `- [x] ...` | 已勾选 checkbox |

每条 bullet 生成一个 AC 对象：

```json
{
  "ac_id": "AC-<N>",         // N 从 1 开始递增
  "description": "<verbatim bullet text>",
  "has_checkbox": true|false // bullet 是否带 checkbox
}
```

**边界情况**：

- proposal.md 不存在 → 返回 `[]`（视为无 AC，pipeline 跳过）
- 没有 `## 验收标准` 段 → 返回 `[]`
- 段内无 bullet → 返回 `[]`

### Step 2: 证据收集（每个 AC 都要）

对每个 AC，**必须**用工具收集至少 1 条证据。优先级工具链：

| 工具 | 用途 | 何时优先用 |
|---|---|---|
| `Read` | 读单个文件全文 | 已知目标文件路径 |
| `Grep` / `regex_search` | 模式匹配 | 已知关键词/正则 |
| `Glob` | 文件 glob | 已知文件名模式 |
| `codegraph_explore` | 结构化代码搜索 | 想找实现/调用者 |
| `Bash` (`git log`/`git diff`/`git show`) | commit/diff 历史 | 验证 commit 是否存在/改了哪些行 |
| `Bash` (`grep`/`find`) | shell 工具 | 简单文本/文件搜索 |

**反模式**：

- ❌ 仅凭 AC 文本描述"推断"实现存在 — 必须查实际代码
- ❌ 跳过证据收集直接判 pass — 视同假阳性，verdict 失效
- ❌ 单条 AC 0 工具调用 — invalid verdict（protocol violation）

### Step 3: 判定 + Verdict JSON 输出

对每个 AC 输出判定 + 证据 + 推理，组成**严格 JSON array**（无任何额外文字）：

```json
[
  {
    "ac_id": "AC-1",
    "description": "<verbatim AC text>",
    "status": "pass" | "fail" | "partial",
    "confidence": 0.0-1.0,
    "evidence": [
      {"tool": "Read|Grep|Glob|codegraph_explore|Bash", "query": "...", "result_summary": "..."}
    ],
    "reasoning": "1-2 sentences explaining verdict; if fail, include drift/gap keywords (see Step 4)"
  }
]
```

**判定规则**：

| Status | 含义 | Confidence 范围 |
|---|---|---|
| `pass` | AC 全部满足 | 0.7-1.0 |
| `fail` | AC 未满足（实现缺失/漂移/不正确） | 0.6-1.0 |
| `partial` | 部分满足，需 caveat | 0.4-0.9 |

**硬约束**：

- array 长度必须等于 AC 数量
- 任何 AC 缺失 → verdict invalid，自动 fallback 为 fail
- `confidence < 0.5` 的 fail 视为低置信度失败，触发 human review 流程

### Step 4: reasoning 关键词约定（失败路由）

为了 Step 5 的启发式分类能正常工作，**reasoning 字段必须包含以下关键词之一**（按优先级）：

**Drift keywords（→ `proposal_drift` → 路由 rdd-builder P1）**：

- `exists but` — 代码存在但与 AC 不符
- `discrepan` — AC 与实现有差异
- `mismatch` — AC 与实现不匹配
- `differs from ac` — 不同于 AC 描述

**Gap keywords（→ `implementation_gap` → 路由 rdd-builder P2）**：

- `not implement` — 未实现
- `missing` — 缺失
- `absent` — 不存在
- `todo: implement` — 标记为待实现

**匹配规则**：

1. 大小写不敏感
2. drift 关键词**优先**匹配（因为 proposal_drift 修复成本更高，分类错误成本也更高）
3. 都不匹配 → conservative default = `implementation_gap`（重跑代码比重写 proposal 便宜）

### Step 5: 持久化（verdict cache + audit log）

**写入 verdict cache**（路径 `.rddf/state/.ac-verdict-<change>.json`）：

```json
{
  "schema_version": 2,
  "version": 2,
  "change": "<change-name>",
  "codebase_commit": "<git rev-parse HEAD>",
  "verdict": [/* 上面的 verdict array */],
  "ran_at": "<ISO 8601 UTC>",
  "ran_by": "rdd-verifier",
  "source": "rdd-verifier",
  "verification_state": "passed" | "failed" | "errored",
  "failed_acs": ["AC-1", "AC-3"],
  "implementation_ref": "openspec/<change-name>"
}
```

写入工具：`Read` + `Write`（先 Read 当前内容判断是否覆盖，再 Write 完整 JSON）。

**追加 audit log**（路径 `.rddf/state/.ac-verification.jsonl`，append-only）：

```json
{"ts": "<ISO 8601 UTC>", "change_name": "<change-name>", "exit_code": 0|1|3, "llm_provider": "agent", "llm_model": "agent", "verdict": [...]}
```

写入工具：`Read`（读取现有内容）+ `Write`（重写完整文件，新行追加在末尾）。

**失败容错**：

- 若 `.rddf/state/` 目录不存在 → `Bash: mkdir -p .rddf/state`
- 若 cache 文件已存在且 SHA 匹配 → **不要覆盖**（cache hit 直接复用）
- 若 verdict JSON 无法 parse → 视为 `Exit 3` error，不写 cache

### Step 6: 退出语义

| 自评结果 | 退出码 | 调用方行动 |
|---|---|---|
| 全部 AC pass | `0` | 标记 `route="archive-ready"`，继续下一个 change |
| 任意 AC fail | `1` | 触发 Step 5 失败分类 → user confirm → 路由 plan/ship |
| 0 个 AC | `0`（pass-through）| 视为无 AC 提案，跳过验证 |
| LLM 自身错误（context 爆炸、工具失败）| `3` | 写入 errored cache，调用方调查 |
| 工具调用全部失败（无法收集证据）| `3` | 同上 |

---

## Per-Change Flow Detail (Orchetration Layer)

这部分与 v1.0 几乎相同，只是不再"调 ac-verifier"，而是按上述"LLM Verification Protocol"自己验证。

### Step 1: Scan Queue

```bash
bash skills/rdd-verifier/scripts/scan_queue.sh
# Stdout: space-separated change names
# Honors RDDF_VERIFIER_MAX_CHANGES (default 10)
```

Source: `iteration.json` filter `status in (in_worktree, completed)` and `tasks_done == tasks_total > 0`; archived and incomplete changes are excluded.

### Step 2: Per-Change Verification

For each change in queue:

1. **`Bash: git rev-parse HEAD`** — 获取当前 commit SHA
2. **`Read .rddf/state/.ac-verdict-<name>.json`** — 读 SHA cache
3. **Cache freshness check**：
   - cache SHA == HEAD SHA → 复用 verdict，**跳过 LLM 验证**
   - cache SHA ≠ HEAD SHA → stale，重跑
   - 无 cache → fresh run
4. **Fresh LLM verification**（按 "LLM Verification Protocol"）：
   - `Read openspec/changes/<name>/proposal.md`
   - 提取 AC list（按 Step 1 协议）
   - 对每个 AC 收集证据 + 判定 + 输出 verdict JSON
   - 写入 cache + audit log
5. **走 cache miss/stale 路径**：直接返回 cache 内容，不重新调 LLM

### Step 3: Heuristic Classification (FAIL only)

使用 `_lib/verifier/classify.py::classify_failure(verdict_item)`：

```python
# 见 _lib/verifier/classify.py
def classify_failure(verdict_item: dict) -> str:
    """Return 'implementation_gap' or 'proposal_drift' based on reasoning keywords."""
```

Per Oracle §E + ADR-0034 §5.1：

- **Drift keywords checked first** → `proposal_drift`
- **Gap keywords** → `implementation_gap`
- **Ambiguous** → conservative default = `implementation_gap`

Rationale: `implementation_gap` → `rdd-builder` P2 re-run cost < `proposal_drift` → `rdd-builder` P1 rewrite cost.

### Step 4: User Confirmation + Route

Per ADR-0034 §6 + user experience：

```
[AI classification result]
AC-1: implementation_gap  (code missing)
AC-2: proposal_drift      (code exists but mismatches AC)

[?] Confirm or override? (y/n/edit):
```

User options：

- `y` → accept AI labels, route per labels
- `n` → manual override per AC (re-classify)
- `e` → edit AC description (proposal drift by definition)

### Step 5: Loop State Update

```bash
bash skills/rdd-verifier/scripts/route_loop.sh "$CHANGE_NAME" "$LABEL"
# Updates `.rddf/state/verifier/<change>.json`: append classification + route
# Exit 0: routed (rdd-builder P1/P2)
# Exit 1: halted (max_loops reached, audit log written)
```

---

## Exit Codes (per ADR-0034 §7.1)

| Code | Meaning | Caller Action |
|------|---------|---------------|
| 0 | All changes verified, archive can proceed | Proceed to `archive` |
| 1 | AC fail, route decision printed to stderr | Jump to indicated phase (plan/ship) |
| 2 | Skipped (`SKIP_RDD_VERIFIER=yes`) | Proceed to `archive` (bypass) |
| 3 | LLM verification error (agent context 爆炸 / 工具失败) | Investigate env config |
| **4** | **Halted (max_loops exceeded)** | **Manual review required** |

> **v2.0 变更**：Exit 3 的语义从"ac-verifier internal error"改为"LLM verification error"。原因：v1.0 外部 LLM 调用失败（provider 不可用、API key 错），v2.0 是 agent 自身错误（context 超限、工具调用全部失败）。

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SKIP_RDD_VERIFIER` | `no` | Write audited `bypassed` state; requires `RDDF_VERIFIER_BYPASS_REASON` and does not weaken hard archive gates |
| `RDDF_VERIFIER_MAX_LOOPS` | `3` | Max retry loops per change |
| `RDDF_VERIFIER_MAX_CHANGES` | `10` | Max changes per scan (cost guardrail) |
| `RDDF_VERIFIER_DRY_RUN` | `no` | Scan + suggest, no state mutation |
| `STRICT_AC_GATE` | `no` | Promote AC fail to archive blocker (shared semantic with archive_gate_check) |
| `FORCE_ARCHIVE_BYPASS_VERIFIER` | `no` | Bypass halted state for force-archive |

> **v2.0 变更**：删除所有 `AC_LLM_*` 系列变量（`AC_LLM_PROVIDER`、`AC_LLM_BASE_URL`、`AC_LLM_API_KEY`、`AC_LLM_MODEL`、`AC_LLM_MOCK`、`AC_LLM_TIMEOUT`、`AC_LLM_MAX_RETRIES`、`SKIP_AC_VERIFICATION`、`STRICT_AC_GATE` 中关于 ac-verifier 的部分）。这些是 ac-verifier 外部 Python 进程的约定。v2.0 不需要 — agent 自己是 LLM。

---

## Audit Log

当 `route="halted"`，append 到 `.rddf/state/.ac-verifier-blocked.jsonl`：

```json
{
  "ts": "2026-08-26T...",
  "change": "my-change",
  "loop_count": 3,
  "classifications": ["implementation_gap", "implementation_gap", "proposal_drift"],
  "last_label": "proposal_drift",
  "halt_reason": "max_loops=3 reached with label=proposal_drift",
  "codebase_commit": "abc1234"
}
```

This log is read-only forensic record. `rdd-doctor --category plan-tdd` can check it during diagnostics.

---

## State Files Owned

| File | Schema | Purpose |
|------|--------|---------|
| `.rddf/state/verifier/<change>.json` | `verifier_loop_schema.json` v2 | Per-change loop count, classification history, route, halt reason |
| `.rddf/state/verifier/<change>.audit.jsonl` | `verifier_audit_schema.json` v1 | Append-only running/failed/halted/bypassed/archive-ready events |
| `.rddf/state/.ac-verdict-<name>.json` | cache schema v2 | SHA-fingerprint verdict cache, verification state, failed ACs, implementation ref |
| `.rddf/state/.ac-verification.jsonl` | audit log schema v1 | Append-only LLM verification runs (ts, change_name, exit_code, verdict) |

All verifier state files are `.rddf/state/` gitignored, per AGENTS.md state file convention. The canonical audit log is `.rddf/state/verifier/<change>.audit.jsonl`.

> **v2.0 变更**：`.rddf/state/.ac-verification.jsonl` 写入方从 `ac_verifier.py::append_audit_log` 改为本 skill 的 Step 5 协议。Schema 保持不变（向后兼容）。

---

## Migration from v1.0 (废弃迁移)

如果你之前在用 ac-verifier 或 rdd-verifier v1.0：

| 旧做法 | 新做法 |
|---|---|
| `rddf ac-verify <name>` | `rddf rdd-verify`（批量）或 `rddf rdd-verify <name>`（单 change） |
| `skill_use("ac-verifier", "<name>")` | `skill_use("rdd-verifier", "<name>")` 或主流程 `skill_use("rdd-verifier")` |
| 设置 `AC_LLM_PROVIDER=openai` | 不需要任何 LLM env var |
| 设置 `AC_LLM_API_KEY=...` | 不需要（agent 自己有 key） |
| 设置 `AC_LLM_MOCK=yes` | 不需要（mock 由测试 agent 承担） |
| 调 `bash skills/ac-verifier/scripts/ac_verifier.sh <name>` | 调 `bash skills/rdd-verifier/scripts/route_loop.sh <name> gap` 等高层 helper |
| 读 `Exit 3 = ac-verifier internal error` | 读 `Exit 3 = LLM verification error` |

**向后兼容窗口**：ac-verifier CLI 在 v2.0 仍可用（thin shim），但仅 1-2 个版本周期。**新代码请直接用 rdd-verifier**。

---

## See Also

- Spec: `docs/superpowers/specs/2026-08-26-rdd-verifier-design.md` (v1.0 spec，v2.0 增量更新待写)
- Plan: `docs/superpowers/plans/2026-08-26-rdd-verifier-implementation.md`
- ADR: `docs/adr/ADR-0034-rdd-verifier-verify-phase-architecture.md`
- Oracle 评审: 82/100 分
- `_lib/verifier/`: heuristic classification + SHA cache + loop state modules（保留）
- `skills/rdd-verifier/scripts/`: 4 bash orchestration helpers（保留 + run_verification.sh 改为内联 LLM 协议）
- `_lib/cli/rdd_verify_cmd.py`: `rddf rdd-verify` CLI backend
- **Deprecated**: `skills/ac-verifier/SKILL.md`（v1.0 实现，已废弃）
