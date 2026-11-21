# retire-general-status-guide-requirement 验收报告

**change**: `retire-general-status-guide-requirement`
**判据来源**: `openspec/changes/retire-general-status-guide-requirement/proposal.md` 的 `## Acceptance`（AC-1 ~ AC-8）
**已用轮次**: 1（本轮即通过）

## 逐条判定

| AC | 判定 | 证据 |
|---|---|---|
| **AC-1** `general/spec.md` 不再出现 `general-status-guide-skill-revision`；`grep -c 'skills/guide\.md\|skills/status\.md\|scan-state\.sh'` = 0（前提 = Group B 已实施） | **PASS** | `grep -c 'skills/guide\.md\|skills/status\.md\|scan-state\.sh' openspec/specs/general/spec.md` ⇒ `0`；`grep -c 'general-status-guide-skill-revision'` ⇒ `0` |
| **AC-1b** `grep -rn 'wt_path_for_branch_inline' _lib/ skills/` = 0 | **PASS** | 该命令输出空（0 行）；唯一残留 `docs/legacy/skills/status/SKILL.md:74` 属归档，不在射程 |
| **AC-2** 14 条 Scenario 退役核算表逐条有证据 | **PASS** | 台账 `.rddf/reviews/retire-general-status-guide-2026-11-22.md` 的「14 条 Scenario 退役核算」表 + proposal 同名表，每行含 `docs/legacy/skills/` 或 successor 文件证据 |
| **AC-3** `test_frontmatter_dupkey.bats` 两处 glob 改为 `skills/*/SKILL.md` 且 4/4 pass | **PASS** | `git diff` 显示 2 处 `for f in skills/*.md` → `local files=(skills/*/SKILL.md); [ -e "${files[0]}" ] || …; for f in "${files[@]}"`；`bats tests/integration/test_frontmatter_dupkey.bats` ⇒ `1..4` / `ok 1..4` |
| **AC-4** 覆盖数 1 → 26，且零命中守卫生效 | **PASS** | `ls skills/*/SKILL.md \| wc -l` ⇒ `26`；零命中守卫实测：`bash -c 'files=(nonexistent-xyz/*.md); [ -e "${files[0]}" ] \|\| echo guard-ok'` ⇒ 触发（会 `return 1`），正常 glob ⇒ 命中 26 个 |
| **AC-5** `validate --all --json` 多重集只减不增；`very long` 不新增；ERROR 不增 | **PASS** | 用 `openspec` 自己的 parser 在临时目录比对新旧 specs：`改前 224 条 / 改后 224 条`，`新增: 无`，`消失: 无`；`very long: 62 → 62`；`openspec validate --all` ERROR 计数 `11 → 11` |
| **AC-6** 残留扫描器命中数不变（0/0/0 + 303/159/41） | **PASS** | `scan_specs(Path('.'))` ⇒ `未豁免 0/0/0`、`含已豁免 303/159/41`、`豁免 303`；四诊断 `stale=0 invalid=0 in_fence=0 fence_rejected=0` |
| **AC-7** `pytest tests/unit/` + bats 全绿；`ruff` 全绿 | **PASS** | `python3 -m pytest tests/unit/ -q` ⇒ `3518 passed, 3 skipped`；`python3 -m ruff check skills/_lib/`（CI/门的实际范围）⇒ `All checks passed!` |
| **AC-8** `./test.sh --full --regression` 全绿（未评估 0、新增失败 0） | **见下** | 见「全量门」 |

## 全量门

`BATS_TIMEOUT=120 BATS_TIMEOUT_RETRY=240 ./test.sh --full --regression`

结果：`GATE_RC=0` · `未评估: 0 个文件` · `新增失败: 0` · `✅ ALL PASSED`

## 遗留清扫

| 项 | 结果 |
|---|---|
| 本次范围内的 TODO / 半截实现 | 无（`tasks.md` T1–T5 全勾，T5.5/T5.6 收口时勾） |
| 注释掉的代码 | 无新增 |
| 临时调试日志 | 无（实施脚本在 `/tmp/opencode/`，不入仓） |
| 被 skip 的测试 | 无新增 skip |
| 未替换的 mock | 不涉及 |
| 临时 fallback 分支 | 无 |

## 实施期教训

1. **「删掉一段 spec」不等于「该 spec 文件变干净」** —— AC 里的 `grep` 是**全文件**范围，
   而另一条 Requirement 可能仍在点名同一个已归档文件。第 1 轮 critic 正是抓到这个
   「T3.2 声明范围 ⊂ AC-1 断言范围」的不对称。**写 AC 前先把 grep 跑一遍**，看它还会命中哪里。
2. **`grep -c 'A\|B'` 在 BRE 下 `\|` 是 alternation**，但写进 proposal 的 markdown 时要转义成
   `\\|`，否则读者复制到 shell 会得到字面量 —— 本次已在 AC-1 里用 `\.` / `\|` 明确。
3. **bash 的 glob 零匹配不报错** —— `for f in skills/*.md` 在无匹配时会把**字面量**当文件名传进
   循环体，`awk` 读不到文件但 `wc -l` 仍返回 0 ⇒ 断言静默通过。凡是「遍历一类文件」的守卫
   都必须配 `[ -e "${files[0]}" ]` 或 `shopt -s nullglob` + 计数断言。
4. **「退役不丢覆盖」必须逐条核到 successor 的具体测试函数名**。本批初版 successor 表用
   「✅ 既有测试」笼统覆盖了 3 条，critic 逐条核对后发现 2 条**根本没有 successor**
   （`review` 状态可见 / archive 确认门）⇒ 改为「❌ 原形态未继承」并进 tail。**笼统打勾 =
   把实现缺口藏进文档。**

## 路由建议

无需返工。本批可归档。tail 里的 2 条实现缺口（`rddf status` 缺 `review` 渲染、
`rddf archive` 缺交互确认门）属 `implementation_gap`，独立立项。
