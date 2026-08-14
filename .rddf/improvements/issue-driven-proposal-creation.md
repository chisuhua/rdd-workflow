# issue-driven-proposal-creation

**优先级**: P1 | **来源**: Oracle 评估（2026-08-13，9 维度深度分析）+ 当前 proposal 创建通路缺口
**阶段**: v2.1+ | **分类**: arch-design
**类型**: feature
**主题**: 不适用（自由模式）
**状态**: 已推迟 (2026-08-14) — 等 fix-generator-scope-extraction 落地后重新评估 (generator 当前会产出 Capabilities/Impact 重复 + Out Scope (TBD) 的破损 proposal.md)

## 架构依据

**现状缺口**：
- rdd-workflow 当前只有 2 条 proposal 创建路径：`add-improve` 头脑风暴（free 模式）+ `propose` 差距扫描
- 用户无法从当前项目的 GitHub issue 直接生成 proposal
- 第三方项目用户看不到自己项目 issue 与 rdd-workflow 提案的关联
- rdd-workflow 自身维护者也无法用 issue backlog 作为提案源
- 项目 README/USAGE 中也未提及"基于 issue 创建提案"这条路径

**现有基础**（无需重建）：
- **ADR-0027 §5/§7**：`_lib/issue_reporter.py`（上游 bug 上报）、`_lib/close_issues.py`（archive close hook）、`gh_repo` schema 字段、`issue_refs` 字段均已实现并测试
- **`add-improve` skill**：已有 `free` 与 `from-roadmap`（v2.2）两种 scaffold 模式，结构可直接复用（bash wrapper + Python 主逻辑 + env-var 契约）
- **`guide-design` Phase 2 菜单结构**：稳定且有扩展空间（ADR-0025）
- **proposal-suggestions.md / proposal-approved.md 双索引**：可追加新提案

**Oracle 评估**（2026-08-13）：
- 阶段归属：✅ `guide-design` Phase 2（与用户直觉一致）
- 实现方式：扩展 `add-improve` 加 `--from-issue` 模式（参照 from-roadmap）
- 提案落地：单一入口池 = `.rddf/improvements/`（不区分 rdd-workflow self vs 第三方）
- Effort: Medium（1-2d）
- ADR：新建 ADR-0028（不 amend ADR-0027）

**风险/前置修复**：
- Oracle 发现 `_lib/close_issues.py:180` comment 模板硬编码 "Fixed in rdd-workflow"——本提案落地后 archive 时会写到第三方 repo，必须一并修复。

## 范围

### In Scope

**A. 新增 scaffold 模式**：
- `skills/add-improve/scripts/from_issue.sh` — bash wrapper，env-var 契约（uppercase snake，trap cleanup EXIT）
- `skills/add-improve/scripts/from_issue.py` — 主逻辑：repo 检测 → issue fetch → dedup → scaffold → 注册
- `skills/_lib/gh_repo_detect.py` — 共享检测模块（env > `gh repo view` > git remote parse）

**B. UI 入口**：
- `skills/guide-design/SKILL.md` Phase 2 菜单新增"🐙 从 GitHub issue 创建提案"选项（编号 3，其他编号顺移）

**C. Schema 复用**：
- 复用 ADR-0027 §7 的 `issue_refs: [N]` + `gh_repo` 字段写入 `.rddf/improvements/<name>.md` frontmatter
- 复用现有 5 段格式（架构依据/范围/关键场景/技术约束/验收标准）

**D. 关联 bug 修复**：
- `_lib/close_issues.py:180` comment 模板去 "rdd-workflow" 字样（repo-neutral 措辞）

**E. 测试**：
- `tests/unit/test_gh_repo_detect.py` — 3 种 fallback 链 + gh 缺失 + auth 失败（pytest + subprocess mock）
- `tests/integration/test_from_issue.bats` — happy path + dedup + slug collision + gh 缺失（bats + PATH stub）

### Out Scope

