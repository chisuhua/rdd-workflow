---
name: rdd-doctor
description: |
  Manual read-only diagnostic tool for workflow state files.

  Invoke when BOTH:
    1. Workflow "feels broken" but no specific error
    2. Need drift detection across `.rddf/state/` / plans / ADR / docs / architecture

  Default: read-only; multi-category; exit codes 0/1/2/3 matching `openspec validate`.

  Boundary ownership: see role.boundaries.owns / not_owns.
license: MIT
compatibility: Requires bash + git + python3.11+ + jsonschema + pyyaml
metadata:
  author: rdd-workflow
  version: 0.2.0
  user-invocable: true
---

# rdd-doctor

## 调用

```bash
bash skills/rdd-doctor/scripts/doctor.sh [--json] [--category {state,plan-tdd,roadmap-meta,proposal-table,proposal-section,tasks-checkbox,migration-residue,roadmap-refs,roadmap-feature,roadmap-md-integrity,roadmap-phases,docs-consistency,ai-context-bootstrap,gitignore,bypass-audit,improvement-frontmatter-consistency,objective-lifecycle,objective-structure,arch-audit,review-debt,roadmap-backup,baseline-freshness,v4-residue,layout,openspec-quota,deferral-registration,commit-gate}] [--quiet] [--help] [--version]
```

## 何时该跑

1. **感觉"流程哪里不对"** → 5 秒排查入口
2. **修改 `_lib/schemas/` 后** → 跑 `--category state` 看是否有旧 state 文件需要迁移
3. **CI 升级 `STRICT_ARCH_GATE=yes` 之前** → 跑一次预估会暴露多少问题
4. **接手别人工作树** → 跑一次看 `.rddf/state/*.json` 是否干净

## 退出码

| Code | 含义 |
|------|------|
| 0 | 所有 23 类 OK |
| 1 | 仅 INFO + WARNING，无 CRITICAL |
| 2 | 至少 1 个 CRITICAL |
| 3 | checker 内部异常（其他类仍能报告） |

## 关键约束（不要违反）

- **只读** — 不修改任何 tracked / gitignored 文件（除了 `--json` 输出 `.rddf/state/.doctor-report.json`）
- **手动触发 only** — 不接入任何 phase gate / 自动调用
- **cat-N 独立于 openspec CLI** — `openspec` 缺失时降级为 checkbox-only，输出 INFO 而非 silent skip

## 检查概览

