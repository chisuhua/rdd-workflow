# fix-review-debt-recorded-gate

**优先级**: P2 | **来源**: Oracle 复核 2026-08-24(G5 + 初版 P1-B + 初版 P2-C 三合并)
**阶段**: v2.1.x | **分类**: infra-quality | **类型**: fix

## 架构依据

ADR-0014 §决策 5 规定 `gate.py` 注册 `review_debt_recorded`(warning 级)检查,确保用户在 `guide-ship` Phase 2.5 review 阶段记录债务或显式跳过。

**Oracle 复核发现三个深层问题**:

### 问题 1:触发时机错位(初版 P1-B 升级版)

`_check_review_debt_recorded`( `_lib/gate.py:341-370` )跑 `git diff HEAD -- <lang-files>`。但按仓库 Worktree Commit Flow(`AGENTS.md` 明确说明):

> execute 不逐任务 commit,统一聚合 commit 在 worktree 内 1 次,Phase 2.7

这意味着 ship_done gate 触发时,worktree 已 commit,diff **已空** → `new_todos` 恒空 → 恒通过 → **整个 gate 几乎 dead**。语言范围仅 `.cpp/.h/.py/.ts` 仅是表面问题。

### 问题 2:cwd 相对路径静默失效

`imp_dir = ".rddf/improvements"` 是相对于 git cwd 的相对路径。若 gate 跑在非项目根(罕见但真实:某些 CI runner 在子目录执行),函数 `os.path.isdir(imp_dir)` 返回 False → return `(False, "warning")` → **阻断 archive,但 stderr 无任何解释**——用户得到一个莫名其妙的"warning"。

### 问题 3:`except Exception: return (True, None)` 吞错

第 370 行的裸 except 把所有错误(`IOError`、`OSError`、`PermissionError` 等)静默转为"通过"——任何故障都被掩盖,运维可见性归零。初版 P2-C 的"debt 绑定宽松"也是同一函数内的问题,合并处理。

## 范围

### In Scope

1. **PR-5.1**:**重新设计 gate 触发时机**。`gate.py:341` 删除该检查函数,改为由 `skills/guide-ship/scripts/ship_review.sh` 在 Phase 2.5 commit **之前**显式调用一个新 helper `check_review_debt_persisted`。helper 返回值用于 ship_review.sh 用户交互菜单的选项 1-3-5(债务未记录 → 提示;已记录 → 跳过)。
2. **PR-5.2**:绝对路径。helper 接收 `ctx['project_root']` 作为必填参数,所有路径用 `Path(project_root) / '.rddf' / 'improvements'` 构造,**禁止**相对路径。
3. **PR-5.3**:收窄 except。仅 catch `(OSError, IOError, PermissionError)`,其余(`ValueError`, `KeyError` 等)raise。无 `except Exception`。
4. **PR-5.4**:扩展语言 glob。覆盖 `.go .rs .java .rb .sh .cpp .h .hpp .py .ts .tsx .js .jsx .c .cs .swift .kt .scala .php`(共 17 种)。
5. **PR-5.5**:debt mtime 绑定。仅接受 `mtime > execute_finished_at` 的 debt 文件;历史 debt 文件不再"通过"当前 change。
6. **PR-5.6**:迁移 `gate.py:341-370` 的函数为新模块 `_lib/review_debt_checker.py`,原函数保留为 deprecated shim(1 个版本过渡,留 audit log)。

### Out of Scope

- **不**改 `guide-ship/SKILL.md:387-475` Phase 2.5 既有菜单(只让 helper 在 Phase 2.5 commit 前介入)
- **不**重写 `ship_review.sh` 整个脚本(只增加 1 行 helper 调用)
- **不**改 `proposal-suggestions.md` 表格 schema
- **不**为 helper 引入新依赖

## 关键场景

### 场景 A:Go 项目新增 TODO(主场景,验证语言扩展)

**GIVEN** `.go` 文件新增 `// TODO: refactor this part`
**WHEN** Phase 2.5 commit 前 ship_review.sh 调 helper
**THEN**
- helper 扫 `.go` 文件(18 种语言 glob 含 `.go`)
- 探测 `.rddf/improvements/cleanup-<change>-debt.md` 是否存在且 mtime > execute_finished_at
- 若不存在 → 提示用户选项 1-3(范围內 / side-effect / arch drift)
- 若存在 → silent pass

### 场景 B:cwd 非项目根(原 P2-D 类问题升级)

**GIVEN** 用户在 `project-root/subdir/` 跑 `rddf doctor` 等触发 gate 的命令
**WHEN** helper 执行
**THEN**
- 必填参数 `project_root` 来自 `ctx`,绝对路径
- `Path(project_root) / ".rddf/improvements"` 解析正确
- 无 silent failure

### 场景 C:磁盘故障(收窄 except)

**GIVEN** `.rddf/improvements/` 目录无读权限或被删
**WHEN** helper 执行
**THEN**
- `except PermissionError as e:` → 记录具体 stderr 提示 `cannot read .rddf/improvements: <reason>`
- 返回 `(False, "warning")`(与 disk-error 相符的警告)
- 不静默 pass

### 场景 D:Rust 项目债务(语言扩展第二例)

