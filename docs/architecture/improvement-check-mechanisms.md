# 改进检查机制对照表

> **本文档目的**：明确区分 rdd-workflow 中两类性质不同的「改进检查」机制,跟踪其在当前代码库中的实施状态,并指出仍需进一步完善的部分。
>
> **维护者**: sisyphus
> **创建日期**: 2026-08-24
> **关联 ADR**: [ADR-0014](../adr/ADR-0014-review-phase-and-debt-reflow.md), [ADR-0027](../adr/ADR-0027-continuous-evolution-feedback-loop.md), [ADR-0029](../adr/ADR-0029-issue-driven-proposal-creation.md)

---

## 一、核心区分(用户已正确指出的本质差异)

| 维度 | **项目级检查** (ADR-0014) | **工作流级检查** (ADR-0027) |
|------|------------------------|--------------------------|
| **检查对象** | **第三方项目代码本身**——当前 change 执行过程中产生的新债务 | **rdd-workflow 自身** —— flow-bug、gate-failure、phase-crash |
| **触发时机** | `guide-ship` Phase 2.5 review(execute 后,archive 前) | 任意 phase 异常退出(Script 平面 trap + Agent 平面 `rddf report-issue`) |
| **数据源** | `git diff` 中的 TODO/FIXME/HACK、测试失败、架构漂移 | 进程 exit code、stderr traceback、gate raise、agent 观察 |
| **落地位置** | `.rddf/improvements/<name>.md`(类型=`debt`) + 追加 tasks.md | `.rddf/issues/<category>-<8char-hash>.md`(L1) → 三重 opt-in → GitHub issue (L2) |
| **消费者** | 用户本人 + 下一次 `guide-arch` / `guide-plan` 时被 deps 重新分析 | `guide-design` Phase 2 选项 3 "从 GitHub issue 创建提案"(ADR-0029) + 上游 rdd-workflow 维护者 |
| **回流路径** | tasks.md / 新 change(走 `propose → plan → ship`) | guide-design 选项 3 → proposal → ADR/proposal.md → archive 时 close issue (ADR-0027 §6) |
| **是否上报** | ❌ **不上报**,仅本地写入 | ✅ **可上报**(默认 opt-out,三重 opt-in) |

**一句话总结**:
- **ADR-0014** = "我刚帮用户改的项目产生了什么债务需要回头收拾"
- **ADR-0027** = "我(rdd-workflow)在执行过程中哪里有 bug 需要维护者修"

---

## 二、ADR-0014 (Phase 2.5 review) 实施情况

### 设计要点

在 `guide-ship` Phase 2 (execute) 与 Phase 3 (archive) 之间插入 review 阶段,收集三类债务:

| 债务类型 | 处理 | deps 重跑? |
|---------|------|-----------|
| 范围内债务(测试覆盖不全等) | 追加 `tasks.md` | ❌ 不需要 |
| 旁效应债务(独立的代码遗留问题) | 创建新 change + 写入 `.rddf/improvements/*.md` (`type=debt`) | ⚠️ 按文件冲突决定 |
| 架构漂移(偏离 ADR 目标) | 回注 `guide-arch` → 生成差距分析 | ❌ |

### 实施状态:**已落地**

| 组件 | 路径 | 行数 | 状态 |
|------|------|------|------|
| SKILL.md Phase 2.5 文档 | [`skills/guide-ship/SKILL.md:387-475`](../../skills/guide-ship/SKILL.md) | ~89 行 | ✅ |
| 已提取 helper(`handle_review_action`) | [`skills/guide-ship/scripts/ship_review.sh`](../../skills/guide-ship/scripts/ship_review.sh) | ~175 行 | ✅ |
| Gate 检查 `review_debt_recorded` (warning 级) | [`_lib/gate.py:341-370`](../../_lib/gate.py) | 30 行 | ✅ |
| 实际 issue 记录已存在(8 个 `.rddf/improvements/*.md` 含 `**类型**: debt`) | `.rddf/improvements/` | — | ✅ |

### Gate 实现细节(`_lib/gate.py:341`)

