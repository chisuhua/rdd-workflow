# spec 残留处置台账 — Phase 1 第六批（2026-11-21）

> 定位：change `repoint-spec-residue-batch6`。**actor / 符号改指**，零标注。
> 批次边界**两次收缩**：台账初判 20 行 → 逐行核实 9 行 → critic 第 1 轮 BLOCKER 后 **6 行 / 3 份**。
> `line` 列是**改前**行号。

## 1. 逐行处置

| file | line | requirement_title | matched_token | disposition | 改前 → 改后 | 落点证据 |
|---|---|---|---|---|---|---|
| `openspec/specs/third-party-feedback-loop/spec.md` | **32**（配套） | Phase traces are replayable from any project subdirectory | —（不命中） | REPOINT（配套） | `trace/guide-plan-*.jsonl` → `trace/execute-*.jsonl` | 同一 Scenario 的 GIVEN 必须与 WHEN 的参数同 kind，否则场景自相矛盾 |
| 同上 | 33 | 同上 | `guide-plan` | REPOINT | `orchestrate show guide-plan` → `... show execute` | `_handle_show` 按 `trace_dir.glob(f"{phase}-*.jsonl")` **严格前缀**匹配（`_lib/cli/orchestrate_cmd.py:728`）；`execute` 是存量真实 kind（本仓 `.rddf/state/trace/` 有 **60 个 `execute-*.jsonl`**） |
| 同上 | 39 | 同上 | `guide-plan` | REPOINT | 同上 | 同上 |
| `openspec/specs/post-flow-analysis/spec.md` | 10 | fix-adr-0027-cli-optin-gate | `guide-ship` | REPOINT | `--phase guide-ship "execute crashed"` → `--phase rdd-builder "builder crashed"` | `--phase` 是**自由字符串元数据**（`_lib/cli/report_issue_cmd.py:44`，无枚举校验）；`"execute crashed"` 的 `execute` 是已退役 skill 名（不在 `RETIRED_TOKENS` 内，但同句一致性要求一并改） |
| `openspec/specs/complete-project-yaml-config-gaps/spec.md` | 70 | verifier-explicit-runner-override | `ac-verifier` | REPOINT | `` `_default_runner` SHALL be invoked (existing ac-verifier behavior) `` → `` `_stage_context_runner` SHALL be invoked (stages agent context for the LLM verifier, per ADR-0045) `` | `_default_runner` 已移除（`_lib/cli/rdd_verify_cmd.py:158-160`「Callers MUST use `_stage_context_runner` directly」）；provider 分派 `:514-521`；行为 docstring `:132-141` |
| 同上 | 179 | verifier-hook-provider-routing | `ac-verifier` | REPOINT | 同上 | 同上 |
| 同上 | 298 | zero-regression-backward-compat | `ac-verifier` | REPOINT | `` `_default_runner` (existing ac-verifier) `` → 同 `:70` | 同上（原文无 `behavior` 一词，统一为三行同句 —— 括注是描述性的，无规范语义损失） |

**合计 6 行 / 3 份 + 1 处配套**。

## 2. 两次收缩（本批最重要的判断）

### 收缩一：20 行 → 9 行（逐行实现核实）

台账按**句子形态**把 20 行判为「E/F 机械改指」。逐行核实 v4 实现后 11 行机制已变或已死：

| spec | 行 | 核实结论 | 依据 |
|---|---|---|---|
| `skeleton-planning` | 11,22,23 | **机制已变** | v4 可执行性 = `artifact_complete`（proposal **and** design，`_lib/discover_ship_changes.py:87-89,212-213`），**与 status 无关**。skeleton 恰因缺 design 而不可执行 ⇒ 结论偶然为真，但句子的 status 逻辑在 v4 **反转** |
| `skeleton-planning` | 43 | **半死** | `phase1_plan.sh` 全文无 skeleton 分支 |
| `skeleton-planning` | 47 | **已死** | 同文件无任何 `warn` |
| `skeleton-planning` | 83 | **已死** | P1 只生成 `tasks.md`；`design.md` 在 rdd-builder scripts **0 命中**（`SKILL.md:53` 明写由执行 agent 撰写） |
| `state-management` | 65 | **半死（rewrite 候选）** | status→`proposed` 由 **P0 approval**（`phase0_approval.sh:252`）；P1 明确不改 status。单改 L65 会与其 Scenario（L72-75 的「fill 创建 design.md 和 tasks.md」半死）自相矛盾 |
| `state-management` | 73 | **已死** | P1 不生成 `design.md` |
| `cross-repo-deps` | 126 | **PARTIAL** | WHEN 半活（`STRICT_DEPS_GATE` 在 `phase1_5_deps.sh:134`，exit 6 在 `builder_cmd.py:66`）；THEN 全死（`rddf hub` 仅 retry-failed；`create_hub_issue` 零生产调用方；`[Dependency]` label 0 生产命中） |
| `cross-repo-federation` | 119 | **已死** | `rdd-planner` 不检查 hub pending（`cross_repo_state` 只被 `report_issue_rfc.py` 写、`watch_hub.py` 读） |
| `roadmap-hierarchy` | 149 | **已死（已被覆盖）** | `plan_done_gate.sh` 不存在；Scenario 写 `.plan-handoff.json`（ADR-0044 Wave 3 RETIRE）；「rdd-doctor 的 roadmap-refs 检查调用 `validate_fragment_refs`」**已逐字存在于同 spec 相邻 Requirement**（L130-145）⇒ 改指 = 重复 |

