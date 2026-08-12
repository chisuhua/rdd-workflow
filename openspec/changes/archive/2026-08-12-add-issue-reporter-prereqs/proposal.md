# add-issue-reporter-prereqs

> **优先级**: P0 (前置依赖)
> **来源**: ADR-0027 实施拆分
> **关联**: `docs/adr/ADR-0027-continuous-evolution-feedback-loop.md` §C3, §8, §4 dedup_hash

## Why

ADR-0027（持续演进反馈环）的 §6.4 失败容忍、§4 dedup_hash 跨机器稳定性、§3 L1 默认 buffer 都依赖 3 个前置能力在 `_lib/` 中已就绪：

1. **`_lib/loop/sanitizer.py` 扩展** — 现有 sanitizer 只覆盖 `/etc/`、`~/.ssh/`、`~/.aws/` 路径。issue 上报需要进一步脱敏 `$HOME` 绝对路径（`/home/<user>/...`、`/Users/<user>/...`、`<root>/...`）和项目名（避免用户名/项目名随 stack trace 外发）。这是 `auto_submit` 启用前的**硬前置条件**（ADR-0027 §C3, §In Scope line 487）。

2. **`_lib/config.py` 新增 `reporting` namespace** — ADR-0027 §8 决策复用现有配置栈。`reporting.enabled` / `reporting.auto_submit` / `reporting.close_on_archive` 等键需注册到 `config_schema.json`，否则无法被现有 schema 校验。

3. **新增 `_lib/issue_dedup.py::normalize_for_hash()`** — ADR-0027 §4 dedup_hash 跨机器稳定性要求 5 条归一化规则（路径→basename、行号删除、数字→N、时间戳→TS、平台字串剥离）。这是防"同问题每台机器产生不同 hash → dedup 失效"的核心不变量。

**为什么独立成一个 change**: 3 项都"阻塞 change-b 的 reporter 主功能"，且各自独立可测可回滚。合并实施但拆分 tasks.md 的 3 个独立 section。

## What Changes

**In Scope**:

- **`_lib/loop/sanitizer.py` 扩展**：新增 `$HOME` 绝对路径与项目名替换规则；扩展 `SENSITIVE_PATH_PATTERNS` 与 `SENSITIVE_NAME_PATTERNS` 两类；保持现有 `/etc/`、`~/.ssh/`、`~/.aws/` 行为不变。
- **`_lib/config.py::Config` 扩展**：新增 `reporting` section 默认值 + `RDDF_REPORT_*` env var 自动注入。
- **`_lib/schemas/config_schema.json` 扩展**：在 `properties` 顶层新增 `reporting` 子 schema（含 `enabled`、`destination`、`auto_submit`、`submit_categories`、`close_on_archive`、`retention_days`、`redact_patterns` 7 个字段）。
- **新增 `_lib/issue_dedup.py`**：导出 `normalize_for_hash(text: str) -> str` 与 `compute_dedup_hash(category: str, error: str, stack: list[str]) -> str` 两个公共函数。
- **新增 `tests/unit/test_sanitizer_home_path.py`**：≥3 个 test 覆盖 `/home/user/`、`/Users/user/`、`<root>/` 三类 home 路径脱敏。
- **新增 `tests/unit/test_config_reporting.py`**：≥3 个 test 覆盖 reporting namespace 默认值、env var 覆盖、schema 校验。
- **新增 `tests/unit/test_issue_dedup.py`**：≥5 个 test 覆盖 5 条归一化规则 + 跨机器稳定性。

**Out of Scope**:

- 不实现 reporter 主功能（`change-b`）
- 不实现 close hook（`change-b`）
- 不写 integration tests（`change-c`）
- 不写文档（`change-c`）
- 不修改现有 sanitizer 已有路径规则
- 不修改 `RDD_REPORT_*` 历史 env var 兼容（项目当前无此 env var 使用）

### 关键场景

