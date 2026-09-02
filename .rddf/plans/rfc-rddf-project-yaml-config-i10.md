# Implementation Plan: rfc-rddf-project-yaml-config-i10

> **Source**: `openspec/changes/rfc-rddf-project-yaml-config-i10/`
> **Phase**: v2.2+ | **Category**: arch-design | **Priority**: P1 | **Type**: feature
> **Issue**: https://github.com/chisuhua/rdd-workflow/issues/10
> **Branch**: `openspec/rfc-rddf-project-yaml-config-i10` (lightweight mode)
> **TDD 5 步结构**: Write failing test → Verify fail → Implement → Verify pass → Commit

## Milestone Overview

| M | 内容 | Task 数 | 风险 | 依赖 |
|---|------|---------|------|------|
| **M1** | 配置基础设施（project_config.sh + config.py merge + schema） | 8 | 🔴 高 | 无 |
| **M2** | ADR 发现可配置（pattern 参数化） | 6 | 🟡 中 | M1 |
| **M3** | openspec_tracked / 轻量模式 | 5 | 🔴 高 | M1 |
| **M4** | verification hook | 5 | 🟢 低 | M1 |
| **M5** | 文档 + 全量测试 | 4+2 | 🟢 低 | M2/M3/M4 |

**验收门**：M5 完成后 `./test.sh --full --regression` 全绿才能 archive。

---

## M1 — 配置基础设施（基石）

### Task 1.1: schema 新增 project 节

**Files**:
- `_lib/schemas/config_schema.json` (modify)
- `tests/unit/test_config_schema.py` (new)

**Write failing test**:
```python
def test_project_schema_section_exists():
    schema = json.load(open("_lib/schemas/config_schema.json"))
    assert "properties" in schema
    assert "project" in schema["properties"]
```

**Verify fail**: schema 当前无 `project` 节 → AssertionError

**Implement**: 添加 `project` 节定义（含 `adr.pattern` / `git.openspec_tracked` / `verification.provider` 字段类型）

**Verify pass**: 单测通过

### Task 1.2-1.5: _load_project_yaml helper + merge 顺序 + defaults

**Files**:
- `_lib/config.py` (modify)
- `_lib/core/defaults.py` (modify)
- `_lib/project_config.sh` (new)
- `tests/unit/test_config.py` (modify — 增加 priority test)

**Write failing test**: `test_priority_project_yaml_over_loop_yaml`

**Implement**: 
- `_load_project_yaml(project_root)` — 缺失返回 {}；存在则 yaml.safe_load + schema 校验
- `parse()` merge 顺序: defaults < .rddf.json < env vars < loop.yaml < project.yaml < overrides
- `_lib/project_config.sh` — yq fallback 到 Python subprocess

**Verify pass**: 单测验证 project.yaml > loop.yaml > env vars > .rddf.json > defaults

### Task 1.6-1.8: 边界测试

- `test_project_yaml_missing_no_effect` — 缺失时不抛异常，merge 退化为现状
- `test_project_yaml_schema_validation_strict` — 字段类型错误 raise ConfigError
- `test_project_yaml_empty_file_handled` — 空文件 → 等价缺失

---

## M2 — ADR 发现可配置（依赖 M1）

### Task 2.1-2.3: 参数化 adr_pattern

**Files**:
- `_lib/adr_catalog.py` (modify)
- `_lib/discover-arch-artifacts.sh` (modify — Path 1.5)
- `populate_lib.py` (modify — 透传)
- `roadmap_incremental_update.py` (modify — 透传)
- `tests/unit/test_adr_catalog.py` (modify)

**Write failing test**: `test_three_digit_adr_pattern` — 创建临时 ADR-001.md / ADR-040.md，project.yaml 设 `adr.pattern: "^ADR-\\d{3}-"`，扫描应返回 1 项。

**Implement**:
```python
def scan_adr_catalog(adr_dir="docs/adr", adr_pattern=None):
    pattern = adr_pattern or r"^ADR-(\d{4})-.*\.md$"
    regex = re.compile(pattern)
    # ... 现有逻辑
```

`discover-arch-artifacts.sh` Path 1.5:
```bash
if [ -f "$PROJECT_ROOT/.rddf/project.yaml" ]; then
    ADR_PATTERN_FROM_PROJECT=$(project_yaml_get "adr.pattern" "")
    [ -n "$ADR_PATTERN_FROM_PROJECT" ] && DISCOVERED_ADR_PATTERN="$ADR_PATTERN_FROM_PROJECT"
fi
```

### Task 2.4-2.6: 集成测试

- `test_adr_pattern_overrides_default`
- `test_discover_arch_artifacts_uses_project_yaml` (integration)
- `test_populate_roadmap_respects_pattern` (integration)

---

## M3 — openspec_tracked / 轻量模式（依赖 M1）

### Task 3.1-3.2: guide-ship 检测

**Files**:
- `skills/guide-ship/SKILL.md` (modify)
- `_lib/ship_execution_mode.sh` (modify)
- `tests/integration/test_guide_ship_execution_mode.bats` (modify — 新增场景)

**Write failing test**:
```bash
@test "guide-ship: openspec_tracked=false forces lightweight mode" {
    cd "$TEST_PROJECT_ROOT"
    echo "git:
  openspec_tracked: false" > .rddf/project.yaml
    
    run bash skills/guide-ship/scripts/ship_env_check.sh
    [ "$status" -eq 0 ]
    [[ "$output" =~ "⚡ 强制轻量模式" ]]
}
```