| 类别 | 检查什么 | 涉及 `.rddf/roadmap/` ? |
|------|---------|:---:|
| `state` | `.rddf/state/*.json` 对 `_lib/schemas/*.json` schema |  |
| `plan-tdd` | `.rddf/plans/*.md` 含 5 个 TDD step markers |  |
| `roadmap-meta` | `openspec/changes/*/path-map.yaml` 字段 + 类型（**manual_deps 漂移会静默忽略**，doctor 报 CRITICAL） |  |
| `proposal-table` | `improvement-suggestions.md` / `improvement-approved.md` Markdown 表格列数 + 链接有效性 |  |
| `proposal-section` | `openspec/changes/*/proposal.md` 段头（## Why / ## Capabilities / ## Acceptance）完整性 |  |
| `tasks-checkbox` | `openspec/changes/*/tasks.md` checkbox 计数（独立于 openspec CLI） |  |
| `migration-residue` | `AGENTS.md` / `README.md` / `USAGE.md` / `docs/proposal-*-format.md` 里的 stale `improvements/X` 引用和 `.rddf/.rddf/improvements/X` 双前缀 bug（WARNING）。`Fix:` 行直接给出 `rddf migrate-improvements --include-docs [--allow-source-repo]` 完整命令 |  |
| `roadmap-refs` | `.rddf/roadmap/` + `.rddf/roadmap.md` 的 R1/R2/R3 cross-ref 完整性（feature.phase_refs 指向存在的 phase 等）| ✅ |
| `roadmap-feature` | `.rddf/roadmap/features/*.md` frontmatter 必需字段 + done/archived 状态 fragment 是否落入 `.rddf/roadmap.md` AUTO-INDEX Features 段 | ✅ |
| `roadmap-md-integrity` | `.rddf/roadmap.md` `## Phase Skeleton` 表 schema + AUTO-INDEX 三段齐全 + ADR 链接有效 + AUTO-SPRINT drift | ✅ |
| `roadmap-phases` | `.rddf/roadmap/phases/*.md` frontmatter 必需字段 + AUTO-INDEX Phases 段同步 + main doc 一致性 | ✅ |
| `docs-consistency` | `package.json` skills 列表 ↔ `skills/` 目录 ↔ `smoke.bats` 注册项 三方一致 |  |
| `ai-context-bootstrap` | AI 上下文层（AGENTS.md / HANDOFF.md / docs/）的层级 + 链接 sanity |  |
| `gitignore` | `.rddf/project.yaml` `git.openspec_tracked` × `.gitignore` 排除项一致性（add-gitignore-hard-protection）。两种合法形态：`openspec/`（整树）或 `openspec/changes/`（只挡归档路径，per ADR-0036 修订）。false+两种都缺 → WARNING（建议追加 + 混合状态提示 `git rm -r --cached`）；true+任一存在 → 反向不一致 WARNING；只挡归档路径但 `openspec/specs/` 未入库 → INFO（保护依赖它被跟踪） |  |
| `bypass-audit` | `.rddf/state/.bypass-audit.jsonl` 旁路使用统计（per `bypass-audit-mechanism` P2 改进）；ARCHIVE_ON_MAIN > 3/月 → WARNING，> 6/月 → CRITICAL |  |
| `improvement-frontmatter-consistency` | `.rddf/improvements/*.md` frontmatter 分隔符存在 + **YAML 可解析**。不可解析（多行 plain scalar 里含 `: `）⇒ 该文件的 priority / phase / category / status 全部丢失，`rddf status` 渲染成「待讨论」+ 空列 |  |
| `objective-lifecycle` | `.rddf/roadmap/objectives/*.md` 生命周期（active → deferred → completed → archived）；`review_by` 超期 → WARNING（per ADR-0054 + add-objective-tracking）| ✅ |
| `objective-structure` | `.rddf/roadmap/objectives/*.md` 结构 / frontmatter 必需字段 | ✅ |
| `arch-audit` | rdd-arch 产物健康度：gap-analysis structural_ok（per ADR-0046 §5）+ completeness（draft/partial/complete）+ ADR inventory（count / latest / superseded / status 漂移）+ `.arch-handoff.json` sanity。advisory only，不阻断任何 gate。设计动机：把 `check_arch_done_gate.sh` 内嵌的 advisory 检查外提为可独立 query 的 doctor category |  |
| `review-debt` | `.py / .sh / .bats` 源文件中 unticketed TODO/FIXME/HACK 标记（无 ticket id 参考，薄封装 `_lib.review_debt_checker._TODO_PATTERN`）|  |
| `v4-residue` | 契约面上残留的 v3 skill 名：R1 路由型 enum 无法表达 v4 路由（CRITICAL）、R2 活代码字符串字面量指向 `guide-*`（WARNING，注释与 docstring 豁免）、R3 SKILL.md frontmatter `name:`（CRITICAL）、**R4 `openspec/specs/*/spec.md` 的 normative 段**（WARNING，受 `doctor.v4_residue.scan_specs` 开关控制，默认 `false`；`checked 0` ≠ clean）。R4 详解见下方「R4 —— spec 面残留」 |  |
| `layout` | `.rddf/` 布局单一真源校验（per ADR-0026）：必需条目缺失 → WARNING、未登记顶层条目 → INFO、`class` 与 `.gitignore` 实况不符 → WARNING。advisory only —— 本 category 永不产生 CRITICAL，且只扫 `.rddf/` 一层（不递归进 `.rddf/wt/`）| |
| `roadmap-backup` | `.rddf/roadmap/.backup/<timestamp>/` 子目录完整性 + staleness（>90 天）+ 多备份建议合并 |  |
| `openspec-quota` | `openspec/changes/` 开放目录数 vs 项目自设上限（`.rddf/project.yaml` 的 `openspec.proposed_limit`；缺省/0 = 不限）。未配置 ⇒ 0 findings；超限 ⇒ **CRITICAL**（`file=.rddf/project.yaml`）；配置值不可用（YAML/类型/bool/负数/层级错）⇒ **WARNING**（不静默当 0）。advisory gate（opt-in 项目自己把 `rddf openspec quota` 接进 CI）|  |
| `commit-gate` | `.rddf/commit-gate.json` 的**可用性**三面（**互斥**，均 WARNING）：①**未声明** ⇒ 门禁三判据不设门禁（ADR D3）；②**空壳**（`verify_commands` 仅 1 条且命令 ∈ `true` / `echo` / `:` / `exit 0`）；③**未 git-tracked**（worktree 内无门禁）。修法分别给 `rddf commit-gate init` / 真实命令 / `git add`。判据单一真源 = `_lib/commit_gate_declaration.py` |  |
| `deferral-registration` | 文档里的 deferral 措辞（`另案` / `另立` / `另行立项` / `后续另案`）是否带**登记目标**（`另案（已登记：<slug>）` 或 `另案（backlog：<主题>）`）。无目标 ⇒ **WARNING**（file + line）；豁免清单 `.rddf/deferral-exemptions.txt` 里的条目不再命中 ⇒ 「可清理」提示（清单不静默腐坏）。只扫 `.rddf/improvements/**` + `.rddf/reviews/**`（代码注释归 `review-debt`）| |
| `baseline-freshness` | `tests/KNOWN_FAILURES.txt` 最近 refresh 注释日期 + 占位符 reasons（>30 天 → WARNING，>90 天 → CRITICAL）。来源是 refresh 注释日期，不用文件 mtime（git checkout / atomic-rename 不可靠） |  |

