# fix-adr-0027-issue-file-frontmatter

**优先级**: P1 | **来源**: Oracle 复核 2026-08-24(P1-A 强化)+ initial 4 文档 §4 自检
**阶段**: v2.1.x | **分类**: infra-quality | **类型**: fix

## 架构依据

ADR-0027 §4 规定 issue 文件必须含完整 8 段 frontmatter(`category`/`detected_at`/`rdd_workflow_version`/`dedup_hash`/`submitted`/`submitted_url`)+ **Reporter 段**(6 必填字段:python/git/os/project_hash/rddf_session_id/skill_invoked)+ **Stack trace 段**+ **Repro 段**。

**Oracle 复核**与实际 7 个样本对比 (`docs/architecture/improvement-check-mechanisms.md §5.3 G1-A`) 显示当前 `_render_issue_body`(`_lib/issue_reporter.py:117-144`)只渲染:
- ✅ `category`、`detected_at`、`rdd_workflow_version`、`dedup_hash`、`submitted`、`submitted_url` (6/8 frontmatter)
- ⚠️ 单行 "Reporter commit" 但无 sha
- ❌ **整个 Reporter 段缺失**(python/git/os/project_hash/rdff_session_id/skill_invoked)
- ❌ Stack trace 段缺失
- ❌ Repro 段缺失

**严重后果**:

1. **AD 排障成本爆炸**:8 个真实 issue 全部 16 行,维护者拿到 issue body 不知道:
   - 用户用的 Python 哪个版本 → 无法判断 compat
   - rddf-session 是哪个 session 触发的 → 无法跟 rddf-session 关联
   - 哪个 skill 触发的上报 → 无法自动定位根因
2. **ADR §3 假名化关联(pseudonymous linking)被破坏**:`project_hash` 缺失意味着不同 issue 之间的 dedup 退化为"完全相同错误信息",跨 issue 串并联分析无法做
3. **L2 启用前置条件**:文档第一章明确说"L2 上报需要 reporter 段"——现 L1 也缺失,L2 开启后用户拿到的 issue 内容无法被维护者高效处理

## 范围

### In Scope

1. **PR-3.1**:`_lib/issue_reporter.py::_render_issue_body` 改造为完整 8 frontmatter + Reporter 段(6 字段)+ Stack trace 段 + Repro 段
2. **PR-3.2**:扩展 `IssueResult` dataclass 携带新字段:
   - `python_version`(str)— 来自 `sys.version`
   - `git_version`(str)— 来自 `git --version` 或 None
   - `os_platform`(str)— 来自 `platform.platform()`
   - `project_hash`(str)— `sha256(project_root)[:8]`,与 ADR §3 一致
   - `rddf_session_id`(str | None)— 从 `RDDF_SESSION_ID` env 读
   - `skill_invoked`(str)— 调用方传入,例如 `rdd-doctor`、`guide-plan`
3. **PR-3.3**:新增 `_lib/issue_reporter.py::_capture_system_env()` 一次性采集 5 个环境信息(避免每次调用都 fork subprocess)
4. **PR-3.4**:Stack trace 段必须经 `loop.sanitizer.sanitize()` 脱敏(`_lib/loop/sanitizer.py:69-71` 已支持 `$HOME` 路径与项目名替换)
5. **PR-3.5**:`write_issue_file` 接收 `metadata` dict 并序列化到 frontmatter(给 PR-1 `--exit-code` 等扩展字段留接口)

### Out of Scope

- **不**改 L1 issue 文件路径(仍是 `.rddf/issues/<cat>-<hash>.md`)
- **不**改 dedup_hash 算法(继续走 `_lib/issue_dedup.py::compute_dedup_hash`)
- **不**改 retention 策略
- **不**改 `sanitizer.py`(已扩展完成,不重复)
- **不**新增 prisma/git 历史/网络相关 reporter 字段(避免隐私扩大化)
- **不**新增国际化字段(中英 `repro_hint` 等暂用英文)

## 关键场景

### 场景 A:手动 `rddf report-issue`(主场景)

**GIVEN** 用户跑 `rddf report-issue --exit-code 137 --phase guide-ship "execute crashed"`
**WHEN** `_render_issue_body` 执行
**THEN** 生成的 `.rddf/issues/phase-crash-<hash>.md` 含:
```yaml
---
category: phase-crash
detected_at: 2026-08-24T10:23:45Z
rdd_workflow_version: 2.1.0
dedup_hash: a1b2c3d4
submitted: false
submitted_url: null
exit_code: 137
---

## Description

execute crashed

## Reporter

- rdd-workflow: 2.1.0
- python: 3.11.4
- git: 2.34.1
- os: linux
- project_hash: 7f8e9d0c
- rddf_session_id: ses_abc123
- skill_invoked: manual

## Stack trace / details

```
No trace captured (manual report)
```

## Repro

`rddf report-issue --exit-code 137 --phase guide-ship "execute crashed"`
```

