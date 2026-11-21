# spec 残留处置台账 — Phase 1 第四批（2026-11-21）

> 定位：change `annotate-spec-residue-guard-batch4`。
> 本批**首次出现混合形态**：纯标注 + **活契约改指** + **已死块补注记**。
> 处置分型沿用 ADR-0036 修订；改指落点沿用 `docs/migration/v3-to-v4.md:28-31` + 实现实证。
> `line` 列是**改前**行号（插入标注/注记后会下移）。

| 处置 | 行数 | 含义 |
|---|---|---|
| `ANNOTATE` | 9 | 行内标注（`guard` 7 / `history` 1 / `rename-history` 1） |
| `REPOINT` | 7 | 活契约里的真残留 ⇒ 逐行手写新文本（**不盲替换**） |
| `ADD_NOTE` | 15 | 已死块补 `RETIRED` 注记（块内命中行另逐行标注） |
| **合计** | **31** | |

## 逐行处置

| file | line | requirement_title | matched_token | disposition | code | 新文本 / 依据 |
|---|---|---|---|---|---|---|
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 10 | rdd-verifier SHALL self-contain its LLM verification | ac-verifier | ANNOTATE | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据；「SHALL NOT depend on a separate `ac-verifier` sub-skill」—— 负向断言 |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 19 | rdd-verifier SHALL self-contain its LLM verification | ac-verifier | ANNOTATE | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据；「SHALL NOT shell out to `ac-verifier/scripts/ac_verifier.sh`」—— 负向断言 |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 56 | rdd-verifier verdict reasoning SHALL embed heuristic | guide-plan | REPOINT | - | rdd-builder |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 63 | rdd-verifier verdict reasoning SHALL embed heuristic | guide-ship | REPOINT | - | rdd-builder |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 98 | archive_gate_check SHALL NOT shell out to ac-verifie | ac-verifier | ANNOTATE | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据；Requirement 标题「archive_gate_check SHALL NOT shell out to ac-verifier」—— 负向断言 |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 100 | archive_gate_check SHALL NOT shell out to ac-verifie | ac-verifier | ANNOTATE | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据；「SHALL NOT invoke … as a fallback」—— 负向断言 |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 146 | ac-verifier SHALL be marked deprecated | ac-verifier | ADD_NOTE | history | 该 skill 已于 2026-09-07 完全删除（ADR-0045 / change `remove-ac-verifier-completely`；`skills/rdd-verifier/SKILL.md:22-23`）⇒「SKILL.md 顶部带弃用横幅」的 MUST 已无对象；同 Requirement 的 CLI 委派 Scenario 亦过时（`_lib/cli/ac_verify_cmd.py:1-13` 是 exit-4 stub） |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 148 | ac-verifier SHALL be marked deprecated | ac-verifier | ADD_NOTE | history | 该 skill 已于 2026-09-07 完全删除（ADR-0045 / change `remove-ac-verifier-completely`；`skills/rdd-verifier/SKILL.md:22-23`）⇒「SKILL.md 顶部带弃用横幅」的 MUST 已无对象；同 Requirement 的 CLI 委派 Scenario 亦过时（`_lib/cli/ac_verify_cmd.py:1-13` 是 exit-4 stub） |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 150 | ac-verifier SHALL be marked deprecated | ac-verifier | ADD_NOTE | history | 该 skill 已于 2026-09-07 完全删除（ADR-0045 / change `remove-ac-verifier-completely`；`skills/rdd-verifier/SKILL.md:22-23`）⇒「SKILL.md 顶部带弃用横幅」的 MUST 已无对象；同 Requirement 的 CLI 委派 Scenario 亦过时（`_lib/cli/ac_verify_cmd.py:1-13` 是 exit-4 stub） |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 152 | ac-verifier SHALL be marked deprecated | ac-verifier | ADD_NOTE | history | 该 skill 已于 2026-09-07 完全删除（ADR-0045 / change `remove-ac-verifier-completely`；`skills/rdd-verifier/SKILL.md:22-23`）⇒「SKILL.md 顶部带弃用横幅」的 MUST 已无对象；同 Requirement 的 CLI 委派 Scenario 亦过时（`_lib/cli/ac_verify_cmd.py:1-13` 是 exit-4 stub） |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 166 | deprecation period SHALL be at least one release cyc | ac-verifier | ADD_NOTE | history | 弃用窗口已关闭（删除发生在 2026-09-07）；本 Requirement 断言「本变更内不得删除」，而那个变更早已完成；其 Scenario 的 GIVEN（package.json 含该条目）今天不成立 |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 170 | deprecation period SHALL be at least one release cyc | ac-verifier | ADD_NOTE | history | 弃用窗口已关闭（删除发生在 2026-09-07）；本 Requirement 断言「本变更内不得删除」，而那个变更早已完成；其 Scenario 的 GIVEN（package.json 含该条目）今天不成立 |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 177 | deprecation period SHALL be at least one release cyc | ac-verifier | ADD_NOTE | history | 弃用窗口已关闭（删除发生在 2026-09-07）；本 Requirement 断言「本变更内不得删除」，而那个变更早已完成；其 Scenario 的 GIVEN（package.json 含该条目）今天不成立 |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 179 | deprecation period SHALL be at least one release cyc | ac-verifier | ADD_NOTE | history | 弃用窗口已关闭（删除发生在 2026-09-07）；本 Requirement 断言「本变更内不得删除」，而那个变更早已完成；其 Scenario 的 GIVEN（package.json 含该条目）今天不成立 |
| openspec/specs/doc-truth-sync/spec.md | 85 | install-usage-readme-metadata-sync | guide-arch,guide-plan | REPOINT | - | rdd-arch/SKILL.md, rdd-builder/SKILL.md |
| openspec/specs/doc-truth-sync/spec.md | 133 | doc-contract-tests-required | guide-spec | ANNOTATE | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据；D6 检测规则本体（必须保留旧名才能检测 stale 引用） |
| openspec/specs/doc-truth-sync/spec.md | 134 | doc-contract-tests-required | guide-arch,guide-plan | ANNOTATE | rename-history | 重命名 / 替代关系说明 —— 类别 ⑤；v1→v2 的替代关系陈述（`docs/migration/v1-to-v2.md:28`） |
| openspec/specs/doc-truth-sync/spec.md | 205 | doc-contract-tests-required | guide-spec | ANNOTATE | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据；Scenario 标题「guide-spec reference caught (D6)」—— 检测规则的判据 |
| openspec/specs/doc-truth-sync/spec.md | 208 | doc-contract-tests-required | guide-spec | ANNOTATE | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据；扫描输入「contains the literal string `guide-spec`」 |
| openspec/specs/doc-truth-sync/spec.md | 243 | doc-surfaces-share-truth-source | guide-ship | REPOINT | - | skills/rdd-builder/SKILL.md + 6 phases (P0→P3) |
| openspec/specs/doc-truth-sync/spec.md | 246 | doc-surfaces-share-truth-source | guide-ship | REPOINT | - | skills/rdd-builder/SKILL.md |
| openspec/specs/doc-truth-sync/spec.md | 247 | doc-surfaces-share-truth-source | guide-ship | REPOINT | - | skills/rdd-builder/SKILL.md |
| openspec/specs/archive-gate-verification/spec.md | 10 | Archive SHALL remain owned by the builder stage | guide-ship | ANNOTATE | history | 已归档的历史叙述 —— 类别 ④；既有「Re-pointed (2026-11-17, per ADR-0036 AMENDED)」注记 —— 已归档的重命名叙述 |
| openspec/specs/archive-gate-verification/spec.md | 70 | Gate precedence SHALL be deterministic across skip, | ac-verifier | REPOINT | - | cached-verdict path（v2.0 起直接 fallback 已移除） |
| openspec/specs/archive-gate-verification/spec.md | 99 | Gate precedence SHALL be deterministic across skip, | ac-verifier | ADD_NOTE | history | 直接 fallback 路径已于 v2.0 移除（ADR-0045；`_lib/archive.sh:787`/`:921`；脚本不存在）⇒ fallback 调用与 exit code 3 语义均无对象 |
| openspec/specs/archive-gate-verification/spec.md | 101 | Gate precedence SHALL be deterministic across skip, | ac-verifier | ADD_NOTE | history | 直接 fallback 路径已于 v2.0 移除（ADR-0045；`_lib/archive.sh:787`/`:921`；脚本不存在）⇒ fallback 调用与 exit code 3 语义均无对象 |
| openspec/specs/archive-gate-verification/spec.md | 109 | Direct archive fallback SHALL write structured verdi | ac-verifier | ADD_NOTE | history | 同上；今天 verdict 只由 `rdd-verifier` 写入 SHA 绑定缓存（`_lib/archive.sh:786-791`） |
| openspec/specs/archive-gate-verification/spec.md | 114 | Direct archive fallback SHALL write structured verdi | ac-verifier | ADD_NOTE | history | 同上；今天 verdict 只由 `rdd-verifier` 写入 SHA 绑定缓存（`_lib/archive.sh:786-791`） |
| openspec/specs/archive-gate-verification/spec.md | 115 | Direct archive fallback SHALL write structured verdi | ac-verifier | ADD_NOTE | history | 同上；今天 verdict 只由 `rdd-verifier` 写入 SHA 绑定缓存（`_lib/archive.sh:786-791`） |
| openspec/specs/archive-gate-verification/spec.md | 126 | Direct archive fallback SHALL write structured verdi | ac-verifier | ADD_NOTE | history | 同上；今天 verdict 只由 `rdd-verifier` 写入 SHA 绑定缓存（`_lib/archive.sh:786-791`） |
| openspec/specs/archive-gate-verification/spec.md | 127 | Direct archive fallback SHALL write structured verdi | ac-verifier | ADD_NOTE | history | 同上；今天 verdict 只由 `rdd-verifier` 写入 SHA 绑定缓存（`_lib/archive.sh:786-791`） |

