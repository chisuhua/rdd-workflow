# rdd-verifier: 5 阶段架构的验证回环阶段设计

> **日期**: 2026-08-26
> **作者**: sisyphus (brainstorming session)
> **状态**: 待用户审查
> **关联 ADR**: ADR-0003（三阶段→四阶段）, ADR-0025（design 阶段独立化）, ADR-0028（role model）, ADR-0017（rddf-session）
> **新增 ADR**: ADR-0034（rdd-verifier 验证回环阶段 — 待起草）

## 1. 背景与问题

rdd-workflow v2.1+ 采用 4 阶段架构：`arch → design → plan → ship`。`ship` 阶段结尾的 `archive` 流程会通过 `_lib/archive.sh::archive_gate_check` 自动调用 `ac-verifier` 技能（SKILL.md v1.0，2026-08-17）验证 OpenSpec change 的 `## 验收标准`，但默认行为是 **warning-only**（`STRICT_AC_GATE=no`）。

当前痛点：
1. **缺独立阶段**: AC 验证仅是 archive 流程的内嵌步骤，没有用户可见的阶段菜单；用户在 `guide` 推荐器里看不到"验证"作为独立选项。
2. **缺强制模式**: 默认 `STRICT_AC_GATE=no`，需手动设置才能阻断；绝大多数用户不会设置，导致 AC fail 仍被 archive。
3. **缺失败回路**: AC 验证失败后唯一路径是用户手动判断，缺乏自动化的实现/提案偏差分类 + 自动回环到 `plan`/`ship` 重新执行的机制。
4. **缺批量能力**: 一次只能验证一个 change，多个 ship-done 的 change 需要循环手动调用 `rddf ac-verify`。

## 2. 设计目标

新增**第 5 阶段 `rdd-verifier`**，解决以上 4 个痛点：

| 目标 | 实现 |
|------|------|
| 独立阶段 | `skills/rdd-verifier/SKILL.md` 状态机 + `guide` 推荐器菜单新增 |
| 强制模式 | 默认 `STRICT_AC_GATE=yes` 风格（与 archive_gate_check 共享同一开关） |
| 失败回路 | AI 启发式分类（implementation_gap / proposal_drift）+ 用户确认 + 自动跳回对应阶段 |
| 批量能力 | `rddf rdd-verify` 扫描 ship-done 队列，串行验证每个，写 verdict 缓存 |

**非目标 (YAGNI)**:
- 不重写 ac-verifier LLM 调用（复用 SKILL + CLI）
- 不并发跑 LLM（避免 token 峰值 + 输出交错难审计）
- 不修改 openspec CLI 内部
- 不新增跨项目联邦验证

## 3. 5 阶段架构 + ADR-0034

### 3.1 扩展后的阶段图

```
arch (guide-arch) → design (guide-design) → plan (guide-plan) → ship (guide-ship) → verify (rdd-verifier) → archive
                                                                ↑                              │
                                                                └──────── 失败回环 ────────────┘
                                                                              ↓
                                                                          plan 或 ship 重新执行
```

**属性**：
- **非线性必经节点**：verify 是**条件必经**——默认必走，`SKIP_RDD_VERIFIER=yes` 跳过
- **人工介入高**（与 arch/design 同档）：涉及 AI 分类 + 用户确认 + 失败回环决策
- **不破坏 4 阶段职责边界**：verify 属于 ship 之后、archive 之前的**验证回环**，不属于新增的设计/规划阶段

### 3.2 新增 ADR-0034

**文件**: `docs/adr/ADR-0034-rdd-verifier-verify-phase-architecture.md`

**核心声明**：
- verify 阶段是 ship 完成后、archive 前的独立验证步骤
- 默认严格（`STRICT_AC_GATE` 风格）
- 失败触发回环到 `plan` 或 `ship`，最多重试 `RDDF_VERIFIER_MAX_LOOPS` 次（默认 3）
- 角色模型（ADR-0028 扩展）：
  - `role.owns`: `.rddf/state/.verifier-loop.json`, `.rddf/state/.ac-verdict-<name>.json`, `.rddf/state/.ac-verifier-blocked.jsonl`
  - `role.not_owns`: `openspec/changes/<name>/`（不修改提案本身）、`docs/adr/`（不写 ADR）
  - `role.human_involvement`: `high`（AI 分类 + 用户确认 + 失败回环决策）

