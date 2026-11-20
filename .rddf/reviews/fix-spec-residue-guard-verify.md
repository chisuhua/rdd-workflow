# 验收报告 — fix-spec-residue-guard

- **change**：`openspec/changes/fix-spec-residue-guard/`
- **定位**：`.rddf/improvements/fix-spec-residue-guard.md`（draft, P2；已过 1 轮 metis）的**实施项**。
  只交付「守卫 + 分类规则 + 普查台账」；逐 spec 清理是 Phase 1（另立项）。
- **验收时间**：2026-11-20
- **实现提交**：本提交（唯一 tracked 交付物 = 代码 + 测试 + 台账 + 本报告）
- **判据来源**：`proposal.md` 的 `## Acceptance`（AC-1 ~ AC-19）

## 审查链

| 环节 | 结论 | 关键处置 |
|---|---|---|
| critic 第 1 轮 | **REJECT（1 BLOCKER + 4 SHOULD_FIX + 4 NITS）** | ① B：AC-8（18 份 `disposition ≠ unset`）与 AC-17（18 份**不再出现**）互斥；且合并键 `(file, requirement_title, matched_token)` 在本仓既有台账上不可达（batch1 token 是上下文片段、标题被截断 58 字符、batch2 37 行只有 21 个唯一键、行号必漂）。② SF1 台账路径与 batch1 撞名。③ SF2 AC-9 常数在 CI 必落空。④ SF3 AC-5 同行混合会一并豁免。⑤ SF4 AC-4/AC-6 优先级未定 |
| 修正 | 放弃跨台账合并（写进「与草案的偏离」第 2 条 + 三障碍实测表）；台账改名 `...-full.md`；AC-9 加 skip 守卫；AC-5 写明「混合须不同行」+ 「已知粒度限制」小节；AC-6 写死「标注 > 启发式」 | 另新增 AC-18（守卫自检）、AC-19（全量门） |
| critic 第 2 轮（复审） | **APPROVE_WITH_CONDITIONS**，mergeable: yes | BLOCKER 闭合（逐条复核）；提 6 条 SHOULD_FIX + 2 NITS |
| 第 2 轮 SF 处置 | ① Impact 段漏改的旧台账路径 → `-full.md` ② §6/Out of Scope 的「统一 `allow=history`」→ 改为**按旧 `disposition` 分类的映射表**（`RETIRED`→history / `PARTIAL` 仍生效子句→**真实 delta** / `KEEP`→取旧 `category` 的 code）③ T1.8 补「仅在无标注时生效」④ AC-14 删掉「台账里标了它」（与幂等互斥）⑤ AC-17 不写死 119 字面量（改运行时计数）⑥ 偏离回写 improvement 草案（T7.9） | NIT-1 删掉 AC-18 的恒真子句；NIT-2 在 AC-9 旁注明「Phase 1 首改动须同 commit 更新常数」 |

## 逐条判定与证据

