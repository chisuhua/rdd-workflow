# fix-commit-gate-generator-fake-green Implementation Plan

> **For agentic workers:** Implement this plan task-by-task, following the TDD 5-step structure below. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `rddf commit-gate init` 不可能产出「恒绿」声明 —— 脚本类入口不再自动推导，工具链类入口要求仓内确有测试件，拒绝路径给出可复制的显式 argv 模板；同时让 spec delta 能**按场景名替代**既有场景。

**Architecture:** 判据仍集中在 `_lib/commit_gate_declaration.py`（单一真源），生成器 `_lib/cli/commit_gate_cmd.py` 只做 IO 与拒绝契约；`generate_full_proposal.py` 的 `_compose_modified()` 从「逐字复制 + 追加」改为「按场景名替换 + 未命中逐字保留」，并补一条本地守恒守卫（openspec <1.7.0 时是唯一守卫）。

**Tech Stack:** Python 3 stdlib（生成器）/ bash + bats（集成）/ pytest（单测）/ openspec 1.14.3。

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `_lib/commit_gate_declaration.py` | 候选表裁决（脚本类移除 / 工具链类加测试件前置）+ 显式来源读取 + 拒绝判据 |
| `_lib/cli/commit_gate_cmd.py` | 拒绝分支（rc=3 / 关键字 / 模板）、`--force` 沿用既有 argv、`atomic_write` |
| `skills/rdd-builder/scripts/generate_full_proposal.py` | `_compose_modified()` 按场景名替代 + `assert_scenarios_conserved()` 本地守卫 |
| `skills/rdd-doctor/scripts/checks/commit_gate_check.py` | `fix_hint` 不再把脚本类仓送进死路 |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_commit_gate_declaration.py` | 候选表裁决 + 测试件前置（改写 2 例、新增 4 例） |
| `tests/unit/test_spec_delta_generator_modified.py` | 场景名替代 + 守恒守卫（新增 2 例） |
| `tests/integration/test_commit_gate_bootstrap.bats` | 改写 3 例既有断言（原断言固化恒绿） |
| `tests/integration/test_commit_gate_bootstrap_noop.bats` | 新增：AC1 / AC2 / AC4 |

---

### Task 1: MODIFIED 按场景名替代

**Files:**
- Modify: `skills/rdd-builder/scripts/generate_full_proposal.py:498-523`
- Test: `tests/unit/test_spec_delta_generator_modified.py`

- [x] **Step 1: Write the failing test**

```python
def test_same_title_scenario_is_replaced_not_duplicated() -> None:
    """作者场景名命中既有场景名 ⇒ 用作者版本**替换**该条（不留两条同名）。"""
    md = (
        "**delta**: modified generator-scope-extraction\n"
        "**语义要求**: generate-proposal-backward-compatible | 系统 SHALL 拒绝空转入口"
        f" | {_EXISTING_SCENARIO} | 语料新增 improvement 时 | 生成器拒绝并给模板\n"
    )
    out = gen_fp.generate_spec_delta(md, "probe")
    assert out.count(f"#### Scenario: {_EXISTING_SCENARIO}") == 1, out
    assert "- **THEN** 生成器拒绝并给模板" in out, out
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_spec_delta_generator_modified.py::test_same_title_scenario_is_replaced_not_duplicated -v`
Expected: FAIL —— `assert 2 == 1`（目前输出两条同名场景）

- [x] **Step 3: Write minimal implementation**

```python
def _split_scenarios(block: str) -> tuple[str, list[tuple[str, str]]]:
    """requirement 头 + [(场景名, 场景块)]（场景块含标题行到下一个 `#### Scenario:` 之前）。"""
    lines = block.split("\n")
    scen_idx = next((i for i, l in enumerate(lines) if l.startswith("#### Scenario:")), len(lines))
    header = "\n".join(lines[:scen_idx]).rstrip()
    groups: list[tuple[str, str]] = []
    for line in lines[scen_idx:]:
        if line.startswith("#### Scenario:"):
            groups.append((line[len("#### Scenario:"):].strip(), line))
        elif groups:
            groups[-1] = (groups[-1][0], groups[-1][1] + "\n" + line)
    return header, [(name, body.rstrip()) for name, body in groups]


