# complete-project-yaml-config-gaps — Design

## Context

`rfc-rddf-project-yaml-config-i10` (P1, 2026-09-02 archived) 是 rdd-workflow 引入 `.rddf/project.yaml` 项目级配置的奠基提案。其 5 优先级配置链扩展和 ChipForge 异构项目适配是核心价值。**但 archive 后审计发现 8 项 task 标记完成但代码未实际落地**,导致:

- 配置 schema 不强校验(破坏 fail-closed 承诺)
- verification hook 是孤儿代码(用户配 hook 不生效)
- 轻量模式仅在 archive 阶段生效(半实现)

本设计作为 follow-up change,在 i10 已实施基础上**针对性补齐 8 项缺口**,不重做已实施工作,保持 100% 向后兼容。

**修复对象**:`openspec/changes/archive/2026-09-02-rfc-rddf-project-yaml-config-i10/tasks.md` 中标 `- [x]` 但实际代码缺失的 task(详见 proposal.md §Why 调研证据)。

**复用资产**:
- `_lib/project_config.sh::project_yaml_get()` — i10 M1 Task 1.4 已实施,本 change 复用
- `_lib/verifier/hook_runner.py::run_verification_hook()` — i10 M4 Task 4.1 已实施,本 change **接线**(Task 4.2 漏做)
- `_lib/archive.sh::archive_change()` openspec_tracked 分支 — i10 M3 Task 3.3 已实施,本 change 仅**前置 Phase 1 检测**(Task 3.1)
- `_lib/adr_catalog.py::scan_adr_catalog(adr_pattern=...)` — i10 M2 Task 2.1 已实施,本 change **透传到 populate_lib.py**(Task 2.3 deferred)

**关联 ADR**:
- ADR-0036 (项目级配置) — i10 已创建,本 change §Consequences 段追加 fix 记录
- ADR-0022 (manual_deps 字段) — 无关
- ADR-0024 (deps-driven execution mode) — 本 change M3 ship_execution_mode 加固可能关联

## Goals / Non-Goals

**Goals**:

1. **修复 fail-closed 缺口** — `project.yaml` 字段类型错误必须 raise `ConfigError`,而非静默通过
2. **修复 hook 接线缺口** — `rddf rdd-verify` 在 provider=hook 时真正调用外部 hook
3. **修复轻量模式时机缺口** — `guide-ship` Phase 1 在 worktree 创建前检测,非 archive 阶段补救
4. **补齐 i10 deferred 项** — populate_lib.py 透传 adr_pattern + 集成测试
5. **100% 向后兼容** — 所有现有 2421 pytest + 现有 bats case 保持绿色
6. **根治预防** — 防止后续 change 再出现 checkbox-as-done(file-level diff vs tasks.md 复核)

**Non-Goals**:

- 不重做 i10 已实施的 M1/M2/M3/M5(archive.sh openspec_tracked 分支、project_config.sh、config.py merge、adr_catalog.py 参数化、discover-arch-artifacts.sh Path 1.5、ADR-0036、README 章节)
- 不实现 `rdd-doctor --category project-config` / `rddf init-project-config`(属 future work)
- 不强制现有项目迁移到 project.yaml
- 不修改 i10 archive 文件(proposal.md / tasks.md / spec.md 保留归档原貌作为修复对象对照)

## Decisions

### Decision 1: Schema 加固策略

**选择**:`_lib/schemas/config_schema.json` 新增 `project` / `adr` / `git` / `verification` 4 个顶层节,`project` 顶层节下嵌套 `adr` / `git` / `verification`(因 project.yaml 实际结构是嵌套)。

**Schema 结构**:

```json
{
  "properties": {
    "project": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "name": {"type": "string"},
        "version": {"type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$"}
      }
    },
    "adr": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "pattern": {"type": "string"},
        "glob": {"type": "string"},
        "dir": {"type": "string"}
      }
    },
    "git": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "openspec_tracked": {"type": "boolean", "default": true}
      }
    },
    "verification": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "provider": {"type": "string", "enum": ["llm", "hook"]}
      }
    }
  }
}
```

