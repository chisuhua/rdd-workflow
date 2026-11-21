# retire-general-status-guide-requirement 台账（2026-11-22）

## 范围

退役 `openspec/specs/general/spec.md` 的 `general-status-guide-skill-revision` Requirement
（88 行 / 14 条 Scenario），主体 `skills/guide.md` 与 `skills/status.md` **都不存在**（已归档
`docs/legacy/skills/{guide,status}`）；连带修正 `general-harden-doc-consistency` 的死判据
（Group B）与 `test_frontmatter_dupkey.bats` 的 glob 塌陷。

## 审查链

| 轮 | 结论 | 处置 |
|---|---|---|
| 1 | **REJECT**（1 BLOCKER + 4 SF + 1 NIT），`mergeable: no` | 见下逐条 |
| 2（复审） | **APPROVE**，`mergeable: yes`，`scope_exceeded: false` | BLOCKER 闭合确认 + 无新增 BLOCKER |

### 第 1 轮 BLOCKER（plan 档第 4 类：伪决策 / 自相矛盾）

`tasks.md` T3.2 声明只删 L170-258，但 `AC-1` 要求
`grep -c 'skills/guide\.md\|skills/status\.md\|scan-state\.sh'` = 0 —— 而**另一条** Requirement
`general-harden-doc-consistency:40` 的 Scenario 仍写「WHEN `skills/status.md` and the (archived)
v1-era execute skill file are inspected」，其 NOTE 只豁免 execute 半句 ⇒ 只做 T3.2 时 AC-1
**恒 fail**；要让它过就必须改 L40，那是未声明的范围蔓延。

**处置（方案 b：显式扩大声明范围）**：新增 **Group B** —— 把该 Scenario 从「点名两个已归档文件」
改为「对现存 live 树的断言」。意图（禁止内联重复实现）完全保留且变成可机判。

## Group B —— `general-harden-doc-consistency` 死判据改写

改前：
```
#### Scenario: Duplicate wt_path_for_branch_inline removed
- **WHEN** `skills/status.md` and the (archived) v1-era execute skill file are inspected
  <!-- NOTE (2026-11-20, retire-execute-skill): ... -->
- **THEN** neither SHALL define an inline `wt_path_for_branch_inline` function
- **AND** both SHALL call `_lib/worktree.sh::wt_path_for_branch` (after sourcing)
```

改后：
```
#### Scenario: no inline re-implementation of wt_path_for_branch
- **WHEN** the live tree (`_lib/`, `skills/`) is searched for an inline
  `wt_path_for_branch` re-implementation
- **THEN** none SHALL define one
- **AND** all callers SHALL use `_lib/worktree.sh::wt_path_for_branch` (after sourcing)
```

依据（实测）：

| 事实 | 证据 |
|---|---|
| `skills/status.md` 不存在 | 已归档 `docs/legacy/skills/status`（ADR-0063） |
| `skills/execute.md` 不存在 | 已归档 `docs/legacy/skills/execute` |
| `wt_path_for_branch_inline` 在 live 树 0 命中 | `grep -rn wt_path_for_branch_inline _lib/ skills/` ⇒ 0（唯一残留 `docs/legacy/skills/status/SKILL.md:74`，属归档） |
| 共享实现存在 | `_lib/worktree.sh:16` `wt_path_for_branch()` |
| 同 Requirement 其余 Scenario 仍为真 | `is_change_committed` live 命中 0；`safe_python_json` 只在 `_lib/state.sh:8,12-13` 注释里 |

## 14 条 Scenario 退役核算

