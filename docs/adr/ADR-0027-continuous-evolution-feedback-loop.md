# ADR-0027: 持续演进反馈环（Continuous Evolution Feedback Loop）

> **状态**: 已采纳
> **日期**: 2026-08-12
> **决策者**: sisyphus
> **Oracle 复核**: PASS-WITH-MINOR-FIXES (2026-08-12, 8/8/7 评分) — 详见 fix-adr-0027-cleanup change

## Context

rdd-workflow 已经发布多个版本（v1.0 → v2.0 → v2.1），拥有：

- 14 个子技能（`skills/`）
- 130+ 已归档的 self-change（`openspec/changes/archive/`）
- 22 个历史 ADR（`docs/adr/`）
- `docs/architecture/historical-evolution.md` 维护演进记录

但**没有结构化的反馈环**：第三方项目在生产环境使用 rdd-workflow 时遇到的流程问题，依赖用户主动提 issue 或私下反馈；维护者/贡献者只能从 `proposal-suggestions.md` 看到自己提的改进，看不到真实使用中的故障模式。

这种**信息不对称**导致：

1. **演进驱动靠直觉而非真实证据**：哪些流程痛点最常见？没有量化数据。
2. **修复响应延迟**：用户遇到 bug 后，要么不提（沉默多数）、要么找不到合适渠道。
3. **dogfooding 闭环缺失**：rdd-workflow 自己运行时的故障（如 `rdd-doctor` 报 CRITICAL、gate 失败、phase crash）同样没有自动上报机制。
4. **issue 与 proposal/ADR 断裂**：GitHub 上的 issue 与 `openspec/changes/<name>/proposal.md`、`docs/adr/ADR-NNNN-*.md` 没有双向追溯链路。

**架构依据**:

- ADR-0003 §2.1: 三阶段架构（arch → plan → ship）+ ADR-0025 扩展为四阶段
- ADR-0007 §3: 门控机制（error/warning 两级）
- ADR-0018: arch_quality_gate + ADR-0019: change_arch_alignment
- ADR-0016 §4: arch-handoff 契约（v1 schema + fallback 链）
- `_lib/loop/sanitizer.py`: 已有的数据脱敏模块（API key/密码/`/etc/`、`~/.ssh/`、`~/.aws/`）— **待扩展** `$HOME` 路径与项目名替换规则（前置依赖，详见 §C3）
- `docs/architecture/extension-points.md`: 贡献者扩展指南
- `docs/architecture/historical-evolution.md`: 演进记录样式

## Decision

我们引入**持续演进反馈环（Continuous Evolution Feedback Loop）**，由 5 个环节组成：

```
┌─────────────────────────────────────────────────────────────────┐
│  [1.Detect] ─→ [2.Buffer] ─→ [3.Report] ─→ [4.Triage] ─→ [5.Close] │
│      ↑                                                            │
│      │                                                            │
│      └────────────────── Archive closes issue ──────────────────┘│
└─────────────────────────────────────────────────────────────────┘
   检测             本地兜底      分层提交        提案化           闭环追溯
```

### 1. 检测（Detect）— post-flow-analysis 触发模型

#### 1.0 两平面架构（必读）

rdd-workflow 的 phase **不是**统一可执行进程，存在两种根本不同的运行时形态：

| 平面 | 范围 | 进程边界 | 失败信号 |
|------|------|---------|---------|
| **Script 平面** | `execute` skill + 所有 per-skill bash 脚本（`skills/*/scripts/*.sh`、`_lib/*.sh`）| ✅ 真实 OS 进程 | exit_code / stderr / traceback / FileNotFoundError / TimeoutExpired |
| **Agent 平面** | `guide-arch` / `guide-plan` / `guide-ship` SKILL.md（agent 逐轮执行 Markdown 状态机）| ❌ 无进程边界（agent 在 turn 中结束）| agent 观察到 gate 硬失败 / 状态机分支错误 / 无法继续 |

**影响**：classifier 必须从两个数据源接收输入：
- **Script plane** → bash trap `ERR` 包装器（`skills/_lib/post_flow_wrap.sh`）捕获 exit_code + stderr，调用 `python3 -m _lib.post_flow_analysis --phase X --exit-code N --stderr-file F`
- **Agent plane** → SKILL.md 指令 agent 在 phase 异常结束时调 `rddf report-issue --category <flow-bug|gate-failure|phase-crash> --phase <name> "<description>"`（agent 自分类，绕开 classifier）

两平面共用同一个 `_lib/post_flow_analysis.classify_phase_outcome`（agent plane 调 `detect_issue` 直接传 category，绕开 classification）。

**关键边界**：`rdd-doctor` **不是** reporter 的触发点。rdd-doctor 是**静态扫描**（检查 `.rddf.json` / schema / config 文件是否符合要求），其 CRITICAL finding 是**第三方项目的本地配置问题**，应在本地用 `rdd doctor --fix` 修复，**不上报**到上游 rdd-workflow issue tracker。

#### 1.0.1 未来扩展 (Python orchestrator, spec 2026-08-12)

`skills/_lib/orchestrator_entry.sh` 提供 `rddf orchestrate` 包装器，由 `RDDF_USE_ORCHESTRATOR=yes` 启用。补 4 个盲区：