**拒绝**:
- 全部 `additionalProperties: true` — 破坏 fail-closed,等于不校验
- 嵌套在 `project.adr` 而非顶层 `adr` — project.yaml 实际是顶层 `adr`(per i10 design.md Decision 3)

### Decision 2: Hook Runner 接线模式

**选择**:`_lib/cli/rdd_verify_cmd.py::cmd_rdd_verify()` 在 `for change in queue:` 循环内检测 project.yaml `verification.provider`,决定 runner 选择:

```python
def cmd_rdd_verify(args, runner=None):
    ...
    for change in queue:
        if skip: ...
        provider = _detect_verification_provider(project_root)
        active_runner = runner or ( _hook_runner if provider == "hook" else _default_runner)
        result = run_one_change(project_root, change, runner=active_runner)
```

**env-var 传递模式**(per Oracle C1):
```bash
# bash 调用方式
VERIFICATION_PROVIDER=$(project_yaml_get "verification.provider" "llm") python3 -c "
from _lib.config import ConfigParser
import os
print(os.environ.get('VERIFICATION_PROVIDER', 'llm'))
"
```

**拒绝**:
- 全局 monkey-patch `cmd_rdd_verify()` 默认 runner — 破坏现有调用方
- 在 `_default_runner()` 内部分支 — 调用方传入 `runner` 时无法 override
- 单独创建 `rddf verify-hook` 子命令 — 与 rdd-verifier 单一入口哲学不符

### Decision 3: Cache 键 hook 分支

**选择**:`_lib/verifier/cache.py::cache_key()` 新增 `provider: hook` 分支,**不破坏现有 LLM 模式**:

```python
def cache_key(change_name, project_root, provider="llm", hook_path=None):
    base = {"change": change_name, "root": str(project_root), "provider": provider}
    if provider == "hook":
        base["hook"] = str(Path(hook_path or project_root / "tools/verify_change.sh").resolve())
    return hashlib.sha256(json.dumps(base, sort_keys=True).encode()).hexdigest()
```

**向后兼容**:默认 `provider="llm"`,现有调用方无需改动。

**拒绝**:
- 单独 `_lib/verifier/hook_cache.py` 模块 — 增加模块复杂度,语义无差异
- 用 hook 输出内容 hash 代替 command path — hook 输出不可重现,缓存键不稳定

### Decision 4: Guide-Ship Phase 1 检测时机

**选择**:`skills/guide-ship/SKILL.md` Phase 1 Step 1.5(在 worktree 创建 Step 2 **之前**)增加:

```bash
# Step 1.5: detect project.yaml openspec_tracked override (before worktree creation)
if [ -f "$PROJECT_ROOT/.rddf/project.yaml" ] && [ -f "$PROJECT_ROOT/_lib/project_config.sh" ]; then
    source "$PROJECT_ROOT/_lib/project_config.sh"
    OPENSPEC_TRACKED=$(project_yaml_get "git.openspec_tracked" "true")
    if [ "$OPENSPEC_TRACKED" = "false" ]; then
        echo "⚡ 强制轻量模式 (openspec_tracked=false, branch only, no worktree)"
        export RDDF_EXECUTION_MODE="lightweight"
    fi
fi
```

**理由**:
- 在 worktree 创建前检测,可避免不必要的 worktree 创建开销
- 用户立即看到行为变化提示,无需等到 archive
- 保留 i10 Task 3.3 的 archive 阶段兜底(双保险,任一漏不致死)

**拒绝**:
- 仅在 archive 阶段检测(当前 i10 状态)— 行为不一致,用户体验差
- 在 worktree 创建 Step 2 内部硬编码检测 — 散乱,违反职责分离

### Decision 5: ship_execution_mode project.yaml 优先级

**选择**:`_lib/ship_execution_mode.sh::parse_execution_mode()` 在 CLI flag / env var 解析后、default 之前增加 project.yaml 检测:

