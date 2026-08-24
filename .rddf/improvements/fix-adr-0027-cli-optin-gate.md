# fix-adr-0027-cli-optin-gate

**优先级**: P0 | **来源**: Oracle 复核 2026-08-24(G3 + G4 合并)
**阶段**: v2.1.x | **分类**: infra-quality | **类型**: fix

## 架构依据

ADR-0027 §3 规定反馈环三重 opt-in 闸门:`reporting.enabled`(默认 false)、`reporting.auto_submit`(默认 false)、`reporting.submit_categories[<cat>]` 粒度 opt-in,叠加 CI 环境自动降级。§1.0 同时规定两平面(脚本 + agent)都必须经过同意边界。

**Oracle 复核发现的两个组合问题**(审计 2026-08-24, 9m32s, 复核 session `ses_fcd821b6dffec9xoFJ515aq5Eo`):

### G3(同意边界绕过)— CLI 路径不经 opt-in 直接外发

**事实**:
```python
# _lib/cli/report_issue_cmd.py:55-57
if not parsed.no_submit:
    gh_repo = os.environ.get("RDDF_REPORT_GH_REPO", "chisuhua/rdd-workflow")
    submit = submit_issue_via_gh(file_path, parsed.category, gh_repo)
    # ↑ 直接 submit,无 RDDF_REPORT_ENABLED / RDDF_REPORT_AUTO_SUBMIT / categories 检查
```

```python
# _lib/cli/issue_cmd.py:64-65 (rddf issue submit)
submit = submit_issue_via_gh(file_path, parsed.category, gh_repo)
```

**对比**:`_lib/post_flow_analysis.py::report_flow_bug` 路径下 `_should_auto_submit()`(342-356 行)做了三重检查;而 CLI 路径**完全跳过**。这违反了 ADR §3 铁律"任何数据外发都需显式 opt-in",也是发布合规风险。

**风险放大**:4 个 phase 的 SKILL.md(gate-arch / guide-plan / guide-design / guide-ship)在 Phase Exit 段指示 agent 在 phase 异常退出时调 `rddf report-issue`。Agent 接受指令时会调用 CLI——CLI 不检查 = agent 平面在零 opt-in 下可触发数据外发。

### G4(agent 平面指令本身不可执行)

**事实**:SKILL.md 文本写的是 `rddf report-issue --phase X --exit <code> "..."`,但 `report_issue_cmd.py:31-42` 的 argparse **只有 `--phase`、`--no-submit`、`--category`,没有 `--exit`**。argparse 未知 flag → exit 2(usage-error)。Agent 照做本来要汇报 flow-bug,反而再制造一个 usage-error。

这解释了 `.rddf/issues/` 8 个样本里 7 个来自 script 平面、1 个是手动测试——**agent 平面从架构上不可用**。

**根因**:ADR-0027 §1.0 规定两平面共用同一 classifier,但**实现**只把同意边界放在 script 平面的 `_should_auto_submit()`,完全遗漏了 CLI 路径;而 agent 平面 SKILL.md 写时也没有人实测 CLI flag 兼容性。

## 范围

### In Scope

1. **PR-1.1**:`_lib/issue_reporter.py::submit_issue_via_gh` 入口加三重 opt-in + CI 检查(单一收束点)。所有现有调用方(`_should_auto_submit`、`report_issue_cmd`、`issue_cmd`)通过此函数**自动**获得保护。
2. **PR-1.2**:`_lib/cli/report_issue_cmd.py` argparse 新增 `--exit-code <N>` 参数(对应 SKILL.md 指令中 `--exit` 的等价物);`write_issue_file` 把它纳入 frontmatter 的 `Metadata` 段。
3. **PR-1.3**:修复 4 个 phase SKILL.md(guide-arch / guide-plan / guide-design / guide-ship)中 Phase Exit 段的 `rddf report-issue` 指令:
   - 把 `--exit <code>` 改为 `--exit-code <code>`(适配 PR-1.2)
   - 增加 `--no-submit`(默认 true,确保 Phase Exit 永不自动外发;用户显式传 `--submit` 才走 L2)
4. **PR-1.4**:`_lib/config.py` 的 `reporting` namespace 校验加 `RDDF_REPORT_ENABLED` / `RDDF_REPORT_AUTO_SUBMIT` env 读取(已部分存在,需验证完整);`_lib/cli/__init__.py` 路由表把 `report-issue` 子命令注册为 `rddf report-issue`(确保被发现)。