| # | Scenario | 主体 | 现状 | 证据 |
|---|---|---|---|---|
| 1 | Frontmatter version key uniqueness | `skills/guide.md` / `skills/status.md` | 已归档 | `ls docs/legacy/skills/` ⇒ `execute`/`guide`/`status` |
| 2 | Status Mode A status vocabulary unification | `status.md` Mode A | 已归档 | 同上 |
| 3 | Status Mode C archive confirmation gate | `status.md` Mode C | 已归档 | 同上 |
| 4 | Status Mode B path uniformity | `status.md` Mode B | 已归档 | 同上 |
| 5 | Status Mode D python uses os.environ | `status.md` Mode D | 已归档 | 同上 |
| 6 | Status Mode E no exec `$0` | `status.md` Mode E | 已归档 | 同上 |
| 7 | guide binding skip + flags | `skills/guide.md` | 已归档 | `docs/legacy/skills/guide` |
| 8 | scan-state.sh priority count alignment | `skills/_lib/scan-state.sh` | 不存在 | successor `_lib/recommender.py` / `_lib/cli/guide_cmd.py` |
| 9 | stale workflow-state.md runtime check | `scan_state()`（同文件） | 不存在 | 同上 |
| 10 | status output style guide | `skills/status.md` | 已归档 | 同上 |
| 11 | regression suite covers all 12 work-units | 12 个 bats 文件 | **11/12 不存在** | 仅 `test_frontmatter_dupkey.bats` 存活 |
| 12 | status.md top-level mode router (S8) | `status.md` | 已归档 | 同上 |
| 13 | status.md Mode A no longer duplicates `git worktree list` (S3) | `status.md` | 已归档 | 同上 |
| 14 | status.md Mode A case handler accepts `i` (S11) | `status.md` | 已归档 | 同上 |

## 退役后不变量覆盖（据实，不笼统打勾）

| 原不变量 | successor 载体 | 守卫 | 据实说明 |
|---|---|---|---|
| 推荐阶梯唯一性/路由 | `_lib/recommender.py` | ✅ | `tests/unit/test_recommender.py:106/:113/:134` |
| 原 Scenario 8（priority count） | 无 | ❌ 无后继 | 原判据是「`scan-state.sh` 注释计数 == `guide.md` 声称计数」的 doc 叙事一致性检查；CLI 化后无对应物 ⇒ 合理消亡 |
| 原 Scenario 9（stale 警告） | `_lib/cli/guide_cmd.py:18-23` | ✅ 弱 | `tests/unit/test_cli_guide.py:105` 只断言子串，不锁完整消息、不锁「不自动删除」 |
| 原 Scenario 2（`review` 显式可见） | `_lib/cli/status_cmd.py` | ❌ 原形态未继承 | `_STATUS_ICON`(:58-65) 无 `review` 键；磁盘推导(:111-117) 只产三态 ⇒ **实现缺口**，进 tail |
| 原 Scenario 3（archive 确认门） | `_lib/cli/archive_cmd.py` → `_lib/archive.sh:1025` | ❌ 原形态未继承 | `openspec archive "$name" --yes` 无条件 ⇒ 交互确认门不存在，无测试锁 ⇒ 进 tail |
| status 其余形态（Mode B/D/E 等） | `_lib/cli/status_cmd.py` | 部分 | 既有测试覆盖的是**别的**判据（列宽 / 磁盘推导 / 损坏消息），不等价于原 Mode A–E 的文档形态检查 |
| skill frontmatter version 唯一性 + semver | `skills/<name>/SKILL.md` | ⚠️ 唯一守卫 | `test_frontmatter_dupkey.bats`，**glob 曾塌陷** ⇒ 本批修 |

⇒ 据实结论：**2 条（review 可见性 / archive 确认门）原形态无 successor**、**1 条（priority count）
无后继**、**1 条（stale 警告）后继弱**。这不推翻退役决定（它们恰恰因为没有干净的改指目标才退役），
但**不得**用「✅ 既有测试」笼统覆盖。

## 连带修复 —— `test_frontmatter_dupkey.bats` glob 塌陷

**问题**：`for f in skills/*.md` —— skills 已目录化，`skills/*.md` 只命中 `INSTALL.md`
**1 个文件**，而实际有 **26** 个 `skills/<name>/SKILL.md` ⇒ 测试自称「all 13 skills」
实际只查 1 个 ⇒ **守卫事实上失效**。