```python
def _check_review_debt_recorded(ctx: dict) -> tuple[bool, Optional[str]]:
    # 扫描 git diff 中的新增 TODO/FIXME/HACK
    result = subprocess.run(
        ["git", "diff", "HEAD", "--", "*.cpp", "*.h", "*.py", "*.ts"],  # ⚠️ 语言范围有限
        ...
    )
    new_todos = [line for line in result.stdout.split('\n')
                 if line.startswith('+') and any(t in line for t in ('TODO', 'FIXME', 'HACK'))]
    if not new_todos:
        return (True, None)  # 没有债务 → 通过
    # 若有债务,要求 .rddf/improvements/ 中存在 debt 类型条目
    ...
    return (True, None) if debt_names else (False, "warning")
```

### 已知局限(ADR-0014 未补完的事项)

1. **语言范围有限**(`_lib/gate.py:347`)
   - 仅扫描 `.cpp/.h/.py/.ts`,不覆盖 `.go/.rs/.java/.rb/.sh`
   - **影响**: 用户的 Go/Rust/Java 项目债务永远不报警
   - **建议**: 扩展 glob pattern 或读取项目语言检测配置

2. **Gate 逻辑过于宽松**(`_lib/gate.py:368`)
   - 只要 `.rddf/improvements/*.md` 中存在 `**类型**: debt` 就通过,不论 debt 与当前 change 的债务是否匹配
   - **影响**: 用户可用历史 debt 文件掩盖当前债务
   - **建议**: Gate 应检查 debt 文件名包含 `<current_change_name>` 或文件 mtime 在 execute 时间之后

3. **架构漂移(选项 3)未真正实现**(SKILL.md:451 仅占位)
   - `guide-arch/scripts/arch_env_check.sh` 等未调用 drift detector
   - **影响**: 选项 3 选中后实际不生成 drift-analysis.md
   - **建议**: 关联 `.rddf/improvements/structural-drift-detector.md` P0 提案

---

## 三、ADR-0027 (持续演进反馈环 5 环) 实施情况

### 设计要点

```
[1.Detect] → [2.Buffer] → [3.Report] → [4.Triage] → [5.Close]
   检测         本地兜底      分层提交       提案化        闭环追溯
```

### 实施状态:**主体已落地,细节有差距**

#### 第 1 环 Detect(脚本 + Agent 双平面)

| 组件 | 路径 | 行数 | 状态 |
|------|------|------|------|
| Bash trap wrapper | [`_lib/post_flow_wrap.sh`](../../_lib/post_flow_wrap.sh) | 115 | ✅ |
| 三段式 classifier | [`_lib/post_flow_analysis.py`](../../_lib/post_flow_analysis.py) | 531 | ✅ |
| Python orchestrator(单写者规则) | [`_lib/orchestrator_entry.sh`](../../_lib/orchestrator_entry.sh) | 106 | ✅ |
| 4 phase entry 脚本 source orchestrator | `skills/guide-{arch,plan,design,ship}/scripts/*env_check.sh` | — | ✅ |

#### 第 2 环 Buffer(本地 issue 文件)

| 组件 | 路径 | 行数 | 状态 |
|------|------|------|------|
| Issue 检测核心 | [`_lib/issue_reporter.py`](../../_lib/issue_reporter.py) | 272 | ✅ |
| Dedup hash 计算 | [`_lib/issue_dedup.py`](../../_lib/issue_dedup.py) | 61 | ✅ |
| 实际写入路径 | `.rddf/issues/<cat>-<hash>.md` | — | ✅ 7 个真实文件 |

#### 第 3 环 Report(L1→L2→L3 分层)

| 组件 | 路径 | 行数 | 状态 |
|------|------|------|------|
| L2 `gh issue create` | `_lib/issue_reporter.py::submit_issue_via_gh` | 含在 272 行内 | ⚠️ 已有代码 |
| L1 写本地 → L3 提示 | 同上 | — | ✅ |
| L1+L2+L3 env-var 配置 | `_lib/config.py` `reporting` namespace | — | ⚠️ 需验证 |

