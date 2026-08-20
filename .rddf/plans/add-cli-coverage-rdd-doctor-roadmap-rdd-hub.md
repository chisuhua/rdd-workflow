# add-cli-coverage-rdd-doctor-roadmap-rdd-hub — 实施计划

> TDD 5 步结构: Write failing test → Verify fail → Implement → Verify pass → Commit

## 文件清单

| 操作 | 文件 | 说明 |
|------|------|------|
| +NEW | `_lib/cli/doctor_cmd.py` | `rddf doctor` 薄包装 (25 行) |
| +NEW | `_lib/cli/roadmap_cmd.py` | `rddf roadmap` 子命令分发表 (30 行) |
| +NEW | `_lib/cli/rdd_hub_bootstrap_cmd.py` | `rddf rdd-hub-bootstrap` 薄包装 (25 行) |
| +MOD | `_lib/cli/__init__.py` | 路由表 +3 行 |
| +NEW | `tests/integration/test_cli_coverage.bats` | 7-8 个集成测试 (80 行) |

**不修改**: `skills/rdd-doctor/`, `skills/roadmap/`, `skills/rdd-hub-bootstrap/` 内部文件

---

## Task 1: `_lib/cli/doctor_cmd.py`

### Step 1: Write failing test
```bash
# 确认 rddf doctor 当前不存在
rddf doctor --help 2>&1 | grep -q "unknown command"
```

### Step 2: Verify fail
```bash
echo "Exit: $? (0=不存在, 符合预期)"
```

### Step 3: Implement
创建 `_lib/cli/doctor_cmd.py`:
- 导出 `cmd_doctor(args: list[str]) -> int`
- 转发到 `bash skills/rdd-doctor/scripts/doctor.sh "$@"`
- 用 `subprocess.run` 调用
- 透传退出码 `return proc.returncode`

### Step 4: Verify pass
```bash
rddf doctor --help 2>&1 | grep -q "state,plan-tdd" && echo "✅ --help 含 8 categories"
rddf doctor --version 2>&1 | grep -q "rdd-doctor" && echo "✅ --version 输出版本"
```

### Step 5: Commit
```bash
git add _lib/cli/doctor_cmd.py
git commit -m "feat(cli): add rddf doctor subcommand (thin wrapper)"
```

---

## Task 2: `_lib/cli/roadmap_cmd.py`

### Step 1: Write failing test
```bash
rddf roadmap --help 2>&1 | grep -q "unknown command"
```

### Step 2: Verify fail
```bash
echo "Exit: $? (0=不存在, 符合预期)"
```

### Step 3: Implement
创建 `_lib/cli/roadmap_cmd.py`:
- 导出 `cmd_roadmap(args: list[str]) -> int`
- 子命令分发表: `migrate` → `bash skills/roadmap/scripts/roadmap_migrate.sh`, `validate-fragments` → `bash skills/roadmap/scripts/roadmap_validate_fragments.sh`
- 无子命令或 `--help` 时显示帮助
- 透传退出码

### Step 4: Verify pass
```bash
rddf roadmap --help 2>&1 | grep -q "migrate" && echo "✅ --help 含 migrate"
rddf roadmap --help 2>&1 | grep -q "validate-fragments" && echo "✅ --help 含 validate-fragments"
```

### Step 5: Commit
```bash
git add _lib/cli/roadmap_cmd.py
git commit -m "feat(cli): add rddf roadmap subcommand (subcommand dispatch)"
```

---

## Task 3: `_lib/cli/rdd_hub_bootstrap_cmd.py`

### Step 1: Write failing test
```bash
rddf rdd-hub-bootstrap --help 2>&1 | grep -q "unknown command"
```

### Step 2: Verify fail
```bash
echo "Exit: $? (0=不存在, 符合预期)"
```