**修法**：
1. 2 处 glob → `skills/*/SKILL.md`
2. 测试名 `all 13 skills:` → `all skills:`
3. 注释删掉「INSTALL.md is a special case / All 12 other skills」（INSTALL.md 已不在射程内）
4. **零命中守卫**（critic NIT）：`local files=(skills/*/SKILL.md); [ -e "${files[0]}" ] || { echo "FAIL: no skills/*/SKILL.md found"; return 1; }`
   —— bash 的 glob 零匹配会把**字面量**传进循环 ⇒ 原写法会静默空转通过

**实测**：`bats tests/integration/test_frontmatter_dupkey.bats` ⇒ **4/4 pass**；覆盖数 **1 → 26**；
零命中守卫在 `bash -c 'files=(nonexistent-xyz/*.md); ...'` 下正确触发。

## 验证实测

| 项 | 改前 | 改后 |
|---|---|---|
| `grep -c 'skills/guide\.md\|skills/status\.md\|scan-state\.sh' general/spec.md` | 3 | **0** |
| `grep -c 'general-status-guide-skill-revision' general/spec.md` | 1 | **0** |
| `grep -rn 'wt_path_for_branch_inline' _lib/ skills/` | 0 | **0**（新判据为真） |
| `bats test_frontmatter_dupkey.bats` 覆盖数 | 1 | **26** |
| 残留扫描器（未豁免） | 0/0/0 | **0/0/0** |
| 残留扫描器（含已豁免） | 303/159/41 | **303/159/41** |
| `openspec validate --all --json` 多重集 | 224 | **224（新增 0 / 消失 0）** |
| `very long` | 62 | **62** |
| `validate --all` ERROR | 11 | **11** |
| `pytest tests/unit/` | 3518 | **3518 passed / 3 skipped** |
| `ruff check skills/_lib/`（门范围） | 绿 | **All checks passed** |
| `general/spec.md` Requirement 数 | 7 | **6** |

## 回滚凭据

- 整树备份：`/tmp/opencode/specs-backup-retire-gsg-<ts>/`（165 份）
- 单文件快照：`/tmp/opencode/gsg-before/general-spec.md`、`/tmp/opencode/gsg-before/test_frontmatter_dupkey.bats`
- 实施脚本：`/tmp/opencode/retire_gsg_apply.py`（内容匹配 + `count(old)==1` 断言，可 `--dry-run`）
- ⚠️ `openspec/` 整树 gitignored ⇒ spec 改动**无 git diff**，上述备份是唯一回滚凭据
- `tests/integration/test_frontmatter_dupkey.bats` 是 tracked ⇒ 有 git diff

## 进 tail（本批不处置）

1. **`rddf status` 缺 `review` 状态渲染**（实现缺口）：`_lib/cli/status_cmd.py:58-65` 的
   `_STATUS_ICON` 无 `review` 键、磁盘推导 `:111-117` 只产三态。原 spec 曾要求「`review` 显式可见」。
2. **`rddf archive` 缺交互确认门**：`_lib/archive.sh:1025` 无条件 `openspec archive --yes`，
   原 Mode C 的「确认先于 archive + `-y` 旁路」语义丢失。评估是否恢复。
3. **3 个 placeholder Requirement**（`general-add-skill-bats-tests` /
   `general-implement-deps-subagent-analysis` / `general-init-adr-directory`）—— 正文是自动生成的
   模板句，零信息量 ⇒ 属「delta 形态垃圾结构」类，独立立项。
4. `doc-truth-sync/spec.md:50/:51/:156` 的 path 形态漂移。
5. `AGENTS.md:92`（「19 个用例」）与 `:103`（「11/11 pass」）自相矛盾。
6. `install.sh:27` 与 `_count_skill_files()` 的 `deprecated:` 口径分叉。
7. `docs/improvement-approved-format.md:3` 旧机制描述 · `rfc-rddf` 的 14 个 `acceptance-N` ·
   62 条 `very long`（冻结）· CI 上 `openspec/` 不存在导致 spec 校验空转。
