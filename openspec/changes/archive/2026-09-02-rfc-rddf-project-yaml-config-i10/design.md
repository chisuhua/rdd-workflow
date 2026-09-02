# rfc-rddf-project-yaml-config-i10 — Design

## Context

rdd-workflow 当前 5 优先级配置链 `runtime > loop.yaml > .rddf.json > env vars > defaults` 缺一个项目级持久化层，导致 4 类硬编码假设阻碍异构项目接入。本设计在现有链中插入 `project.yaml`，作为单一权威项目级配置源，零侵入式地解决 ADR 编号灵活性、openspec_tracked 切换、外部验证 hook、配置可发现性 4 类问题。

参考：
- **proposal.md** Why + What Changes + Capabilities + Acceptance（已批准）
- **specs/.../spec.md** 自动生成的 D2 映射规范（验收契约）
- **issue #10** upstream RFC

## Goals / Non-Goals

**Goals**:
1. **零侵入集成**：project.yaml 缺失时所有现有行为不变（merge 顺序退化为现状）
2. **统一发现入口**：单一 `.rddf/project.yaml` 作为项目级配置权威
3. **可配置 ADR 编号**：支持 3 位（`ADR-\d{3}`）和 4 位（默认）
4. **可配置 openspec 跟踪模式**：支持 git-tracked（默认）和 untracked（轻量）
5. **可插拔验证**：支持 LLM（默认）和外部 hook 两种 verifier
6. **完整 schema 校验**：jsonschema 强校验，缺失字段报错而非静默降级
7. **里程碑式实施**：M1 → M2/M3/M4（并行）→ M5，单 PR 风险可控

**Non-Goals**:
- 不实现 roadmap 多路径聚合（candidates 字段预留）
- 不改 RDDF_REPORT_GH_REPO 等既有 env var 语义
- 不强制现有项目迁移到 project.yaml
- 不实现 project.yaml 热重载（修改后需重跑工具）

## Decisions

### Decision 1: project.yaml 位置 + 加载机制

**选择**：`.rddf/project.yaml`（与 `.rddf/state/` 同根，符合 rdd-workflow 约定）。

**加载方式**：
- Python (`_lib/config.py`) 优先用 PyYAML + jsonschema 校验
- Bash (`_lib/project_config.sh`) 通过 yq fallback 到 Python subprocess（避免硬依赖）
- env-var 传递模式（禁止 `python3 -c "...$VAR..."` 内联，参照 add-improve env.py 模式）

**拒绝**：
- 放在 repo 根 (`project.yaml`) — 与 `_lib/config.py` 默认查找约定不一致
- 用 TOML — 与现有 yaml 工具链分裂，CI 注入繁琐

### Decision 2: 优先级链插入点

**选择**：在 `loop.yaml` 之上插入 `project.yaml`（最强项目级覆盖），env vars 仍可临时覆盖：

```
runtime_overrides > project.yaml > loop.yaml > env vars > .rddf.json > defaults
```

**理由**：
- 项目级配置优先级 ≥ loop.yaml（团队共享 > 单文件）
- env vars 在 project.yaml 之下（保留 CI 临时注入语义）
- 不破坏 `test_priority_loop_yaml_over_rddf_json` 等锁定旧顺序的单测

**替代方案**：
- env vars > project.yaml（CI 优先）— 拒绝：项目级配置失去权威性
- project.yaml > env vars > loop.yaml（project 最高）— 拒绝：破坏 env var CI 注入语义

### Decision 3: ADR 编号可配置

**选择**：在 `_lib/adr_catalog.py::scan_adr_catalog(..., adr_pattern=None)` 加参数，None 时用硬编码默认 `^ADR-(\d{4})-.*\.md$`（保留向后兼容），非 None 时覆盖。

**对应 Shell 侧**：`_lib/discover-arch-artifacts.sh` Path 1.5 读 project.yaml `adr.pattern`，导出 `DISCOVERED_ADR_PATTERN` 给 `populate_lib.py` / `roadmap_incremental_update.py` 透传。

**ADR 与 glob 配对**：
- `adr.pattern` (Python re) — adr_catalog.py 使用
- `adr.glob` (Shell glob) — discover-arch-artifacts.sh 使用
- 文档强制两者语义等价（如 `adr.pattern: "^ADR-\d{3}-"` ↔ `adr.glob: "ADR-???.md"`）

**拒绝**：
- 完全移除 4 位硬编码 — 破坏 36 个现有 ADR 兼容性
- 用 per-ADR 字段标记编号长度 — 侵入式，破坏目录约定

### Decision 4: openspec_tracked 配置

**选择**：`git.openspec_tracked: false` 时 guide-ship 强制走轻量模式（branch-only，无 worktree），archive 跳过 git merge/commit，仅调用 `openspec archive` + mark_iteration。

**入口检测**：
- `skills/guide-ship/SKILL.md` Phase 1 Step 1-3 增加读 project.yaml
- 检测 `git.openspec_tracked == false` → 跳过 worktree 创建，直接进入 lightweight 路径