### 3.3 AGENTS.md 更新

将"四阶段架构（arch → design → plan → ship）"改为"五阶段架构（arch → design → plan → ship → verify）"，与 ADR-0025 扩展 ADR-0003 同样做法（增 1 行 + 阶段表追加一行）。

## 4. 组件设计

### 4.1 三个新组件（Approach C 混合形态）

| 组件 | 路径 | 职责 |
|------|------|------|
| **rdd-verifier SKILL.md** | `skills/rdd-verifier/SKILL.md` | 状态机：菜单 → 扫队列 → 逐个验证 → 启发式分类 → 用户确认 → 路由 |
| **rdd-verify CLI** | `_lib/cli/rdd_verify_cmd.py` | 工程后端：`rddf rdd-verify [--loop] [--dry-run] [--max-changes N]` |
| **bash helpers** | `skills/rdd-verifier/scripts/{scan_queue,run_verification,classify_failure,route_loop}.sh` | 单职责编排（与 `ship_archive.sh` 同模式） |

### 4.2 两个新状态文件（gitignored）

**文件 1**: `.rddf/state/.verifier-loop.json`
```json
{
  "version": 1,
  "change": "<name>",
  "loop_count": 0,
  "max_loops": 3,
  "classification_history": [
    {"loop": 1, "label": "implementation_gap", "user_confirmed": true, "at": "..."}
  ],
  "codebase_commit_at_last_run": "<sha>",
  "route": "guide-ship | guide-plan | archive-ready | halted",
  "halt_reason": null,
  "updated_at": "..."
}
```

**文件 2**: `.rddf/state/.ac-verdict-<name>.json`
```json
{
  "version": 1,
  "change": "<name>",
  "codebase_commit": "<sha>",
  "verdict": [
    {"ac_id": "AC-1", "status": "pass", "confidence": 0.95, "evidence": [...], "reasoning": "..."}
  ],
  "ran_at": "...",
  "ran_by": "rdd-verifier | archive_gate_check"
}
```

### 4.3 复用现有组件

- `skills/ac-verifier/scripts/ac_verifier.sh` — bash wrapper（rdd-verifier 内部调用）
- `_lib/cli/ac_verify_cmd.py` — `rddf ac-verify` CLI（保留为单点入口）
- `_lib/parallel_throttle.sh` / `_lib/rate_limiter.py` — 串行调度（v1 默认串行，不使用 throttle）
- `_lib/sessions.json` 管理（ADR-0017）— 沿用 owner session

## 5. 数据流

```
guide-ship done
    ↓
[rddf session 提示] "进入 rdd-verifier？"
    ↓ (yes, or direct `rddf rdd-verify`)
rdd-verifier 扫描:
    iteration.json status="ship-done" ∧ openspec status="merged" ∧ archived=false
    ↓
对每个 change 串行:
1. 读 .ac-verdict-<name>.json
    ├─ codebase_commit == HEAD → 复用缓存 (skip ac-verifier)
    └─ 否则 → bash skills/ac-verifier/scripts/ac_verifier.sh <name>
2. 写 verdict cache
3. verdict fail? → 启发式分类 (基于 verdict JSON evidence 字段):
    ├─ 证据指向"代码缺失/未实现" → label = implementation_gap
    ├─ 证据指向"代码存在但与 AC 不一致" → label = proposal_drift
    └─ ambiguous → label = implementation_gap (保守 default)
4. [用户确认]: 同意 AI 分类 OR 手动改 label
5. 按 label 路由:
    ├─ implementation_gap → 跳回 guide-ship (worktree 复用)
    ├─ proposal_drift → 跳回 guide-plan (强制 worktree)
    └─ loop_count == max_loops → 阻断 archive, 写 audit log
6. 全 pass → 写 .verifier-loop.json status="verified"
    ↓
archive (复用 archive_change_for_mode 流程)
```

### 5.1 启发式分类规则（不调 LLM）