#### 第 4 环 Triage(原设计已变更)

| 组件 | 状态 |
|------|------|
| 原 ADR-0027 §5 设计: `guide-design` Phase 2 选项 4 "📨 triage 上游 issue" | ❌ **未实现** |
| 实际方案: **ADR-0029** `add-improve --from-issue` + `guide-design` 选项 3 "🐙 从 GitHub issue 创建提案" | ✅ **功能等价替代** |

**说明**: 原始 ADR-0027 §5 的 "triage 选项 4" 设计被 ADR-0029 (Issue-Driven Proposal Creation) 取代。后者把 triage 流程拆为两步:用户先在 `guide-design` 选项 3 选择目标 issue → 触发 `add-improve --from-issue` 走完整 brainstorm → 生成 proposal。功能等价但路径不同。**建议**: 在 ADR-0027 §5 文末加 supersession 注:"§5 Triage 设计由 ADR-0029 替代。"

#### 第 5 环 Close(archive 时自动关闭)

| 组件 | 路径 | 行数 | 状态 |
|------|------|------|------|
| Close hook 业务逻辑 | [`_lib/close_issues.py::close_issues_for_change`](../../_lib/close_issues.py) | 259 | ✅ |
| Worktree 模式 hook | [`_lib/archive.sh:428,657,662`](../../_lib/archive.sh) | inline | ✅ |
| Lightweight 模式 hook | [`skills/guide-ship/scripts/ship_archive.sh:239`](../../skills/guide-ship/scripts/ship_archive.sh) | inline | ✅ |
| `issue_refs` 字段扩展 | `openspec/changes/<name>/roadmap-meta.yaml` | — | ✅ |
| PR 探测 + 6 个 CI 标识探测 | `_lib/issue_reporter.py::is_ci_environment` | — | ✅ |

### 实施证据: 当前已捕获的真实问题

```bash
$ ls -1 .rddf/issues/
flow-bug-267a7384.md   # git auto-detect 实测示例
flow-bug-541abda7.md
flow-bug-815f2e4d.md
flow-bug-9d745b3a.md
flow-bug-b9ef7edd.md
flow-bug-bd677735.md
manual-49ef7d45.md
phase-crash-1028200b.md
```

### ⚠️ Issue 文件内容 vs ADR-0027 §4 模板的差距

**ADR-0027 §4 规定的完整 frontmatter**:
```yaml
---
category: <category>
detected_at: <ISO timestamp>
rdd_workflow_version: <semver>
dedup_hash: <8-char hash>
submitted: <bool>
submitted_url: <url or null>
---
+ ## Reporter(rdd-workflow/python/git/os/project_hash/rddf_session_id/skill_invoked)
+ ## Stack trace / details
+ ## Repro
```

**实际生成的 issue 文件**(7 个样本,各 16 行):

```yaml
---
category: "manual"
detected_at: "2026-08-13T07:40:33.549003+00:00"
rdd_workflow_version: "2.0.9"
dedup_hash: "49ef7d45"
submitted: false
submitted_url: null
---

## Description

test manual reporting

## Reporter commit

rdd-workflow v2.0.9
```

**差异**:
1. ❌ 缺 `Reporter` 段(含 `python`/`git`/`os`/`project_hash`/`rddf_session_id`/`skill_invoked`)— ADR-0027 §4 规定必填
2. ❌ 缺 `Stack trace / details` 段
3. ❌ 缺 `Repro` 段
4. ❌ `Reporter commit` 段被简化(只一行,缺 sha)

**影响**: 上报到 GitHub 后,维护者无法看到完整环境信息,issue 排障成本高。

### 已知测试覆盖

| 测试文件 | 覆盖范围 |
|---------|---------|
| `tests/unit/test_post_flow_analysis.py` | 3 段式 classifier 路径 |
| `tests/unit/test_cli_reporter.py` | `rddf report-issue` CLI |
| `tests/unit/test_doctor_no_issue_write.py` | doctor 边界(写 .rddf/issues/?) |
| `tests/unit/test_cli_all_subcommands.py` | 全部 CLI 子命令 |
| `tests/unit/test_cross_repo_state.py` | 跨仓库 state 隔离 |
| `tests/integration/test_feedback_loop.bats` | 双模式 close hook |