```
优先级: --parallel CLI flag > project.yaml git.openspec_tracked=false (强制 lightweight) > RDD_SHIP_PARALLEL=yes > default=serial
```

**注意**: `git.openspec_tracked: false` **强制 lightweight(映射到 serial)**,而非"关闭 parallelism"。这是因为 openspec untrack 项目无法做 worktree 并行,串行是唯一安全选择。

**拒绝**:
- project.yaml 单独字段 `execution.mode`(新增配置项)— 与 git.openspec_tracked 语义重叠,增加 schema 复杂度

### Decision 6: populate_lib.py 透传 adr_pattern

**选择**:`populate_lib.py::catalog_sources(adr_pattern=None)` 增加可选参数,从 `.rddf/project.yaml` 或 `.rddf/state/.arch-handoff.json` 读取 pattern(优先级后者,因 arch-handoff 是 arch 阶段已确认的产物)。

**env-var 传递模式**:
```python
# Python 端
import os
from pathlib import Path

def catalog_sources(project_root, adr_pattern=None):
    if adr_pattern is None:
        handoff_path = Path(project_root) / ".rddf" / "state" / ".arch-handoff.json"
        if handoff_path.is_file():
            adr_pattern = json.loads(handoff_path.read_text()).get("adr_pattern")
    ...
```

**拒绝**:
- 直接读 `.rddf/project.yaml` — arch-handoff 已是 arch 阶段产物,避免 arch 重复触发
- 全局硬编码 4 位 pattern — 破坏 ChipForge 3 位支持

### Decision 7: 根治预防 — checkbox-as-done 检测 (MANDATORY)

**选择**(强制,非可选):新增 `tests/integration/test_archive_gate_tasks_checklist_match.bats`,在 archive 流程中跑:

```bash
@test "archive gate: tasks.md checkboxes match file-level diff" {
    # 1. 读取 openspec/changes/$CHANGE/tasks.md 所有 - [x] task
    # 2. 对每个 task 关键字(如 "_lib/cli/rdd_verify_cmd.py"),用 git diff $BASE..HEAD 验证至少 1 个匹配
    # 3. 若 task 标 done 但 diff 无匹配 → fail
}
```

**理由**:本次 i10 archive 出现 8 项 checkbox-as-done,根因是缺乏 file-level 自动化校验。本 change 既是修复,也是建立预防机制。本测试为 MANDATORY,否则 root cause 未根治。

**拒绝**:
- 通过现有 `./test.sh --full --regression` 间接捕获 — 该脚本只验证测试通过,不验证 task vs diff
- 引入新 skill(如 `rdd-doctor --check tasks-diff`)— 过度工程,简单 bats 测试足够
- 标"可选" — 本 change 根因即 checkbox-as-done,预防机制必须强制

### Decision 8: 显式 runner 优先级 (Metis 歧义 #1)

**选择**:`cmd_rdd_verify(args, runner=None)` 调用时,**显式传入的 `runner` 参数永远胜出**于 project.yaml `verification.provider` 自动检测。Provider 检测仅在 `runner is None` 时生效。

