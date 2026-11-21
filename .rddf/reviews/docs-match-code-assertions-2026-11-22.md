# docs-match-code 契约族假断言修正台账（2026-11-22）

> 定位：change `fix-docs-match-code-assertions`。
> **7 组 / 2 spec + 5 文档 + 1 测试文件**。
> 判据形式 = **`general-docs-match-code` 与 `doc-contract-tests-required` 两个 Requirement 的
> 每一条 Scenario 断言，都能在当前实现上逐条核实为真**。
> 处置原则 = **判据错改 spec；实现/文档错改文档**（根因在哪改哪）。

## 0. 为什么这批不被残留扫描器覆盖

`skills/rdd-doctor/scripts/spec_residue_scan.py` 只扫**退役 stage 名**
（`guide-arch` / `guide-design` / `guide-plan` / `guide-ship` / `guide-spec`）
⇒ 「判据本身与实现相反」这一类 rot **不在它的射程内** ⇒ 必须靠人工逐条核实。
本批是 Phase 1 收口后第一次**按 Requirement 逐条核**。

## 1. A 组 —— skill 计数口径（`general/spec.md`）

| | 改前 | 改后 |
|---|---|---|
| 判据 | `- **AND** \`ls skills/*.md \| wc -l\` is computed` | `- **AND** the canonical skill count is computed (\`skills/<name>/SKILL.md\`,`&nbsp;&nbsp;`  excluding skills whose \`SKILL.md\` contains a \`metadata:\`/\`deprecated:\` marker)` |

**依据**：`ls skills/*.md` 只命中 `skills/INSTALL.md`（**1**）—— skills 在 v2.x 已目录化
（`skills/<name>/SKILL.md`）；canonical skill 实测 **26**，`package.json::skills[]` = 26
⇒ 改前判据的差值是 **25**，不是 0。
排除口径与 `tests/unit/test_doc_contracts.py::_count_skill_files`（`metadata:.*deprecated:` + DOTALL）
一致 ⇒ **critic NIT-1** 要求 spec 措辞对齐实现口径 ⇒ 写成「`metadata:`/`deprecated:` marker」。

## 2. B 组 —— `status.md` 不存在 ⇒ 重写为「指令面不得硬编码具体路径」

**改前**：`- **WHEN** \`skills/status.md\` L68-70 is read`（该文件**不存在**）

**改后**

```
#### Scenario: skill instruction files do not hardcode a concrete machine or project path

- **WHEN** the instruction surface (`skills/**/*.md`) is searched for hardcoded
  concrete machine or project paths (`/path/to/CppHDL`, `/workspace/project/<name>`,
  `/home/<user>/.config/...`)
- **THEN** none SHALL appear (generic placeholders such as `/path/to/<repo>`,
  `<project-root>`, `~/.config/opencode` and `${PROJECT_ROOT}` are allowed)
```

**依据**：`status` 已不是 skill（现为 `rddf status` CLI，`_lib/cli/status_cmd.py`）。

⚠️ **critic SHOULD_FIX-1（已采纳）**：原设计的 surface（`skills/*/SKILL.md` + `skills/*.md`）
**不覆盖** `skills/*/README.md`，而那里有 **3 处活例** ⇒ 「声称保留意图、实际弱化」。
⇒ surface 扩到 `skills/**/*.md`（**38** 个 .md），并**顺带修这 2 份 README**：

| 位置 | 改前 | 改后 | 理由 |
|---|---|---|---|
| `skills/rdd-session-bootstrap/README.md:177-178` | `/workspace/project/ChipForge`（PoC 验证记录） | `<project-root>` | 与同段 `:181` 的 `<rdd-workflow-repo>` 占位风格一致 |
| `skills/session-lesson-mining/README.md:25` | `/home/ubuntu/.config/opencode`（实跑位置记录） | `~/.config/opencode` | 机器专属路径 ⇒ 改成 home 相对形式 |