## 逐文件汇总

| spec | ANNOTATE | REPOINT | ADD_NOTE | 合计 |
|---|---|---|---|---|
| `inline-ac-verifier-into-rdd-verifier` | 4 | 2 | 8 | 14 |
| `doc-truth-sync` | 4 | 4 | 0 | 8 |
| `archive-gate-verification` | 1 | 1 | 7 | 9 |

## 记 tail（范围外，本批不改）

1. **同 Requirement 内自相矛盾**（critic SF-2）：`archive-gate-verification:72-76` 的 THEN 说「`STRICT_AC_GATE=no` ⇒ it **blocks**」，与实现相反（`_lib/archive.sh:913-915` 只 warning；`phase3_archive.sh:135-137`；ADR-0035:81「默认 warning only」）。**本批改指 L70 后该矛盾从「藏在过时措辞里」变成「同一个 Requirement 里两句话打架」** ⇒ 须专项立项（改 THEN = 改活契约）。
2. **ADR 过时**（critic SF-2）：`docs/adr/ADR-0034-rdd-verifier-verify-phase-architecture.md:70` 仍写「`STRICT_AC_GATE` 仅控制 legacy direct ac-verifier fallback；不影响 cached verifier 状态」—— 与实现相反，也与本批改指后的文本矛盾。**ADR-0045:32** 已决定移除 fallback ⇒ ADR-0034 该句被后序 ADR 失效。⚠️ **builder 不得单方面改已签批 ADR 的决策内容** ⇒ 路由 architect 补 amendment。
3. `doc-truth-sync:227` 把 L1 定义为 `skills/*.md`（v3 单文件形态）；`:242` 用 v3 stage 名「ship-side」，`USAGE.md:331` 仍写「Ship 端（Phase 1, 1.5, 2, 2.5, 3, 4, 5）」。
4. `doc-truth-sync:133` 的 D6 描述的守卫范围比现行 `tests/unit/test_doc_contracts.py:46-60`（只查 `general/spec.md`）更宽。
5. `general/spec.md:62,128` 仍写 ship-side = **7 numbered subphases**（v3 模型），与 L1（`rdd-builder` 6-phase）不符；被 `tests/unit/test_doc_contracts.py:36-42,64-68` 锁定 ⇒ **本批改指后的 Scenario「update … general/spec.md to match」若被字面执行会撞该锁定**。
6. `docs-v4-sync-scope-followup:13` 说 README 目录树显示 `rdd-arch.md` / `rdd-builder.md` 等**单文件**名（v4 实为 `rdd-*/SKILL.md` 目录形态）—— 与本批 `doc-truth-sync:85` 同类的spec-vs-impl 漂移（该文件属批 3，本批未改）。