**GIVEN** `.rs` 文件新增 `// TODO: handle error properly`
**WHEN** Phase 2.5 helper 执行
**THEN**
- 扫描 `.rs`(glob 含)
- 与场景 A 行为一致

### 场景 E:历史 debt 文件(防宽松绑定)

**GIVEN** Phase 2.5 执行前,`.rddf/improvements/old-debt-2024.md` 已存在(mtime 旧)
**WHEN** 当前 change 新增 TODO
**THEN**
- helper 探测到 mtime 早于 execute_finished_at
- 不视作有效 debt 文件
- 提示用户"发现新 TODO,但未见对应 debt 文件"

## 技术约束

### helper 函数签名

```python
# _lib/review_debt_checker.py
def check_review_debt_persisted(
    project_root: str,                          # 必填,绝对路径
    change_name: str,                           # 必填,对应当前 change
    execute_finished_at: datetime,              # 必填,gate 决定 mtime 比较的阈值
    extensions: set[str] | None = None,         # 可选,默认 17 种
) -> ReviewDebtVerdict:
    """
    Returns (persisted: bool, reason: str, found_count: int, new_todos: list[str])
    persisted=True 表示当前 change 的债务已记录到 .rddf/improvements/<change>-debt.md
    """
```

### helper 与 gate 关系

```
Phase 2 execute 完成 (tasks.md all [x])
   ↓
Phase 2.5: ship_review.sh 调用 helper → 提示用户 → 用户选项 1/2/3/5
   ↓     (helper 返回 false → 继续提示;返回 true → 跳过)
ship_review.sh 调用一次 (单一跳转)
   ↓
Phase 2.7 worktree commit (aggregate)
   ↓
Phase 3 archive → 不再触发 helper(shim 已删除)
```

### gate.py 删除原函数

`_check_review_debt_recorded` 不再 registered。`_DEFAULT_CHECKS["arch_done"]` / `["plan_done"]` / `["ship_done"]` 都不含此 check。否则即使 helper 改对了位置,gate 仍会去跑 dead code。

### 17 种扩展 glob

```python
DEFAULT_EXTENSIONS = frozenset({
    '.go', '.rs', '.java', '.rb', '.sh',
    '.cpp', '.c', '.h', '.hpp',
    '.py', '.ts', '.tsx', '.js', '.jsx',
    '.cs', '.swift', '.kt', '.scala', '.php',
})
```

总 19 种(初版 P1-B 提到 17 种,实际多 2 种,本提案更新)。

## 验收标准

### 功能验收

- [ ] **AC-1**:`ship_review.sh` 在 Phase 2.5 commit 前调用 helper(新函数)
- [ ] **AC-2**:helper 不在 ship_done gate 运行时被调用(原 dead path 删除)
- [ ] **AC-3**:Go / Rust / Java / Ruby / Shell 项目债务被 helper 识别
- [ ] **AC-4**:helper 使用 `ctx['project_root']` 绝对路径,不依赖 cwd
- [ ] **AC-5**:`except` 仅 catch `(OSError, IOError, PermissionError)`,其他 raise
- [ ] **AC-6**:历史 debt 文件(mtime 早于 execute_finished_at)不算当前 change 的 debt
- [ ] **AC-7**:helper 函数返回 `ReviewDebtVerdict` dataclass,含 4 字段(persisted / reason / found_count / new_todos)

### 测试

- [ ] 4 unit 测试(场景 A + C + D + E 各一)
  - `tests/unit/test_review_debt_checker.py` 新建
  - `test_go_project_todo_detected`
  - `test_permission_error_not_swallowed`
  - `test_rust_project_todo_detected`
  - `test_historic_debt_file_not_counted`
- [ ] 1 unit 测试(项目根绝对路径)
  - `test_helper_uses_project_root_not_cwd`
- [ ] 1 integration 测试(ship_review.sh 集成)
  - `tests/integration/test_ship_review_phase25_helper.bats`(或在 test_ship_review_extraction.bats 加 case)
- [ ] 1 regression gate(G1 之前 gate.py:341 删除后)
  - `tests/unit/test_gate_no_review_debt.py` 验证 `review_debt_recorded` 不在 `_DEFAULT_CHECKS` 中

### 不变量

- `_lib/gate.py:341-370` 函数可保留为 shim,1 版本内删除(留 `@deprecated` docstring)
- 不改 `proposal-suggestions.md` schema
- 不改 `archive.sh::archive_change` 任何逻辑

## 依赖

- **前置**:无
- **依赖**:与 PR-1(CLI opt-in gate)和 PR-2(close hook 修复)**独立**——本提案只触碰 detect 阶段的 review 债务检查
- **后续**:helper 输出(`new_todos`)可作为未来"自动 debt change"提案的输入(由独立 ADR 决定,不在本 PR scope)

## 相关 ADR/文档

- [ADR-0014 §决策 5](docs/adr/ADR-0014-review-phase-and-debt-reflow.md) gate 机制约束
- [Oracle 复核记录](docs/architecture/improvement-check-mechanisms.md#五oracle-复核) §5.3 G5 + 5.2 P1-B / P2-C
- `_lib/gate.py:341-370` 当前实现
- `skills/guide-ship/scripts/ship_review.sh` 调用点
- `AGENTS.md` "Worktree Commit Flow" trigger timing 约束