**archive 分支**：
- `_lib/archive.sh` 新增 `if not project_yaml.openspec_tracked` 分支
- 跳过 `check_worktree_commits` + `git merge` + `commit_archive_moves`
- 仅 `openspec archive <name> --yes` + `mark_iteration archived`

**拒绝**：
- 把 openspec_tracked 检测放到 worktree 创建内部 — 散乱，难以审计
- 提供 per-change `openspec_tracked` 覆盖 — 与项目级配置语义冲突

### Decision 5: verification hook 插件机制

**选择**：新增 `_lib/verifier/hook_runner.py`，`verification.provider: hook` 时调用 `tools/verify_change.sh <change>`（约定路径）。

**退出码映射**：
- exit 0 → passed
- exit 1 → failed (走 classify_failure 复用)
- exit 2+ → error (network/setup 类问题)
- stdout 末尾 `[verdict=passed|failed] [sha=<git-sha>]` 用于缓存键

**缓存复用**：`_lib/verifier/cache.py` SHA-based 缓存继续工作，hook 模式下缓存键改为 `git-sha + command-hash`。

**拒绝**：
- 用 docker 容器隔离 hook — 过度工程，本地开发体验差
- 用 JSON-RPC / gRPC 协议 — 复杂度过高，bash 退出码足够

### Decision 6: schema 校验失败处理

**选择**：严格 fail-closed — schema 校验失败时 raise `ConfigError` 阻断后续工具，stderr 输出违规字段。

**MUST**：
- `skills/_lib/schemas/config_schema.json` 增加 `project` 节定义
- 字段类型（bool/int/string/list）严格校验
- 缺失必填字段报错（而非默认填充）

**保留**：
- 整体 schema 文件缺失时跳过校验（向后兼容）
- `SKIP_CONFIG_VALIDATION=yes` 环境变量紧急绕过

### Decision 7: 里程碑拆分

**选择**：M1 → M2/M3/M4（并行）→ M5，每阶段独立 PR。

**理由**：
- M1 是基石（merge 顺序全局影响），独立 PR 易于 review + revert
- M2/M3/M4 互相独立，可 3 个 reviewer 并行审查
- M5 是文档 + 全量测试，必须等 M1-M4 落地

**PR 标题规范**（参考 existing commit 风格）：
- `feat(config): add .rddf/project.yaml as project-level config source (M1)`
- `feat(adr): configurable ADR pattern via project.yaml (M2)`
- `feat(ship): openspec_tracked flag forces lightweight mode (M3)`
- `feat(verifier): hook provider for external verification (M4)`
- `docs(project-config): migration guide + integration tests (M5)`

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| **M1 merge 顺序全局影响** | 🔴 高 — 错误的优先级会静默覆盖用户配置 | (a) M1 必须先落 `test_priority_project_yaml_over_loop_yaml` 单测；(b) 默认值设 ZERO（不插入）；(c) 不改 `_deep_merge` 既有签名 |
| **archive.sh 分支破坏现有归档路径** | 🔴 高 — 影响每个 change 的归档流程 | (a) 仅在 `openspec_tracked=false` 时分支；(b) 增加 `test_archive_with_openspec_tracked_false` 集成测试；(c) M3 单独 PR + 全量回归门 |
| **hook runner shell 注入风险** | 🟡 中 — `tools/verify_change.sh` 路径受 project.yaml 控制 | (a) 路径白名单 + 强制在 `$PROJECT_ROOT/tools/` 下；(b) 不接受绝对路径；(c) 复用 env-var 传递模式 |
| **schema 校验破坏现有 `.rddf.json` 用户** | 🟢 低 — `.rddf.json` 在 priority 链末端 | (a) `_lib/schemas/config_schema.json` 新增 `project` 节（旧 schema 不破坏）；(b) 增加向后兼容测试 |
| **ADR 编号 pattern 误配导致归档丢失** | 🟡 中 — 项目升 4→3 位时旧 ADR 被静默跳过 | (a) `discover-arch-artifacts.sh` 在 pattern 变更时打印 warning；(b) `rdd-doctor --category project-config` 检测漂移 |
| **里程碑拆分导致 review 摩擦** | 🟢 低 — M2/M3/M4 都改 `guide-ship` / `_lib/` 顶层文件 | (a) 按文件冲突矩阵分批合并；(b) `rdd-deps` 检测并发 PR 冲突 |

## Implementation Notes

### M1: 配置基础设施 (基石)

