# verify: improve-worktree-build-hint

> **验收对象**：本 change 的**实现**（worktree 分支 `openspec/improve-worktree-build-hint`，1 个提交 `bccd9884`）
> **验收时间**：2026-11-27
> **执行角色**：builder（角色内建 verifier 契约 · **本地验收路径**）
> **判据来源**：`proposal.md` 的 `## Acceptance`（AC1–AC5）

## 分流判定（为什么走本地验收，而不是 `rdd-verifier` skill）

| 条件 | 实测 | 判定 |
|---|---|---|
| ① change 存在 + 有 AC 段 | `openspec/changes/improve-worktree-build-hint/proposal.md` 含 `## Acceptance`（5 条） | ✅ |
| ② P3 archive gate 触发 | 主仓 `iteration.json` 该 change `tasks_done=0`（P0 快照）；批量分流扫主仓、实现落在 worktree | ❌ |
| ③ `rdd-verifier` skill 可加载 | installed | ✅ |

⇒ 条件② 不满足 ⇒ **本地验收**。

## 逐条判定（AC1–AC5）

| AC | 判据 | 证据 | 判定 |
|:--:|---|---|:--:|
| AC1 | worktree 无 `build/` ⇒ 输出含提示行 | `tests/integration/test_phase2_build_hint.bats::phase2: a worktree without build/ gets the hint on stderr`（断言含 `build/` + 「后台任务」+「勿 sleep 轮询」）—— 修复前红（无提示）⇒ 修复后绿 | ✅ |
| AC2 | worktree 已有 `build/` ⇒ **不**含提示行（防噪音） | 同文件 `phase2: an existing build/ directory means no hint (no noise)`（预置 `.rddf/wt/add-x/build/`） | ✅ |
| AC3 | 判别力：检测条件反相 ⇒ AC1 必须红 | 实测（临时把 `[ ! -d ... ]` 反相为 `[ -d ... ]`）⇒ **AC1 与 AC2 两例同时红**，回滚后 4 例全绿；`grep -c MUTATION` == 0 | ✅ |
| AC4 | 通道：提示行在 **stderr**，stdout 不含 | 同文件 `phase2: the hint does not pollute stdout`（单独抓 stdout 再断言不含该行） | ✅ |
| AC5 | 门：`./test.sh --gates` 与 `./test.sh --bats` 全绿 | gates ⇒ **ALL PASSED**（`openspec validate --all` 167/167）；bats：新增 4 例 + `test_phase2_commit_gate.bats` 8 例全绿；`openspec validate <change> --strict` ⇒ valid；unit ⇒ 3786 passed（6 = 既有 worktree 环境性） | ✅ |

## 验证步骤（verifier 契约 1–5 步）

1. **静态检查**：`./test.sh --gates` ⇒ **ALL PASSED**；`bash -n` 脚本 ⇒ syntax ok。
2. **单元测试**：`pytest tests/unit` ⇒ **3786 passed / 2 skipped / 6 failed**（6 = 既有环境性）。
3. **集成**：新增 bats 4 例全绿；既有 phase2 bats 8 例全绿（**零回归**）。
4. **边界与错误路径**：无 build / 有 build / lightweight 模式 / stdout 与 stderr 分通道 —— 四种情形各有独立用例。
5. **遗留清扫**：`TODO|FIXME|MUTATION|pytest.skip` ⇒ 零残留。

### 环境性失败（**非本次引入**）

`tests/unit/test_resolve_project_root_contract_python.py`（5）+ `test_skills_lib_python_resolve_project_root.py`（1）：
worktree 下实现经 `--git-common-dir` 解析到主仓，测试期望 worktree 根；主仓跑同组全绿 ⇒ 既有不一致，另案。

## 已知遗留（登记，不静默）

| # | 遗留 | 归属 |
|---|---|---|
| 1 | **不实现**任何构建缓存机制（ccache / 复用主仓 build / 只构建 target） | **项目侧**决策（本 change 的 Out of Scope 明确） |
| 2 | 提示不检测项目是否已用 ccache ⇒ 已用 ccache 的项目也会看到这行 | 有意（文案只做引用，不做分支；场景 3 明确） |
| 3 | `iteration.json` 的 `tasks_done` 不刷新；worktree 模式 6 个 project-root 失败 | U5 同类 / 另案 |

## 已用轮次

**1 / 3**（`RDDF_VERIFIER_MAX_LOOPS=3`）。失败项：**0**。
