---
id: objective-proposal-lifecycle-truth
status: active
created: 2026-11-27
last_revised: 2026-11-27
review_by: 2026-12-27
owner: rdd-planner
priority: P0
manual_deps: []
supersedes: null
theme: 提案产物与状态面的可信性 —— 立项产物一次成型 + 状态/队列不再静默失效
---

# Objective: objective-proposal-lifecycle-truth

## 1. 驱动诊断（Why now）

2026-11-26 的两次真实会话（CppTLM `ses_de7dcca7` 立项、`ses_de80d7eb` rddf status 重排）暴露同一类问题：
**工具的产物与状态在「静默」层面不可信**，而每一处都已被单独记录过、却都缺登记载体：

| # | 症状 | 复发证据 |
|---|---|---|
| 1 | 立项产物的 In/Out Scope 被逗号切碎 + Out 段重复 | `fix-bats-per-file-timeout.md:411` 记「另案」→ 第 2 次 |
| 2 | delta 恒 `ADDED` + 形态退化（`acceptance-N` / 恒真 WHEN） | `fix-spec-v3-naming-sync.md:192` 记「第三次…另案」→ 第 4 次 |
| 3 | 批量 verifier 分流在无 `iteration.json` 时永远空 | oracle 2026-11-26 定位（per-change `--stage` 不受影响 ⇒ 单边失效） |
| 4 | `rddf status` 把 13 条已落地当 pending；4 条已归档条目完全隐身 | `ses_de80d7eb` 实测（19 → 6 真待办） |
| 5 | P2 setup 完成即写 `execution_status=completed`（无消费方） | `ses_de7dcca7` 中断态实测 |
| 6 | 使用方仓无 commit-gate 声明 ⇒ 门禁三判据一条没跑 | `ses_de7dcca7` 实测（CppTLM / rdd-workflow 均无声明） |
| 7 | 「另案立项」无登记载体 ⇒ 缺陷无限期悬空 | 本表 #1 / #2 的根因 |

⇒ 本 objective 的主题不是「修 7 个 bug」，而是**让「产物对不对」「状态真不真」变成可机判的判据** ——
每个单元都必须以「**测试先红后绿**」收口，而不是以「这次手工修对了」收口。

## 2. 目标愿景 + 完成判据

- 立项一次成型：从 improvement 到 `proposal.md` + `design.md` + `tasks.md` + `specs/**/spec.md`，
  **零手工重写**（当前每次都要重写 proposal 与 delta）；
- 状态面可信：`rddf status` 的 pending 数 = 真待办数（差值 ≤ 约定容差）；陈旧状态行**可见**；
- 队列不空转：批量 verifier 分流在**无** `iteration.json` 的项目里仍能发现 eligible change；
- 门禁要能用：使用方仓能生成**合法且非平凡**的声明；有存量红的仓也能声明（baseline）；
- 每条「另案」都有载体：deferral 必须写清目标 slug 或 backlog 占位。

**done-when**（全部满足 ⇒ 转 completed）：

- [ ] 7 个单元（U1–U7）全部完成，且每个单元的 **TDD 判据**（红→绿→变异）已入库并**持续绿**；
- [ ] `tests/unit/` + `tests/integration/` + `bats` 全绿，且 `./test.sh --gates` 绿；
- [ ] 一次**新的**立项（真实 change）**零手工重写**产出 proposal / design / tasks / delta（实测记录）；
      ⚠ **强制时点**：本条**不**等 7 个单元全完 —— **W1（U1+U2）收口时立即执行**（它才是用户真实意图所在）；
- [ ] `rddf status` 在一个真实仓上的 pending 数与人工对账差值 ≤ 1；
- [ ] 一个**无** `iteration.json` 的项目里，`rddf rdd-verify --dry-run` 能列出 eligible change；
- [ ] deferral 扫描对全仓零噪音（存量豁免清单已登记）。

## 3. 架构依据

- **ADR-0025**（D2 段映射 + D3 delta + **D6 头部元数据优先级**）—— delta 声明载体沿 D6 的头部字段机制，不扩固定段映射；
- **ADR-commit-verification-gate** D2/D3/D9②/D9① —— 声明是门禁的唯一入口；未声明 ⇒ 不设门禁（**明文决策，不改**）；
  D9② 提供「事实性补登 / 检测 ≠ 拦截」先例；D9① 提供「声明被弱化」的防护面；