### Step 3: Implement
创建 `_lib/cli/rdd_hub_bootstrap_cmd.py`:
- 导出 `cmd_rdd_hub_bootstrap(args: list[str]) -> int`
- 转发到 `bash skills/rdd-hub-bootstrap/scripts/*.sh "$@"`
- 透传退出码

### Step 4: Verify pass
```bash
rddf rdd-hub-bootstrap --help 2>&1 | grep -q "init" && echo "✅ --help 含 init"
```

### Step 5: Commit
```bash
git add _lib/cli/rdd_hub_bootstrap_cmd.py
git commit -m "feat(cli): add rddf rdd-hub-bootstrap subcommand (thin wrapper)"
```

---

## Task 4: `_lib/cli/__init__.py` 注册

### Step 1: Verify current state
```bash
grep -c "cmd_doctor\|cmd_roadmap\|cmd_rdd_hub_bootstrap" _lib/cli/__init__.py
```

### Step 2: Confirm missing
```bash
echo "期望: 0 引用 (当前不存在)"
```

### Step 3: Implement
在 `_lib/cli/__init__.py` 添加:
```python
from _lib.cli.doctor_cmd import cmd_doctor
from _lib.cli.roadmap_cmd import cmd_roadmap
from _lib.cli.rdd_hub_bootstrap_cmd import cmd_rdd_hub_bootstrap
```
路由表添加:
```python
"doctor": cmd_doctor,
"roadmap": cmd_roadmap,
"rdd-hub-bootstrap": cmd_rdd_hub_bootstrap,
```

### Step 4: Verify pass
```bash
rddf --help 2>&1 | grep -E "doctor|roadmap|rdd-hub-bootstrap" && echo "✅ 3 个新命令出现在 rddf --help"
```

### Step 5: Commit
```bash
git add _lib/cli/__init__.py
git commit -m "feat(cli): register doctor, roadmap, rdd-hub-bootstrap in routing table"
```

---

## Task 5: 集成测试

### Step 1: Write failing test
创建 `tests/integration/test_cli_coverage.bats`:
- test_doctor_help_shows_8_categories
- test_doctor_version_output
- test_doctor_exit_code_passthrough
- test_roadmap_help_shows_migrate
- test_rdd_hub_bootstrap_help_shows_init
- test_rddf_help_shows_new_commands
- test_skill_files_not_modified

### Step 2: Verify fail
```bash
bats tests/integration/test_cli_coverage.bats 2>&1 | grep -c "not ok" | grep -q "0" && echo "测试存在" || echo "等待测试通过"
```

### Step 3: Implement
编写完整的 bats 测试用例, 覆盖 AC-1~AC-10.

### Step 4: Verify pass
```bash
bats tests/integration/test_cli_coverage.bats
```

### Step 5: Commit
```bash
git add tests/integration/test_cli_coverage.bats
git commit -m "test(cli): add integration tests for rddf doctor/roadmap/rdd-hub-bootstrap"
```

---

## Task 6: 回归验证

### Step 1: 验证现有测试不回归
```bash
./test.sh --quick
```

### Step 2: 验证 lsp_diagnostics 干净
```bash
# 检查新文件无错误
```

### Step 3: 验证 AC-1~AC-10
```bash
# AC-1: rddf doctor --help exit 0 + 8 categories
# AC-2: rddf doctor --version 输出 rdd-doctor 0.1.0
# AC-3: rddf doctor --category roadmap-refs exit 0
# AC-4: rddf roadmap --help exit 0 + migrate
# AC-5: rddf roadmap migrate --dry-run exit 0
# AC-6: rddf rdd-hub-bootstrap --help exit 0 + init
# AC-7: rddf --help 含 3 个新命令
# AC-8: bats 测试全绿
# AC-9: ./test.sh --quick 全绿
# AC-10: skills/ 内部文件未修改
```

---

## Task 7: 最终验证 + worktree commit

### 聚合 commit (轻量模式)
```bash
git add -A
git status
git log --oneline -5
```