- ❌ 不重载 `rddf issue list/show` 命名空间（属于本地 `.rddf/issues/` 缓冲，ADR-0027 §10）
- ❌ 不实现 label-based filtering、batch multi-select、closed-issue sync、linked-PR warning（full scope，列入 ADR-0028 后续）
- ❌ 不新增 CLI dispatcher（skill-only MVP）
- ❌ 不修改 ADR-0027 §5 triage menu（保持分离：triage=维护者读上游；本提案=项目用户读本项目）
- ❌ 不实现 proposal 自动检测"是不是 rdd-workflow"——单一入口池策略（`.rddf/improvements/` 永远是入口）

## 关键场景

**场景 1 — 第三方项目 dogfooding**：
- GIVEN: 用户在第三方项目 X 跑 rdd-workflow，X 有 GitHub repo + 开放 issue
- WHEN: 用户在 guide-design Phase 2 选择"从 GitHub issue 创建提案"
- THEN: gh auth status 前置检查通过 → `gh repo view` 检测 X → 列出 open issues（限 30）→ 用户选 N → dedup 通过（双位置扫描）→ 预填 scaffold（title/body 截断 4k/issue_ref/gh_repo）→ brainstorm HARD-GATE 完成 → 落 `.rddf/improvements/<slug>-i<N>.md` + 注册 proposal-suggestions.md

**场景 2 — rdd-workflow self-use**：
- GIVEN: 用户在 rdd-workflow 自身跑 add-improve，看到 `chisuhua/rdd-workflow` 的开放 issue
- WHEN: 选 issue → 创建 proposal
- THEN: 同场景 1 流程，但 `.rddf/improvements/` 检测 signal 命中 rdd-workflow self 模式，proposal 自然落入正确池

**场景 3 — gh 未认证**：
- GIVEN: `gh auth status` 返回非 0
- WHEN: 启动 from-issue 流程
- THEN: 硬退出 exit 2 + stderr 输出 "gh 未认证，请运行 `gh auth login`"（不写任何文件）

**场景 4 — Dedup 命中**：
- GIVEN: Issue #42 已在 `.rddf/improvements/foo.md` frontmatter `issue_ref: 42`
- WHEN: 用户再次尝试 from-issue 42
- THEN: 列出已关联的现有 proposal 文件路径，让用户决定跳过或新建独立 proposal

**场景 5 — Slug 冲突**：
- GIVEN: Issue #10 和 #20 标题类似（slug 相同）
- WHEN: 用户依次创建
- THEN: 第一个落 `foo.md`，第二个落 `foo-i20.md`（确定性可 grep）

**场景 6 — Issue body 超限**：
- GIVEN: Issue body > 4k 字符（含图片附件、复制粘贴大量日志）
- WHEN: 预填 scaffold
- THEN: 截断到 ~4k，剩余内容追加 "... (剩余 N 字符，参见 <issue-url>)"

**场景 7 — env 覆盖**：
- GIVEN: 用户 `export RDDF_PROPOSAL_GH_REPO=myorg/my-fork`
- WHEN: 启动 from-issue
- THEN: 跳过 `gh repo view` 自动检测，直接使用 env 指定值（用于 fork / 跨仓库场景）

## 技术约束

### MUST

- 当前项目 GH repo 检测链（按优先级）：
  1. `RDDF_PROPOSAL_GH_REPO` env（显式覆盖）
  2. `gh repo view --json nameWithOwner` (subprocess + 10s timeout)
  3. `git remote get-url origin` parse + GitHub URL 提取
  4. 失败 → stderr 错误信息 + exit 2（不写文件）
- 前置 `gh auth status` 检查（即使只读，gh CLI 也需要认证）
- Dedup 双重扫描位置：
  - `.rddf/improvements/*.md` frontmatter 的 `issue_ref: N` 字段
  - `openspec/changes/*/roadmap-meta.yaml::issue_refs`