### R4 —— spec 面残留（`openspec/specs/*/spec.md`）

已采纳的 capability spec 里若仍以**已删除的 stage**（`guide-arch` / `guide-design` / `guide-plan` /
`guide-ship` / `guide-spec` / `ac-verifier`）为主体，按规范施工的人会去实现一个不存在的流程，
而没有任何检查会报错 —— R4 就是补这一层。

**开关**：`.rddf/project.yaml` 的 `doctor.v4_residue.scan_specs`（**默认 `false`**）。
`v4-residue` 属 advisory gate ⇒ R4 的 WARNING **不会**拖红 CI。

**口径（冻结常量）**：扫描根恰为 `openspec/specs/*/spec.md`（非递归，**不扫** `openspec/changes/**`）；
normative 段 = `### Requirement:` 标题+正文 / `#### Scenario:` 标题+正文 / 正文内 fenced code block；
**不含** `## Purpose` 等散文段。命中按**块**归类。

**合法引用要显式标注**（**禁止文件级 allowlist**）。标注是**独占一行**的 HTML 注释，
有两个位置：

**位置一 —— 行位置**（默认）：标注紧跟**命中行**，豁免该行的全部退役 token。

```markdown
SHALL accept `guide-ship` for legacy state files.
<!-- v4-residue:allow=enum -->
```