| AC | 判定 | 证据 |
|---|---|---|
| AC-1 扫描根恰为 `openspec/specs/*/spec.md` | **pass** | `test_r4_scan_root_excludes_openspec_changes`：`openspec/changes/archive/x/spec.md` 同内容 ⇒ 0 WARNING；`openspec/specs/demo/spec.md` ⇒ 1 WARNING。纯行为断言（未绑常量名） |
| AC-2 口径锁定 + 可复算 | **pass** | 4 组合实测（选定口径）：`True×True` **350 处 / 192 块 / 46 份**；`True×False` 320/189/46；`False×True` 348/191/45；`False×False` 318/188/45。表在 `spec_residue_scan.py` 的 CALIBRATION 段 + 台账头部；`test_r4_code_block_switch_off_drops_it` / `test_r4_requirement_title_is_matched` 各守一个开关 |
| AC-3 五类各有正反例 | **pass** | `test_r4_each_allow_code_exempts`（5 个参数）+ `test_r4_without_annotation_is_reported`（5 个参数）= 10 个夹具；另 `test_r4_invalid_allow_code_does_not_exempt`（拼错 code 不豁免） |
| AC-4 标注生效 + stale allow | **pass** | `test_r4_each_allow_code_exempts` / `test_r4_stale_allow_is_reported` |
| AC-5 禁止文件级 allowlist | **pass** | `test_r4_mixed_same_spec_only_exempts_annotated_line`（同 spec 两 Requirement、不同行 ⇒ 只豁免前者）+ `test_r4_annotation_at_file_head_does_not_exempt_whole_file`（文件头一条标注不豁免全文） |
| AC-6 标注优先于措辞启发式 | **pass** | `test_r4_weak_wording_warns_without_annotation`（无标注 ⇒ WARNING + 「措辞」提示）+ `test_r4_annotation_wins_over_weak_wording`（有标注 ⇒ 不报） |
| AC-7 台账已生成 + 列齐 | **pass** | `.rddf/reviews/spec-residue-census-2026-11-20-full.md`（409 行）；`test_row_schema_has_all_columns` |
| AC-8 幂等 + 只含未豁免 + 不合并 | **pass** | 生成器两次输出 `diff` 为空（逐字节）；`test_idempotent_byte_identical` / `test_only_unexempted_hits_appear` / `test_prior_ledgers_and_batch_ledgers_untouched`（旧台账字节不变）；`git status --porcelain .rddf/reviews/` 只出现新文件 |
| AC-9 已知残余常数 | **pass** | `test_r4_repo_residue_constant`：`files_scanned==165` / `blocks==192` / `specs==46` / `hits==350`；按 `_REQUIRES_SPECS` skipif 守卫（CI 无 `openspec/`） |
| AC-10 变异验证 | **pass** | `test_r4_mutation_inject_then_remove`（clean ⇒ 注入 ⇒ 报 ⇒ 撤掉 ⇒ 不报） |
| AC-11 `openspec/` 缺失不报错 | **pass** | `test_r4_missing_openspec_does_not_raise`（只返回 INFO） |
| AC-12 `checked 0` ≠ clean | **pass** | `test_r4_checked_zero_is_not_clean`（snippet 含 `checked 0` + `不等于 clean`）；`test_r4_summary_reports_files_scanned`（`checked 2 spec file(s)`）。⚠️ `exit_code_for` 对 INFO 也返回 1 —— 已实测 `--category v4-residue` rc=1，不影响 advisory gate（`--gate advisory` rc=0） |
| AC-13 门控不被拖红 | **pass** | `.rddf/project.yaml` 开 `doctor.v4_residue.scan_specs: true`；`doctor.sh --gate structural` **rc=0**（10 categories 不含 v4-residue）；`--gate advisory` **rc=0**；`--quiet` 仍单行 |
| AC-14 既有断言的连带影响已登记 | **pass** | proposal §7 + Out of Scope 均记 `tests/unit/test_doc_contracts.py:64-68`；**未**写进台账（与幂等互斥） |
| AC-15 hub-managed 只报不修 | **pass** | `test_hub_managed_rows_marked_excluded`（`.rddf/config/hub.yaml` 有 `contracts: [demo]` ⇒ 该行 `disposition=excluded(hub-managed)`）；本仓无 hub 配置 ⇒ 实际 0 行 |
| AC-16 异常 spec 目录 | **pass** | 实测 6 个（`phase-20260829063800`/`-2`/`phase-20260829063801`/`-2`/`phase-20260829063814`/`tests`），均含 `spec.md`、**均 0 命中**且不产生 finding；**不删**（删用户工件需单独确认）⇒ 记 tail |
| AC-17 头部指针 + 不写死字面量 | **pass** | 台账头部含两个旧台账路径 + 「这 18 份当前仍有 120 个命中行（159 条实例）」为**运行时计算**；`test_header_points_at_prior_ledgers`；`git status` 中 `openspec/specs/**` 零改动 |
| AC-18 守卫自检 | **pass** | `test_r4_inline_annotation_on_hit_line_is_ignored`（同行标注被忽略 + snippet 明示）/ `test_r4_adjacent_hit_lines_each_annotated`（相邻命中行逐行标注 ⇒ 无 stale 误报） |
| AC-19 全量门 | **pass** | `BATS_TIMEOUT=120 BATS_TIMEOUT_RETRY=240 ./test.sh --full --regression` → **GATE_RC=0** + `✅ ALL PASSED`；bats regression **229/229 评估、未评估 0、新增失败 0** |