```python
def classify_failure(verdict_item: dict) -> str:
    """基于 ac-verifier verdict JSON 的 evidence 字段做启发式分类。"""
    evidence = verdict_item.get("evidence", [])
    reasoning = (verdict_item.get("reasoning") or "").lower()

    # Rule 1: 证据中提到"未实现"/"缺失" → implementation_gap
    if any(kw in reasoning for kw in ["not implement", "missing", "absent", "todo"]):
        return "implementation_gap"

    # Rule 2: 证据中提到"代码存在但与 AC 不一致" → proposal_drift
    if any(kw in reasoning for kw in ["exists but", "discrepan", "mismatch", "differs from ac"]):
        return "proposal_drift"

    # Rule 3: evidence 为空 / reasoning 为空 → ambiguous → conservative fallback
    return "implementation_gap"  # 默认 implementation_gap (Oracle §E)
```

可单元测试，纯规则，零 LLM 成本。

## 6. 失败回环路径

### 6.1 路径 1: implementation_gap → 跳回 guide-ship

```bash
# 1. 写 .verifier-loop.json: classification="implementation_gap", route="guide-ship"
# 2. iteration.json: status 回退 "ship-done" → "in-progress"
# 3. worktree 不重建 (复用现有 .rddf/wt/<name>/ 或分支)
# 4. .rddf/state/.plan-handoff.json: 不动 (ship 端会用)
# 5. .rddf/state/sessions.json: append "verifier-loop-back-to-ship" 事件
# 6. 跳到 guide-ship Phase 2 (execute 继续修代码 → tasks.md 更新 → worktree commit → 回到 rdd-verifier)
```

### 6.2 路径 2: proposal_drift → 跳回 guide-plan

```bash
# 1. 写 .verifier-loop.json: classification="proposal_drift", route="guide-plan"
# 2. iteration.json: status 回退 "ship-done" → "planned"
# 3. ⚠️ 强制 worktree 模式 (ADR-0034 §3): 避免污染已准备 archive 的 artifacts
#    ├─ 若 change 当前在 lightweight (branch on main): 提示用户先 git worktree add
#    └─ 若 change 已在 worktree: 复用 .rddf/wt/<name>/
# 4. .rddf/state/.plan-handoff.json: 保留 execution_mode_decisions
# 5. 跳到 guide-plan Phase 0 (intake) → proposal.md / specs 修改 → design-handoff refresh
# 6. 走完整 plan → ship → verify 再次循环
```

### 6.3 路径 3: 阻断（max_loops 触发）

```bash
# 1. .verifier-loop.json: loop_count == max_loops, status="halted", halt_reason=<last label>
# 2. 阻断 archive (写 stderr 提示: "archive halted; manual review needed")
# 3. 写 .rddf/state/.ac-verifier-blocked.jsonl (审计 log)
# 4. 退出码 4
# 5. 提示用户:
#    a) 手动修复提案 + 重跑 rdd-verify
#    b) FORCE_ARCHIVE_BYPASS_VERIFIER=yes 强制 archive
```

### 6.4 关键不变量

- **永不 reset iteration.json 的 features 字段**（features 视图依赖）
- **永不 reset sessions.json 的 owner session**（ADR-0017 跨 session 恢复）
- **worktree 重建条件**：仅当 `git worktree list` 无记录时（已被 cleanup）才重建
- **sibling change 隔离**：一个 change 阻断不影响其他 change 的 verify 流程

## 7. 错误处理 + 与 STRICT_AC_GATE 兼容

### 7.1 退出码统一（扩展 ac-verifier 的 0/1/2/3）

| 退出码 | 含义 |
|--------|------|
| 0 | 全部 pass，archive 可继续 |
| 1 | AC fail（implementation_gap / proposal_drift），触发回环 |
| 2 | `SKIP_RDD_VERIFIER=yes` 跳过 |
| 3 | ac-verifier 内部错误（LLM 失败、API key 缺失等） |
| **4 (new)** | **max_loops 触发，archive halted，需人工** |

### 7.2 与 archive_gate_check 的协作（双门控 + SHA 缓存）

