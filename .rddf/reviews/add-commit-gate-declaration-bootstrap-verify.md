# verify: add-commit-gate-declaration-bootstrap

> **验收对象**：本 change 的实现（worktree 分支 `openspec/add-commit-gate-declaration-bootstrap`，1 个提交 `6439ae9a`）
> **验收时间**：2026-11-27
> **执行角色**：builder（角色内建 verifier 契约 · **本地验收路径**）
> **判据来源**：`proposal.md` 的 `## 验收标准`（AC1–AC8）
> **范围**：**只判 rdd-workflow 半边** —— 「未声明留痕」属 **U7b（治理仓 architect 轨）**，不在本 change。

## 分流判定（为什么走本地验收）

| 条件 | 实测 | 判定 |
|---|---|---|
| ① change 存在 + 有 AC 段 | `proposal.md` 含 `## 验收标准`（8 条） | ✅ |
| ② P3 archive gate 触发 | 主仓 `iteration.json` 该 change `tasks_done=0`（P0 快照）；批量分流扫主仓、实现落在 worktree | ❌ |
| ③ `rdd-verifier` skill 可加载 | installed | ✅ |

⇒ 条件② 不满足 ⇒ **本地验收**。

## 逐条判定（AC1–AC8）

| AC | 判据 | 证据 | 判定 |
|:--:|---|---|:--:|
| AC1 | 有声明的入口 ⇒ 生成声明，argv 指向**仓内既有**入口，且**不代 add** | `tests/integration/test_commit_gate_bootstrap.bats::test.sh 存在 ⇒ 生成 [[./test.sh]] 且不代 add`（断言 `git diff --cached --name-only` 为空） | ✅ |
| AC2 | 无入口 ⇒ **不生成** + 手工模板 | 同文件 `找不到入口 ⇒ 不生成 + 给手工模板`（断言文件不存在 + 输出含模板）；另 `package.json` 无 `scripts.test` ⇒ 不算命中 | ✅ |
| AC3 | 空壳声明 ⇒ doctor WARNING | `tests/unit/test_commit_gate_doctor.py::test_shell_declaration_is_reported`（`true` ⇒ 「空壳」） | ✅ |
| AC4 | 未 tracked ⇒ doctor WARNING | 同文件 `test_untracked_declaration_is_reported`（真 git 仓库 + 未 add） | ✅ |
| AC5 | 未声明 ⇒ doctor WARNING（点名期望路径） | 同文件 `test_missing_declaration_is_reported`（`file == .rddf/commit-gate.json` + 给 `rddf commit-gate init`） | ✅ |
| AC6 | 非平凡判据是**枚举**且与 `--help` 同源 | `tests/unit/test_commit_gate_declaration.py`：`SHELL_COMMANDS == ("true","echo",":","exit 0")`、两类必拒（单条空壳 / 两条不算空壳 / 真命令不算）、`test_help_text_renders_the_same_enumeration` | ✅ |
| AC7 | 变异：关非平凡检测 ⇒ AC3 红；关未 tracked ⇒ AC4 红 | 实测：① `is_shell_declaration` 短路为 `False` ⇒ **5 failed**；② doctor 的未 tracked 分支短路 ⇒ **1 failed**；回滚后 24 passed；`MUTATION` 计数 = 0 | ✅ |
| AC8 | `./test.sh --gates` + `./test.sh --unit` 全绿 + `openspec validate --strict` | gates ⇒ **ALL PASSED**（`openspec validate --all` 168/168）；`openspec validate <change> --strict` ⇒ **valid**；unit ⇒ **3819 passed / 2 skipped / 7 failed**（7 = 既有 worktree 环境性：6 个根解析 + 1 个语料快照，后者已刷新） | ✅ |

## 验证步骤（verifier 契约 1–5 步）

1. **静态检查**：`./test.sh --gates` ⇒ ALL PASSED；`python3 -m ruff check` 改动文件 ⇒ 无新增。
2. **单元**：本 change 面 41 例全绿（含 doctor 注册契约 `test_doctor_main.py` 6 例）。
3. **集成**：bats 5/5。
4. **边界与错误路径**：无入口 / 已有声明 / `--dry-run` / `--force` / 解析失败 / 三面互斥 —— 各有用例。
5. **遗留清扫**：`TODO|FIXME|MUTATION|pytest.skip` ⇒ 零残留。

### 环境性失败（非本次引入）

`test_resolve_project_root_contract_python.py`（5）+ `test_skills_lib_python_resolve_project_root.py`（1）：
worktree 下实现经 `--git-common-dir` 解析到主仓、测试期望 worktree 根；主仓同组全绿 ⇒ 既有不一致。

## 已知遗留（登记，不静默）

| # | 遗留 | 归属 |
|---|---|---|
| 1 | 「未声明留痕」（检测 ≠ 拦截）| **U7b（治理仓）** —— 原 AC4 已移出，本 change 不碰治理仓 |
| 2 | 候选表只覆盖 6 类入口（test.sh / npm / make / pytest / go / cargo） | 设计取舍（不猜）；新增语言时**加一行候选表** |
| 3 | 生成器不代 `git add`（声明须 tracked 才生效） | 有意（D3 的 git-tracked 要求是**作者**的责任；doctor 面③会提示） |

## 已用轮次

**1 / 3**（`RDDF_VERIFIER_MAX_LOOPS=3`）。失败项：**0**。

## 归档后补正（2026-11-28 · 归档 commit `db5786ec` 之后）

| 项 | 发现 | 处置 |
|---|---|---|
| **AC6 的用户面假绿** | AC6 原来只测**函数面**（`cmd_commit_gate(["--help"])` ⇒ 我自己的 `_print_help`，含枚举）；但**用户实际执行的** `rddf commit-gate --help` 走**注册表**的 `_SUBCOMMAND_DESCRIPTION["commit-gate"]`（一行描述，**没有枚举**）⇒ 「`--help` 文案里的枚举 == `SHELL_COMMANDS`」这条**在用户面上不成立** | ✅ 已补：help 条目改为**从常量渲染**（`f"... Shell 判据（同源枚举）: {shell_commands_display()}"`）+ 新增用例 `test_registry_help_renders_the_same_enumeration`（直接断言 `_SUBCOMMAND_DESCRIPTION["commit-gate"]` 含全部枚举）；实测 `rddf commit-gate --help` 现输出 `Shell 判据（同源枚举）: true / echo / : / exit 0` |

⇒ **教训**：判据必须打**用户面**（真实 CLI 入口 / 真实文件），不能只打函数面 —— 函数面绿 ≠ 用户看到的东西对。