- GIVEN `_lib/loop/sanitizer.py` 已扩展, WHEN 调用 `sanitize("/home/alice/proj/main.py:42")`, THEN 返回 `<REDACTED>/main.py`（basename + 行号）
- GIVEN `_lib/loop/sanitizer.py` 已扩展, WHEN 调用 `sanitize("stack in /Users/bob/repo at 2026-08-12")`, THEN 返回 `<REDACTED>/repo at TS`
- GIVEN `_lib/config.py` 已扩展, WHEN 用户设置 `RDDF_REPORT_ENABLED=yes`, THEN `config.reporting.enabled == True`
- GIVEN `_lib/schemas/config_schema.json` 已扩展, WHEN 加载无 `reporting` 段的 `.rddf.json`, THEN 默认值生效，schema 校验通过
- GIVEN `_lib/issue_dedup.py` 已实现, WHEN 同一错误在不同机器的 stack 传入, THEN dedup_hash 相同
- GIVEN 错误信息含 PII（API key、密码）, WHEN normalize_for_hash 处理, THEN 这些 token 被脱敏后再 hash（防止 PII 进入 hash 而被搜索）

## Capabilities

### 1. Sanitizer 扩展

- MUST 新增 `$HOME` 绝对路径检测模式：`/home/<user>/...`、`/Users/<user>/...`、`/root/...`（Linux/macOS/root 三种）
- MUST 新增项目名检测模式（从 `git config --get remote.origin.url` 或 `os.path.basename(project_root)` 派生）
- MUST 保持现有 `/etc/`、`~/.ssh/`、`~/.aws/` 规则行为不变（不破坏现有 Tribunal 评审链路）
- MUST 在 `_lib/loop/sanitizer.py` 顶层 docstring 更新三类（API key / password / path+name）说明
- MUST 提供 ≥3 unit test 验证三类 home 路径都被脱敏

### 2. Config namespace 扩展

- MUST `_lib/config.py::Config` 类的 `DEFAULTS` dict 新增 `reporting` section 默认值
- MUST `_lib/schemas/config_schema.json` 顶层 `properties` 新增 `reporting` 子对象 schema
- MUST 支持 `RDDF_REPORT_ENABLED`、`RDDF_REPORT_AUTO_SUBMIT`、`RDDF_REPORT_CLOSE_ON_ARCHIVE`、`RDDF_REPORT_DESTINATION` 4 个 env var 自动覆盖
- MUST 提供 ≥3 unit test 覆盖默认值、env 覆盖、schema 校验

### 3. Dedup_hash 模块

- MUST 新增 `_lib/issue_dedup.py` 文件
- MUST 导出 `normalize_for_hash(text: str) -> str` 函数
- MUST 导出 `compute_dedup_hash(category: str, error_message: str, stack_frames: list[str]) -> str` 函数
- MUST 实现 5 条归一化规则：路径→basename、行号删除、数字→N、时间戳→TS、平台字串剥离
- MUST 同一 category + error + 3 帧 stack 在不同机器/时间/路径下产生相同 hash
- MUST 提供 ≥5 unit test 覆盖归一化、跨机器稳定性、长度裁剪

## Impact

- 影响文件：
  - 修改: `_lib/loop/sanitizer.py`（新增 ~30 行 patterns + docstring 更新）
  - 修改: `_lib/config.py`（新增 ~15 行 reporting defaults + env var mapping）
  - 修改: `_lib/schemas/config_schema.json`（新增 ~30 行 reporting schema）
  - 新增: `_lib/issue_dedup.py`（~60 行）
  - 新增: `tests/unit/test_sanitizer_home_path.py`（~50 行）
  - 新增: `tests/unit/test_config_reporting.py`（~60 行）
  - 新增: `tests/unit/test_issue_dedup.py`（~80 行）
- 兼容性：所有现有依赖 sanitizer / config 的代码保持不变（向后兼容）
- 风险：低 — 纯扩展性变更，5 个新 test file + 1 个新 module

## Acceptance

- `tests/unit/test_sanitizer_home_path.py` 全部通过（≥3 cases）
- `tests/unit/test_config_reporting.py` 全部通过（≥3 cases）
- `tests/unit/test_issue_dedup.py` 全部通过（≥5 cases）
- 现有 `_lib/loop/sanitizer.py` 的 8 个 test 全部保持通过（无 regression）
- 现有 `_lib/config.py` 的相关 test 全部保持通过
- `openspec validate add-issue-reporter-prereqs --type change --json` 0 errors
- commit message 符合 conventional commit（`feat(reporter): add issue reporter prerequisites`）
- TDD 5 步证据：每个 module 都有"先 failing test → 实现 → test pass"的过程可追溯