- **B1**: 任何子脚本（无需 source wrapper）都可被 orchestrator 捕获
- **B2**: agent 不调 finalize 时，下次 entry 扫盘检测 stale trace
- **B3**: 多步骤累积失败（exit 0 但 stderr 含 invalid state）通过 analyze_phase_trace 检测
- **B4**: SIGKILL/OOM 留下未 finalize 的 trace，下次 entry 触发 `phase-interrupted` 报告

迁移条件：本仓库 dogfood 2 周零误报后 flip 默认值。

#### 1.1 类别清单

reporter 处理的类别（区分两平面）：

| 类别 | 含义 | 触发平面 | 上报？ |
|------|------|---------|--------|
| `flow-bug` | rdd-workflow 自身 bug（逻辑错误、状态机错误、archive 失败）| 两平面都触发 | ✅ |
| `gate-failure` | gate 逻辑错误（**不是**用户配置错；是 ADR-0007/0018/0019 自身实现问题）| 两平面都触发 | ✅ |
| `phase-crash` | phase 抛未捕获异常 / exit code 非 0 且非环境/用法原因 | Script 平面（agent 平面通过 `flow-bug` 表达）| ✅ |
| `manual` | 用户显式 `rddf report-issue "<desc>"` | Agent 平面（CLI）| ✅ |
| `usage-error` | 用户用错（错参数、错顺序、缺 flag）| 两平面都识别 | ❌ **不收集** |
| `environment-error` | 缺工具 / 网络 / 权限 / 磁盘满 | 两平面都识别 | ❌ **不收集** |

#### 1.2 三段式判定（Script 平面 classifier）

```
phase exit_code != 0  AND  exit_code NOT IN {130, 143}  (排除 SIGINT/SIGTERM)
  │
  ├─[1] usage-error？  →  UI 提示 "用法：...，参考 docs/..."，不报
  │    判据: stderr 匹配 re(r"usage: .*\[-|error: (unrecognized arguments|argument .*(is required|invalid|expected))", re.I)
  │         OR argparse.ArgumentError raised
  │         OR exit_code == 2 (rdd CLI handler convention)
  │         OR stderr 匹配 re(r"(run \S+ first|missing required (argument|flag)|先执行)", re.I)
  │
  ├─[2] environment-error？  →  退出 + "需要 X / Y 工具 / 网络 / 权限"，不报
  │    判据: FileNotFoundError 缺 gh|git|openspec|bats|python3
  │         OR PermissionError on path OUTSIDE project tree
  │         OR TimeoutExpired / 网络错误 (Could not resolve host|Connection refused)
  │         OR No space left on device
  │         OR stderr 匹配 re(r"(requires|需要).*(version|版本).*(openspec|git|python|bats)")
  │
  └─[3] flow-bug（默认 fail-open）  →  reporter 上报
       判据: stderr 含 "Traceback" 且帧在 _lib/ 或 skills/
            OR ConfigError surfaced as crash（schema 自身错）
            OR stderr 匹配 re(r"(invalid state|unexpected (status|phase)|状态机)")
            OR bash helper exit non-zero with no U/E match
            OR (无任何 U/E 匹配 AND 非 exit 130/143)  ← 兜底
```

fine-grained 映射：`F1`（traceback in `_lib/`）→ `phase-crash`；`F4-gate`（gate raised）→ `gate-failure`；其他 `F` → `flow-bug`。

**In Scope**（本 ADR 实施范围内）:
- `_lib/post_flow_analysis.py` 三段式 classifier（Script 平面）
- `skills/_lib/post_flow_wrap.sh` bash trap wrapper（Script 平面）
- 4 个 phase entry 脚本 + `execute` 各加 1 行 trap（Script 平面）
- 4 个 phase SKILL.md 各加 "Phase Exit" 段（Agent 平面指令）
- `cli/report_issue_cmd.py` + `cli/issue_cmd.py`（manual 类别 + list/show）
- 单元测试 ≥15 + bats 集成测试 ≥6
- rdd-doctor 边界回归测试（doctor 跑完不写 `.rddf/issues/`）

**Out of Scope**:
- gate 自身实现（ADR-0007/0018/0019 范围）
- rdd-doctor 改造
- ADR-0017 冲突解决器扩展

**Out Scope**（不纳入 reporter 类别，**也不在 post-flow-analysis 里上报**）:
- `rdd-doctor` 的 CRITICAL / WARNING / INFO — 这是**本地诊断工具**，不是 flow 问题
- `usage-error` — UI 提示即可，不收集
- `environment-error` — 退出 + 诊断，不收集
- ADR-0017 4 选项冲突解决器扩展（需独立 ADR 修改 rddf-session）

### 2. 缓冲（Buffer）— 离线/失败安全网

检测到的问题**先**写入本地 issue 文件，**再**异步/同步尝试提交到 GitHub：

- **路径**: `.rddf/issues/<category>-<8char-hash>.md`
- **格式**: 标准 Markdown issue body（见 §4）
- **内容**: 通过 `_lib/loop/sanitizer.py` 脱敏（API key、密码、`/etc/`、`~/.ssh/`、`~/.aws/`）。**需先扩展 sanitizer**: 新增 `$HOME` 绝对路径（`/home/<user>/...`、`/Users/<user>/...`）与项目名替换规则 — 现有规则**不覆盖**这些（验证 `_lib/loop/sanitizer.py` lines 1-19）。在 sanitizer 扩展完成前，issue 文件**不应自动提交**，仅写本地
- **失败容忍**: 网络失败、`gh` CLI 缺失、GitHub 5xx → 全部仅写本地文件 + 终端提示用户