---

## 四、是否需要进一步完善代码?

### 初版判断(后被 Oracle 推翻部分优先级)

初版我识别了 4 个 gap。Oracle 复核后**显著调整**(详见第五节):
- P1-B(gate 语言范围)降级为 P2,因为触发时机本身有更深层问题
- 新增 4 个我漏掉的关键 gap,其中 **G1 是 P1-top 的功能性死代码**,**G3+G4 接近 P0(同意边界)**

第五节列出修订后的完整 PR 序列。本节先记录原始 4 gap 的方案作为参考,但**不再单独执行**。

---

## 五、Oracle 复核(8m 32s 深度审计)— 修订后的完整改进包

### 5.1 复核结论摘要

Oracle 用 9m32s 重新审视所有相关代码(16+ 文件、4 个 ADR、9 个测试),在初版 4 gap 基础上额外发现 **8 个新 gap**。其中 1 个标注 **P1-top(close 环整体死代码)**、1 个标注 **P0-边界(CLI 跳过 opt-in)**、1 个标注 **P1(SKILL.md 指令自身不可执行)**。

### 5.2 初版 4 gap 复核裁定

| 初版 | Oracle 验证 | 裁定 |
|------|----------|------|
| **P1-A** issue 文件缺 Reporter/Stack/Repro | ✅ 成立 + **新增发现**: 缺 `project_hash`,ADR §3 承诺的"跨 issue 假名化关联"也不成立 | 维持 **P1** |
| **P1-B** gate glob 仅 4 种语言 | ✅ 事实成立,但 **Oracle 补刀**: gate 跑 `git diff HEAD` 在 worktree commit 后**diff 已空**→ 几乎 dead code | **降级为 P2**,必须先解触发时机 |
| **P2-C** debt 绑定宽松 | ✅ 成立 + 更糟: cwd 相对路径 + 裸 `except → True`,静默失效 | **合并到 P2 PR-5** 一起修 |
| **P2-D** ADR-0027 §5 缺 supersession | ✅ 成立 | 维持 **P2** |

### 5.3 Oracle 新增的 8 个 gap(按严重度排序)

#### G1(P1-top)— Close 环整体死代码

**事实**: `openspec archive <name>` 把 `openspec/changes/<name>/` **移动**到 `openspec/changes/archive/<name>/`。但 `archive.sh:422` 先 archive,`:428` 才调 `close_issues_for_change_hook`,而 `close_issues.py:133` 读的是 PRE-move 路径 → 永远找不到 `roadmap-meta.yaml` → 恒 no-op。

**代码证据**:
```bash
# _lib/archive.sh:422-428
if ! openspec archive "$name" --yes; then     # ← 移动发生在此
    ...
fi
close_issues_for_change_hook "$name" "$main_root" || true  # ← hook 在后
```

```python
# _lib/close_issues.py:129-144
def _load_issue_refs(change_name, project_root):
    meta_path = Path(project_root) / "openspec/changes" / change_name / "roadmap-meta.yaml"
    # ↑ 永远是 archive/ 不存在的旧路径
```

**测试盲区**: `tests/integration/test_archive_close_dual_mode.bats:26` 用**行号断言固化错误顺序**;单元测试用 `tmp_path` fixture,从不走真实 post-archive 布局。

**修复方向**:
- A(推荐): `_load_issue_refs` 先查 `changes/<name>/`,fallback 到 `changes/archive/<name>/`(无需改 archive 主流程)
- B: archive 前快照 refs 到 state 文件

#### G2(P1)— 本地 issue 文件永不被标记关闭,retention 死亡

**事实**: `close_issues.py:208` 用 `dedup_hash == issue_number` 匹配,但 `dedup_hash` 是 8 位 hex、`issue_number` 是整数——恒不匹配 → `closed_at` 字段永不写入 → `_is_old_closed` 恒 false → `prune_old_issues` 永不删文件。