**Implement**: `guide-ship/SKILL.md` Phase 1 Step 1.5 + `ship_execution_mode.sh` 检测 `git.openspec_tracked`，true→worktree，false→lightweight。

### Task 3.3: archive.sh 分支

**Files**:
- `_lib/archive.sh` (modify)
- `tests/integration/test_archive_openspec_tracked_false.bats` (new)

**Write failing test**: `test_archive_with_openspec_tracked_false_skips_git_ops` — 设置 `openspec_tracked: false`，archive 时不调用 `git merge`/`git commit`，仅 `openspec archive` + `mark_iteration`。

**Implement**:
```bash
archive_change() {
    local name="$1"
    local openspec_tracked=$(project_yaml_get "git.openspec_tracked" "true")
    
    if [ "$openspec_tracked" = "false" ]; then
        echo "📦 openspec_tracked=false: 跳过 git merge/commit"
        openspec archive "$name" --yes
        mark_iteration_archived "$name"
        return 0
    fi
    
    # 现有逻辑
}
```

### Task 3.4-3.5: 集成测试

- `test_guide_ship_execution_mode_openspec_tracked_false`
- `test_archive_with_openspec_tracked_false_skips_git_ops`

---

## M4 — verification hook（依赖 M1）

### Task 4.1: hook_runner.py

**Files**:
- `_lib/verifier/hook_runner.py` (new)
- `tests/unit/test_hook_runner.py` (new)

**Write failing test**:
```python
def test_hook_runner_path_whitelist():
    with pytest.raises(ValueError, match="must be in tools/"):
        run_verification_hook("change-x", Path("/etc/passwd"))

def test_hook_runner_exit_0_passes(tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools/verify_change.sh").write_text("#!/bin/bash\nexit 0\n")
    (tmp_path / "tools/verify_change.sh").chmod(0o755)
    
    assert run_verification_hook("change-x", tmp_path) == "passed"
```

**Implement**:
```python
def run_verification_hook(change_name: str, project_root: Path) -> str:
    hook_path = project_root / "tools" / "verify_change.sh"
    if not hook_path.exists():
        return "skipped"
    
    resolved = hook_path.resolve()
    if not str(resolved).startswith(str(project_root.resolve()) + "/tools/"):
        raise ValueError(f"hook path must be in tools/, got {resolved}")
    
    result = subprocess.run(
        [str(hook_path), change_name],
        cwd=project_root, capture_output=True, text=True, timeout=300,
    )
    if result.returncode == 0: return "passed"
    elif result.returncode == 1: return "failed"
    return "error"
```

### Task 4.2: rdd_verify_cmd.py provider=hook 分支

**Files**:
- `_lib/cli/rdd_verify_cmd.py` (modify)
- `tests/integration/test_rdd_verifier.bats` (modify)

**Write failing test**:
```bash
@test "rdd_verify: provider=hook calls external script" {
    cd "$TEST_PROJECT_ROOT"
    mkdir -p tools
    cat > tools/verify_change.sh <<'EOF'
#!/bin/bash
[ "$1" = "test-change" ] && exit 0 || exit 1
EOF
    chmod +x tools/verify_change.sh
    
    echo "verification:
  provider: hook" > .rddf/project.yaml
    
    run rddf rdd-verify test-change
    [ "$status" -eq 0 ]
    [[ "$output" =~ "passed" ]]
}
```

**Implement**: `rdd_verify_cmd.py` 读 project.yaml `verification.provider`，hook 时调用 `hook_runner.run_verification_hook`。

### Task 4.3-4.5: 缓存键 + 集成测试

- `test_hook_runner_cache_key` (unit)
- `test_rdd_verifier_provider_hook` (integration)
- `test_hook_runner_missing_script_skipped` (unit)

---

## M5 — 文档 + 全量测试（依赖 M2/M3/M4）

### Task 5.1-5.2: 文档

**Files**:
- `README.md` (modify)
- `USAGE.md` (modify)

**添加章节**: `.rddf/project.yaml` 配置（字段表 + ChipForge 示例）

### Task 5.3: ChipForge 真实反馈

**操作**: 邀请 ChipForge 维护者 review（外部协作，本地不强求）

### Task 5.4: 全量回归

```bash
./test.sh --full --regression
```

**通过标准**: 全绿 + 无新增 KNOWN_FAILURES 偏差

### Task 5.5: 新建 ADR

**Files**:
- `docs/adr/ADR-0036-project-level-config.md` (new)
- `docs/adr/README.md` (modify — 更新索引)

---

## Cross-Milestone Verification

### Task X.1: M1 完成后
```bash
./test.sh --unit  # 验证基础不破
```

### Task X.2: M2-M4 完成后
```bash
./test.sh --python --bats
```

### Task X.3: archive 前
```bash
./test.sh --full --regression  # 必须全绿
```

---

## Pre-Archive Checklist

- [ ] 25 个 task 全部 `[x]`（M1-M5 + 跨里程碑）
- [ ] M5 后 `./test.sh --full --regression` 全绿
- [ ] Worktree 单一聚合 commit (`feat(ship): implement rfc-rddf-project-yaml-config-i10`)
- [ ] `openspec validate rfc-rddf-project-yaml-config-i10 --json` passed
- [ ] `rdd ac-verify rfc-rddf-project-yaml-config-i10` passed（rdd-verifier）

## Execution Mode

- **Mode**: lightweight（无并行 worktree + 单 change）
- **Branch**: `openspec/rfc-rddf-project-yaml-config-i10`（已在 master 创建）
- **Worktree**: 无（直接在当前仓库执行）