**新增状态文件**: `.rddf/state/.issue-reporter.json`（gitignored，结构同 `.env-cache.json`）

```json
{
  "schema_version": 1,
  "last_reported_at": "2026-08-12T10:00:00Z",
  "local_hashes": ["a1b2c3d4", ...],
  "submitted_hashes": ["e5f6g7h8", ...],
  "buffer_size": 3
}
```

**新增 schema**: `_lib/schemas/issue_reporter_schema.json`（与现有 10 个 schema 同目录；沿用 ADR-0016 v1 schema 风格）

### 3. 上报（Report）— 分层提交策略

| 层级 | 触发条件 | 行为 |
|------|---------|------|
| **L1: 本地优先** | 永远 | 写 `.rddf/issues/<file>.md` |
| **L2: gh CLI 提交** | `gh` 在 PATH + `gh auth status` OK + `RDDF_REPORT_AUTO_SUBMIT=yes` + `submit_categories[<cat>]: true` + **非 CI 环境** (`CI != true`) | `gh issue create --repo chisuhua/rdd-workflow --label auto-reported,<category>,needs-triage --title "<title>" --body-file <path>`（三重 label: 自动来源 + 类别 + 待 triage，与 §5 查询的 AND 语义对齐） |
| **L3: 仅本地 + 提示** | 默认（`gh` 缺失或未认证） | 输出"已写本地文件，运行 `rddf issue submit <file>` 或手动粘贴到 https://github.com/chisuhua/rdd-workflow/issues/new" |

**默认配置**（在 `.rddf.json` 的 `reporting` namespace 下可覆盖，或通过 `RDDF_REPORT_*` env var 覆盖；不存在时使用以下默认值 — 与 §8 复用 `_lib/config.py` 的决策一致）：

```yaml
reporting:
  enabled: false                # 必须显式 opt-in（默认不上报任何东西）
  destination: github           # github | local | custom-url
  custom_repo_url: ""           # 当 destination=custom-url 时使用（如 GitLab 自托管）
  auto_submit: false            # 必须显式 opt-in（默认仅写本地）
  submit_categories:            # 分类粒度 opt-in (只对真正 flow 问题类别)
    flow-bug: true
    gate-failure: true
    phase-crash: true
    manual: true
  close_on_archive: true        # archive 时自动 close issue（默认 true，需 dry-run 可关闭）
  retention_days: 30            # .rddf/issues/ 中已 close 的文件保留天数
  redact_patterns:              # 额外正则脱敏（叠加 _lib/loop/sanitizer.py）
    - "(?i)api[_-]?key\\s*[:=]\\s*\\S+"
    - "(?i)secret\\s*[:=]\\s*\\S+"
```

**铁律**:
- `enabled: false`（默认）+ `auto_submit: false`（默认）+ 分类开关 = 三重 opt-in 闸门
- 任何数据外发都需要用户在 config 中显式声明
- 第一次启用时打印一次性 banner: "Heads up: rdd-workflow will now report **pseudonymous** issues to github.com/chisuhua/rdd-workflow (project_hash links reports from the same project). Disable by setting `RDDF_REPORT_ENABLED=no` or `.rddf.json::reporting.enabled = false`."

### 4. Issue 格式（上报契约）

`.rddf/issues/<category>-<8char-hash>.md` 文件结构：

```markdown
---
category: doctor-critical
detected_at: 2026-08-12T10:00:00Z
rdd_workflow_version: 2.0.9
dedup_hash: a1b2c3d4
submitted: false
submitted_url: null
---

## Description

<自动生成的单行描述，如 "rdd-doctor: state schema drift detected — 3 files stuck on schema_version 0">

## Reporter

- rdd-workflow: 2.0.9
- openspec CLI: 1.3.1
- python: 3.11.4
- git: 2.34.1
- os: linux
- project_hash: 7f8e9d0c            # sha256(project_root)[:8]
- rddf_session_id: ses_abc123      # 仅当 rddf-session 启用时
- skill_invoked: rdd-doctor         # 哪个 skill 触发的上报

## Stack trace / details

```
<sanitized stack trace via _lib/loop/sanitizer.py>
<CRITICAL finding snippets from rdd-doctor>
<gate failure details>
```

## Repro

<自动生成或用户输入的最小复现步骤>

## Reporter commit

<sha of rdd-workflow when this was reported — 用于追溯哪个版本引入了 bug>
```

**dedup_hash 算法**: `sha256(category + normalized_error_message + first_3_normalized_stack_frames)[:8]`

**归一化规则**（必须满足跨机器稳定性；未归一化会导致每台机器一个 hash，dedup 失效）:
- 绝对路径 → basename（如 `/home/alice/proj/src/foo.py` → `foo.py`）
- 行号删除（如 `foo.py:42` → `foo.py`）
- 连续数字归一为 `N`（如 `port=8080` → `port=N`、`PID 12345` → `PID N`）
- 时间戳归一为 `TS`（如 `2026-08-12T10:00:00Z` → `TS`）
- 平台相关字串（`linux`/`darwin` 字符串本身从 stack 中剥离 — OS 信息单独记录在 Reporter 段）

归一化在 `_lib/issue_reporter.py::normalize_for_hash()` 中实现并配 ≥5 个 unit test。

**属性**:
- 相同问题在不同机器/时间/路径 → 同一 dedup_hash → 只产生 1 个 issue
- 跨进程纯函数（无需中心化状态）
- 8 字符 = 32 bits；碰撞概率 1/2^32（≈ 43 亿），对个人项目量级可接受；同 hash 文件按多份保留

