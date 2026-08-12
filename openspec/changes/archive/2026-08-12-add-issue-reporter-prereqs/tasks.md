# Tasks: add-issue-reporter-prereqs

## 1. Sanitizer 扩展 ($HOME 路径 + 项目名)

- [ ] 1.1 写 failing test: `/home/user/proj/main.py:42` → `<REDACTED>/main.py`
- [ ] 1.2 写 failing test: `/Users/bob/repo/lib.py` → `<REDACTED>/lib.py`
- [ ] 1.3 写 failing test: `/root/etc/config.toml` (root user home) → `<REDACTED>/config.toml`
- [ ] 1.4 写 failing test: 项目名脱敏（`/home/alice/my-secret-proj/` → `<REDACTED>`）
- [ ] 1.5 在 `_lib/loop/sanitizer.py` 的 `SENSITIVE_PATH_PATTERNS` 新增三类 home 路径 regex
- [ ] 1.6 在 `_lib/loop/sanitizer.py` 的 `SENSITIVE_NAME_PATTERNS` 新增项目名 regex（从 env 或 default 推断）
- [ ] 1.7 更新 docstring 第 1-19 行说明三类规则
- [ ] 1.8 跑 `pytest tests/unit/test_sanitizer_home_path.py` 验证 4/4 pass
- [ ] 1.9 跑 `pytest tests/unit/test_sanitizer.py` 验证 8/8 旧 test 不 regression

## 2. Config namespace 扩展 (reporting)

- [ ] 2.1 写 failing test: `Config().reporting.enabled == False` (默认)
- [ ] 2.2 写 failing test: `RDDF_REPORT_ENABLED=yes` env 覆盖后 `config.reporting.enabled == True`
- [ ] 2.3 写 failing test: 加载无 `reporting` 段的 `.rddf.json` 校验通过
- [ ] 2.4 写 failing test: `submit_categories` 字段类型校验（dict[str, bool]）
- [ ] 2.5 在 `_lib/config.py::DEFAULTS` 新增 `reporting` section（含 7 字段默认值）
- [ ] 2.6 在 `_lib/config.py` 新增 4 个 env var mapping: `RDDF_REPORT_ENABLED` / `RDDF_REPORT_AUTO_SUBMIT` / `RDDF_REPORT_CLOSE_ON_ARCHIVE` / `RDDF_REPORT_DESTINATION`
- [ ] 2.7 在 `_lib/schemas/config_schema.json` 顶层 `properties` 新增 `reporting` 子对象
- [ ] 2.8 跑 `pytest tests/unit/test_config_reporting.py` 验证 4/4 pass
- [ ] 2.9 跑 `pytest tests/unit/test_config.py` 验证旧 test 不 regression

## 3. Dedup_hash 模块 (_lib/issue_dedup.py)

- [ ] 3.1 写 failing test: `normalize_for_hash("/home/alice/proj/main.py:42") == "<REDACTED>/main.py"`
- [ ] 3.2 写 failing test: 数字归一化 `port=8080` → `port=N`、`PID 12345` → `PID N`
- [ ] 3.3 写 failing test: 时间戳归一化 `2026-08-12T10:00:00Z` → `TS`
- [ ] 3.4 写 failing test: 平台字串剥离（`Linux 5.4.0` 移除）
- [ ] 3.5 写 failing test: 跨机器稳定性（同 category + error + 3 frames 在 5 个不同 machine/path 产生同一 hash）
- [ ] 3.6 写 failing test: hash 长度固定 8 字符
- [ ] 3.7 新建 `_lib/issue_dedup.py`，实现 `normalize_for_hash(text)` 5 条规则
- [ ] 3.8 在同文件实现 `compute_dedup_hash(category, error_message, stack_frames)`，内部用 `hashlib.sha256(...).hexdigest()[:8]`
- [ ] 3.9 跑 `pytest tests/unit/test_issue_dedup.py` 验证 6/6 pass

## 4. 集成验证

- [ ] 4.1 跑 `pytest tests/unit/test_sanitizer_home_path.py tests/unit/test_config_reporting.py tests/unit/test_issue_dedup.py` 全部通过
- [ ] 4.2 跑 `./test.sh --unit` 验证现有 unit test 无 regression
- [ ] 4.3 跑 `openspec validate add-issue-reporter-prereqs --type change --json` 0 errors
- [ ] 4.4 检查 `_lib/loop/sanitizer.py` 与 `_lib/config.py` 的 diff 仅含扩展性变更

## 5. Commit

- [ ] 5.1 `git add _lib/loop/sanitizer.py _lib/config.py _lib/schemas/config_schema.json _lib/issue_dedup.py tests/unit/test_sanitizer_home_path.py tests/unit/test_config_reporting.py tests/unit/test_issue_dedup.py`
- [ ] 5.2 `git commit -m "feat(reporter): add issue reporter prerequisites

Implements ADR-0027 §C3, §8, §4:
- Sanitizer: add \$HOME path + project name redaction
- Config: add 'reporting' namespace with RDDF_REPORT_* env vars
- Dedup: new _lib/issue_dedup.py with normalize_for_hash()

TDD: 14 unit tests (4 sanitizer + 4 config + 6 dedup), 0 regression."`
- [ ] 5.3 （change-b 解锁后）`openspec archive add-issue-reporter-prereqs --yes`