### 场景 B:自动 post-flow-analysis 检测(主场景)

**GIVEN** `guide-plan` phase exit code != 0,`post_flow_wrap.sh` 调用 classifier
**WHEN** classifier 标记为 `flow-bug`
**THEN** 生成的 issue 文件:
- `project_hash` 与 reporter 段已填
- Stack trace 段含 `_lib/...py` 经 sanitizer 脱敏的栈帧
- `skill_invoked` 填 `post-flow-analysis`
- `rddf_session_id` 若 rddf-session 启用则填

### 场景 C:字段缺失的优雅降级

**GIVEN** 用户在 CI 环境(无 git config 设置)
**WHEN** 采集 `git_version`
**THEN** 输出 `git: unknown`(不是 raise,不是空字符串)

**GIVEN** 用户未启用 rddf-session(无 `RDDF_SESSION_ID` env)
**WHEN** 读取 `rddf_session_id`
**THEN** 输出 `rddf_session_id: none`(不是 raise)

## 技术约束

### 环境采集必须**单次**完成

`_capture_system_env()` 必须 batch 采集(单次 `subprocess.run(['git', '--version'], capture_output=True)` + 单次 `platform.platform()` + 单次 `sha256`),不允许在 `_render_issue_body` 内多次 fork。

### 字段命名严格匹配 ADR-0027 §4

```yaml
project_hash: <8-char hex>     # 不是 project-hash
rddf_session_id: <ses_...>     # 不是 session_id
skill_invoked: <skill-name>    # 不是 skill
```

### stack trace 处理

```python
def _format_stack(stack: list[str]) -> str:
    raw = "\n".join(stack)
    sanitized = sanitize(raw)  # 来自 loop.sanitizer 已扩展
    return f"```\n{sanitized}\n```" if sanitized else "```\nNo trace captured\n```"
```

### 必须向后兼容(已写入的 8 个 issue 不变)

不修改 `_render_issue_body` 对**已有字段**的渲染;只**新增**字段。现有 `.rddf/issues/flow-bug-*.md` 等 8 个样本**不**重新生成。

## 验收标准

### 功能验收

- [ ] **AC-1**:手动 `rddf report-issue` 生成的 md 含 ADR-0027 §4 全部段
- [ ] **AC-2**:`project_hash` 是 sha256(project_root)[:8](用 `python3 -c "import hashlib; print(hashlib.sha256(b'$PROJECT_ROOT').hexdigest()[:8])"` 验证)
- [ ] **AC-3**:Stack trace 段脱敏后不含 `/home/<user>/`(用 grep 在新生成文件上验证)
- [ ] **AC-4**:rddf-session 未启用时 `rddf_session_id: none`,启用时填 `ses_...`
- [ ] **AC-5**:`skill_invoked` 字段根据调用方填(`rdd-doctor` / `post-flow-analysis` / `manual`)
- [ ] **AC-6**:`metadata` dict 字段(如 `exit_code`)正确序列化到 frontmatter

### 测试

- [ ] 2 unit 测试 (字段完整性)
  - `tests/unit/test_issue_reporter_frontmatter.py::test_all_reporter_fields_present`
  - `test_stack_trace_sanitized_no_home_path`
- [ ] 1 unit 测试 (degrade)
  - `test_rddf_session_id_none_when_env_unset`
- [ ] 1 unit 测试 (项目 hash 稳定性)
  - `test_project_hash_deterministic_for_same_project_root`
- [ ] 1 integration (端到端)
  - `tests/integration/test_feedback_loop.bats` (如不存在则新建,改名)

### 不变量

- 现有 `.rddf/issues/*.md` 8 个样本**不修改**(只用新函数生成新文件验证)
- dedup_hash 算法不变(`_lib/issue_dedup.py::compute_dedup_hash`)

## 依赖

- **依赖**:`sanitize` 函数在 `_lib/loop/sanitizer.py:69-71` 已扩展(完成,无需本 PR 触碰)
- **前置**:无
- **后续**:配合 `fix-adr-0027-close-hook-dead-code`(PR-2),使 `_update_local_issue_files` 能根据 `submitted_url` 匹配到完整文件

## 相关 ADR/文档

- [ADR-0027 §4](docs/adr/ADR-0027-continuous-evolution-feedback-loop.md) Issue 格式契约
- [ADR-0027 §3](docs/adr/ADR-0027-continuous-evolution-feedback-loop.md) project_hash 假名化关联设计
- [Oracle 复核记录](docs/architecture/improvement-check-mechanisms.md#五oracle-复核) §5.2 P1-A 强化
- `_lib/issue_reporter.py:117-144` `_render_issue_body` 当前实现
- `_lib/loop/sanitizer.py:69-71` 已扩展的脱敏规则
- `_lib/issue_dedup.py::compute_dedup_hash`