**GitHub issue title 模板**: `[<category>] <description truncated 60 chars> (<dedup_hash>)`

例: `[flow-bug] state schema drift detected — 3 files on v0 (a1b2c3d4)`

### 5. Triage — guide-design / guide-arch 消费 issue

**guide-design 改造**（v2.1+）：

新增 Phase 2 菜单选项：

```
设计阶段 - 提案管理

📂 提案池:
  - 待审查: N 个
  - 已归档(自动批准): M 个
  - 已推迟: K 个
  - 📨 来自上游 issue: J 个          ← 新增

选择操作:
  1. ➕ 创建新提案（add-improve 交互式创建）
  2. 📋 审查待批准提案
  3. ✅ 批量批准所有提案
  4. 📨 triage 上游 issue              ← 新增
  5. ✅ 完成设计阶段 → 进入设计门控
  0. 💾 保存并退出
```

选项 4 流程：

```bash
# 1. 拉取未 triage 的 issue（自动 + 手动双源）
gh issue list --repo chisuhua/rdd-workflow \
  --label "auto-reported,needs-triage" --state open --json number,title,body,labels

# 2. 对每个 issue 展示给用户
echo "Issue #123: state schema drift detected (3 reports)"
echo "Category: flow-bug | Hash: a1b2c3d4 | Reporter count: 3"
echo "---"
cat body
echo "---"

# 3. 用户选择（每个动作完成后必做：移除 needs-triage label 避免重 triage）
y → 调用 skills/guide-design/scripts/issue_to_proposal.sh 生成 proposal 草稿
   + gh issue edit <num> --remove-label needs-triage --add-label triage-in-progress
n → gh issue comment --body "Not actionable: <reason>" + close
   + gh issue edit <num> --remove-label needs-triage --add-label not-actionable
d → 标记 needs-design（延期）
   + gh issue edit <num> --remove-label needs-triage --add-label deferred
s → 跳过（保持原 label，下次 triage 再处理）

# 4. issue_to_proposal.sh 预填 proposal.md 模板
#    - 标题: <从 issue title>
#    - Why: <从 issue body + Reporter 段>
#    - 影响范围: 用户确认
#    - 验收标准: 用户输入
#    - issue_refs: [123]                  ← 新字段
```

**新增字段 `issue_refs`**（在已存在的 `openspec/changes/<name>/roadmap-meta.yaml` 中；proposal 关联走 `proposal.md` 正文 `> **issue_refs**: [123]` 块引用 — **`proposal-meta.yaml` 当前不存在**，新建须列入 In Scope 并指定 schema 所有方，本 ADR 不引入）：

```yaml
# roadmap-meta.yaml （已存在的 per-change metadata 文件）
issue_refs: [123]              # GitHub issue 编号列表
gh_repo: chisuhua/rdd-workflow # issue 所在仓库（支持 fork）

# proposal.md frontmatter / 块引用扩展（沿用 ADR 模板的 blockquote 风格）
> **issue_refs**: [123]
> **gh_repo**: chisuhua/rdd-workflow
```

**guide-arch 改造**（v2.1+）：

当创建新 ADR 时，允许在 frontmatter 中关联 issue（沿用 ADR-0000 模板的 blockquote header 风格 — 仓库全部 26 个 ADR 均无 YAML frontmatter）：

```markdown
# ADR-0028: <title>

> **状态**: 待定
> **日期**: YYYY-MM-DD
> **决策者**: <name(s)>
> **issue_refs**: [789]              ← 新增（ADR-0000 模板同步扩展）
> **gh_repo**: chisuhua/rdd-workflow ← 新增

## Context
...
```

`adr_refs` extractor（`skills/deps.md` Step 1b）扩展支持 `issue_refs` 字段提取，写入 `deps-analysis.json` 的 `issue_links` 节点，供后续 close 流程使用。

### 6. Close — archive 时自动关闭 issue

`guide-ship` Phase 3 在归档成功后，调用新建的 `skills/_lib/close_issues.sh::close_issues_for_change` 完成 issue 关闭：

#### 6.1 双模式覆盖（关键）

close hook **必须**在两条路径都生效（与 `archive_gate_check` 的双模式约定一致，见 AGENTS.md）：

| 模式 | 触发函数 | hook 插入点 |
|------|---------|-----------|
| **worktree 模式** | `_lib/archive.sh::archive_change` | `openspec archive` 之后（line 340）、`cleanup_worktree_and_branch` 之前（line 346） |
| **lightweight 模式** | `skills/guide-ship/scripts/ship_archive.sh::archive_change_for_mode` 的 inline 分支 | `openspec archive` 之后、`commit_archive_moves` 之前 |

两个插入点都调用同一个 `close_issues_for_change` 函数，避免逻辑分叉。

#### 6.2 权限边界（C1 关键修复）

`gh issue close` 需要目标 repo 的 **写权限** — 第三方用户对 `chisuhua/rdd-workflow` 没有写权限。因此 close hook **先做权限探测**：

```python
# skills/_lib/close_issues.py::can_close_in_repo(gh_repo: str) -> bool
# 通过 gh api 检查当前认证用户在目标 repo 的 push 权限
result = subprocess.run(
    ["gh", "api", f"repos/{owner}/{repo}", "--jq", ".permissions.push"],
    capture_output=True, text=True, timeout=10
)
return result.stdout.strip() == "true"
```