- Slug 生成规则：`kebab-case(title)`，冲突时 append `-i<N>` (issue number)
- Issue body 截断 ~4000 字符，剩余追加 "... (剩余 N 字符，参见 <URL>)"
- env-var 传递模式（参照 add-improve 已有 env.py 模式，禁止 `python3 -c "...$VAR..."` 内联）
- 保留 brainstorm HARD-GATE（与 from-roadmap 一致：scaffold 预填 + brainstorm 完善）
- Proposal 永远落 `.rddf/improvements/`（单一入口池；不区分 rdd-workflow self vs 第三方）
- close_issues.py:180 comment 模板改成 repo-neutral（用 change_name + repo_name，不用 "rdd-workflow" 字面量）

### MUST NOT

- 不回退到 `chisuhua/rdd-workflow` 作为检测 fallback（防止误把第三方 issue 当作上游）
- 不复用 `RDDF_REPORT_GH_REPO` env（那是 ADR-0027 reporter 的上游目标，与本提案语义不同）
- 不重载 `rddf issue list/show` 命令（命名空间冲突，违反命名约定）
- 不修改 ADR-0027 §5 triage menu 代码路径
- 不静默吞错（gh 缺失/未认证/git remote 不可解析 → 硬退出 + 明确错误）

### SHOULD

- `from-issue` / `from-roadmap` / `free` 3 种 scaffold 在 add-improve 内共享 dedup + scaffold write + register 的公共逻辑
- `gh_repo_detect.py` 设计上为 ADR-0027 triage 后续复用留接口（不强制本期采用）
- 检测失败错误信息包含建议命令（如 `gh auth login`、`git remote add origin ...`）
- Issue 列表支持 `--limit 30` 上限 + `--label` 可选过滤（v2.2+ 可扩展）

## 验收标准

### 功能验收

- [ ] `add-improve --from-issue <N>` 在 rdd-workflow 自身能跑通（dogfooding）
- [ ] `add-improve` 无参数时按 Phase 0 模板收集描述
- [ ] guide-design Phase 2 菜单包含新增"从 GitHub issue 创建提案"选项
- [ ] 当前项目 GH repo 检测：env 覆盖 > `gh repo view` > git remote parse 三层均正确
- [ ] Dedup 在 `.rddf/improvements/*.md` + `openspec/changes/*/roadmap-meta.yaml` 双重位置生效
- [ ] Slug 冲突正确生成 `-i<N>` 后缀
- [ ] Issue body >4k 字符正确截断 + 链接保留
- [ ] `gh` 缺失/未认证时硬退出 + 清晰错误

### 关联修复验收

- [ ] `close_issues.py:180` comment 模板去 "rdd-workflow" 字样
- [ ] 修改后 archive 不写"Fixed in rdd-workflow"到第三方 repo

### 测试验收

- [ ] `tests/integration/test_from_issue.bats` 覆盖 happy path + dedup + slug collision + gh 缺失
- [ ] `tests/unit/test_gh_repo_detect.py` 覆盖 3 层 fallback + subprocess mock
- [ ] 与 `from-roadmap` / `free` 并行运行不冲突（共享 env-var cleanup）
- [ ] `./test.sh --full --regression` 全绿后才允许 archive（按 AGENTS.md 全量回归门）

### ADR 验收

- [ ] 新建 `docs/adr/ADR-0028-issue-driven-proposal-creation.md` 记录本次决策
- [ ] 引用 ADR-0025（菜单结构）、ADR-0027 §5（scope 区分）/§7（schema 复用）、ADR-0026（命名空间约定）

## 参考

- `_lib/issue_reporter.py` — 上游 bug 上报（参考 env-var 契约）
- `_lib/close_issues.py:180` — 待修复的 comment 模板
- `skills/add-improve/scripts/from_roadmap.{sh,py,env.py}` — from-issue 的直接模板
- `skills/guide-design/SKILL.md` Phase 2 — 菜单插入点
- `docs/adr/ADR-0027-continuous-evolution-feedback-loop.md` §5/§7 — issue 集成基础
- `docs/adr/ADR-0025-design-proposal-creation.md` — design 阶段菜单结构
- `docs/adr/ADR-0026-internal-metadata-namespace-convention.md` — 元数据命名约定
- Oracle 评估：2026-08-13（9 维度分析，详见对话记录）