改后三个模式在 `skills/**/*.md` 中 **0 命中** ✓
（`skills/INSTALL.md:67,339` 的 `/path/to/rdd-workflow-repo` 是**通用占位符**，被 allowlist 允许）。

## 3. C 组 —— glob 过时（`general/spec.md`）

| | 改前 | 改后 |
|---|---|---|
| 判据 | `skills/*.md` is searched … | `skills/**/*.md` is searched … |

**依据**：改前只覆盖 **1** 个文件（`INSTALL.md`）⇒ 26 个 `SKILL.md` 全在射程外。
改后覆盖 **38** 个 .md；实测「main 分支」/「main branch」**0 命中** ✓（结论不变，覆盖面从 1 → 38）。

## 4. D 组 —— `tests/README.md` Layout（`general/spec.md` + `tests/README.md`）

**改后**

```
#### Scenario: tests/README.md Layout matches the actual test tree

- **WHEN** `tests/README.md` Layout section is read
- **THEN** it SHALL list every top-level directory of `tests/` except generated
  ones (`__pycache__`)
- **AND** it SHALL list the root files `smoke.bats`, `test_helper.bash`, and
  `conftest.py`
- **AND** it SHALL mention `deps-subagent.bash` under `tests/_lib/`
```

**依据**：`tests/README.md:7-27` 的 Layout 树**漏掉** `unit/`（**307** 个 .py，最大的一块）、
`e2e/`、`fixtures/`、`scripts/`、`conftest.py`；`tests/_lib/` 实际 **18** 项、README 只列 **4** 项
⇒ 改前「SHALL list actual files in `tests/_lib/`」**为假**。
末条「test counts SHALL match …」是**空条款**（README 里**没有任何计数陈述**）⇒ 删掉
（写死测试文件数会随每次加测试文件而腐化 = 维护陷阱）。

⚠️ **critic SHOULD_FIX-2（已采纳）**：spec 正文**不冻目录闭集** ——
闭集进主 spec 会让「新增一个测试目录」升级成「修订主 spec」，成本不对称
⇒ 判据 **name-free**（从 disk 派生），闭集只落在守卫与 README。

**`tests/README.md` 侧**：Layout 树补 `unit/` / `e2e/` / `fixtures/` / `scripts/` /
`conftest.py` + 三个 `KNOWN_*.txt`。

## 5. E 组 —— `npm test` 陷阱（本批价值最高的一条）

**实测 `package.json::scripts`**

```json
"test": "npm run test:bats && npm run test:python",
"test:bats": "bats tests/ --recursive",
"test:python": "python3 -m pytest tests/unit/ tests/integration/ -q --tb=short"
```

⇒ **`npm test` 会跑 pytest**。而 `USAGE.md` 与 `AGENTS.md` 都在说它**不会** ——
且 `tests/unit/test_doc_contracts.py:169-196`（`test_npm_test_trap_caveat_locked`）
**已经**断言 `scripts.test` 同时含 `test:bats` 与 `test:python`、且 `test:bats` 带 `--recursive`
⇒ **实现与测试是对的，spec 与文档是错的** ⇒ 按 `doc-truth-sync` 的 truth-source hierarchy
（L1 runtime → L2 契约 → L3 文档）**改文档**。

**改后判据**

```
#### Scenario: npm test runs both the bats and the pytest suites

- **WHEN** `package.json::scripts.test` is read
- **THEN** it SHALL invoke both `test:bats` and `test:python`
- **AND** `scripts.test:bats` SHALL use `--recursive`
- **AND** `USAGE.md` and `AGENTS.md` SHALL state that `npm test` runs the Python
  suite, and SHALL NOT claim that it skips it
```

**文档侧 7 处**