**位置二 —— 围栏位置**：标注紧跟 fenced code block 的**结束行**（` ``` `），豁免该围栏内**全部**行。

````markdown
```json
"route": "archive-ready|guide-ship|guide-plan|halted|null",
```
<!-- v4-residue:allow=enum -->
````

围栏内的命中没有可用的行位置：标注插围栏**内**会污染读者照抄的示例，放围栏**后**则前一行是
结束符、无 token ⇒ 报 `stale allow`。围栏位置有**四个限制**：

1. **局部性** —— 必须紧跟围栏**结束行**（与「标注在内容之后」同向）；
2. **`code` 限 `enum` / `guard`** —— 围栏是读者照抄的规范性示例，能合法保留旧名的只有
   ① 该值仍在某个 schema 的 enum 里 ② 反漂移断言 / 夹具。其它 code（`history` 等）⇒
   **不生效**并报 `fence-position allow code`；
3. **可见性** —— 每条围栏式豁免都进普查台账的「围栏式豁免清单」（file / 围栏行范围 / code / tokens）。
   它与被豁免的文本物理分离，且台账不列已豁免行 ⇒ 没有这份清单，它就只存在于一个没人读的注释里；
4. **逐行 disposition** —— 人工台账仍逐行记理由。

**未闭合围栏**（EOF 前无结束行）没有可跟的结束行 ⇒ 不构成围栏位置（fail-closed）；其正文仍被扫描。
**围栏内的标注不是元数据**（是示例内容）⇒ 不豁免任何东西，并报 `in_fence`。

`code` 只能取五类之一：`enum`（该枚举值今天仍存在于 schema）/ `proposal-name`（提案名）/
`guard`（反漂移守卫自身）/ `history`（归档历史，如 RETIRED 注记保留的原文）/
`rename-history`（重命名说明）。写错 code ⇒ 标注**不生效**并报 `invalid allow code`。

- 标注**与命中同行无效**（命中照报）—— 标注须独占一行，紧跟命中行。
- 标注的**豁免范围**已无命中 ⇒ 报 `stale allow`（豁免清单会自己过期，不会腐化成第二个假通过）。
- 「把旧名说成现存物」（`the existing ...`）且**无标注** ⇒ WARNING 并提示措辞；**有标注** ⇒ 按标注豁免。
- `## Purpose` 等**非 normative** 段里的围栏也可带围栏式标注，但它豁免不到任何被扫描的行，
  也不报 stale（围栏里确实有 token）—— 与行位置作用在非规范行上的语义一致。

**`checked 0` ≠ clean**：`openspec/specs/` 不存在（干净 clone、或本仓 `openspec/` 被 gitignore）时
报 INFO「checked 0」，**不报**「无残留」。

⚠️ **标注的已知副作用**：标注行（约 33 字符）落在 Requirement 正文里 ⇒ 被 openspec 的
`extractRequirementBody` 计入正文长度 ⇒ 临界长度的 Requirement（约 467–500 字符）加标注后会新增
一条 advisory WARNING `requirements[N]: very long (>500 characters)`。
这是**机制固有代价**（HTML 注释渲染不可见、不改语义；`validate --all` 的 ERROR 数不受影响），
**不是内容回归**。⇒ 验证「标注未改变校验结果」时必须按 **issue 类型 + 目标做多重集比对**，
不能只数一种 issue（只数一种会让判据被平凡满足）。

⚠️⚠️ **比对必须用 `--json`**：`openspec validate` 的**文本输出不显示** `requirements[N]` 这类 issue
—— 只有 `--json` 才报。⇒ 用文本输出做「逐字节相同」比对**看不到** `very long` 增量
（这是 2026-11-21 之前批 3 / 4 / 5 的验收判据的真实缺口：实测那些批次合计引入了 **25 条**
从未被验证覆盖的 `very long`）。

```bash
openspec validate --all --json | jq '.items[].issues[] | select(.message | test("very long"))'
```

**常驻守卫**：`tests/unit/test_spec_requirement_length.py` 冻结了 `very long` 清单
（当前 62 条 / 38 spec）与「注入造成的增量」（当前 25 条 / 13 spec）⇒
任何批次让 Requirement 跨过 500 ⇒ 守卫红 ⇒ 必须在同一提交里更新冻结值并说明
「新增的 very long 是否可接受」。

⚠️ **执法点是本地，不是 CI**：本仓 `openspec/` 整树被 `.gitignore:45` 排除 ⇒ CI 的 fresh checkout
里**没有** `openspec/specs/` ⇒ 守卫在 CI 上恒 `skip`（这是**预期**：CI 上没有可校验的 spec，
让它 fail 只会让 CI 恒红）。⇒ 守卫在**本地执行批次时**生效。

