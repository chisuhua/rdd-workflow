# fix-flow-drift-batch-1 Implementation Plan

**Goal:** 修三处契约/行为漂移：① `rdd-verifier/SKILL.md` 的段头正则漏了 `Acceptance` 变体（实现 `protocol.py:34` 有）；② `layout_check.py` 的 missing-required `fix_hint` 对 **file** 条目也加尾斜杠（实测 `create .rddf/roadmap.md/`）；③ `rdd_verify_cmd.py` 的 `_migrate_legacy_state` 在 dry-run 判断**之前**无条件执行 ⇒ `--dry-run` 真写盘（fixture 实测文件被移动）。

**Architecture:** 三处都是小范围修正 + 各自的回归测试，不引入新抽象。

## File Structure

| File | 类型 | Responsibility |
|---|---|---|
| `skills/rdd-verifier/SKILL.md` | 改（1 行） | 段头正则补 `Acceptance` 变体，与 `_lib/verifier/protocol.py:34` 一致 |
| `skills/rdd-doctor/scripts/checks/layout_check.py` | 改（1 处） | `fix_hint` 按 `kind` 分支：dir 带尾斜杠、file 不带 |
| `_lib/verifier/cache.py` | 改（+1 参数） | `migrate_legacy_state(project_root, dry_run=False)`：dry-run 时返回 `("would-move", name)` 不移动 |
| `_lib/cli/rdd_verify_cmd.py` | 改 | 迁移调用受 dry-run 约束；dry-run 报 `Would migrate N`；`--dry-run --stage` 互斥报错 |
| `tests/unit/test_rdd_verifier_protocol_headers.py` | 新 | 三种段头的**行为**断言（parse_acs 均得 N 条）+ SKILL.md 含三变体 |
| `tests/integration/test_doctor_layout_fix_hint.bats` | 新 | fix_hint：dir 有尾斜杠、file 无尾斜杠 |
| `tests/integration/test_rdd_verify_dry_run.bats` | 新 | `--dry-run` 对 legacy fixture 零写入 + 输出含 `Would migrate`；`--dry-run --stage` 报错 |

### Task 1: SKILL.md 正则对齐（行为测试，不做跨文件字符串比对）
- [ ] 测试：`## 验收标准` / `## Acceptance Criteria` / `## Acceptance` 三种段头的 fixture proposal ⇒ `parse_acs` 均得 N 条；另加一条存在性断言（SKILL.md 含三个变体字符串）。
- [ ] 实现：SKILL.md:155 的正则补 `|Acceptance`。

### Task 2: fix_hint 按 kind 分支
- [ ] 测试：dir 条目 ⇒ `create .rddf/<dir>/`；file 条目（`roadmap.md`）⇒ `create .rddf/roadmap.md`（无尾斜杠）。
- [ ] 实现：`layout_check.py:126` 改为 `target = f".rddf/{e.path}/" if e.kind == "dir" else f".rddf/{e.path}"`。

### Task 3: dry-run 零副作用
- [ ] 测试：legacy fixture（`.rddf/state/.ac-verdict-x.json`）+ `--dry-run` ⇒ 目录快照不变、输出含 `Would migrate`；`--dry-run --stage` ⇒ exit 2 且提示互斥。
- [ ] 实现：`cache.migrate_legacy_state` 加 `dry_run` 参数；`rdd_verify_cmd` 把 `parsed.dry_run` 传进去；`--dry-run --stage` 互斥校验。

### Task 4: 全量回归 + 遗留清扫