**修复**: 改为按 `submitted_url` 末尾 `/issues/<N>` 反向匹配 ref。

#### G3(P0-边界)— CLI 上报路径绕过三重 opt-in 闸门

**事实**: `report_issue_cmd.py:55-57` 和 `cli/issue_cmd.py:64-65` 直接调 `submit_issue_via_gh`,**不**检查 `RDDF_REPORT_ENABLED` / `RDDF_REPORT_AUTO_SUBMIT` / `submit_categories`,也不查 CI 标识。ADR-0027 §3 铁律"任何数据外发都需显式 opt-in"被违反。

**代码证据**:
```python
# _lib/cli/report_issue_cmd.py:55-57
if not parsed.no_submit:
    gh_repo = os.environ.get("RDDF_REPORT_GH_REPO", "chisuhua/rdd-workflow")
    submit = submit_issue_via_gh(file_path, parsed.category, gh_repo)
    # ↑ 直接 submit,无 opt-in 检查
```

**特别风险**: 4 个 SKILL.md(G1 的 agent 平面触发是 G4)指示 agent 在异常退出时调 `rddf report-issue` **且不带 `--no-submit`** → agent 平面在零 opt-in 下可外发数据。

**修复**: 在 `submit_issue_via_gh` **单一收束点**加三重 opt-in 检查,所有调用方自动生效。禁止各调用方单独检查(防遗漏)。

#### G4(P1)— Agent 平面指令本身跑不通

**事实**: 4 个 phase SKILL.md 写的是 `rddf report-issue --phase X --exit <code> "..."`,但 `report_issue_cmd.py:31-42` 的 argparse **没有 `--exit` 参数** → agent 照做会得到 exit 2 (argparse usage-error) → 实际**没有任何 issue 被上报**,而是退化成下一个 usage-error。这解释了 `.rddf/issues/` 8 个样本里 7 个来自 script 平面、1 个是手动测试。

**修复二选一**:
- A: SKILL.md 改写——把 `--exit <code>` 直接并入 `description`(`report-issue "phase X exit=N: <text>"`)
- B: CLI 新增 `--exit-code N` 参数,作为 issue metadata

#### G5(P2)— classifier 内部矛盾

**事实**: `post_flow_analysis.py:234` F3(`_STATE_VIOLATION`,匹配 "invalid state")先于 `:246` F2 匹配 → F2 的 "invalid state" 分支**不可达**,gate-failure 只剩 "ConfigError" 一条路径;而 `analyze_phase_trace:490` 的 F2-cumulative 把同样的 "invalid state" 文本映射为 gate-failure → **两条路径对同一信号分类不一致**。ADR §1.2 承诺的 `F4-gate`(gate raised → gate-failure)规则完全未实现。

**修复**: F2 提到 F3 前(优先级:ConfigError → gate raised → invalid state);补 F4-gate 正则;统一 `analyze_phase_trace` 映射。

#### G6(P2)— ADR 承诺的配套工件缺失

**事实**:
- `_lib/schemas/issue_reporter_schema.json` 不存在(schemas/ 目录 17 个文件中无) — **已由 PR-6 删除承诺**（改依赖 `config_schema.json` 的 reporting namespace）
- `.rddf/state/.issue-reporter.json` 全库无写入点 — **已由 PR-6 删除承诺**
- `.rddf/state/.reporting-config.json` 缓存未实现 — **已由 PR-6 删除承诺**
- ADR-0027 §3 的一次性 banner 未实现 — **已由 PR-6 删除承诺**
- `_should_auto_submit` 只读 env var,`.rddf.json` 的 `reporting.enabled` **不生效**(调用方全传 None)

**修复二选一**(推荐方案 2):
- A: 全部补实现(工作量 ~3-5 天,跨多文件)
- **B: 改 ADR 文本,删掉冗余承诺**(env-var 方案已够用,成本 0.5 天)