- **归档决策 `register-change-in-iteration`** —— 「缺失时不创建半成品 iteration.json」**保持原样** ⇒
  verifier 队列改走 **disk 推导**（方案 B），不与该决策冲突；
- **`4661096a`（`rddf-status-based-on-improvements`）** —— 「iteration.json 是流程记账，不是维护真源」⇒ 方向一致；
- **`rddf status` Mode A** —— 已 disk 推导 ⇒ 本 objective 的队列推导**复用同源实现**（禁第二套真源）；
- **`fix-generator-scope-extraction`（已归档）** —— 前一次补丁只覆盖 bullet/numbered ⇒ 本次补「纯表格」形态；
- **`tests/KNOWN_FAILURES.txt`** —— baseline 机制**形态对齐**它，不发明第二套语义。

## 5. 反例

- 不要在 rdd-workflow 仓实现构建缓存 / ccache（属项目侧；RW-7 降级为一行提示）；
- 不要为「让状态更好看」自动回填既有 improvement 的状态行（只读面 + 各仓自修）；
- 不要为了「统一」把 `iteration.json` 与 disk 双写（真源只减不增）；
- 不要在 baseline 里放「时间窗口内忽略失败」这类不可判定的机制；
- 不要把「另案」的登记做成自动创建 improvement（只报警，不代写）；
- 不要把治理面（`~/.config/opencode`）的改动混进 rdd-workflow 的 change（两仓各自的审查链）。

## 9. 目标依赖与 Decision Gate

### 9.1 前置 objective 依赖

无（本 objective 自包含；与 `objective-onboard-new-skill` 无耦合）。

### 9.2 Go / No-Go Decision Gate

- **Go 判据**（全部 5 条 → 转 completed）：
  - [ ] U1–U7 全部完成且各自 TDD 判据持续绿；
  - [ ] 一次真实立项零手工重写（实测记录）；
  - [ ] `rddf status` pending 数与人工对账差值 ≤ 1；
  - [ ] 无 `iteration.json` 的项目里批量分流非空；
  - [ ] 使用方仓的门禁声明可生成且非平凡。

- **No-Go / 降级判据**：
  - 若 U4（handoff 生命周期）找不到**消费方** ⇒ 该单元降级为 noted（不提交纯化妆的 schema 变更）；
  - 若 U7（baseline）的前置 ADR SU 未 Accepted ⇒ 暂停实现，保留 design 结论；
  - 若 U5（声明生成）无法在仓内推导真实验证命令 ⇒ 只交付「未声明可观测」部分，生成入口延后。

### 9.3 跨 objective 影响

- 受此 objective 影响的下游：所有「从 improvement 到可执行 change」的流程；
- 与 `objective-bypass-audit-hub-governance` 的接口：U6 的「未声明可观测」留痕可复用其 audit log 通道（**不新建**并行通道）。

### 9.4 单元清单与批次

| 单元 | 主题 | 归属仓 | 优先级 | 批次 | 阻塞于 |
|---|---|---|---|---|---|
| U1 | 范围节解析（纯表格 + 带注解标题） | rdd-workflow | P0 | W1 | — |
| U2 | delta 形态守卫 + MODIFIED 语义 | rdd-workflow | P0 | W1 | — |
| U3 | verifier 批量分流 disk 化 | rdd-workflow | P1 | W2 | — |
| U4 | rddf status 终态词表 + 陈旧可见 | rdd-workflow | P1 | W2 | — |
| U5 | P2 生命周期真实性（setup/tasks + 分叉检出） | rdd-workflow | P1 | W3 | — |
| U6 | deferral 登记载体 | rdd-workflow | P1 | W3 | — |
| U7 | commit-gate 声明生成 + 未声明可观测 | 治理仓 + rdd-workflow | P0 | W4 | — |
| U8 | commit-gate baseline（known_failures） | 治理仓 | P1 | W5 | ADR SU |
| U9 | worktree 构建提示（降级形态） | rdd-workflow | P2 | W5 | — |

### 9.4b 目标性质轴（metis 2026-11-27 追加）

P0–P2 只表达**优先级**，不表达**性质**；planner 按 P0 把跨仓项与本仓项排同期会踩「跨仓提交 + 双审预算」的坑 ⇒ 增一列：