| 文件:行 | 改前 | 改后 |
|---|---|---|
| `USAGE.md:825` | 「⚠️ **`npm test` 陷阱**：`npm test` 只跑 `bats tests/`，**不会**捕获 Python 测试失败。改完任何 Python 代码后必须显式 `pytest tests/`，CI 才会捕获。」 | 「⚠️ **`npm test` 说明**：`npm test` = `npm run test:bats && npm run test:python` ⇒ **bats + pytest 都跑**（v3.0 起）。但它是**裸跑**：无本地门（隔离 / ruff / mypy / doctor），也**不做** KNOWN_FAILURES baseline 对比 ⇒ 已知失败会直接报出来。要带门的完整验证用 `./test.sh --full --regression`。」 |
| `USAGE.md:830` | `# === bats（npm test 等价命令，仅覆盖 shell 测试）===` | `# === bats（npm test 会跑 bats + pytest）===` |
| `USAGE.md:831` | `npm test                                # 等价于 bats tests/，不跑 Python` | `npm test                                # bats tests/ --recursive + pytest unit/integration` |
| `USAGE.md:835` | `# === Python（必须显式调用，npm test 不会自动跑）===` | `# === Python（npm test 也会跑；这里是单独跑的入口）===` |
| `AGENTS.md:49` | `npm test                                # = bats tests/ --recursive (全量 bats, 不跑 pytest)` | `npm test                                # = bats tests/ --recursive + pytest unit/integration (bats + pytest 都跑)` |
| `AGENTS.md:54` | `# Python (npm test 不会跑, 必须显式调用)` | `# Python (npm test 也会跑; 这里是单独跑的入口)` |
| `AGENTS.md:67` | 「> **重要**: `npm test` 只跑 bats, **不会**捕获 Python 测试失败. 改完 Python 后必须手动 `pytest tests/` 或 `./test.sh --python`/`--unit`/`--integration`.」 | 「> **重要**: `npm test` = **bats + pytest 都跑**（v3.0 起; 见 `package.json::scripts.test`）。但它是**裸跑** —— 无本地门（隔离 / ruff / mypy / doctor），也**不做** KNOWN_FAILURES baseline 对比 ⇒ 已知失败会直接报出来。交付前用 `./test.sh --full --regression`.」 |

⚠️ **critic focus 1(b)**：「裸跑」这段说明**属实且必要**（`scripts.test` 确实无门、无 baseline 对比），
且能防止读者误以为 `npm test` 可替代 `./test.sh --full --regression` ⇒ 保留。

## 6. F 组 —— `doc-truth-sync/spec.md`（与 A 同步）

| 行 | 改前 | 改后 |
|---|---|---|
| 64 | …all on-disk `skills/*.md` files | …all on-disk `skills/<name>/SKILL.md` files |
| 66 | the count SHALL be 13 (current `ls skills/*.md \| wc -l`), matching … | the count SHALL match the canonical on-disk skill count, matching … |
| 87 | the skill count in any narrative text SHALL match `ls skills/*.md` | … SHALL match the canonical on-disk skill count |
| 114 | D1: `package.json::skills[]` length disagrees with `ls skills/*.md \| wc -l` | D1: … disagrees with the canonical on-disk skill count (`skills/<name>/SKILL.md`, excluding `deprecated:` shims) |

**依据**：与 A 组同源；**必须同批改**，否则两个 spec 对同一口径各说各话。

## 7. G 组 —— 子技能计数（`README.md` + `AGENTS.md`）

| 文件:行 | 改前 | 改后 | 依据 |
|---|---|---|---|
| `README.md:33` | `- **28 个子技能** symlink 到 …` | `- **26 个子技能** symlink 到 …` | `install.sh:27` `[ -f "$d/SKILL.md" ] && SUB_SKILLS+=("$s")` ⇒ 实际 symlink `skills/<name>/SKILL.md` 共 **26** 个；`skills/INSTALL.md:4` 已写「全部 26 个子技能」 |
| `AGENTS.md:98` | `- 28 个子技能 symlink 完整性` | `- 26 个子技能 symlink 完整性` | 同上 |