```bash
# _lib/archive.sh::archive_gate_check 修改后的逻辑
archive_gate_check() {
    local change_name="$1"
    local tasks_root="$2"

    # ... 既有 tasks.md 完成度检查 ...

    # AC verification (改造: 先读 verdict 缓存)
    if [ "${SKIP_AC_VERIFICATION:-no}" != "yes" ]; then
        local verdict_cache="$tasks_root/.rddf/state/.ac-verdict-${change_name}.json"
        local current_commit=$(git -C "$tasks_root" rev-parse HEAD 2>/dev/null)

        if [ -f "$verdict_cache" ]; then
            local cached_commit=$(jq -r '.codebase_commit' "$verdict_cache" 2>/dev/null)
            if [ "$cached_commit" = "$current_commit" ]; then
                echo "⚠️  Reusing ac-verifier verdict cache (commit $cached_commit)"
                # 直接消费 verdict，不重跑 LLM
            else
                echo "⚠️  ac-verifier verdict cache stale (cached: $cached_commit, current: $current_commit)"
                # 调用 ac-verifier 重跑
            fi
        else
            # 无 cache，调 ac-verifier (兜底: 用户绕过 rdd-verifier 直接 archive)
        fi

        # ... 既有 verdict 评估逻辑（STRICT_AC_GATE=yes → 阻断; no → warning）...
    fi
}
```

**关键点**：
- 保留 archive_gate_check 内的 ac-verifier 调用作为**独立兜底**（用户绕过 rdd-verifier 直接 archive 时仍守门）
- **SHA 指纹比对避免双跑**：rdd-verifier 跑过的 change，archive_gate_check 自动复用 verdict 不重调 LLM（省 token + 时间）
- rdd-verifier 默认 STRICT_AC_GATE=yes 行为一致；只在 archive 直接调用时由 env var 控制

### 7.3 环境变量

| Env Var | 作用域 | 默认 | 说明 |
|---------|--------|------|------|
| `SKIP_RDD_VERIFIER` | rdd-verifier 阶段 | no | 完全跳过 5 阶段（紧急） |
| `RDDF_VERIFIER_MAX_LOOPS` | rdd-verifier 回环 | 3 | 最大重试次数 |
| `RDDF_VERIFIER_MAX_CHANGES` | 批量入口 | 10 | 单次扫描最多 change 数（成本护栏） |
| `RDDF_VERIFIER_DRY_RUN` | rdd-verifier | no | 只扫描 + 输出建议，不动状态 |
| `STRICT_AC_GATE` | archive_gate_check | no | 复用作 strict 行为（与 rdd-verifier 共享语义） |
| `FORCE_ARCHIVE_BYPASS_VERIFIER` | archive | no | max_loops 后强制 archive |

### 7.4 错误场景处理

| 场景 | 行为 |
|------|------|
| ac-verifier LLM 失败 | 退出码 3，提示设置 `AC_LLM_PROVIDER` / `AC_LLM_MOCK=yes` |
| verdict 文件被损坏 | archive_gate_check 视为 cache miss → 重跑 |
| `.verifier-loop.json` 状态异常 | 拒绝执行，提示运行 `rdd-doctor` |
| 用户拒绝所有分类（连续 3 次） | 等同 max_loops 阻断 |
| worktree 已被 cleanup 但 iteration.json 还标 ship-done | 触发 worktree 重建路径 |

## 8. 测试策略

### 8.1 测试矩阵

| 测试类型 | 文件 | 覆盖点 |
|---------|------|--------|
| Python 单元 | `tests/unit/test_rdd_verifier.py` | `classify_failure()` 启发式逻辑 / `verdict_cache()` SHA 比对 / `.verifier-loop.json` schema / 退出码 4 |
| Python 单元 | `tests/unit/test_classify_failure.py` | evidence 字段触发 implementation_gap vs proposal_drift；ambiguous fallback |
| Python 单元 | `tests/unit/test_ac_verdict_cache.py` | SHA 一致性 / 文件损坏 / cache stale 重跑 |
| bats 集成 | `tests/integration/test_rdd_verifier_e2e.bats` | 端到端：guide-ship→rdd-verifier→archive 全绿；失败跳回 |
| bats 集成 | `tests/integration/test_rdd_verifier_loop.bats` | 3 次循环失败后阻断；audit log 写入 |
| bats 集成 | `tests/integration/test_rdd_verifier_archive_compat.bats` | SHA 指纹复用：rdd-verifier 跑过，archive_gate_check 不重跑 |
| bats 集成 | `tests/integration/test_rdd_verifier_skip.bats` | SKIP_RDD_VERIFIER=yes 完全跳过；强制 archive bypass |
| bats 回归 | `tests/integration/test_ac_verifier_*` | 保护 ac-verifier 既有测试不退化 |
| 全量回归 | `./test.sh --full --regression` | archive 前必跑（AGENTS.md 硬性约束） |

