# complete-third-party-replay-and-upstream-reporting

## Why

本提案基于以下架构约束和审查结论：

- ADR-0027 continuous evolution feedback loop：运行时失败应先分类，再写入本地 `.rddf/issues/`，最后按策略提交上游。
- ADR-0016 arch discovery contract：工具包安装路径与业务项目路径必须分离，项目布局通过运行时发现而非硬编码。
- ADR-0017 rddf-session：trace/session 必须绑定当前业务项目的 workflow session，不能读取工具包仓库状态。
- 2026-08-13 orchestrator default-ON rollout：默认开启 orchestrator 后，normal finalize 必须形成可审计的报告结果，不能只记录 trace。
- Oracle 审查确认：第三方全局安装场景存在 helper 路径缺失、业务项目根目录误归属、normal finalize 不调用 `report_flow_bug`、`rddf issue`/`rddf report-issue` import 崩溃和 reporting 配置漂移。

核心原则：工具包代码运行在全局安装位置，trace、session、issue 和 archive 状态属于当前第三方业务项目；任何上游提交默认指向 `chisuhua/rdd-workflow`，但必须保留本地 issue 缓冲。

## What Changes

**In Scope**:

- 统一解析工具包根目录和当前业务项目根目录。
- 全局安装和项目安装都能找到 `orchestrator_entry.sh`、`post_flow_wrap.sh` 及相关共享 helper。
- `RDDF_PROJECT_ROOT` 必须指向调用方业务项目，不能由 helper 的 `BASH_SOURCE` 推导为 rdd-workflow 工具仓库。
- `rddf orchestrate show <phase>` 从项目根目录或子目录运行时读取同一份 trace。
- 默认 trace 路径基于业务项目根目录，而不是隐式依赖当前工作目录。
- trace 能保留 phase、session、命令结果、checkpoint、finalize 和报告状态。
- 可报告分类在 finalize 时调用 `report_flow_bug`。
- `report_written` 只有在 issue 文件实际成功写入后才为 true。
- usage-error、environment-error、SIGINT/SIGTERM 不生成 flow-bug issue。
- reporter 失败不阻断原工作流，并保留可诊断 trace/警告。
- 修复 `rddf issue list/show/submit` 和 `rddf report-issue` 的 import 路径。
- CLI 在源码仓库、全局安装和第三方项目中都可运行。
- 本地 issue 先落盘，GitHub 不可用时保留本地记录。
- 上游默认仓库为 `chisuhua/rdd-workflow`，允许显式 `RDDF_REPORT_GH_REPO` 覆盖。
- 统一 auto-submit、category allowlist、GitHub repo 和 archive close 的实际运行时配置。
- 消除未生效的 `config` 参数和 schema/runtime 命名漂移，或明确删除无效配置。
- 手动提交和自动提交遵循一致的 CI、分类和目标仓库策略。
- 第三方项目 archive 时，close hook 能正确导入或明确降级为 manual links。
- 移除 Python 命令中的 bash 字符串插值，并修复版本参数命名/传递问题。
- close hook 失败不得阻断 archive。
- 添加第三方隔离项目的端到端测试，覆盖 trace、issue 和上游提交路径。
- 更新安装文档，说明 `rddf orchestrate show`、trace 位置、`.rddf/issues/`、上游仓库和 opt-in 提交策略。

### 关键场景

- **GIVEN** 第三方 Git 项目已通过全局安装启用 rdd-workflow，**WHEN** 在项目根目录或任意子目录运行 `rddf orchestrate show guide-plan`，**THEN** 显示该业务项目 `.rddf/state/trace/` 中的 phase timeline，而不读取工具包仓库状态。

- **GIVEN** 第三方项目运行 phase 时一个被 `orchestrator_run` 包装的命令失败，**WHEN** phase 正常执行 EXIT finalize，**THEN** trace 包含失败 subprocess 和 finalize，且可报告分类生成一个 `.rddf/issues/<category>-<hash>.md` 文件。

- **GIVEN** 同一失败属于 usage-error、environment-error 或用户主动 SIGINT/SIGTERM，**WHEN** finalize 完成，**THEN** 不生成 flow-bug issue，`report_written` 为 false。

- **GIVEN** 第三方项目存在 `.rddf/issues/phase-crash-<hash>.md`，**WHEN** 用户运行 `rddf issue list`、`rddf issue show <file>` 或 `rddf issue submit <file>`，**THEN** 命令成功运行并读取第三方项目的本地 issue。

- **GIVEN** 用户显式允许上游提交并配置 `RDDF_REPORT_GH_REPO`，**WHEN** issue submit 执行，**THEN** 使用 `gh issue list/create --repo` 操作目标仓库；默认目标为 `chisuhua/rdd-workflow`，不是第三方项目 remote。

- **GIVEN** `gh` 不存在、网络失败或没有上游写权限，**WHEN** 自动或手动提交，**THEN** 本地 issue 文件保留，命令输出可执行的手工提交提示，不阻断 workflow/archive。

- **GIVEN** archive 在第三方项目执行，**WHEN** close hook 无法访问上游 issue，**THEN** archive 主流程成功完成并留下 manual close 信息，不把失败写入工具包仓库。