⚠️ **归因漂移边界**：若新增的 `very long` 来自**新形态**的注记（守卫的剥除规则不认得），
断言 B 不会红（增量被算进 baseline 侧）⇒ 只更新冻结清单就能转绿，而「注入 / 存量」的归因会静默腐化。
⇒ **规则**：断言 A 红且增量疑似来自新注记形态时，**必须同步扩展守卫的剥除规则**，
**不得只改冻结值**。

台账：`.rddf/reviews/spec-very-long-baseline-2026-11-21.md`。

**清理清单**：`.rddf/reviews/spec-residue-census-*-full.md`（机器生成，`disposition=unset` 的行归零
= 清理完成的判据）。生成器：`python3 skills/rdd-doctor/scripts/gen_spec_residue_census.py --out <path>`。

### `.rddf/roadmap/` 文档诊断速查

如果你的目标是**诊断 `.rddf/roadmap/` 下的文档**（phases / features / objectives / 主表完整性），直接用以下 6 个 category：

```bash
bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-feature     # .rddf/roadmap/features/*.md frontmatter + AUTO-INDEX 同步
bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-refs        # .rddf/roadmap.md + .rddf/roadmap/ 内的 cross-ref 完整性
bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-phases        # .rddf/roadmap/phases/*.md 完整性 + main doc 引用一致
bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-md-integrity  # .rddf/roadmap.md 表 schema + AUTO-INDEX sync + ADR 链接
bash skills/rdd-doctor/scripts/doctor.sh --category objective-lifecycle # .rddf/roadmap/objectives/*.md review_by 超期检查
bash skills/rdd-doctor/scripts/doctor.sh --category objective-structure # .rddf/roadmap/objectives/*.md 结构校验
```

完整入口：`bash skills/rdd-doctor/scripts/doctor.sh`（默认跑全部 20 类）。

## 路径解析（MUST 行为）

doctor 总是从**真实的 `_lib/`**（`<project_root>/_lib/`）读取 schema，**不**走 `skills/_lib/` shim 路径——这是 commit c3a90fe 之后所有代码必须遵循的规则，doctor 是其中第一个强制执行者。

## AI 助手编排协议（v0.2.0 新增）

当 `skill_use("rdd-doctor")` 被调用时，AI 助手（OpenCode / Claude Code / Cursor / etc.）**必须**遵循以下流程。**用户不需要手工跑任何命令行**——AI 会执行。

### Step 1 — 收集 findings

```bash
bash skills/rdd-doctor/scripts/doctor.sh --json
```

解析 `.rddf/state/.doctor-report.json`（或 stdout）得到 findings 列表。如果 AI 是被 `guide` 推荐器调起的，可以用 `--category <name>` 缩小范围。

### Step 2 — 展示给用户

按严重度分组展示：

```
=== CRITICAL (N) ===
  ❌ [category] file:line — snippet
      Fix: hint
=== WARNING (N) ===
  ⚠️ ...
=== INFO (N) ===
  ℹ️ ...
```

**不允许**默默跳过任何严重度。CRITICAL 必须显眼（用户问题严重）。

### Step 3 — 询问用户授权

```
检测到 N 个 findings。要修复吗？
  y — 全部修
  n — 不修（仅记录）
  p — 选择性修（用户逐个标）
```

**铁律**：**用户没明确授权前，禁止执行任何修复**。"修" 意味着调用会写文件的命令（rddf migrate-improvements 等），不是只读的 doctor 本身。

### Step 4 — 执行修复（按 category 映射）