| 轴 | 单元 | 含义 |
|---|---|---|
| 产物正确性（diff 型 AC：逐字节对） | U1 / U2 | 生成器输出形态 |
| 状态可信性（对账型 AC：视图 vs 真源差值） | U3 / U4 / U5 | 队列 / 看板 / handoff |
| 跨仓治理机制（两仓各自的审查链与门） | U7 / U8 | 治理仓机制面（须 SU）+ rdd-workflow 引导 |
| 流程纪律（载体化） | U6 | 欠账登记 |
| DX（等待有预期） | U9 | 提示 |

⇒ **U7/U8 虽为 P0/P1，但审查链与门禁口径与本仓不同** ⇒ 排期时按「跨仓」单独看，不与 U1/U2 同期合批。

### 9.5 DAG snapshot (2026-11-27)

> Snapshot derived at 2026-11-27, regenerate: `rddf deps objective-proposal-lifecycle-truth`

```
U1 (scope 解析) ─┐
U2 (delta 生成) ─┼─→ W1 ─→ [真实立项零手工重写 验收点]
U9 (构建提示)  ─┘        │
                          ▼
U3 (verifier disk) ──→ U4 (status 判据) ──→ [pending 对账 ≤1 验收点]
                          │
                          ▼
U5 (P2 生命周期) ─→ U6 (deferral 载体) ──→ [deferral 零噪音 验收点]
                          │
                          ▼
U7 (声明生成+可观测) ─→ U8 (baseline, 需 ADR SU) ──→ [声明可生成且非平凡]
```

## 10. next_sprint_candidates
- [x] **U2** delta 形态守卫 + MODIFIED 语义（与 U1 合批；含 openspec 版本口径裁决）—— **W1 已归档**
- [x] **U1** 范围节解析（纯表格 + 带注解标题）—— 与 U2 同文件 ⇒ 同 change —— **W1 已归档**
- [x] **U7a** commit-gate 声明生成入口 + doctor 三面检测（rdd-workflow 半边）—— **W6 已归档**；**U7b**（未声明留痕 · 治理仓 architect 轨）仍待立项
- [x] **U3** verifier 批量分流 disk 化（写回侧落点 = 不创建半成品 iteration.json，记账本 = verdict cache + 审计日志）—— **W2 已归档**
- [x] **U4** rddf status 终态词表 + 陈旧状态可见性 —— **W2 已归档**
- [x] **U5** P2 生命周期真实性 —— **W4 已归档**（消费方裁决 = P2.5 review；setup 写 running、归档才写 completed）
- [x] **U6** deferral 登记载体 —— **W4 已归档**（约定 + doctor category + 豁免清单入库）
- [x] **U8** baseline / known_failures —— **已落地**（治理仓 SU `Accepted` + 实现提交 `4cbf5c0` · 演练回填 `973b451` · 验收 `f711085`；AC1–AC9 全 pass）
- [x] **U9** worktree 构建提示（降级形态，独立可做）—— **W5 已归档**
- [x] **U10** status 视图不得截断 issue 列表（U4 上线后第一次真实使用即暴露：标题报 6、只列 5）—— **W3 已归档**