**执行状态**: 采用方案 B。clean-adr-0027-section-5-supersede change 已删 ADR-0027 中 `issue_reporter_schema.json` / `.issue-reporter.json` / `.reporting-config.json` / 一次性 banner / `retention_days` 的冗余承诺（PR-6）。

#### G7(P3)— 文档/名称小错

- `tests/integration/test_feedback_loop.bats` **不存在**,实际是 `test_archive_close_dual_mode.bats`
- ADR-0027 写 `normalize_for_hash` 在 `issue_reporter.py`,实际在 `_lib/issue_dedup.py`(实现更合理,属 ADR 文本漂移)

#### G8(P2)— category taxonomy 微漂移

`post_flow_analysis.py` 的 `_classify_interrupted_phase` 用了 "phase-interrupted" 类别,但 ADR §1.1 类别清单**没有这一项**。需在 ADR §1.1 末尾追加,或改回 ADR 规定的 4 类之一。

### 5.4 Oracle 复核验证项 — 核实无 gap

为防止遗漏,Oracle 主动核对了以下方面,**全部确认无问题**:
| 关注点 | 验证结论 |
|--------|---------|
| `sanitizer.py` 是否扩展到 `$HOME` 路径 | ✅ 已扩展 (`sanitizer.py:69-71` 有 `/home/`、`/Users/`、`/root/`、`sensitive_names` 项目名替换) |
| `config.py` `reporting` namespace | ✅ 存在(env 映射 41-45 行 + defaults + schema) |
| rdd-doctor 不触发 reporter | ✅ doctor_cmd.py 无 issue_reporter 引用,test_doctor_no_issue_write.py 存在 |
| orchestrator race condition | ✅ 无竞态(trap 默认 defer + `\|\| true` + `"$@"` fallback) |
| `RDDF_USE_ORCHESTRATOR=no` 逃生舱 | ✅ 有测试(`test_orchestrator_default_on.bats` T4 + `test_env_var_toggle.bats`) |
| `phase.review_validation` state handoff | ✅ 抽样路径未发现 gap(debt 通过文件流转 `.rddf/improvements/` + `proposal-suggestions.md` 给 guide-design,与 ADR-0025 一致) |

### 5.5 修订后的优先级

| 优先级 | Gap | 理由 |
|--------|-----|------|
| **P0**(1) | G3 + G4(同意边界 + SKILL.md 指令坏) | 唯一涉及数据外发同意边界;agent 平面目前整体不可用;两者同文件合并修 |
| **P1**(2) | G1(close 死代码)+ G2(closed_at 永不写) | ADR-0027 第 5 环承诺静默失效;无用户可见报错,难发现 |
| **P1**(1) | 初版 P1-A(issue frontmatter 补全) | 维持。上报内容质量是 L2 开启的前置 |
| **P2** | G5(classifier 矛盾)+ 初版 P2-C(gate debt 绑定) + 初版 P1-B(gate 语言范围,降级) | 三者都触 `gate.py`/`post_flow_analysis.py`,合并修 |
| **P2** | 初版 P2-D(ADR §5 supersession)+ G6/G7/G8(文档对齐包) | 一次性文档/category taxonomy 对齐 |

### 5.6 6-PR 分批实施计划(Oracle 给出)