| finding.category | 修复动作（AI 调用）|
|------------------|---------------------|
| `migration-residue` | `rddf migrate-improvements [--include-docs] [--allow-source-repo]`（dry-run → 确认 → 跑）|
| `state`（schema drift）| 提示用户重跑对应 phase（doctor 没有执行动作） |
| `plan-tdd`（缺 step marker） | 提示手工补全或 reject plan |
| `proposal-table`（列数不符） | 提示手工调整表格格式 |
| `tasks-checkbox` | 提示运行 execute 或手工 fix tasks.md |
| `roadmap-meta`（manual_deps drift）| 提示手工调整或重跑 plan |
| `arch-audit`（gap-analysis drift / draft / ADR status 漂移 / arch-handoff 异常） | 全部为 **advisory 无写操作**：gap-analysis 骨架漂移提示手工补全或重跑 rdd-arch Phase 3；gap-analysis draft 提示手工策展；ADR status 漂移提示手工 finalize；arch-handoff 异常提示重跑 rdd-arch。无可执行 `rddf` 命令——落入 Step 5.5 的 `only-no-action` 终止分支 |

**所有写操作必须先 `--dry-run`**，让用户看到会改什么再决定。例如：

```bash
# 不直接跑 rddf migrate-improvements
rddf migrate-improvements --dry-run --include-docs
# 展示输出给用户
# 用户确认后
rddf migrate-improvements --include-docs
```

**合并**：同 category 的多个 findings 合并为一次执行（migrate-improvements 一次跑就能修所有 migration-residue）。

### Step 5 — 验证 + 循环

修复完成后**必须**再跑一次 doctor，确认 findings 清零：

```bash
bash skills/rdd-doctor/scripts/doctor.sh
```

#### Step 5.5 — 迭代循环（重要）

**重新扫描不是终点**。修复可能：
- 暴露之前被掩盖的 finding（修一个看见更多）
- 修复本身引入新问题（regression 检测）
- 解锁可修复的下一批 finding（dependency 关系）

**AI 必须循环直到满足以下任一终止条件**：

| 终止条件 | 含义 |
|----------|------|
| ✅ **clean** | 再跑 doctor 0 个 finding |
| 🛑 **user-stop** | 用户主动说"停" / "我来手动处理" / "够了"|
| 🟡 **only-no-action** | 剩余 findings 全部属于"无执行动作"类别（state drift / plan-tdd 缺 step / proposal-table 格式 / tasks-checkbox / roadmap-meta），AI 无可执行命令，提示用户手工处理 |

每次循环回到 **Step 2**（展示新 findings）+ **Step 3**（再次问授权）。**不允许**在一次跑完后宣布"完成"，即使看起来没新问题。

向用户报告每轮循环结果：
- 本轮修了什么（X category / Y finding）
- 累计修了什么
- 当前还剩什么 / 为什么剩

### 循环示例

```
第 1 轮:
  doctor → 3 个 finding (2 migration-residue, 1 proposal-table)
  修复: rddf migrate-improvements --include-docs
  再 doctor → 1 个 finding (proposal-table)

第 2 轮:
  doctor → 1 个 finding (proposal-table)
  AI: 这个类别无可执行动作，提示用户手工调整表格格式
  用户: "我手动改"
  AI: stop iteration

最终状态:
  修了 2 个 migration-residue
  剩余 1 个 proposal-table（用户选择手工处理）
```

### 关键约束

- **doctor 本身永远是只读的** — AI 严禁修改 doctor.py / doctor.sh / *_check.py 来"自动化"修复
- 修复通过**单独的写命令**（rddf migrate-improvements 等）实现，保持单一职责
- **任何用户没明确授权的修复**，禁止执行
- 用户可随时说"只报告不修"，AI 必须尊重

### 第三方纯 CLI 用户（非 AI 助手场景）

无 AI 编排时，rdd-doctor 仍可单独使用：

```bash
bash skills/rdd-doctor/scripts/doctor.sh   # 看报告
rddf migrate-improvements --help          # 找对应 flag
rddf migrate-improvements --dry-run       # 预览
rddf migrate-improvements                 # 执行
```

doctor 的 `Fix:` 行已经写了完整命令，直接复制即可。