def _compose_modified(main_block: str, req: dict[str, str]) -> str:
    header, existing = _split_scenarios(main_block)
    author = f"#### Scenario: {req['scenario']}\n\n- **WHEN** {req['when']}\n- **THEN** {req['then']}"
    name = req["scenario"].strip()
    replaced = [(n, author if n == name else body) for n, body in existing]
    out = [header, "", req["body"], ""]
    for _, body in replaced:
        out += [body, ""]
    if not any(n == name for n, _ in existing):
        out += [author, ""]
    return "\n".join(out).rstrip()
```

（`existing` 里未命中的场景体原样保留；命中则整块替换；作者新场景才追加。）

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_spec_delta_generator_modified.py -v`
Expected: PASS（含既有 4 例仍绿）

- [x] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交（`COMMIT_IN_EXECUTE=yes` 可逐任务提交，不推荐）。

---

### Task 2: 本地场景守恒守卫

**Files:**
- Modify: `skills/rdd-builder/scripts/generate_full_proposal.py`（新增 `assert_scenarios_conserved`，在 `_compose_modified` 之后调用）
- Test: `tests/unit/test_spec_delta_generator_modified.py`

- [x] **Step 1: Write the failing test**

```python
def test_conservation_guard_refuses_dropped_scenario() -> None:
    """既有场景名不在输出里 ⇒ 拒绝（openspec <1.7.0 时这是唯一守卫）。"""
    main = "### Requirement: R\n\nbody\n\n#### Scenario: keep me\n\n- **WHEN** a\n- **THEN** b"
    out_block = "### Requirement: R\n\nnb\n\n#### Scenario: another\n\n- **WHEN** a\n- **THEN** b"
    with pytest.raises(ValueError) as exc:
        gen_fp.assert_scenarios_conserved(main, out_block)
    assert "keep me" in str(exc.value), str(exc.value)
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_spec_delta_generator_modified.py::test_conservation_guard_refuses_dropped_scenario -v`
Expected: FAIL —— `AttributeError: module has no attribute 'assert_scenarios_conserved'`

- [x] **Step 3: Write minimal implementation**

```python
def assert_scenarios_conserved(main_block: str, out_block: str) -> None:
    """既有场景名集合 ⊆ 输出场景名集合；否则拒绝（**不依赖 openspec 版本**）。"""
    _, existing = _split_scenarios(main_block)
    _, produced = _split_scenarios(out_block)
    missing = [n for n, _ in existing if n not in {p for p, _ in produced}]
    if missing:
        raise ValueError("MODIFIED 丢掉了既有 Scenario：" + " / ".join(missing)
                         + " ⇒ 拒绝生成（本地守恒守卫）")
```