## 11. 跟踪台账（append-only）
| Sprint | kind | 内容 | Decision/调整 | 原因 |
|--------|------|------|---------------|------|
| sprint-2026-11-27 | go-decision | objective 创建（9 单元 · TDD 三段判据入库）+ 9 份 improvement 草稿 + 提案池登记 | 立项走 oracle→critic 双审；RW-3 走方案 B（disk 化）；OC-1c 走 baseline | 2026-11-26 两次真实会话暴露 7 处「静默失效」，且 3 处已在 backlog 里以「另案」记录却从未立项（本次一并补载体） |
| sprint-2026-11-27 | go-decision | **W1 起 change**：`fix-proposal-generator-output-fidelity`（U1+U2 合批）立项完成（P0 approve → P1 plan/tasks → P1.5 deps，mode=worktree · 0 blockers）⇒ 15 条 AC · 6 Task ×(5 步+变异第 6 步) | 用户裁决：RW-3=B / OC-1c=baseline / 治理面合并交付 | metis 复核合并稿给出 3 blocker + 10 项 high/medium ⇒ 合并稿整体重写（AC 真重排 + 4 项 design 裁决载体 + 半成品防护 + golden snapshot 判据） |
| sprint-2026-11-27 | go-decision | **W1 归档**：`fix-proposal-generator-output-fidelity`（U1+U2）已归档 （`2026-11-27-fix-proposal-generator-output-fidelity` · 15/15 AC pass · spec 合流：`generator-scope-extraction` +3/~2、新建 `spec-delta-generator-fidelity` +6）| 实施期发现并修正两处契约缺口：① delta 改 **opt-in**（原「总是生成、无载体即拒绝」会把存量 300+ 无载体 improvement 的 P0 全拒，实测 18 个 bats 红）；② 归档后两条 requirement 缩短以避免 very-long 债增长 | 遗留（登记，不静默）：worktree 模式 6 个 project-root 测试失败（另案）、`iteration.json` 的 tasks_done 实现后未刷新（U5 同类）、`validate_delta_targets` 的 archive 侧接线未做 |
| sprint-2026-11-27 | go-decision | **W2 起 change**：U3（`fix-verifier-discovery-disk-derive`）与 U4（`fix-rddf-status-terminal-markers`）**独立立项**（代码面不相交）⇒ 各自 P0 approve + P1 plan/tasks + P1.5 deps（mode=worktree · 0 blockers）⇒ 各 7 条 AC | 用户裁决：两个 change 都走 merge | 写回侧落点在 design D-1 落定（不创建半成品 `iteration.json`）；U4 的 stale 告警落点钉死 = `snap.errors`（metis 裁决） |
| sprint-2026-11-27 | go-decision | **W2 归档**：U3 `2026-11-27-fix-verifier-discovery-disk-derive`（7/7 AC · spec 合流 `verifier-lifecycle` ~2）+ U4 `2026-11-27-fix-rddf-status-terminal-markers`（7/7 AC · spec 合流 `proposal-lifecycle-sync` ~1）均已归档 | 实施期决策：U3 的 disk 推导与 `rddf status` Mode A **共用一个实现**（`_lib/change_status.py`，对象身份断言）；`scan_queue.sh` 删除第二份判据改为薄委派；U4 的终态词表提为公开常量 + `rddf status --help` 从常量渲染 | 遗留（登记，不静默）：`iteration.json` 的 tasks_done 仍不刷新（U5）；worktree 模式 6 个 project-root 失败（另案）；既有 improvement 的陈旧状态行**不回填**（只读面，项目侧自修） |
| sprint-2026-11-27 | go-decision | **W3 = U10 立项**：`fix-status-issue-list-truncation`（U4 归档后第一次真实使用即暴露的截断缺陷）⇒ planner 批准 + P0 生成 proposal/delta（新 capability `status-issue-visibility`）+ design D-1~D-5 + 5 Task × 5 步 plan | 用户裁决：起 W3 = U10 | 根因在**消费侧**（`errors[:5]` 硬截断 ⇒ 标题报 6、只列 5）⇒ 与 U4 修的是同一类「静默失效」；设计取「全量列出 + 阈值 20 后**明示**未展开数」而非「无限列出」 |
| sprint-2026-11-27 | go-decision | **W3 归档**：`2026-11-27-fix-status-issue-list-truncation`（7/7 AC pass · 新建 capability `status-issue-visibility` +1 requirement） | 实施期决策：状态摘要清洗函数 `clean_status_snippet` 与分类器**同模块同源**（对象身份可断言）；requirement 正文压到 479 字 ⇒ 不增长 very-long 债 | 遗留（登记，不静默）：CppTLM 侧 6 条已归档但状态行陈旧的 improvement 未回填（工具只指路，项目侧自修）；阈值 20 为工程取舍（已由测试钉住） |
| sprint-2026-11-27 | go-decision | **W4 = U5 + U6 立项**（独立两个 change）⇒ 各自 P0 + design + plan/tasks（mode=worktree） | 用户裁决：起 W4 | U5 的**消费方**在 design 阶段裁决 = **P2.5 review（合并决策点）**—— archive gate / status / dashboard 均已另有真源，不重复；U6 走「约定先行 ⇒ 扫描 ⇒ 接线」三步 |
| sprint-2026-11-27 | go-decision | **W4 归档**：U5 `2026-11-27-fix-builder-handoff-p2-lifecycle-truth`（7/7 AC · 新 capability `builder-lifecycle-truth`）与 U6 `2026-11-27-add-deferral-registration-guard`（7/7 AC · 新 capability `deferral-registration`）均已归档 | 实施期决策：① U5 的真相源 = disk 的 tasks.md（`implementation_state()` 单一计算点），handoff 只贡献「声明」⇒ 真源不增；② U6 的豁免清单**按文件粒度**入库（78 处未登记 / 33 个文件），本仓 doctor 零噪音 | 遗留（登记，不静默）：存量 78 处未登记 deferral 只登记豁免、不回改（项目侧自修）；`iteration.json` 的 tasks_done 仍不刷新；worktree 模式 6 个 project-root 失败 |
| sprint-2026-11-27 | go-decision | **W5 起 change**：U9（`improve-worktree-build-hint`）立项完成（P0 → design D-1~D-5 → plan/tasks 4 Task × 5 步 → P1.5 worktree）⇒ 5 条 AC | 用户裁决：起 W5 | objective §9.4 的批次表把 W5 定为「U8（治理仓，ADR SU）+ U9（rdd-workflow）」；本次先起 U9（自包含、无前置），U8 需治理仓 SU（architect 轨） |
| sprint-2026-11-27 | go-decision | **W5 归档**：U9 `2026-11-27-improve-worktree-build-hint`（5/5 AC pass · 新建 capability `worktree-build-hint`）已归档 | 实施期决策：提示只**引用**项目侧加速手段（ccache / 复用 build 目录）而**不检测** ⇒ 已用 ccache 的项目也会看到这行（可忽略）；lightweight 模式不提示（主仓即工作区，属噪音） | 遗留（登记，不静默）：**不实现**任何构建缓存机制（项目侧决策）；`iteration.json` 的 tasks_done 不刷新；worktree 模式 6 个 project-root 失败 |
| sprint-2026-11-27 | go-decision | **W5 = U8 的 Status Update（治理仓 · architect 轨）**：起草 `ADR-commit-verification-gate` 的 **D10**（失败可被 baseline 显式容忍 · `known_failures`）⇒ oracle（治理面）**BLOCK**（6 条全采纳）→ critic（arch）**REJECT**（2 BLOCKER：C1 fail-closed 无 commit 路径执行者 / C2 ⊆ 交付不了「不能增」）→ 复审 **APPROVE_WITH_CONDITIONS**（0 BLOCKER）⇒ **Status: Accepted（SU 2026-11-27）** | 用户裁决：等 oracle/critic 结论后继续推进 SU 收口 | 两个 BLOCKER 的要害都是「**声称没有执行者**」：① 「巡检缺席 ⇒ 字段无效」的 fail-closed 必须钉在 **commit 路径**（巡检守卫须为独立条目 + 不得被 baseline 绑定 + 载体 git-tracked + 判定在 commit 时）；② 「baseline 不能增」不能由 ⊆ 断言交付（同提交内「制造新失败 + 登记条目」仍满足 ⊆）⇒ **显式指派**给声明内容守卫（D9① 形态扩展到 `known_failures` 字段） | 遗留（登记，不静默）：① **D9⑰ 未进 D9 表** —— 守卫硬断言「恰 16 项」且要求四面覆盖，而 AC 面载体属实现另案 ⇒ 改为 D10③′ 段内登记 + **V25** 钉住义务；② 治理仓的 SU 提交被**并行会话的在途改动**打回门禁（`bun test tests/` 红在 plan-topics 回滚清单，非本 SU 引起）⇒ 待其清单同步后提交；③ 实现另案（治理仓）须携带 D9⑰ 四面登记 + 巡检存在性/绑定守卫 + `match` 特异性守卫 + 声明内容守卫扩展 + 回滚清单同批（D10⑥） |
| sprint-2026-11-27 | go-decision | **U8 实现立项（治理仓）**：载体 `.rddf/improvements/commit-gate-baseline-known-failures.md`（5 段 · metis 1 轮已修订，**真实 finding 逐条处置**）+ `openspec/changes/commit-gate-baseline-known-failures/`（proposal 含 **D9 AC 面 ①–⑰** / design D-1~D-9 / tasks 8 Task × 5 步含 7 条变异腿 / `.openspec.yaml` skip_specs）⇒ `openspec validate --strict` valid | metis 6 个 P0 全采纳：① 补**识别机制**（声明 `inspection` 字段 —— SU 未定义 ⇒ 三条硬约束否则无执行者）；② 巡检层**不复用子串语义**（否则 `3 fail ⊆ 13 fail` 永远命中）；③ **D9 计数 16→17 的迁移陷阱**（只 bump 计数 ⇒ 已归档 proposal 的 AC 面并集塌陷 ⇒ 守卫须多标题兼容）；④ 留痕走 notice/账本；⑤ 超时不得豁免；⑥ 畸形声明总兜底 | 遗留（登记，不静默）：治理仓提交被**并行会话的在途改动**打回门禁（全仓 `bun test tests/` 红在 plan-topics 回滚清单，非本 change 引起）⇒ 待其清单同步后提交；实现期 Task 6（D9⑰ 治理面登记）须 architect 落笔并与机制面**同批一个 commit** |
| sprint-2026-11-27 | go-decision | **U8 已落地（治理仓）**：实现 `4cbf5c0`（18 文件：`lib/commit-gate.ts` 声明形状/命中判定/特异性/总兜底/巡检硬约束 + `plugins/commit-gate.ts` 全量输出+notice 账本+巡检静态检查 + 新 `scripts/commit-gate-baseline-doctor.ts` 巡检层 + 防增守卫 + D9⑰ 四面登记 + 回滚面）⇒ 演练 PASS 回填 `last_drill`（`973b451`，registry 回 `active`）⇒ 验收报告 AC8/AC9 转 pass（`f711085`）。**独立复核**：`bun test tests/` ⇒ 1378 tests / 0 fail；`rollback-drill` ⇒ PASS；`commit-gate-doctor` ⇒ PASS（active）；`openspec validate --strict` ⇒ valid | 并行会话代提交我方 18 个文件（内容未改，除回滚清单补 1 条 edit） | **演练首次 FAIL 暴露我这份清单的真缺陷**：撤了 D9⑰ 的三处载体却**漏撤 ADR D9 表的 `| ⑰ |` 行**（根因 = 我的 hunk 过滤器跳过了含表格分隔行的 hunk）⇒ 回滚后测试算 17、期望 16；由并行会话补 1 条 edit 修复 ⇒ 演练通过。⇒ **教训登记**：自动生成回滚 edits 时，**表格行也是回滚面**（不能因『含分隔行』整 hunk 跳过）| 遗留登记：① `plan-topics` / `plan-synthesis-offload` 两条**相邻机制**因并行会话的 change 打破回演练，保持 `proving`（债在并行会话侧）；② 宿主的模块缓存坑再次实证（改 `lib/**`/`plugins/**` ⇒ 必须 `opencode service restart`，否则门禁静默消失）；③ 本 change 未 push |
| sprint-2026-11-27 | go-decision | **W6 = U7a 立项 + 归档**：`2026-11-27-add-commit-gate-declaration-bootstrap`（8/8 AC · 新 capability `commit-gate-declaration-bootstrap` · +2 requirement）—— `rddf commit-gate init`（候选表推导，**不猜**）+ doctor `commit-gate` 三面（未声明 / 空壳 / 未 tracked，均 WARNING ⇒ 检测 ≠ 拦截） | 用户裁决：起 W6（先 rdd-workflow 半边） | 范围裁决：原跨仓提案拆两 change ⇒ 本 change 只做 rdd-workflow 半边；「未声明留痕」移出 U7b（治理仓，改 `plugins/commit-gate.ts` 接线 ⇒ architect 轨 + oracle→critic） | 遗留（登记，不静默）：① **U7b 未立项**（objective 最后一个单元）；② 宿主模块缓存坑（改 `lib/**`/`plugins/**` ⇒ 必须 restart）； ③ 两仓均未 push 最新提交（治理仓已同步、rdd-workflow 有 1 个新提交待推）| **经验**：`git commit` 的长 heredoc 正文若含特字符会被工具层「单独成段」规则整条拒 ⇒ 改用短消息 + 详情进文档 |
| 2026-11-28 | go-decision | **U7a 归档后补正**：AC6 原只测**函数面**（`cmd_commit_gate(["--help"])`），而用户实际执行的 `rddf commit-gate --help` 走注册表 `_SUBCOMMAND_DESCRIPTION`（无枚举）⇒ **用户面假绿**。已改为**从常量渲染** + 新增 `test_registry_help_renders_the_same_enumeration`（直接断言注册表条目） | 归档后自查 | **教训（写进本 objective 的方法论）**：判据必须打**用户面**（真实 CLI 入口 / 真实文件路径），只打函数面会让「用户看到的东西」漏测 —— 与 U10 的「消费侧截断」是同一类错位 |