**理由**:
- 测试隔离:测试 fixture 需要传入 mock runner,不应被 project.yaml 覆盖
- 显式 > 隐式是 Python 调用约定(callers' choice is authoritative)
- 一致性:与 `cache_key(provider="llm")` 默认值策略相同

**代码语义**:
```python
# cmd_rdd_verify 内
for change in queue:
    if runner is not None:
        active_runner = runner  # explicit wins
    else:
        provider = _detect_verification_provider(project_root)
        active_runner = _hook_runner if provider == "hook" else _default_runner
    result = run_one_change(project_root, change, runner=active_runner)
```

**拒绝**:
- Provider 检测永远胜出 — 破坏测试隔离,fixture 无效
- Provider 检测先跑,显式 runner 覆盖 — 同当前选择,但措辞更精确

**测试**:`test_explicit_runner_overrides_provider_detection` — 调用 `cmd_rdd_verify(args, runner=mock_runner)`,project.yaml 设 `provider: hook`,验证 mock_runner 被调用而 `_hook_runner` 未被调用。

### Decision 9: RDDF_EXECUTION_MODE env var 语义 (Metis 歧义 #2)

**选择**:`RDDF_EXECUTION_MODE` env var 是 **Phase 1 检测的输出**,不是 `parse_execution_mode` 的输入。
- `parse_execution_mode` 直接读 project.yaml(Decision 5),不读 env var
- `_lib/archive.sh::archive_change()` 直接读 project.yaml(i10 Task 3.3 已实现),不读 env var
- `RDDF_EXECUTION_MODE` env var 由 Phase 1 Step 1.5 export,供**其他下游工具**(尚未存在)使用,作为 "we're in lightweight mode" 的旁路信号

**理由**:
- 避免循环依赖(env var 由 Phase 1 set,不应被 Phase 1 内的 parse_execution_mode 读)
- 与 `RDD_SHIP_PARALLEL` 模式一致(env var 是外部 override,不是派生状态)
- parse_execution_mode 是自包含的,可独立测试

**Phase 1 行为**:
```bash
# 仅当 project.yaml openspec_tracked=false 时 set
if [ "$OPENSPEC_TRACKED" = "false" ]; then
    echo "⚡ 强制轻量模式 ..."
    export RDDF_EXECUTION_MODE="serial"  # ← 实际值,不是 "lightweight"
fi
```

**parse_execution_mode 优先级**(不变):CLI flag > project.yaml > RDD_SHIP_PARALLEL env > default。

**拒绝**:
- parse_execution_mode 读 RDDF_EXECUTION_MODE env — 引入循环依赖
- 单 env var 唯一来源 — 失去 project.yaml canonicality
- 引入 RDDF_FORCE_LIGHTWEIGHT 等新 env var — 增加 schema/env 复杂度

### Decision 10: ADR-0036 Fix Record 节命名 (Metis 歧义 #6)

**选择**:在 ADR-0036 中,在原有 Consequences 节**之后**新增一节 `## Post-hoc Fix Record (2026-09-02)`,**不追加到 Consequences 节**。

**理由**:
- 保留原始决策 rationale 完整不被混淆(审计完整性)
- 未来读者可清楚区分"原始决策"vs"后续修复"
- 创建新 ADR-0037 属过度工程 — ADR-0036 仍是正确锚点
- 创立新 convention:post-hoc fix records 有专属节

**结构示例**:
```markdown
## Consequences

[原始决策影响,不变]

## Post-hoc Fix Record (2026-09-02)

[本 change 修复内容、commit hash、关联 archived tasks.md]
```

**拒绝**:
- 追加到 Consequences — 混淆原始决策
- 创建 ADR-0037 — 过度工程
- 仅在 commit message 记录 — 缺乏正式可发现性

### Decision 11: Schema 严格性范围 (Metis 歧义 #4)

**选择**:Schema **根级**保持 `additionalProperties: true`(默认),允许用户 project.yaml 含额外根级 key(如 `my_custom_tooling`)。**新增 4 个节**(`project` / `adr` / `git` / `verification`)各自的**内部**属性设 `additionalProperties: false`,严格校验字段类型。

**理由**:
- 与现有 schema 模式一致(`interaction` / `openspec_gate` / `reporting` 已 strict on contents,根 loose)
- 不破坏现有用户的根级 extras(零回归)
- 新增节内部严格 → 真正实现 fail-closed 承诺

**Schema 片段**:
```json
{
  "additionalProperties": true,  // 根级保留宽松
  "properties": {
    ...
    "project": {"additionalProperties": false, "properties": {...}},
    "adr": {"additionalProperties": false, "properties": {...}},
    "git": {"additionalProperties": false, "properties": {"openspec_tracked": {"type": "boolean"}}},
    "verification": {"additionalProperties": false, "properties": {"provider": {"enum": ["llm", "hook"]}}}
  }
}
```

**测试**:`test_project_yaml_root_level_extras_allowed` — `.rddf/project.yaml` 含 `my_tooling: {x: 1}` 根级 extras,assert `ConfigParser.parse()` 成功(根 loose)。

**拒绝**:
- 根级 additionalProperties: false — 破坏现有用户
- 所有节 loose — 失去 fail-closed 承诺
- 仅 verification strict — 不一致,且 i10 已承诺全部 strict

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| **`rdd_verify_cmd.py` 改 _default_runner 默认行为** | 🟡 中 — provider=llm 用户行为变化 | (a) 默认 provider="llm" 完全保留 `_default_runner` 调用;(b) 单测 `test_default_runner_invoked_when_no_provider` 锁默认;(c) `--provider` 显式 flag 可 override |
| **schema strict 破坏现有 `.rddf.json` 用户** | 🟢 低 — `.rddf.json` 在 priority 链末端,且 schema 改动只新增 4 节 | (a) 单测 `test_rddf_json_with_unknown_top_level_key` 验证现有 schema 不破坏;(b) 字段缺失 raise 而非静默降级符合 fail-closed |
| **guide-ship Phase 1 早检测改变默认项目行为** | 🟢 低 — `openspec_tracked: true` 默认,行为不变 | (a) `project_yaml_get` 缺失/默认 true 时不改 `RDDF_EXECUTION_MODE`;(b) 集成测试 `test_guide_ship_default_behavior_unchanged` 锁默认 |
| **populate_lib.py 透传 pattern 影响 arch-handoff schema** | 🟡 中 — 现有 handoff 文件无 adr_pattern 字段 | (a) `adr_pattern` Optional[str],None → fallback 默认 4 位;(b) bump arch_handoff_schema.json v1→v2(可选 follow-up);(c) 旧 handoff 文件加载时 adr_pattern=None,行为兼容 |
| **archive.sh 已有 openspec_tracked 分支 + Phase 1 早检测重复** | 🟢 低 — 双保险,任一漏不致死 | (a) Phase 1 检测设 env var `RDDF_EXECUTION_MODE=lightweight`,archive.sh 沿用相同检测路径(无需双查);(c) 文档明确两者关系 |
| **ADR-0036 §Consequences 段追加可能破坏 ADR 已采纳状态** | 🟢 低 — Consequences 是事后记录,不影响决策本身 | (a) 追加段标注"后续 fix 记录",保持 ADR 决策不变;(b) ADR 状态保持 "已采纳" |
| **arch-handoff 过期导致 populate_lib 用错 adr_pattern** | 🟡 中 — 用户在 arch-done 后修改 project.yaml adr.pattern,handoff 仍指向旧 pattern | (a) `populate_lib.py::catalog_sources` 增加 fallback:handoff 无 adr_pattern / handoff 缺失时,直接读 `.rddf/project.yaml` 的 `adr.pattern`;(b) bump arch_handoff_schema.json v1→v2 添加 `adr_pattern` 字段(Task 4.4 范围内);(c) 文档明确 handoff 是 arch 阶段产物,arch-done 后修改 project.yaml 需重跑 arch(新 Task 4.4) |
| **修复 vs 重做的边界判断失误** | 🟡 中 — 可能错改了不该改的文件 | (a) 本 change 严格限定 14 个文件,见 proposal.md §Impact;(b) PR review 强制检查 "未触碰 i10 已实施代码";(c) `./test.sh --full --regression` 兜底 |

## Implementation Notes

### M1 Schema + Defaults

```python
# _lib/core/defaults.py 新增
DEFAULTS = {
    ...
    "project": {},  # 占位结构,空 dict;project.yaml 缺失时不插入
    # adr / git / verification 不在 DEFAULTS(仅 project.yaml 提供,缺 = 走项目硬编码默认)
}
```

```json
// _lib/schemas/config_schema.json 新增 4 节(顶层)
// "project": {"type": "object", "additionalProperties": false, "properties": {...}}
// "adr": {"type": "object", "additionalProperties": false, "properties": {"pattern": {...}, "glob": {...}, "dir": {...}}}
// "git": {"type": "object", "additionalProperties": false, "properties": {"openspec_tracked": {"type": "boolean", "default": true}}}
// "verification": {"type": "object", "additionalProperties": false, "properties": {"provider": {"type": "string", "enum": ["llm", "hook"]}}}
```

### M2 Hook Runner 接线

```python
# _lib/cli/rdd_verify_cmd.py 新增
def _detect_verification_provider(project_root: Path) -> str:
    """Read .rddf/project.yaml verification.provider (default 'llm')."""
    project_yaml = project_root / ".rddf" / "project.yaml"
    if not project_yaml.is_file():
        return "llm"
    try:
        import yaml
        cfg = yaml.safe_load(project_yaml.read_text()) or {}
        return cfg.get("verification", {}).get("provider", "llm")
    except (yaml.YAMLError, OSError):
        return "llm"

def _hook_runner(change_name: str, project_root: Path) -> dict:
    """Hook-based verifier runner (i10 M4 Task 4.2)."""
    from _lib.verifier.hook_runner import run_verification_hook
    from pathlib import Path
    verdict = run_verification_hook(change_name, Path(project_root))
    if verdict == "passed":
        return {"exit_code": 0, "verdict": [{"ac_id": f"hook-{change_name}", "status": "pass"}],
                "verdict_json": {"verdict": []}, "failed_acs": [], "provider": "hook"}
    elif verdict == "failed":
        return {"exit_code": 1, "verdict": [{"ac_id": f"hook-{change_name}", "status": "fail"}],
                "verdict_json": {"verdict": []}, "failed_acs": [f"hook-{change_name}"], "provider": "hook"}
    elif verdict == "error":
        return {"exit_code": 3, "verdict": [], "verdict_json": None, "failed_acs": [],
                "error": "hook execution error/timeout", "provider": "hook"}
    else:  # "skipped"
        return {"exit_code": 0, "verdict": [], "verdict_json": None,
                "failed_acs": [], "provider": "hook", "note": "hook script missing"}
```

```python
# cmd_rdd_verify 内调用
for change in queue:
    if skip: ...
    provider = _detect_verification_provider(Path(project_root))
    active_runner = runner or (_hook_runner if provider == "hook" else _default_runner)
    result = run_one_change(project_root, change, runner=active_runner)
```

### M3 Guide-Ship Phase 1 + ship_execution_mode

```bash
# skills/guide-ship/SKILL.md Phase 1 Step 1.5 新增(在 Step 2 worktree 创建之前)
# Step 1.5: Detect project.yaml openspec_tracked override
if [ -f "$PROJECT_ROOT/.rddf/project.yaml" ] && [ -f "$PROJECT_ROOT/_lib/project_config.sh" ]; then
    # shellcheck disable=SC1090
    source "$PROJECT_ROOT/_lib/project_config.sh"
    OPENSPEC_TRACKED=$(project_yaml_get "git.openspec_tracked" "true")
    if [ "$OPENSPEC_TRACKED" = "false" ]; then
        echo "⚡ 强制轻量模式 (openspec_tracked=false, branch only, no worktree)"
        export RDDF_EXECUTION_MODE="lightweight"
    fi
fi
```

```bash
# _lib/ship_execution_mode.sh::parse_execution_mode() 在 CLI flag / env var 之后,default 之前
# CLI flag takes precedence (above)
# ...
# NEW: project.yaml detection (after CLI flag, before env var)
if [ -z "$cli_mode" ] && [ -f "${PROJECT_ROOT:-.}/.rddf/project.yaml" ]; then
    local _helper="${PROJECT_ROOT:-.}/_lib/project_config.sh"
    if [ -f "$_helper" ]; then
        # shellcheck disable=SC1090
        source "$_helper"
        local _tracked
        _tracked=$(project_yaml_get "git.openspec_tracked" "true")
        if [ "$_tracked" = "false" ]; then
            echo "serial"  # openspec untrack 强制 lightweight = serial
            return 0
        fi
    fi
fi

# Fall back to env var
if [[ "${RDD_SHIP_PARALLEL:-}" == "yes" ]]; then ...
```

### M4 populate_lib.py 透传

```python
# populate_lib.py::catalog_sources 新增可选参数 + fallback (Task 4.4)
def catalog_sources(project_root=None, adr_pattern=None):
    if adr_pattern is None and project_root:
        # Priority 1: arch-handoff (arch 阶段产物)
        handoff_path = Path(project_root) / ".rddf" / "state" / ".arch-handoff.json"
        if handoff_path.is_file():
            try:
                handoff = json.loads(handoff_path.read_text())
                adr_pattern = handoff.get("adr_pattern")
            except (json.JSONDecodeError, OSError):
                pass
        # Priority 2 (NEW Task 4.4): .rddf/project.yaml direct fallback
        # 当 handoff 缺失 adr_pattern 字段或 handoff 缺失时,
        # 用户可能已在 arch-done 后修改 project.yaml
        if adr_pattern is None:
            project_yaml_path = Path(project_root) / ".rddf" / "project.yaml"
            if project_yaml_path.is_file():
                try:
                    import yaml
                    cfg = yaml.safe_load(project_yaml_path.read_text()) or {}
                    adr_pattern = cfg.get("adr", {}).get("pattern")
                except (yaml.YAMLError, OSError):
                    pass
    # Priority 3: 默认 4 位 pattern (硬编码)
    # ... 现有 catalog_sources 逻辑,用 adr_pattern 替换硬编码 ADR_PATTERN
```

### arch-handoff schema v1→v2 bump (Task 4.4 副作用)

```python
# _lib/schemas/arch_handoff_schema.json v1 → v2 添加字段
{
  "version": 2,  # was 1
  "properties": {
    "adr_pattern": {"type": "string"},
    ...
  }
}
```

向后兼容:v1 字段保留;v2 新增 `adr_pattern` optional 字段。旧 handoff 文件加载时 `adr_pattern=None`,fallback 走 Priority 2 (project.yaml 直接读)。

### ADR-0036 §Consequences 追加段

```markdown
## Consequences (continued: 2026-09-02 fix record)

`complete-project-yaml-config-gaps` change 审计 i10 archive 后发现 8 项 task 标记完成但代码未落地,
通过本 change 补齐:
- schema `project` / `adr` / `git` / `verification` 4 节(fail-closed 强化)
- hook runner 接线(`rdd_verify_cmd.py` 真正调用 `hook_runner.run_verification_hook()`)
- guide-ship Phase 1 早检测(`git.openspec_tracked: false` 在 worktree 创建前生效)
- populate_lib.py 透传 adr_pattern

参考:`openspec/changes/archive/2026-09-02-rfc-rddf-project-yaml-config-i10/tasks.md` 23/25 done
```

## Open Questions

无 — 全部决策已锁定。后续如有疑问,在 plan 阶段 ask。

## Cross-References

- i10 proposal: `openspec/changes/archive/2026-09-02-rfc-rddf-project-yaml-config-i10/proposal.md`
- i10 design: `openspec/changes/archive/2026-09-02-rfc-rddf-project-yaml-config-i10/design.md`
- i10 tasks: `openspec/changes/archive/2026-09-02-rfc-rddf-project-yaml-config-i10/tasks.md` (修复对象)
- ADR-0036: `docs/adr/ADR-0036-rddf-project-yaml-config.md` (§Consequences 段追加)
- `.rddf/improvements/rfc-rddf-project-yaml-config-i10.md` (上游 RFC #10)
- `.rddf/improvements/complete-project-yaml-config-gaps.md` (本 change 上游 issue ref)