| PR | 优先级 | 范围 | 验收 | 测试 |
|----|--------|------|------|------|
| **PR-1** | **P0**(Quick) | `submit_issue_via_gh` 加三重 opt-in + CI 检查;4 个 SKILL.md 把 `--exit <code>` 并入 description 或新增参数 | 无 `RDDF_REPORT_ENABLED=yes` 时 `rddf report-issue` 只写本地并打印 L3 提示;agent 平面可成功上报 | 3 unit(闸门 on/off × CLI 两路径)+ 修正 1 个现有 CLI 测试 |
| **PR-2** | P1(Short) | `_load_issue_refs` 增加 `openspec/changes/archive/<name>/` 回退路径;`_update_local_issue_files` 改为按 `submitted_url` 尾号匹配 | post-archive 布局下 close 真实执行;重复执行幂等 | 1 unit(模拟 archive 后路径) + 修 `test_archive_close_dual_mode.bats` 行号断言(改为"hook 存在且容错",不再固化顺序) |
| **PR-3** | P1(Medium) | 初版 P1-A: `_render_issue_body` 补 Reporter 段(python/git/os/project_hash/rddf_session_id/skill_invoked)+ Stack trace + Repro | 新样本含全部 §4 字段;project_hash=sha256(project_root)[:8] 经 sanitize | 2 unit(字段齐全 + 脱敏生效)+ 1 integration(与 PR-6 文档对齐配套) |
| **PR-4** | P2(Quick) | classifier 顺序修正:F2 提至 F3 前 + 补 F4-gate + 统一 `analyze_phase_trace` 映射 | "invalid state → 一致分类" 回归 | 4 unit |
| **PR-5** | P2(Short) | `_check_review_debt_recorded` 重做:绝对路径 + 收窄 except + 明确触发时机(由 ship_review.sh 在 Phase 2.5 commit 前调用,而非 ship_done gate)+ 扩展语言 glob + debt mtime 绑定 | gate 真正触发;Go/Rust 项目也覆盖 | 4 unit |
| **PR-6** | P2(Quick) | ADR-0027 §5 supersession 注 + ADR 文本对齐(normalize_for_hash 位置、test 文件名 + G6 取舍决策:**推荐改 ADR,删除冗余 state-file/banner 承诺**,非补实现) + G8 类别补完 | 文档自洽 | 0 test(纯文档) |

**PR 顺序理由**: PR-1 风险最低最先落地;PR-2/3 可并行;PR-4/5/6 任意序。**无 PR 间硬依赖**,均不触碰 archive 主流程与既有 handoff 契约,无破坏性变更。

**工作量汇总**: 6 PR,约 8-10 天人工工作量(初版估 3-4 天的"最低可行包"覆盖 PR-1/2/3 + PR-6 子集)。

### 5.7 三大架构风险(Oracle 总结)

1. **Close 环无重试/无对账** — archive 成功 + `gh issue close` 失败 → refs 随目录移走,永不再试。**缓解**: PR-2 加 archive/ 回退路径 + 失败时把 pending close 追加到本地 issue 文件(复用现有载体,不增 state 文件)。
2. **同意闸门散落在调用方而非收束点** — 当前 env 检查在 `_should_auto_submit`(自动路径)有、CLI 路径无,未来新增调用方必漏。**缓解**: PR-1 把闸门下沉到 `submit_issue_via_gh`,并加约定注释"任何新上报调用方必须经此函数"。
3. **warning 级 gate 的静默通过模式**(`_check_review_debt_recorded` 的 cwd 相对路径 + 裸 `except → True`)在整个 `gate.py` 中可能是**系统性模式**——**建议**: PR-5 顺手 grep 同类写法定位范围,**不**在本轮扩大修复(避免 scope creep)。

### 5.8 选择题:采纳哪个版本?

| 方案 | 范围 | 工作量 | 风险 |
|------|------|--------|------|
| **A. 最小可行包**(初版估) | PR-1/2/3 + PR-6 子集 | 3-4 天 | 低 — 只覆盖 P0/P1 高价值 50% gap;P2 暂缓 |
| **B. Oracle 完整包**(推荐) | 6 PR | 8-10 天 | 中 — 覆盖所有真实 gap,含同意边界修复 |
| **C. 仅 PR-1**(紧急) | P0 同意边界 | 1-2 天 | 最低 — 但 P1 死代码继续存在 |

**推荐**: **方案 B**(Oracle 完整包)。P0 是数据外发同意边界,任何生产暴露都用得上;P1 dead code 影响功能完整性且用户无法察觉,拖到后期修复成本更高。

#### 任务 A:完善 issue 文件 frontmatter

**目标**: 让实际生成的 `.rddf/issues/*.md` 符合 ADR-0027 §4 模板。

**位置**: `_lib/issue_reporter.py::write_issue_file` 当前的渲染函数。