## 实施期发现的判据缺陷（2 处，已修正）

**① 词边界左边界过严**：原正则 `(?<![\w-])(...)(?![\w-])` 把 `fill-phase-in-guide-plan`
（`iterative-plan-fill:6` 的 **Requirement 标题**）漏掉了 —— 它以退役 stage 名作**尾部构件**，
读者会据此去找 `guide-plan`，而 `title_in=True` 存在的全部意义就是抓这种标题。
改为 `(?<!\w)(...)(?![\w-])`（左边界只排除词字符，右边界不变 ⇒ `guide-plan-quick-finish` 仍不命中）。
**全仓差异 1 处**（350 vs 349），块数不变（192）。⇒ 已同步 proposal 的实测表、AC-9 常数、扫描器 CALIBRATION 段。

**② 扫描核心不能放 `checks/`**：首版落在 `skills/rdd-doctor/scripts/checks/spec_residue_scan.py`，
全量门报 2 个失败 —— `tests/unit/test_doctor_main.py` 有**「一文件一 checker」**不变式
（`test_checkers_dict_has_one_entry_per_check_file` + `test_category_names_constant_matches_disk`：
`checks/*.py` 必须各对应一个 `_CHECKERS` 条目）。扫描核心是**库模块**（无 `run()`），不是 category
⇒ 移到 `skills/rdd-doctor/scripts/spec_residue_scan.py`，`v4_residue_check` 与生成器改用
`from spec_residue_scan import ...`（与 `from doctor_render import ...` 同型平铺导入）。
⇒ 60 passed（含 `test_doctor_main.py` 全部）。

## 遗留清扫

- 本次范围内（T7.5）：新增 / 改动的 5 个 Python 文件 **0** 处 TODO/FIXME/HACK；无 `pass` / `NotImplemented` 半截实现。
- **spec 零改动**：`openspec/specs/**` 未被写入（本项只读）⇒ 无需回滚凭据。
- **记 tail（范围外）**：
  | tail | 归属 |
  |---|---|
  | 逐 spec 清理（46 份 / 350 处 / 192 块）+ 给 18 份已处置 spec 做**逐行**判定与标注（**不是**统一 `allow=history`） | Phase 1（另立项），由本项台账驱动 |
  | 150/165 spec 的 `## Purpose` 仍是 `TBD - created by archiving ...` 占位 | 仓库级历史债（与 Phase 1 同批处理） |
  | `openspec/specs/` 下 6 个非 capability 目录（`phase-*` ×5 + `tests`） | 测试残留；**不删**（删用户工件需单独确认） |
  | `test.sh:86` 注记「advisory gate (4 categories)」与 `_GATES["advisory"]` 的 5 个不符 | 既有漂移（critic NIT-4） |
  | `AGENTS.md:118/:133` 的既有漂移 | 后续批次 |
  | `tests/unit/test_doc_contracts.py:64-68` 锁定 `general/spec.md` 必须含 `guide-arch` | Phase 1 的连带影响（已登记） |

## 失败项与路由建议

**本次验收无失败项** —— AC-1 ~ AC-19 全部 pass，全量门 `GATE_RC=0`。

## 已用轮次

- **critic 评审**：2 轮（REJECT → 修正 → APPROVE_WITH_CONDITIONS）。已达每 change 2 轮上限，未再发第 3 轮。
- **验收轮次**：1 轮。