### Out of Scope

- **不**改 GDPR/隐私合规设计(ADR §3 三重 opt-in 是合规设计,本提案只补实现)
- **不**新增 sanitizer 规则(已扩展完成,`_lib/loop/sanitizer.py:69-71` 有 `/home/`、`/Users/`、`sensitive_names` 项目名替换)
- **不**改 L1 本地 issue 文件路径/格式(由 `fix-adr-0027-issue-file-frontmatter` 提案处理)
- **不**改 GitHub 提交脚本本身的 gh 调用(`submit_issue_via_gh` 已用 env var 模式,符合 Oracle C1 安全要求)
- **不**引入新依赖

## 关键场景

### 场景 A:agent 报告 phase crash(主场景)

**GIVEN** `guide-ship` Phase 2 execute 结束、exit code = 137(SIGKILL)
**WHEN** SKILL.md Phase Exit 段指示 agent 调 `rddf report-issue --exit-code 137 --no-submit --category phase-crash --phase guide-ship "execute crashed"`
**THEN**
1. argparse 接收全部已知 flag → exit 0
2. `--no-submit` 默认 true → `submit_issue_via_gh` **不调用**
3. 写本地 `.rddf/issues/phase-crash-<hash>.md`,含 `--exit-code 137` 在 metadata
4. stdout 输出 `✅ wrote <path>`(L3 提示,提示用户手动提交)

### 场景 B:用户显式提交到 GitHub

**GIVEN** 用户在本地看到 `.rddf/issues/phase-crash-<hash>.md` 想提交
**WHEN** `RDDF_REPORT_ENABLED=yes RDDF_REPORT_AUTO_SUBMIT=yes rddf issue submit .rddf/issues/phase-crash-<hash>.md`
**THEN**
1. `issue_cmd::cmd_issue` 校验 `RDDF_REPORT_ENABLED=yes` → 通过
2. 校验 `RDDF_REPORT_AUTO_SUBMIT=yes` → 通过
3. 校验文件 frontmatter 的 `category` 在 `submit_categories` 列表 → 通过
4. 校验 `CI != true` → 通过(本地)
5. `submit_issue_via_gh` 通过单一收束点实际提交,exit 0,`submitted: true` 写回 frontmatter

### 场景 C:用户误配置(三重 opt-in 缺一)

**GIVEN** 用户没设 `RDDF_REPORT_AUTO_SUBMIT`(即使 `RDDF_REPORT_ENABLED=yes`)
**WHEN** `rddf issue submit <file>`
**THEN**
1. `submit_issue_via_gh` 直接拒绝并打印提示:L2 opt-out by default,exit 2,非 0
2. 本地 issue 文件**不变**(L1 已写,保留供用户后续手动操作)
3. stderr 提示:`Set RDDF_REPORT_AUTO_SUBMIT=yes AND ensure file category is in RDDF_REPORT_SUBMIT_CATEGORIES`

## 技术约束

### 单一收束点(single choke point)

**所有外发必须**经过 `submit_issue_via_gh`。禁止任何调用方绕开(防遗漏)。约定注释:
```python
# 任何新增上报调用方必须经此函数;若新增直接 gh issue create 调用,
# 请先 patch 此函数的 opt-in 检查。详见 ADR-0027 §3 + fix-adr-0027-cli-optin-gate。
def submit_issue_via_gh(...) -> SubmitResult:
    ...
```

### opt-in 检查实现契约

```python
def _check_opt_in_gate(category: str, parsed_cli_args, config: ReportingConfig) -> OptInVerdict:
    """Return (allowed: bool, reason: str, downgrade_to: Literal['L1','L3'])"""
    # 1. enabled?
    if not config.enabled:
        return (False, "L2 disabled by .rddf.json::reporting.enabled", "L1")
    # 2. auto_submit?
    if not config.auto_submit:
        return (False, "auto_submit disabled", "L1")
    # 3. category 粒度?
    if category not in config.submit_categories:
        return (False, f"category '{category}' not in submit_categories", "L1")
    # 4. CI 探测?
    if is_ci_environment():
        return (False, "CI detected; L2 auto-downgraded to L1", "L1")
    # 5. CLI override: --no-submit?
    if getattr(parsed_cli_args, "no_submit", False):
        return (False, "user passed --no-submit", "L3")
    return (True, "", "L2")
```