**实现要点**:
```python
def write_issue_file(result: IssueResult, env: SystemEnv, session_id: Optional[str]) -> Path:
    md = f"""---
category: {result.category}
detected_at: {result.detected_at}
rdd_workflow_version: {env.rdd_workflow_version}
dedup_hash: {result.dedup_hash}
submitted: false
submitted_url: null
---

## Description
{result.description}

## Reporter
- rdd-workflow: {env.rdd_workflow_version}
- openspec CLI: {env.openspec_cli_version}
- python: {env.python_version}
- git: {env.git_version}
- os: {env.os_platform}
- project_hash: {sha256(project_root)[:8]}
- rddf_session_id: {session_id or 'none'}
- skill_invoked: {result.skill_invoked}

## Stack trace / details
```
{result.sanitized_trace or 'No trace captured'}
```

## Repro
{result.repro_hint or 'See skill_invoked above for context'}
"""
```

**测试**:
- 增加 fixture: 实际生成 file → 解析 frontmatter → 验证 6 个 Reporter 字段非空
- 增加 fixture: 验证 stack trace 经 `loop.sanitizer.sanitize()` 脱敏(无 `~/.ssh/`,无 `/etc/passwd`,无 API key)

#### 任务 B:扩展 reviewer gate 语言范围

**位置**: `_lib/gate.py:347`。

**改动**:
```python
# 原:仅 4 种语言
subprocess.run(["git", "diff", "HEAD", "--", "*.cpp", "*.h", "*.py", "*.ts"], ...)

# 新:从项目配置或自动检测 + 全量
subprocess.run(["git", "diff", "HEAD"], ...)  # 全部文件
# 然后在 Python 内按行过滤 matched extensions
extensions = {'.go', '.rs', '.java', '.rb', '.sh', '.cpp', '.h', '.hpp',
              '.py', '.ts', '.tsx', '.js', '.jsx', '.c', '.cs',
              '.swift', '.kt', '.scala', '.php'}
```

**测试**:
- fixture: Go 项目 → 创建 `.go` 文件 + TODO → gate returns warning
- fixture: 无扩展名的 shell script → 不扫(白名单策略,避免 false positive)

> 注:任务 C(加严 debt 绑定)、任务 D(ADR §5 supersession)已被 Oracle 复核合并到 PR-5 / PR-6,不再单独执行。详细方案见第五节 5.6 节。

---

## 六、参考

- [ADR-0014](../adr/ADR-0014-review-phase-and-debt-reflow.md) — review 阶段债务回流(项目级)
- [ADR-0027](../adr/ADR-0027-continuous-evolution-feedback-loop.md) — 持续演进反馈环(工作流级)
- [ADR-0029](../adr/ADR-0029-issue-driven-proposal-creation.md) — issue-driven proposal(取代 ADR-0027 §5)
- [`_lib/gate.py`](../../_lib/gate.py) — 门控机制:`_check_review_debt_recorded` 在第 341 行
- [`_lib/issue_reporter.py`](../../_lib/issue_reporter.py) — Issue reporter 核心(272 行)
- [`_lib/post_flow_analysis.py`](../../_lib/post_flow_analysis.py) — 三段式 classifier(531 行)
- [`_lib/close_issues.py`](../../_lib/close_issues.py) — Close hook 业务逻辑(259 行)
- [`_lib/cli/report_issue_cmd.py`](../../_lib/cli/report_issue_cmd.py) — `rddf report-issue` CLI(62 行)
- [`_lib/cli/issue_cmd.py`](../../_lib/cli/issue_cmd.py) — `rddf issue` 子命令(150 行)
- [`skills/guide-ship/scripts/ship_review.sh`](../../skills/guide-ship/scripts/ship_review.sh) — Phase 2.5 helper
- [`skills/guide-ship/scripts/ship_archive.sh:239`](../../skills/guide-ship/scripts/ship_archive.sh) — Lightweight close hook
- [`.rddf/issues/`](../../.rddf/issues/) — 实际捕获的 8 个 issue 样本

**Oracle 复核记录**: 2026-08-24, 9m32s 深度审计 (含 G1-G8 验证 + 6-PR 序列 + 3 架构风险)。