- **可写**（maintainer / fork owner / 同仓库 dogfooding）→ 正常 close
- **不可写**（第三方用户 close 上游 issue）→ 输出 `[issue] #123 fixed in <change>; please close manually: <URL>` 提示用户**自行关闭**（或由 maintainer 在 review 时批量关闭）
- **未认证 `gh`** → 仅本地标记，不尝试关闭

#### 6.3 实现骨架

```bash
# skills/_lib/close_issues.sh (新增)
# 依赖：gh 在 PATH + python3（用 PyYAML 读 yaml，不用 yq）

close_issues_for_change() {
    local change_name="$1"
    local roadmap_meta="${PROJECT_ROOT}/openspec/changes/${change_name}/roadmap-meta.yaml"
    [ -f "$roadmap_meta" ] || return 0  # 无 issue_refs = 跳过
    [ "${RDDF_REPORT_CLOSE_ON_ARCHIVE:-yes}" = "yes" ] || return 0

    # 1. 解析 issue_refs（python + PyYAML，零新增依赖）
    local issue_refs
    issue_refs=$(RDD_ROADMAP_META_PATH="$roadmap_meta" \
        python3 -c '
import os, yaml, json
data = yaml.safe_load(open(os.environ["RDD_ROADMAP_META_PATH"]))
refs = data.get("issue_refs", [])
gh_repo = data.get("gh_repo", "chisuhua/rdd-workflow")
print(json.dumps({"refs": refs, "gh_repo": gh_repo}))
')
    local gh_repo
    gh_repo=$(echo "$issue_refs" | python3 -c 'import sys,json; print(json.load(sys.stdin)["gh_repo"])')

    # 2. 权限探测（C1 修复）
    if ! RDD_GH_REPO="$gh_repo" python3 -c '
import os, subprocess, sys
r = subprocess.run(["gh", "api", f"repos/{os.environ[\"RDD_GH_REPO\"]}", "--jq", ".permissions.push"],
                   capture_output=True, text=True, timeout=10)
sys.exit(0 if r.stdout.strip() == "true" else 1)
'; then
        log_warn "No push permission to $gh_repo; cannot auto-close issues"
        log_warn "Manually close: ${issue_refs}"  # 输出 issue URL 给用户
        return 0
    fi

    # 3. 关闭（幂等 + 失败容忍）
    # env-var 必须前置（命令行后置会变成 argv，不是 environment）
    RDDF_ISSUE_DATA="$issue_refs" RDDF_CHANGE_NAME="$change_name" RDDF_NEW_VERSION="${RDD_NEW_VERSION:-next}" \
    python3 -c '
import os, json, subprocess, sys
data = json.loads(os.environ["RDDF_ISSUE_DATA"])
gh_repo = data["gh_repo"]
short_sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
version = os.environ.get("RDDF_NEW_VERSION", "next")
change_name = os.environ["RDDF_CHANGE_NAME"]
for num in data["refs"]:
    # 幂等检查
    state = subprocess.run(["gh", "issue", "view", str(num), "--repo", gh_repo, "--json", "state", "-q", ".state"],
                          capture_output=True, text=True).stdout.strip()
    if state == "CLOSED":
        print(f"[skip] issue #{num} already closed")
        continue
    # 关闭
    comment = f"✅ Fixed in rdd-workflow v{version} via archive {short_sha}.\n\nSee: openspec/changes/{change_name}/\n"
    r = subprocess.run(["gh", "issue", "close", str(num), "--repo", gh_repo, "--comment", comment],
                       capture_output=True, text=True)
    if r.returncode == 0:
        print(f"[closed] issue #{num}")
    else:
        print(f"[warn] failed to close #{num}: {r.stderr.strip()}", file=sys.stderr)
'
    # subprocess 失败被脚本忽略，不阻断 archive（与 _lib/post_archive_cleanup.sh line 415 `|| true` 同模式）
    return 0
}
```

#### 6.4 幂等性 / 失败容忍 / 追溯完整性

- **幂等**: `gh issue view --json state` 检查后 skip 已 CLOSED 项
- **失败容忍**: 整个 `close_issues_for_change` 在 `archive_change` 中以 `|| true` 调用，网络/gh 失败不阻断 archive 主体
- **本地状态同步**: 关闭成功后，按 `dedup_hash` 精确更新对应的 `.rddf/issues/<cat>-<hash>.md` 文件（不是全量 sed）— 由同一 python 脚本处理
- **追溯完整**: comment 包含 change 名、commit SHA、rdd-workflow 新版本号

### 7. 双向追溯矩阵

| 资产 | 引用 issue 的方式 | issue 引用资产的方式 |
|------|-----------------|---------------------|
| `openspec/changes/<name>/proposal.md` | 块引用 `> **issue_refs**: [N]` | issue body: "Repro" 段提到 change 名 |
| `openspec/changes/<name>/roadmap-meta.yaml` | `issue_refs: [N]` + `gh_repo` 字段 | — |
| `docs/adr/ADR-NNNN-*.md` | 块引用 `> **issue_refs**: [N]`（与现有 ADR 模板的 blockquote header 风格一致） | issue body: "Related ADR" 段（issue_to_proposal 自动填充） |
| `.rddf/issues/<file>.md` | `submitted_url` 字段记录 issue URL | — |
| `CHANGELOG.md` | 新版本段落 "Fixes #N" | — |
| commit message | `Closes #N` (auto-appended by archive hook) | — |

