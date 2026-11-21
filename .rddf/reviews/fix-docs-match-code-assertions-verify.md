# 验收报告 — fix-docs-match-code-assertions

- **change**：`openspec/changes/fix-docs-match-code-assertions/`
- **定位**：docs-match-code 契约族（`general-docs-match-code` + `doc-contract-tests-required`）
  的假断言修正 —— **不被残留扫描器命中**的一类 rot。
- **范围**：**7 组** / 2 spec + 5 文档 + 1 测试文件（新增 4 个守卫）。
- **验收时间**：2026-11-22
- **实现提交**：本提交
- **判据来源**：`proposal.md` 的 `## Acceptance`（AC-1 ~ AC-8）

## 审查链

| 环节 | 结论 | 处置 |
|---|---|---|
| critic 第 1 轮 | **APPROVE_WITH_CONDITIONS**；`mergeable: yes` / `scope_exceeded: false`；**0 BLOCKER** + 3 SHOULD_FIX + 2 NIT | **SHOULD_FIX-1**（B 组 surface 缺口 ⇒ 扩到 `skills/**/*.md` + 修 2 份 skill README）；**SHOULD_FIX-2**（D 组 ⇒ name-free 判据，不冻目录闭集）；**SHOULD_FIX-3**（E 组守卫 ⇒ 行级黑名单 + 正向断言）；**NIT-1**（deprecated 措辞对齐实现）；**NIT-2**（allowlist 显式枚举）—— **全部实施**。 |

## 逐条判定与证据

| AC | 判定 | 证据 |
|---|---|---|
| AC-1 每条 Scenario 断言可核实为真 | **pass** | A：canonical **26** == `package.json::skills[]` **26**（`_comment` 键 **0**）；B：`skills/**/*.md` 三个模式 **0 命中**；C：「main 分支」/「main branch」**0 命中**；D：`tests/README.md` Layout 覆盖 `tests/` 全部顶层条目（守卫绿）；E：`scripts.test` 同时含 `test:bats`+`test:python`、`test:bats` 带 `--recursive`、两份文档含 `bats + pytest`；F：D1 与 L64/66/87 同口径 |
| AC-2 文档改动逐条等于设计表 | **pass** | 实施脚本用**内容断言**（`count(old) == 1`）⇒ general 5 处 + doc-truth-sync 4 处 + USAGE 4 处 + AGENTS 4 处 + README 1 处 + 2 份 skill README 各 1 处 + `tests/README.md` 1 处，**全部精确匹配** |
| AC-3 新增 4 个守卫绿；既有 test_doc_contracts 绿 | **pass** | `tests/unit/test_doc_contracts.py` **20 passed**（原 16 + 新 4）；`pytest tests/unit/` **3518 passed / 3 skipped**；`ruff` 全绿 |
| AC-4 残留命中数不变 | **pass** | 未豁免 **0/0/0**；含已豁免 **303/159/41**；豁免 **303**；四诊断全 **0** |
| AC-5 issue 多重集只减不增；very long 不新增 | **pass** | `--json` 比对：**224 → 224**（新增 0 / 消失 0）；`very long` **62 → 62**；ERROR **11 → 11** |
| AC-6 台账覆盖 A–G | **pass** | `.rddf/reviews/docs-match-code-assertions-2026-11-22.md`（逐组改前/改后/依据 + 实测数字 + 审查链 + tail + 回滚凭据） |
| AC-7 pytest unit 全量 + ruff | **pass** | **3518 passed, 3 skipped**；`ruff check tests/unit/test_doc_contracts.py` ⇒ All checks passed |
| AC-8 全量门 | **pass** | `./test.sh --full --regression` ⇒ **GATE_RC=0** + 未评估 0 + 新增失败 0 |

## 实施期发现

**1. 本批抓到的是一条「给 agent 的错误指令」**：`AGENTS.md` 与 `USAGE.md` 都在说
「`npm test` 只跑 bats、不会捕获 Python 测试失败」，而
`package.json::scripts.test` = `npm run test:bats && npm run test:python`
⇒ **`npm test` 会跑 pytest** ⇒ 按现文档办事的 agent 会以为改完 Python 不必跑测试。
而 `tests/unit/test_doc_contracts.py:169-196` **早已**断言了正确行为
⇒ 实现与测试是对的，spec 与两份文档是错的。

**2. critic 抓到一个我设计的缺口**：B 组我原本把 surface 定为
`skills/*/SKILL.md` + `skills/*.md`，**不覆盖** `skills/*/README.md` ——
而那里正好有 3 处活例（`/workspace/project/ChipForge` ×2、`/home/ubuntu/.config/opencode`）。
⇒ 我原以为「声称保留意图、实际弱化」是不成立的 ⇒ 实际成立 ⇒ 已扩 surface 并修掉那 3 处。
⇒ 教训：**判据的 surface 必须覆盖「同类文本」，否则缺口里的活例会继续骗人**。

**3. 守卫作用域踩坑**：E 组守卫最初用**全文件**黑名单（"只跑 bats" 等），
会误伤 `AGENTS.md:30` 的 `./test.sh --bats  # 只跑 bats recursive`（**那是正确表述**）
⇒ 收紧到「提到 `npm test` 的那一行」+ 叠加正向断言。
⇒ 教训：**黑名单守卫必须限定作用域**，否则会惩罚正确表述。

**4. 规格冻结闭集的成本不对称**（critic SHOULD_FIX-2）：D 组我原本把 `tests/` 的
目录闭集写进主 spec ⇒ 「新增一个测试目录」会升级成「修订主 spec」
⇒ 改为 name-free 判据（从 disk 派生），闭集只留在守卫与 README。

## 遗留清扫

- 本次范围内：无 TODO / 半截实现；7 组全部落盘；新增 4 个守卫全绿；
  无被 skip 的新测试、无临时日志、无未替换的 mock。
- **未处置项（范围外，已进形态台账 tail）**：
  `general/spec.md` 的 `general-status-guide-skill-revision` Requirement 整体失效
  （`skills/guide.md` / `skills/status.md` 均不存在）·
  `doc-truth-sync/spec.md:50/:51/:156` 的 path 形态漂移 ·
  `AGENTS.md:92` 与 `:103` 自相矛盾的用例计数 ·
  `install.sh:27` 与 `_count_skill_files()` 的 deprecated 口径分叉 ·
  `docs/improvement-approved-format.md:3` 旧机制描述 · `rfc-rddf` 的 14 个 `acceptance-N` ·
  62 条 `very long`（冻结）· CI 上 `openspec/` 不存在导致 spec 校验空转。

## 失败项与路由建议

**本次验收无失败项** —— AC-1 ~ AC-8 全部 pass，全量门 `GATE_RC=0`。

## 已用轮次

- **critic 评审**：**1 轮**（APPROVE_WITH_CONDITIONS，0 BLOCKER ⇒ 按预算规则无需复审）
- **验收轮次**：1 轮