```python
# _lib/config.py 新增
def _load_project_yaml(project_root: Path) -> dict:
    """Load .rddf/project.yaml with strict schema validation."""
    project_path = project_root / ".rddf" / "project.yaml"
    if not project_path.exists():
        return {}  # 缺失 = 零影响
    with open(project_path) as f:
        raw = yaml.safe_load(f) or {}
    # jsonschema 校验（缺失 schema 文件时跳过）
    validate_project_config(raw)
    return raw

def parse(overrides=None):
    # ... 现有逻辑 ...
    project_yaml = _load_project_yaml(Path(PROJECT_ROOT))
    # priority: runtime > project_yaml > loop.yaml > env vars > .rddf.json > defaults
    merged = _deep_merge(defaults, _load_rddf_json(...))
    merged = _deep_merge(merged, env_var_overrides)
    merged = _deep_merge(merged, loop_yaml)
    merged = _deep_merge(merged, project_yaml)  # 关键插入点
    if overrides:
        merged = _deep_merge(merged, overrides)
    return merged
```

```bash
# _lib/project_config.sh 新建
project_yaml_load() {
    local project_root="${1:-$PROJECT_ROOT}"
    local pyfile="$project_root/.rddf/project.yaml"
    [ ! -f "$pyfile" ] && return 0  # 缺失 = 零影响
    PROJECT_CONFIG_FILE="$pyfile" python3 -c '
import os, yaml, json
with open(os.environ["PROJECT_CONFIG_FILE"]) as f:
    print(json.dumps(yaml.safe_load(f) or {}))
'
}

project_yaml_get() {
    # project_yaml_get <key> [default]
    local key="$1" default="${2:-}"
    # 委托给 _lib/config.py（确保 merge 顺序一致）
    PYTHONPATH="$PROJECT_ROOT" python3 -c "
from _lib.config import ConfigParser
import os
parser = ConfigParser()
result = parser.get('$key', default='$default')
print(result)
"
}
```

### M2: ADR 发现可配置

```python
# _lib/adr_catalog.py
def scan_adr_catalog(
    adr_dir: str = "docs/adr",
    adr_pattern: Optional[str] = None,  # 新参数
) -> List[ADREntry]:
    pattern = adr_pattern or r"^ADR-(\d{4})-.*\.md$"
    regex = re.compile(pattern)
    # ... 现有逻辑，pattern 替换硬编码 ...
```

```bash
# _lib/discover-arch-artifacts.sh 新增 Path 1.5
# Path 1.5: read .rddf/project.yaml (highest priority over defaults)
if [ -f "$PROJECT_ROOT/.rddf/project.yaml" ]; then
    ADR_PATTERN_FROM_PROJECT=$(project_yaml_get "adr.pattern" "")
    if [ -n "$ADR_PATTERN_FROM_PROJECT" ]; then
        DISCOVERED_ADR_PATTERN="$ADR_PATTERN_FROM_PROJECT"
        echo "✅ ADR pattern from project.yaml: $DISCOVERED_ADR_PATTERN"
    fi
fi
```

### M3: openspec_tracked / 轻量模式

```bash
# skills/guide-ship/SKILL.md Phase 1 增加 Step 1.5
if [ -f "$PROJECT_ROOT/.rddf/project.yaml" ]; then
    OPENSPEC_TRACKED=$(project_yaml_get "git.openspec_tracked" "true")
    if [ "$OPENSPEC_TRACKED" = "false" ]; then
        echo "⚡ 强制轻量模式 (openspec_tracked=false, branch only, no worktree)"
        RDDF_EXECUTION_MODE="lightweight"
    fi
fi
```

```bash
# _lib/archive.sh 增加分支
archive_change() {
    local name="$1"
    local openspec_tracked
    openspec_tracked=$(project_yaml_get "git.openspec_tracked" "true")

    if [ "$openspec_tracked" = "false" ]; then
        echo "📦 openspec_tracked=false: 跳过 git merge/commit, 仅 openspec archive"
        openspec archive "$name" --yes
        mark_iteration_archived "$name"
        return 0
    fi

    # 现有逻辑：worktree_commits check → merge → openspec archive → cleanup
    # ...
}
```

### M4: verification hook

```python
# _lib/verifier/hook_runner.py 新建
import subprocess
from pathlib import Path

def run_verification_hook(change_name: str, project_root: Path) -> str:
    """Run tools/verify_change.sh and return verdict."""
    hook_path = project_root / "tools" / "verify_change.sh"
    if not hook_path.exists():
        return "skipped"  # 缺失 = 视为 pass（向后兼容）

    # 安全检查：路径必须在 project_root/tools/ 下
    resolved = hook_path.resolve()
    if not str(resolved).startswith(str(project_root.resolve()) + "/tools/"):
        raise ValueError(f"hook path must be in tools/, got {resolved}")

    result = subprocess.run(
        [str(hook_path), change_name],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=300,  # 5 分钟上限
    )
    if result.returncode == 0:
        return "passed"
    elif result.returncode == 1:
        return "failed"
    else:
        return "error"
```

### M5: 文档 + 全量测试

- README.md 增加 `.rddf/project.yaml` 章节
- USAGE.md 增加配置迁移示例
- 4 个里程碑的集成测试全绿（`./test.sh --full --regression`）
- ChipForge 作为首个异构项目采用者提供真实反馈