并在 `generate_spec_delta()` 的 modified 分支里 `assert_scenarios_conserved(block, composed)` 之后才 append。

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_spec_delta_generator_modified.py -v`
Expected: PASS

- [x] **Step 5: Defer commit**

同 Task 1。

---

### Task 3: 脚本类入口不再自动推导

**Files:**
- Modify: `_lib/commit_gate_declaration.py:26-35`（`CANDIDATES`）与 `:72-84`（`derive_verify_commands`）
- Test: `tests/unit/test_commit_gate_declaration.py`

- [x] **Step 1: Write the failing test**

```python
def test_script_entry_points_are_not_auto_derived(tmp_path):
    """脚本类入口（test.sh / package.json::scripts.test / Makefile::test:）**不再推导**。"""
    _touch(tmp_path, "test.sh", "#!/bin/sh\nprint_help\n")
    assert derive_verify_commands(tmp_path) is None
    (tmp_path / "test.sh").unlink()
    _touch(tmp_path, "package.json", json.dumps({"scripts": {"test": "echo ok"}}))
    assert derive_verify_commands(tmp_path) is None
    (tmp_path / "package.json").unlink()
    _touch(tmp_path, "Makefile", "test:\n\t@echo no tests\n")
    assert derive_verify_commands(tmp_path) is None
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_commit_gate_declaration.py::test_script_entry_points_are_not_auto_derived -v`
Expected: FAIL —— `assert [['./test.sh']] is None`

- [x] **Step 3: Write minimal implementation**

```python
CANDIDATES: tuple[dict, ...] = (
    # ⚠ 脚本类入口（test.sh / package.json::scripts.test / Makefile::test:）**故意缺席**：
    #    裸调用是否执行验证不可静态判定（本仓 test.sh 无参只打印 help 并 exit 0）
    #    ⇒ 只能来自显式来源（既有合法声明），否则拒绝。
    {"requires": "pyproject.toml", "argv": ["python3", "-m", "pytest"], "tool": "pytest"},
    {"requires": "pytest.ini", "argv": ["python3", "-m", "pytest"], "tool": "pytest"},
    {"requires": "setup.cfg", "argv": ["python3", "-m", "pytest"], "tool": "pytest"},
    {"requires": "go.mod", "argv": ["go", "test", "./..."], "tool": "go"},
    {"requires": "Cargo.toml", "argv": ["cargo", "test"], "tool": "cargo"},
)
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_commit_gate_declaration.py -v`
Expected: PASS

- [x] **Step 5: Defer commit**

同 Task 1。

---

### Task 4: 工具链类要求仓内存在测试件

**Files:**
- Modify: `_lib/commit_gate_declaration.py`（新增 `_has_test_files`，`derive_verify_commands` 调用）
- Test: `tests/unit/test_commit_gate_declaration.py`

- [x] **Step 1: Write the failing test**

```python
@pytest.mark.parametrize("evidence,tool_file,expected", [
    ("pyproject.toml", "tests/test_core.py", ["python3", "-m", "pytest"]),
    ("go.mod", "pkg/a_test.go", ["go", "test", "./..."]),
    ("Cargo.toml", "tests/it.rs", ["cargo", "test"]),
])
def test_toolchain_needs_test_files(tmp_path, evidence, tool_file, expected):
    _touch(tmp_path, evidence, "")
    assert derive_verify_commands(tmp_path) is None          # 零测试件 ⇒ 不推导
    _touch(tmp_path, tool_file, "")
    assert derive_verify_commands(tmp_path) == [expected]     # 有测试件 ⇒ 推导
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_commit_gate_declaration.py::test_toolchain_needs_test_files -v`
Expected: FAIL —— 零测试件时仍返回 argv

- [x] **Step 3: Write minimal implementation**

```python
_TEST_FILE_GLOBS = {
    "pytest": ("test_*.py", "*_test.py"),
    "go": ("*_test.go",),
    "cargo": ("tests/**/*.rs", "src/**/*.rs"),  # cargo 另需 #[test] 命中，见下
}


def _has_test_files(root: Path, tool: str) -> bool:
    for pattern in _TEST_FILE_GLOBS.get(tool, ()):
        if any(root.glob(pattern)):
            if tool != "cargo":
                return True
            for p in root.glob(pattern):
                try:
                    if "#[test]" in p.read_text(encoding="utf-8"):
                        return True
                except (OSError, UnicodeDecodeError):
                    continue
    return False
```

`derive_verify_commands` 在命中候选后追加：`if candidate.get("tool") and not _has_test_files(root, candidate["tool"]): continue`。

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_commit_gate_declaration.py -v`
Expected: PASS

- [x] **Step 5: Defer commit**

同 Task 1。

---

### Task 5: 拒绝分支 + 显式来源沿用 + atomic_write

**Files:**
- Modify: `_lib/cli/commit_gate_cmd.py:51-100`
- Test: `tests/integration/test_commit_gate_bootstrap.bats`（改写 3 例）、`tests/integration/test_commit_gate_bootstrap_noop.bats`（新增）

- [x] **Step 1: Write the failing test**

```bash
@test "commit-gate init: 空转脚本入口 ⇒ rc=3 + 不写文件 + 给显式 argv 模板" {
  printf '#!/bin/sh\nif [ -z "$1" ]; then echo "usage"; exit 0; fi\n' > test.sh
  chmod +x test.sh
  run _run_init
  [ "$status" -eq 3 ]
  [ ! -f .rddf/commit-gate.json ]
  [[ "$output" == *"需要显式 argv"* ]]
  [[ "$output" == *'"verify_commands"'* ]]
}

@test "commit-gate init --force: 既有合法声明即显式来源 ⇒ 逐字沿用 + 提示未重新推导" {
  mkdir -p .rddf
  printf '{"verify_commands":[["./test.sh","--verify"]]}\n' > .rddf/commit-gate.json
  printf '#!/bin/sh\necho verify\n' > test.sh && chmod +x test.sh
  run _run_init --force
  [ "$status" -eq 0 ]
  [[ "$output" == *"未重新推导"* ]]
  run python3 -c "import json;print(json.load(open('.rddf/commit-gate.json'))['verify_commands'])"
  [[ "$output" == *"'--verify'"* ]]
}

@test "commit-gate init --force: 拒绝时不改动既有声明（字节相等）" {
  mkdir -p .rddf
  printf '{"verify_commands":[["echo"]]}\n' > .rddf/commit-gate.json
  cp .rddf/commit-gate.json /tmp/opencode/cg-before.json
  run _run_init --force
  [ "$status" -eq 3 ]
  run cmp -s .rddf/commit-gate.json /tmp/opencode/cg-before.json
  [ "$status" -eq 0 ]
}
```