### 8. 配置与发现

**决策**: **复用**现有 `_lib/config.py` 多源配置栈（`loop.yaml` → `.rddf.json` → `RDDF_*` env → defaults），把 `reporting` 作为新 namespace 并入 `config_schema.json`。**不**新建独立的 `.rddf/config.yaml`。

**理由**:
- `_lib/config.py` 已实现 schema 校验 + 多源 fallback（被 `guide-arch`/`guide-plan`/`guide-ship` 入口读取）
- 新建并行系统会引入第二份配置发现逻辑、schema 校验、env var 命名空间冲突
- 复用统一前缀 `RDDF_REPORT_*` env var 即可（与现有 `RDDF_*` 家族一致）

**加载顺序**（沿用 `_lib/config.py` 既有约定）:

```
loop.yaml 默认段 < .rddf.json 覆盖 < RDDF_REPORT_* env var 覆盖 < 命令行 --report-* flag 覆盖
```

**配置发现契约**（仿 ADR-0016 arch-handoff）：

- 路径: `.rddf/state/.reporting-config.json`（gitignored）— 解析后的有效配置缓存
- 内容: `{ enabled, destination, auto_submit, submit_categories, close_on_archive, retention_days }`
- 缓存 TTL: 3600s（同 `.env-cache.json`，详见 `add-env-cache-arch-discovery`）
- 缓存失效：branch 切换、`.rddf.json` mtime 变化、`RDDF_REPORT_*` env 变化

### 9. CI 环境抑制（关键安全门）

**`auto_submit` 在 CI 环境强制降级**：

CI runner 通常携带作用域受限的 `GH_TOKEN`，自动开 issue 会污染上游 + 触发 GitHub abuse detection。L2 提交前检查：

```python
if os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true":
    if config["auto_submit"]:
        log_warn("CI detected; auto_submit downgraded to L1 (local-only)")
        # 仍写本地文件，用户/CI 后处理阶段可手动 rddf issue submit
```

**适用范围**: L2（GitHub 提交）+ close hook（需要 `gh` 写权限，CI 里 token 通常仅读）
**L1（本地 issue 文件）不受影响**：CI 仍会写 `.rddf/issues/*.md`，开发者事后 review + 手动提交

**新增 env 探测**: `_lib/issue_reporter.py::is_ci_environment()` 检查 `CI`、`GITHUB_ACTIONS`、`JENKINS_URL`、`BUILDKITE`、`CIRCLECI` 等 6 个常见 CI 标识。

### 10. 数据流总览

```
┌────────────────┐  detect    ┌───────────────┐
│ rdd-doctor     │──────────→ │ IssueReporter │──┐
│ Gate (error)   │            │ (singleton)   │  │
│ Phase crash    │            └───────────────┘  │
│ Manual rddf    │                     │         │
│ Conflict UI    │                     ▼         │
└────────────────┘            ┌────────────────┐│
                              │ Sanitizer      ││
                              │ (脱敏 + 去敏感) ││
                              └────────────────┘│
                                         │       │
                                         ▼       │
                              ┌────────────────┐ │
                              │ .rddf/issues/  │←┘ (always)
                              │ <cat>-<hash>   │ │
                              │ .md (Markdown) │ │
                              └────────────────┘ │
                                         │       │
                                         ▼       │
                              ┌────────────────┐ │
                              │ L2: gh issue   │ │ (opt-in)
                              │ create ...     │ │
                              └────────────────┘ │
                                         │       │
                                         ▼       ▼
                              ┌────────────────────────┐
                              │ GitHub                  │
                              │ chisuhua/rdd-workflow   │
                              │ Issues                  │
                              └────────────────────────┘
                                         ▲
                                         │ close
                                         │
                              ┌────────────────────────┐
                              │ archive_change (Phase3)│
                              │ issue_refs → close     │
                              └────────────────────────┘
                                         ▲
                                         │
                              ┌────────────────────────┐
                              │ guide-design Phase 2   │
                              │ Triage 选项 4          │
                              │ issue → proposal draft │
                              └────────────────────────┘
```

### 影响范围

**In Scope**:

- 新增模块: `_lib/issue_reporter.py`（核心 reporter + sanitizer 扩展）+ `_lib/close_issues.py`（close hook 业务逻辑）+ `skills/_lib/close_issues.sh`（bash 入口，通过 shim 调用）
- 新增 schema: `_lib/schemas/issue_reporter_schema.json`（与现有 10 个 schema 同目录）
- **配置复用**: `_lib/config.py` 现有栈新增 `reporting` namespace + `config_schema.json` 同步扩展（**不**新建独立 `.rddf/config.yaml`）
- 改造 skill: `guide-design`（Phase 2 菜单 + `issue_to_proposal.sh`）、`guide-arch`（blockquote header `issue_refs`）、`guide-ship`（双模式 close hook）
- 改造 ADR 模板: `docs/adr/ADR-0000-template.md` 扩展 blockquote header 加入 `issue_refs` / `gh_repo` 字段
- 改造 `_lib/loop/sanitizer.py`: 新增 `$HOME` 绝对路径（`/home/<user>/...`、`/Users/<user>/...`）与项目名替换规则（**前置依赖**，完成前不允许 auto_submit）
- 改造 `_lib`: `_lib/archive.sh::archive_change`（worktree 模式 hook）+ `skills/guide-ship/scripts/ship_archive.sh::archive_change_for_mode`（lightweight 模式 hook）— 双模式覆盖
- `.gitignore`: 新增 `.rddf/issues/`
- 改造 docs: `docs/architecture/extension-points.md`（新增"添加上报触发点"小节）、`docs/architecture/historical-evolution.md`（新增 v2.1.x 条目）
- 新增 CLI: `rddf report-issue "<desc>"`, `rddf issue submit <file>`, `rddf issue list`, `rddf issue show <hash>` — 复用 `_lib/cli/` 现有路由表
- 新增 state 文件: `.rddf/state/.issue-reporter.json`、`.rddf/state/.reporting-config.json`
- 新增 retention 机制: `retention_days: 30` 由 `_lib/issue_reporter.py::prune_old_issues()` 在每次 reporter 启动时执行（按 `submitted` + `closed_at` 字段清理；未提交文件**不**自动删除，避免数据丢失）
- 新增 CI 探测: `_lib/issue_reporter.py::is_ci_environment()`（6 个 CI 标识）+ L2 强制降级
- 新增 rdd-env-check 检测: `.rddf/state/.env-cache.json` 新增 `gh_available` 字段（best-effort，不阻塞 phase 入口）
- 测试: `tests/unit/test_issue_reporter.py`（≥15 cases，含 hash normalization ≥5 cases、sanitizer extension ≥3 cases、CI detection ≥2 cases）、`tests/integration/test_feedback_loop.bats`（≥8 cases，覆盖 worktree + lightweight 双模式）
- 文档: `docs/architecture/extension-points.md`、`docs/architecture/historical-evolution.md`、CHANGELOG.md（v2.1.x 条目）

**Out Scope**:

- 不做 issue 内容的人工编辑界面（用户跑 `rddf issue show <hash>` 看本地 Markdown 即可）
- 不做 issue 状态看板（用 GitHub 原生 UI）
- 不做跨仓库 issue 同步（fork 用户自己改 `gh_repo` 配置）
- 不做实时 issue 流（每 24h pull 一次足够）
- 不改 `rdd-doctor` 内部（只在外部 wrap 上报 hook）
- 不改 gate 内部机制（只 hook 失败事件）
- 不影响 WARNING 级报告（噪音过滤）
- **不做** rate-limiting（GitHub 默认 5000 req/h 对单项目足够；如出现 abuse 后续单独 ADR）
- **不引入**新 skill `rddf-reporter`（CLI 走现有 `_lib/cli/` 路由，避免新增 17th skill 引发 smoke-test + install.sh 同步成本）

### 备选方案

| 备选 | 评估结果 |
|------|---------|
| **A. Webhook collector**（maintainer 自托管服务收集 issue） | ❌ 拒绝 — 增加运维负担；rdd-workflow 是工具不是 SaaS |
| **B. 邮件列表**（report 直接发邮件到 maintainer） | ❌ 拒绝 — 邮件难结构化；issue tracker 是事实标准 |
| **C. Sentry / 错误监控平台** | ❌ 拒绝 — 引入第三方依赖；隐私风险更高；本场景不是运行时错误 |
| **D. 仅本地 issue 文件**（不连 GitHub） | ⚠️ 备选保留 — 如果 GitHub API 长期不稳定可降级到此模式；当前不推荐因为闭环断裂 |
| **E. 默认 opt-out**（不配置即上报） | ❌ 拒绝 — 隐私红线；任何数据外发必须显式 opt-in |
| **F. 双层缓存（Redis + 本地）** | ❌ 拒绝 — 增加部署复杂度；本地 JSON 已足够 |

## Consequences

### 正面

- **真实证据驱动演进**：`rdd-doctor --json` 累积的统计 + `issue_refs` 在 archive 中的 close 率 → 维护者有量化数据决定优先级
- **沉默故障可视化**：WARNING 级不上报避免噪音，但 CRITICAL/gate-failure/phase-crash 自动上报 → 用户无需主动汇报也能被发现
- **完整双向追溯链**：issue → ADR/proposal → archive commit → release notes → close issue，单向链路完整
- **dogfooding 闭环**：rdd-workflow 仓库自己的 `.rddf/issues/` 自动捕获 self-bug，发现即上报
- **隐私友好**：三重 opt-in + sanitizer + project_hash 假名化（pseudonymous，跨 issue 关联）+ 不强制 gh 认证
- **离线/降级友好**：网络失败、gh 缺失、GitHub 5xx 全部降级为本地文件，不破坏用户流程

### 负面 / 风险

- **GitHub 单点依赖**：上报和 close 都依赖 `github.com/chisuhua/rdd-workflow` 可达性
  - **缓解**: 本地文件兜底 + `destination: custom-url` 支持 fork/GitLab
- **dogfooding 噪音**：rdd-workflow 仓库自己的 reporter 可能高频触发（开发阶段）
  - **缓解**: 默认 `enabled: false`，开发者在 `.rddf.json` 的 `reporting` namespace 或 `RDDF_REPORT_*` env 显式开启
- **issue 标题碰撞**：8 字符 hash 有 1/16^8 ≈ 1/4B 概率碰撞
  - **缓解**: L2 提交前先 `gh issue list --search "<dedup_hash>" --state all` 查重；GitHub **不去重标题**，已存在则 comment "另一次上报: <reporter_count++>" 而非新建（重复 issue 会触发 GitHub spam heuristic）