### 8.2 测试基线 (`AC_LLM_MOCK=yes`)

- 所有 verify 测试**强制 mock LLM**（避免真实 API 调用 + token 成本）
- mock verdict 需覆盖：全 pass / 混合 pass+fail / 全 fail / malformed JSON / 缺字段
- fixture 文件: `tests/_lib/verifier_mocks/` (pass/fail/proposal_drift/implementation_gap 4 套)

## 9. 完成度检查表

| 检查项 | 满足？ |
|--------|--------|
| 新增 ADR-0034（verify 是可选非线性必经节点） | ✓ |
| AGENTS.md 4 阶段表 → 5 阶段表 | ✓ |
| `skills/rdd-verifier/SKILL.md` 状态机（菜单 + checkpoint） | ✓ |
| `_lib/cli/rdd_verify_cmd.py` 工程后端 | ✓ |
| 4 个 bash helper（scan/run/classify/route） | ✓ |
| `.rddf/state/.verifier-loop.json` schema + version bump | ✓ |
| `.rddf/state/.ac-verdict-<name>.json` 带 codebase_commit | ✓ |
| 启发式分类（基于 verdict JSON，非新 LLM 调用） | ✓ |
| SHA 比对避免双跑（archive_gate_check 改造） | ✓ |
| 3 阶段退出码（含 4 = halted） | ✓ |
| 6 个 env var（SKIP/MAX_LOOPS/MAX_CHANGES/DRY/STRICT/BYPASS） | ✓ |
| 8 个测试文件（4 unit + 4 integration） | ✓ |
| 4 套 mock fixture | ✓ |
| 全量回归门（archive 前必跑） | ✓ |
| CHANGELOG.md 记录新阶段 | ✓ |

## 10. 风险与权衡

| 风险 | 缓解 |
|------|------|
| 5 阶段扩展破坏现有 `guide` 推荐器菜单 | 推荐器扫描顺序附录即可，阶段表加 1 行 |
| SHA 缓存误判（worktree 与 main repo commit 不一致） | verdict 文件存 `codebase_commit` 时显式记录 worktree 路径 + commit |
| 启发式分类误判率高 | 用户确认步骤兜底；ambiguous 默认 implementation_gap |
| 3 次重试耗时长 | RDDF_VERIFIER_MAX_LOOPS=1 允许单次模式；MAX_CHANGES 成本护栏 |
| 与 ac-verifier SKILL.md 双入口混淆 | SKILL.md 顶部写"批量/回环用 rdd-verify"，ac-verify CLI 加 --help 提示 |
| 旧项目 `.rddf/state/` 无 `.verifier-loop.json` | 首次运行 rdd-verifier 时 lazy init（status="new"）|

## 11. 实施步骤概览（writing-plans 阶段展开）

1. **Phase 0**: 起草 ADR-0034 + 更新 AGENTS.md 5 阶段表
2. **Phase 1**: 实现 `.verifier-loop.json` + `.ac-verdict-<name>.json` schema + Python 模块
3. **Phase 2**: 实现启发式分类 + SHA 缓存（复用 ac-verifier LLM）
4. **Phase 3**: 实现 `rddf rdd-verify` CLI + 4 个 bash helper
5. **Phase 4**: 改造 `_lib/archive.sh::archive_gate_check` 支持 SHA 缓存读取
6. **Phase 5**: 编写 `skills/rdd-verifier/SKILL.md` 状态机 + guide 推荐器菜单
7. **Phase 6**: 编写 4 个 Python 单元测试 + 4 个 bats 集成测试 + 4 套 mock fixture
8. **Phase 7**: 全量回归（`./test.sh --full --regression`）+ CHANGELOG.md 更新

## 12. 参考

- **OpenSpec 项目**: `2026-08-17-ac-verifier-skill-design.md` — ac-verifier 原始设计
- **GitHub Issue/Discussion**: 待补充
- **Oracle 评审**: 82/100 分，6 个 section actionable 建议已吸收

---

**Status**: ✅ 5 个 design sections 已与用户达成共识；待用户最终 spec 审查后转入 writing-plans 阶段。