## 8. F 组新增守卫（4 个 pytest，全在 `tests/unit/test_doc_contracts.py`）

| 守卫 | 判据 | 实现要点 |
|---|---|---|
| `test_skill_instruction_files_have_no_hardcoded_project_path` | B 组 | 扫 `skills/**/*.md`；3 个正则 |
| `test_docs_do_not_claim_npm_test_skips_python` | E 组 | **行级**黑名单（6 种子）+ **正向**断言含 `bats + pytest` |
| `test_tests_readme_layout_lists_every_top_level_entry` | D 组 | 从 disk 派生 `tests/` 顶层条目逐一在 Layout 段出现 |
| `test_skill_count_in_narrative_docs_matches_disk` | G 组 | 两文档中所有 `(\d+)\s*个子技能` == `_count_skill_files()` |

⚠️ **critic SHOULD_FIX-3**：黑名单若做**全文件**匹配会误伤 `AGENTS.md:30` 的
`./test.sh --bats  # 只跑 bats recursive`（**那是正确表述**）⇒ 守卫作用域收紧到
**提到 `npm test` 的那一行**，并叠加正向断言（两份文档必须含 `bats + pytest`）。

## 9. 实测数字

| 指标 | 改前 | 改后 |
|---|---|---|
| 残留未豁免 | 0 / 0 / 0 | **0 / 0 / 0（不变）** |
| 残留含已豁免 | 303 / 159 / 41 | **303 / 159 / 41（不变）** |
| 已登记豁免 | 303 | **303（不变）** |
| `stale`/`invalid`/`in_fence`/`fence_rejected` | 0 / 0 / 0 / 0 | **0 / 0 / 0 / 0** |
| `openspec validate --all --json` issue 多重集 | 224 | **224（新增 0 / 消失 0）** |
| `very long` | 62 | **62（未新增）** |
| `validate --all` ERROR | 11 | **11** |
| `pytest tests/unit/` | 3514 passed | **3518 passed（+4 新守卫）** |

## 10. 审查链

| 环节 | 结论 | 处置 |
|---|---|---|
| critic 第 1 轮 | **APPROVE_WITH_CONDITIONS**；`mergeable: yes` / `scope_exceeded: false`；**0 BLOCKER** + 3 SHOULD_FIX + 2 NIT | 3 个 SHOULD_FIX + 2 个 NIT **全部采纳并实施**（见 proposal 的审查链表 + 本文件第 2/4/5/8 节） |

## 11. 范围外（记 tail，已进形态台账）

1. **`general/spec.md` 的 `general-status-guide-skill-revision` Requirement 整体失效** ——
   正文仍写「`skills/guide.md` 和 `skills/status.md` SHALL accurately reflect the codebase state」，
   而两个文件**都不存在**（`guide` 已归档到 `docs/legacy/` per ADR-0063，`status` 现为 CLI）。
2. **`doc-truth-sync/spec.md` 的其余 path 形态漂移**：`:50` `skills/loop.md`、`:51`
   `skills/_lib/session_v20.py`、`:156` `skills/foo.md`。
3. `AGENTS.md:92` 的「19 个用例」与 `:103` 的「11/11 pass」自相矛盾。
4. `install.sh:27` 收集 sub-skill 时**不**排除 `deprecated:` shim（当前无 deprecated skill ⇒ 暂时相等）。
5. `docs/improvement-approved-format.md:3` 旧机制描述 · `rfc-rddf` 的 14 个 `acceptance-N` ·
   62 条 `very long`（冻结）· CI 上 `openspec/` 不存在导致 spec 校验空转。

## 12. 回滚

- 文档 / 测试 / 台账：`git revert <sha>`（tracked）。
- spec 改动：`openspec/` gitignored ⇒ 回滚凭据 = `/tmp/opencode/dmc-before/`（9 份改前快照）
  + `/tmp/opencode/specs-backup-dmc-<ts>/`（165 份整树）。