- **依赖 `_lib/loop/sanitizer.py` 进化**：脱敏规则必须持续更新
  - **缓解**: `redact_patterns` 配置项允许项目自定义额外规则
- **CI 成本增加**：`gh` CLI 调用 + 新增 tests
  - **缓解**: L1 永远不依赖 gh；L2 仅 opt-in 时启用
- **issue 与 proposal/ADR 双向同步复杂**：用户可能编辑了 issue body 导致 link 断裂
  - **缓解**: 双向字段是 reference 而非 mirror（链接足够）

### 后续待办

**前置依赖**（必须先完成，否则禁止发布 `auto_submit` 默认 ON）:

- [ ] **待修复**: 扩展 `_lib/loop/sanitizer.py` 新增 `$HOME` 路径与项目名替换规则（≥3 unit tests）
- [ ] **待修复**: 扩展 `_lib/config.py` 与 `config_schema.json` 加入 `reporting` namespace
- [ ] **待修复**: 实现 `dedup_hash` 归一化函数 `normalize_for_hash()`（≥5 unit tests，覆盖路径/行号/数字/时间戳归一化）

**主体功能**:

- [ ] **待修复**: 编写 `_lib/issue_reporter.py` + `skills/_lib/close_issues.{py,sh}`（首个 PR 核心）
- [ ] **待修复**: 扩展 `roadmap-meta.yaml` schema 支持 `issue_refs`（`proposal-meta.yaml` **不**新建 — 用 proposal.md 块引用）
- [ ] **待修复**: 扩展 `docs/adr/ADR-0000-template.md` 加入 `issue_refs` blockquote header
- [ ] **待修复**: 编写 `guide-design` triage 菜单（Phase 2 选项 4）+ `issue_to_proposal.sh`
- [ ] **待修复**: 双模式 close hook 插入（`_lib/archive.sh` worktree + `ship_archive.sh` lightweight）
- [ ] **待修复**: 新增 `.gitignore` 条目 `.rddf/issues/`
- [ ] **待修复**: `_lib/cli/` 路由表新增 `report-issue` / `issue` 子命令

**测试与文档**:

- [ ] **待修复**: 编写 ≥15 unit + ≥8 integration tests（覆盖 worktree + lightweight 双模式）
- [ ] **待修复**: 更新 `extension-points.md`（"添加上报触发点"小节）
- [ ] **待修复**: 更新 `historical-evolution.md`（v2.1.x 条目）
- [ ] **待修复**: CHANGELOG.md 新增 Unreleased 段记录本 ADR

**暂不修复 / 未来**:

- [ ] **暂不修复**: 跨平台 issue（GitLab/Gitea）— 等用户需求出现
- [ ] **暂不修复**: 实时 issue 拉取流 — 24h 手动 pull 足够
- [ ] **暂不修复**: rate-limiting（GitHub 默认 5000 req/h 对单项目足够）
- [ ] **暂不修复**: ADR-0017 第 5 选项 "report upstream"（需独立 ADR 修改 rddf-session）
- [ ] **未来参考**: issue 数据可视化（哪些 category 最频繁？哪些 rdd-workflow 版本引入最多 bug？）

## References

- `docs/proposal-suggestions-format.md` — 提案格式规范
- `docs/adr/ADR-0000-template.md` — ADR 模板（待扩展 `issue_refs` blockquote header）
- `docs/adr/ADR-0007-gate-mechanism.md` §3 — 门控 error/warning 两级（`gate-failure` 类别判定参考）
- `docs/adr/ADR-0016-arch-artifact-discovery-contract.md` §4 — handoff schema 风格
- `docs/adr/ADR-0018-arch-quality-gate.md` — arch_quality_gate 上报契约
- `docs/adr/ADR-0019-change-arch-alignment.md` — change_alignment 上报契约
- `docs/adr/ADR-0024-deps-driven-execution-mode.md` §3 — handoff 写入模式（仿 `.plan-handoff.json`）
- `docs/adr/ADR-0025-design-proposal-creation.md` §5 — guide-design Phase 2 菜单结构（新增 triage 选项）
- `docs/architecture/extension-points.md` — 扩展指南（待更新"添加上报触发点"小节）
- `docs/architecture/historical-evolution.md` — 演进记录（待更新 v2.1.x 条目）
- `_lib/loop/sanitizer.py` — 数据脱敏（**待扩展**：新增 `$HOME` 路径与项目名替换规则）
- `_lib/config.py` — 多源配置栈（**复用**：新增 `reporting` namespace）
- `_lib/cli/__init__.py` — 路由表（**复用**：新增 `report-issue` / `issue` 子命令）
- `_lib/archive.sh::archive_change` — close hook 插入点（worktree 模式，verified line 340/346）
- `skills/guide-ship/scripts/ship_archive.sh::archive_change_for_mode` — close hook 插入点（lightweight 模式，verified line 231/237）
- `_lib/post_archive_cleanup.sh` — 失败容忍模式参考（`|| true` 包裹）
- `AGENTS.md` "archive_gate_check 双模式约定" — close hook 必须双模式覆盖
- `docs/adr/ADR-0010-multi-session-management.md` §3 — 多会话管理（rddf_session_id 作为 issue 关联字段 — **注意**: ADR-0017 的冲突解决器不直接触发上报，本 ADR 仅引用 session 字段做 issue 关联）
- `tests/integration/test_global_install_external_project.bats` — 第三方项目集成测试模式