### 环境变量名(沿用 Oracle C1 约束)

- `RDDF_REPORT_ENABLED` (yes/no)
- `RDDF_REPORT_AUTO_SUBMIT` (yes/no)
- `RDDF_REPORT_SUBMIT_CATEGORIES` (逗号分隔 list, 默认 `flow-bug,gate-failure,phase-crash`)
- `RDDF_REPORT_GH_REPO` (默认 `chisuhua/rdd-workflow`)
- `RDDF_PROJECT_ROOT` (路径解析根)

新增:
- `RDDF_REPORT_CLOSE_ON_ARCHIVE` (default yes) — 配合 `fix-adr-0027-close-hook-dead-code`

### argparse 兼容 matrix(必须 100% 向后兼容)

| 现有用法 | 保留? | 备注 |
|---------|------|------|
| `rddf report-issue "desc"` | ✅ | 不变 |
| `rddf report-issue --category flow-bug "desc"` | ✅ | 不变 |
| `rddf report-issue --no-submit "desc"` | ✅ | 不变 |
| `rddf report-issue --phase X "desc"` | ✅ | 不变 |
| **新增** `rddf report-issue --exit-code 137 "desc"` | ➕ | 写 metadata |
| **新增** `rddf report-issue --submit "desc"` | ➕ | 显式覆盖 --no-submit 默认 |

## 验收标准

### 功能验收

- [ ] **AC-1**:`rddf report-issue --phase X --exit-code 137 "desc"` 执行 exit 0(`--exit-code` 不再触发 argparse error)
- [ ] **AC-2**:未设 `RDDF_REPORT_ENABLED=yes` 时,`rddf report-issue` 不调 `gh`、仅写本地文件、stdout 提示 L1-only
- [ ] **AC-3**:已设 `RDDF_REPORT_ENABLED=yes` 但 category 不在 `RDDF_REPORT_SUBMIT_CATEGORIES`,exit 2 且 stderr 明确提示(不静默 no-op)
- [ ] **AC-4**:`CI=true rddf report-issue --no-submit=false ...` 在 CI 环境自动降级为 L1,不调 `gh`(即使 env 全部设对)
- [ ] **AC-5**:4 个 SKILL.md Phase Exit 段改为 `--exit-code` 且默认 `--no-submit`(确认 PR-1.3 改完)
- [ ] **AC-6**:`submit_issue_via_gh` 函数 docstring 含 single choke point 警告注释(防未来散落)

### 测试

- [ ] 3 unit 测试(闸门 on/off × CLI 两路径)
  - `tests/unit/test_issue_reporter_optin.py`:
    - `test_opt_in_disabled_writes_local_only`
    - `test_opt_in_enabled_category_not_in_list_rejects_with_exit_2`
    - `test_ci_environment_auto_downgrades`
- [ ] 1 unit 测试(argparse `--exit-code` 接收)
  - `tests/unit/test_report_issue_cli.py::test_exit_code_flag_accepted`
- [ ] 1 regression 测试(防未来散落)
  - `tests/unit/test_single_choke_point.py`:grep `from issue_reporter import` + `gh issue create` 等 pattern,禁止 cli/ 路径直接调 gh
- [ ] 修正 1 个现有测试(`test_cli_reporter.py` 可能依赖旧行为,需更新 fixture)

### 兼容性

- 不破坏现 `.rddf/issues/` 8 个样本(仅追加 frontmatter,不改路径/命名)
- 不修改 `_lib/post_flow_analysis.py::report_flow_bug`(它已经过 `_should_auto_submit`,自动继承新检查)

## 依赖

- **阻塞**:无
- **被阻塞**:无(独立 PR,可最先落地)
- **后续**:与 PR-2 配对验证 end-to-end(自动 close hook 修复后,完整 Detect→Buffer→Report→Triage→Close 才能跑通)

## 相关 ADR/文档

- [ADR-0027 §1.0](docs/adr/ADR-0027-continuous-evolution-feedback-loop.md) 两平面建模
- [ADR-0027 §3](docs/adr/ADR-0027-continuous-evolution-feedback-loop.md) 三重 opt-in 铁律
- [Oracle 复核记录 2026-08-24](docs/architecture/improvement-check-mechanisms.md#五oracle-复核) §5.3 G3/G4
- 父文档:[improvement-check-mechanisms.md](docs/architecture/improvement-check-mechanisms.md)