- [x] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_commit_gate_bootstrap_noop.bats`
Expected: FAIL —— 现状 rc=0 且写出 `[["./test.sh"]]`

- [x] **Step 3: Write minimal implementation**

```python
_REFUSAL_RC = 3
_REFUSAL_KEY = "需要显式 argv"


def _explicit_source(project_root: Path) -> list[list[str]] | None:
    """既有**合法且非 shell** 声明即显式来源；否则 None。"""
    decl = read_declaration(project_root)
    cmds = decl.get("verify_commands") if isinstance(decl, dict) else None
    if not cmds or is_shell_declaration(cmds):
        return None
    return cmds


# cmd_commit_gate 内，替换 verify_commands 推导段：
if target.is_file() and force:
    reused = _explicit_source(project_root)
    if reused is not None:
        print("ℹ️  沿用既有声明的 verify_commands（未重新推导）")
        verify_commands = reused
    else:
        verify_commands = derive_verify_commands(project_root)
else:
    verify_commands = derive_verify_commands(project_root)

if verify_commands is None:
    print(f"❌ 找不到可自动推导的验证入口 ⇒ 拒绝生成（{_REFUSAL_KEY}）", file=sys.stderr)
    print("   脚本类入口（test.sh / npm test / make test）需要显式 argv ⇒ 手写声明：", file=sys.stderr)
    print(manual_template(), file=sys.stderr)
    return _REFUSAL_RC
```

`--force` + 既有非法声明（shell）⇒ 也走 `derive_verify_commands`，其结果在本仓为 None ⇒ rc=3（不覆盖文件）。

- [x] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_commit_gate_bootstrap_noop.bats tests/integration/test_commit_gate_bootstrap.bats`
Expected: PASS（bootstrap 的 3 例已按新契约改写）

- [x] **Step 5: Defer commit**

同 Task 1。

---

### Task 6: 文案同步（doctor fix_hint / SKILL.md / CHANGELOG）

**Files:**
- Modify: `skills/rdd-doctor/scripts/checks/commit_gate_check.py:71-74`、`skills/rdd-doctor/SKILL.md`（commit-gate 行）、`CHANGELOG.md`

- [x] **Step 1: Write the failing test**

```python
def test_fix_hint_offers_both_paths():
    """脚本类仓走 init 会 rc=3 ⇒ 提示必须同时给「init 生成 / 手写声明」。"""
    findings = run(tmp_path_with_no_declaration)
    hint = findings[0].fix_hint
    assert "rddf commit-gate init" in hint and "手写" in hint
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_commit_gate_doctor.py -k fix_hint -v`
Expected: FAIL（现文案只有 init 一条路）

- [x] **Step 3: Write minimal implementation**

```python
fix_hint=(
    "未声明 ⇒ 门禁三判据不设门禁（ADR D3 明文决策）⇒ 该仓的 commit 没有跑过任何验证命令。"
    " 启用：工具链类仓可直接 `rddf commit-gate init`；脚本类入口（test.sh / npm test / make test）"
    "需**手写** `.rddf/commit-gate.json` 给出显式 argv（init 会以 rc=3 拒绝并打印模板）"
),
```