### 收缩二：9 行 → 6 行（critic 第 1 轮 BLOCKER）

**`rfc-rddf-project-yaml-config-i10:26/28/31` 移出** —— 我原声明的落点**是事实错误**：

| 我原声明 | 实际 |
|---|---|
| 「轻量模式判定在 `_lib/ship_execution_mode.sh:97`」 | 轻量模式判定是 `_lib/builder_deps.py::decide_execution_mode(file_count, task_count, risk_keywords)`（`:42-75`）—— **无 `openspec_tracked` 输入** |
| 「由 rdd-builder P2 消费」 | `ship_execution_mode.sh:97` 读 `git.openspec_tracked` 是 **WAVE 串并行**判定，注释明写「(This is the WAVE dimension — **it says nothing about the execution mode**...)」 |
| — | 姐妹 Requirement `complete-project-yaml-config-gaps:198-207` 已于 2026-11-17 按 ADR-0036 AMENDED 对**同一机制**做 retire 注记 + `v4-residue:allow=history` 围栏，并改写判据 |

⇒ 机制不存在 ⇒ 移交批 7，按姐妹 Requirement 同款形态（retire-NOTE + `history`）。

**这条是「改指一个不存在的落点」的实例** —— 若按原方案实施，会造出一个「`git.openspec_tracked` 强制轻量模式」的假判据，读者会照着实现一个 v4 没有的机制。

## 3. 实测数字

| 指标 | 改前 | 改后 |
|---|---|---|
| 未豁免 | 42 处 / 35 块 / 15 份 | **36 处 / 29 块 / 12 份** |
| 含已豁免 | 325 / 176 / 46 | **319 / 170 / 44**（改指**消除**命中） |
| 已登记豁免 | 283 | **283（不变）** |
| `stale` / `invalid` / `ignored` / `fence_rejected` / `in_fence` | 0 / 0 / 0 / 0 / 0 | **0 / 0 / 0 / 0 / 0** |
| `fence_allows` | 1 | **1** |
| `files_scanned` | 165 | **165** |
| `doctor --category v4-residue` | 35 WARNING | **29 WARNING** |
| `openspec validate --all` ERROR | 11 | **11** |

### 三种处置对两个口径的影响（本批学到的口径）

| 处置 | 未豁免 | 含已豁免 | 说明 |
|---|---|---|---|
| **标注**（`allow`） | −N | **不变** | token 还在，只是被标记为豁免（batch5 的口径） |
| **改指**（换 token） | −N | **−N** | token 真的消失（本批的口径） |
| 纯清理（删行） | −N | −N | — |

## 4. 诚实边界（不可夸大）

**`post-flow-analysis:10` 改后仍不可验证。** 其 GIVEN「SKILL.md Phase Exit 段指示 agent 调 `rddf report-issue …`」在 v4 **无对应物**（`skills/rdd-builder/SKILL.md` 全文无 report-issue / Phase Exit 段；现存的 abnormal-exit 指示只有 `rdd-arch/SKILL.md:692 --phase rdd-arch` 与 `rdd-planner/SKILL.md:269 --phase rdd-planner`）。

本批只做 **token 处置**（`guide-ship` → `rdd-builder` 是 `--phase` 自由字符串下的正确值），**不声称**恢复了该 Scenario 的可验证性。整份 spec 是自动生成的 delta 形态工件（`### Requirement: fix-adr-0027-cli-optin-gate` + `- **GIVEN** **WHEN**` 混行），属「9 份未合并 delta 形态」专项。

## 5. 记 tail（范围外）

1. **14 行移交批 7** —— 11 行（收缩一）+ rfc-rddf 3 行（收缩二），按 **annotate / rewrite** 两类处置：
   - `annotate`：`skeleton-planning` 6、`cross-repo-deps` 1（PARTIAL）、`cross-repo-federation` 1、`roadmap-hierarchy` 1、`rfc-rddf` 3
   - `rewrite`：`state-management:65+72-75`（唯一候选 —— 需 Requirement + Scenario 成对改写）
2. **`general/spec.md` 4 行** —— 测试锁定 + 断言漂移，需三方联动专项
3. **delta 形态垃圾结构**（`post-flow-analysis` / `rfc-rddf-*` 的自动生成 Requirement 名）—— 专项
4. **`dashboard-verification-status` 围栏示例与 schema 脱节** —— 文本修正专项

## 6. 审查链

| 环节 | 结论 | 处置 |
|---|---|---|
| critic 第 1 轮 | REJECT（2 BLOCKER + 3 SF） | BLOCKER-1 rfc-rddf 落点事实错误 ⇒ 移出 3 行；BLOCKER-2 常数重算 ⇒ 已按块数实测修正；SF-1 块数 35→29（不是 31）；SF-2 tpfl 改 `execute`（`stage_builder` 是 session kind，不是 trace 前缀）；SF-3 repoint/annotate 二分漏 rewrite ⇒ 批 7 按两类打标 |

## 7. 回滚

- 台账 / 测试：`git revert <sha>`（tracked）。
- spec 改动：`openspec/` gitignored ⇒ 回滚凭据 = `/tmp/opencode/specs-b6-before/`（3 份改前快照）
  + `/tmp/opencode/specs-backup-b6-<ts>/`（165 份整树）+ T0 的 18 组 validate 输出。