**Out of Scope**:
- ReflectEngine 与 `issue_reporter` 两套 dedup 系统统一。
- 实时 trace streaming。
- 用 pytest 全面替换 bats。
- 将 L2 GitHub auto-submit 改为默认开启。
- 自动修复第三方项目中的业务配置或用户代码问题。


## Capabilities

- **MUST** 将工具包代码路径和业务项目状态路径作为两个独立概念传递。
- **MUST** 通过调用上下文的 Git 根目录或明确的 `RDDF_PROJECT_ROOT` 解析业务项目根目录，**MUST NOT** 用 helper 自身路径冒充业务项目根目录。
- **MUST** 保持 global install、project install 和源码运行的 Python import 行为一致。
- **MUST** 对 issue description、stack 和可提交的运行输出执行现有 sanitizer；敏感数据不得进入 GitHub issue。
- **MUST** 本地 issue 写入先于 GitHub 提交，GitHub 失败不得丢失本地记录。
- **MUST** 对 auto-submit 保持显式 opt-in 和 category allowlist；本提案不改变 L2 默认关闭策略。
- **MUST** 让 trace 的 `report_written` 反映真实文件写入结果。
- **MUST** 为根目录解析、global install、子目录 replay、normal finalize、CLI submit 和失败降级添加回归测试。
- **MUST NOT** 将 third-party issue 默认提交到第三方项目 remote；上游目标必须是 `chisuhua/rdd-workflow` 或用户显式配置的目标。
- **MUST NOT** 使用 bash 字符串插值构造 Python 代码或命令参数；使用环境变量/argv 传值。
- **SHOULD** 保持 `rddf orchestrate show` 与 `rddf issue` 分离：前者展示原始运行证据，后者管理分类后的 issue artifact。
- **SHOULD** 在工具包缺失、Python/gh 不可用时 fail-open，继续执行原有 phase 并给出诊断信息。

## Impact

- **MUST** 将工具包代码路径和业务项目状态路径作为两个独立概念传递。
- **MUST** 通过调用上下文的 Git 根目录或明确的 `RDDF_PROJECT_ROOT` 解析业务项目根目录，**MUST NOT** 用 helper 自身路径冒充业务项目根目录。
- **MUST** 保持 global install、project install 和源码运行的 Python import 行为一致。
- **MUST** 对 issue description、stack 和可提交的运行输出执行现有 sanitizer；敏感数据不得进入 GitHub issue。
- **MUST** 本地 issue 写入先于 GitHub 提交，GitHub 失败不得丢失本地记录。
- **MUST** 对 auto-submit 保持显式 opt-in 和 category allowlist；本提案不改变 L2 默认关闭策略。
- **MUST** 让 trace 的 `report_written` 反映真实文件写入结果。
- **MUST** 为根目录解析、global install、子目录 replay、normal finalize、CLI submit 和失败降级添加回归测试。
- **MUST NOT** 将 third-party issue 默认提交到第三方项目 remote；上游目标必须是 `chisuhua/rdd-workflow` 或用户显式配置的目标。
- **MUST NOT** 使用 bash 字符串插值构造 Python 代码或命令参数；使用环境变量/argv 传值。
- **SHOULD** 保持 `rddf orchestrate show` 与 `rddf issue` 分离：前者展示原始运行证据，后者管理分类后的 issue artifact。
- **SHOULD** 在工具包缺失、Python/gh 不可用时 fail-open，继续执行原有 phase 并给出诊断信息。

## Acceptance

1. 全局安装模拟第三方项目：`rddf orchestrate show <phase>` 从项目根目录和子目录均能读取相同 trace，且 trace/issue/session 均位于第三方项目 `.rddf/` 下。
2. 四个 phase entry script 在只存在全局安装、第三方项目没有 `skills/_lib/` 副本时，均能找到 helper 并产生 trace/finalize。
3. 失败 subprocess + normal finalize 至少生成一个正确分类的 `.rddf/issues/*.md`，成功/usage/environment/SIGINT 场景不误报。
4. `report_written` 在文件成功写入时为 true，写入失败或不可报告分类时为 false。
5. `rddf issue list/show/submit` 和 `rddf report-issue --no-submit` 在源码、全局安装、第三方项目三种运行方式下成功。
6. 上游提交测试验证默认/显式 repo 均使用 `chisuhua/rdd-workflow` 目标，并通过 dedup hash 避免重复 issue。
7. `gh` 缺失、超时、网络失败和无权限时，命令不阻断工作流，且本地 issue 与手工提示保留。
8. reporting schema、环境变量和运行时行为一致；无效或未实现配置不再静默失效。
9. archive close hook 在第三方项目中成功关闭可关闭 issue，无法关闭时降级为 manual links，且不使用 Python 字符串插值。
10. 安装文档明确说明全局安装、trace 路径、`rddf orchestrate show`、`.rddf/issues/`、上游 issue 目标和 L2 opt-in 策略。
11. 相关 targeted bats/pytest 全部通过；全量回归无新增失败，或明确记录已知环境失败。