同时 `skills/rdd-doctor/SKILL.md` 的 commit-gate 行、「修法分别给…」一句按同口径改写；`CHANGELOG.md` 的「生成器假绿」段改为指向本 change。

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_commit_gate_doctor.py -v`
Expected: PASS

- [x] **Step 5: Defer commit**

同 Task 1。

---

### Task 7: D3 契约措辞（逐字 → 按场景名）

**Files:**
- Modify: `skills/rdd-builder/SKILL.md`（D3 spec-delta 契约 ②）、`skills/rdd-builder/scripts/generate_full_proposal.py`（docstring）

- [x] **Step 1: Write the failing test**

```python
def test_skill_doc_states_title_keyed_conservation():
    text = (_ROOT / "skills/rdd-builder/SKILL.md").read_text(encoding="utf-8")
    assert "按场景名" in text and "逐字保留全部既有 Scenario" not in text, "D3 措辞未更新"
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_spec_delta_generator_modified.py::test_skill_doc_states_title_keyed_conservation -v`
Expected: FAIL

- [x] **Step 3: Write minimal implementation**

把该段 ② 改为：

```markdown
### ② `**delta**: modified <capability>` ⇒ `## MODIFIED Requirements` + **按场景名保留**

- 块内**按场景名**保留 main spec 该 requirement 的**全部既有 Scenario**：作者场景名命中 ⇒ 用作者版本**替换**正文；
  未命中的既有场景**逐字保留**；作者新场景追加。缺一个场景名 ⇒ 归档时 openspec 直接 abort（1.7.0+ 原生检查；
  更早版本由生成器内的本地守恒守卫兜底）。
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_spec_delta_generator_modified.py -v`
Expected: PASS

- [x] **Step 5: Defer commit**

同 Task 1。

---

### Task 8: 重生成本 change 自己的 delta（AC5）

**Files:**
- Modify: `openspec/changes/fix-commit-gate-generator-fake-green/specs/commit-gate-declaration-bootstrap/spec.md`

- [x] **Step 1: Write the failing test**

```bash
@test "本 change 的 delta 只保留一条同名场景（不是 D 形态）" {
  delta=openspec/changes/fix-commit-gate-generator-fake-green/specs/commit-gate-declaration-bootstrap/spec.md
  run grep -c "^#### Scenario: A project with a test entry point gets a declaration" "$delta"
  [ "$output" -eq 1 ]
  run grep -c "THEN\` the command exits with the dedicated refusal code" "$delta"
  [ "$output" -eq 1 ]
}
```

- [x] **Step 2: Run test to verify it fails**

Run: 手工 `grep -c '^#### Scenario: A project with a test entry point gets a declaration' <delta>`
Expected: `2`（D 形态：旧场景 + 同名新场景）

- [x] **Step 3: Write minimal implementation**

```bash
OUTPUT_MODE=spec-delta CHANGE_NAME=fix-commit-gate-generator-fake-green \
  IMPROVEMENTS_PATH=.rddf/improvements/fix-commit-gate-generator-fake-green.md \
  PROJECT_ROOT="$PWD" \
  python3 skills/rdd-builder/scripts/generate_full_proposal.py \
  > /tmp/opencode/delta.tmp && mv /tmp/opencode/delta.tmp \
  openspec/changes/fix-commit-gate-generator-fake-green/specs/commit-gate-declaration-bootstrap/spec.md
openspec validate --strict fix-commit-gate-generator-fake-green
```

- [x] **Step 4: Run test to verify it passes**

Run: 同上 grep ⇒ `1`；`openspec validate --strict` ⇒ valid。
Expected: PASS

- [x] **Step 5: Defer commit**

同 Task 1。

---

### Task 9: 全量回归（AC9）

**Files:**
- Modify: `tests/fixtures/proposals_corpus_snapshot.json`（若语料指纹变化则刷新）

- [x] **Step 1: Write the failing test**

```bash
./test.sh --full --regression 2>&1 | tail -20
```

Expected: 全绿或仅 `tests/KNOWN_FAILURES.txt` 已登记的已知失败。

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_generate_full_proposal_corpus.py -q`
Expected: 若 improvement 正文变化 ⇒ FAIL「快照缺 …」

- [x] **Step 3: Write minimal implementation**

```bash
python3 tests/fixtures/refresh_proposals_corpus_snapshot.py
```

- [x] **Step 4: Run test to verify it passes**

Run: `./test.sh --full --regression`
Expected: ✅ 全绿（或仅 baseline 已知失败）；`openspec validate --all --strict` 0 ERROR。

- [x] **Step 5: Defer commit**

全部 task 完成后由 P3 归档流程统一提交（本仓 `commit-gate` 会在 commit 时跑 `--gates` + `--quick`）。
