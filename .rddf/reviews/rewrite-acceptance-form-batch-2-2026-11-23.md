# rewrite-acceptance-form-batch-2 台账（2026-11-23）

## 范围

`acceptance-N` 系列**第 2 批**（3 份 spec / 27 条 AC）⇒ **19 条契约 + 8 条退役**；
清单 promote 1 → **4** 份；**扩展 2 个既有 bats 用例**（补 critic 指出的无守卫子句）。

## 审查链

| 轮 | 结论 | 处置 |
|---|---|---|
| 1 | **APPROVE_WITH_CONDITIONS**（0 BLOCKER + 4 SHOULD_FIX + 3 NIT），`mergeable: yes` / `scope_exceeded: false` | 4 SF + 3 NIT **全部采纳** |

### 第 1 轮 finding 处置

| # | finding | 处置 |
|---|---|---|
| **SF-1** | `fix-worktree-archive-path` 的「branch SHALL be removed」子句**无守卫**（守卫只断言 worktree 目录删除） | **补守卫**：`test_phase3_archives_in_main_repo.bats` 的 cleanup 用例加 `git rev-parse --verify --quiet refs/heads/openspec/demo` ⇒ 断言分支不存在（fixture 用 `git worktree add -q .rddf/wt/demo -b openspec/demo` 建了该分支 ⇒ 断言非空转） |
| **SF-2** | `fix-p3-verifier-gate` 的「消息列出三条出路」子句**无守卫**（守卫只断 `rdd-verifier`） | **补守卫**：`test_rdd_builder_phase3_archive.bats` 的 missing-cache 用例加 `rddf rdd-verify` / `SKIP_RDD_VERIFIER` / `.ac-verdict-demo.json` 三条断言（三条都在 `_lib/archive.sh:947-951` 的消息里） |
| **SF-3** | `archive-gate-runs-when-openspec-is-untracked` **引错守卫**（`test_rdd_builder_phase3_archive.bats` 的夹具是 lightweight 模式） | **改正**为 `tests/integration/test_archive_gate_tracked_false.bats` 的两个用例 |
| **SF-4** | AC-9 退役理由文本**不准确**（critic 核出 `archive_commit_sha` 有 helper 级 + lightweight 流程守卫） | 退役结论不变，理由改为准确表述：「**没有流程级守卫**断言 worktree/untracked 路径写入这两个字段（untracked 路径 `_lib/archive.sh:1034` 传**空 sha**；`archive_path` **全仓无守卫**）；已有守卫不覆盖本 AC 的路径」 |
| **NIT-1** | dry-run「byte-identical」与守卫力度不符（守卫只比路径列表） | 措辞改为「the set of files under the fixture's state directory SHALL be unchanged」 |
| **NIT-2** | `SHALL NOT migrate or stage anything` 无守卫 | 删掉该子句，改为有守卫的「the message SHALL state that the two options are mutually exclusive」；「输出多少个文件」改为「输出哪些文件」 |
| **NIT-3** | tracked 路径引的是 grep 级守卫 | 改引**行为级**守卫 `test_phase3_return_code_mapping.bats` → `success → phase3 exits 0 and the worktree branch is merged into the default branch` |

### 第 1 轮 focus 结论（要点）

- **focus 1（8 条退役全部成立）**：critic 核出全仓唯一断言「归档后 spec 文件存在」的
  `test_rdd_builder_e2e.bats:89` 是 **mock 型 e2e**（`scenarios/b_e9.json:12` 直接铺文件）
  ⇒ AC-4 的「无守卫」判定成立；AC-8 的推翻登记构成充分证据。
- **focus 2（19 条守卫背书）**：16 条核实为真；3 处缺口 = SF-1 / SF-2 / NIT-3（已处置）。
- **focus 3（基线重建忠实）**：3 份 spec 各只有**一个**归档 change 携带同名 delta 目录（无后续修改者）
  ⇒ delta 重建是唯一且充分的基线来源。
- **focus 4（AC-8 退役的信息损失）**：**不成立** —— 新的 lightweight 行为已落在
  `archive-openspec-tracked-skip-commit/spec.md:44-72` 与 `archive-auto-commit/spec.md:85-107`。

## 27 条 AC 的分流

### `fix-flow-drift-batch-1`（8 → 6）

| AC | 处置 | 新 Requirement 名 | 守卫 |
|---|---|---|---|
| 1 + 2 | **合并**改写 | `ac-header-variants-are-parsed-uniformly`（2 Scenario） | `tests/unit/test_rdd_verifier_protocol_headers.py::test_parse_acs_accepts_every_header_variant`（parametrize ×3）+ `::test_skill_doc_lists_every_header_variant` |
| 3 | 改写 | `layout-fix-hint-distinguishes-file-from-directory` | `tests/integration/test_doctor_layout_fix_hint.bats`（2 例） |
| 4 | 改写 | `rdd-verify-dry-run-writes-nothing` | `test_rdd_verify_dry_run.bats` → `rdd-verify --dry-run does not move legacy state files` |
| 5 | 改写 | `rdd-verify-dry-run-reports-what-it-would-migrate` | → `rdd-verify --dry-run still reports what it would migrate` |
| 6 | 改写 | `rdd-verify-dry-run-and-stage-are-mutually-exclusive` | → `rdd-verify --dry-run --stage is rejected (mutually exclusive)` |
| 7 | 改写 | `rdd-verify-stage-still-migrates-and-stages` | → `rdd-verify --stage (non dry-run) still migrates legacy state and stages` |
| 8 | **退役** | — | 元断言（全绿） |

### `fix-worktree-archive-path`（10 → 6）

| AC | 处置 | 新 Requirement 名 | 守卫 |
|---|---|---|---|
| 1 | 改写 | `phase3-worktree-mode-delegates-to-archive-change`（2 Scenario） | `test_phase3_archive_delegation.bats` → `phase3: no longer calls 'openspec archive' itself in worktree mode` + `phase3: worktree mode delegates to archive_change` |
| 2 | 改写 | `phase3-no-longer-runs-post-archive-cleanup-itself` | → `phase3: no longer calls post_archive_cleanup itself (archive_change does)` |
| 3 | 改写 | `worktree-archive-runs-in-the-main-repository` | `test_phase3_archives_in_main_repo.bats` → `phase3: the archive runs in the MAIN repo, not in the worktree` |
| 4 | **退役** | — | **无守卫** —— 全仓唯一断言「归档后 spec 存在」的 `test_rdd_builder_e2e.bats:89` 是 mock 型 e2e |
| 5 | 改写 | `worktree-directory-and-branch-are-cleaned-up` | → `phase3: the worktree is cleaned up after the delegated archive`（**本批扩展**：加分支删除断言） |
| 6 | 改写 | `tracked-openspec-archive-merges-back-into-the-main-repository` | `test_phase3_return_code_mapping.bats` → `success → phase3 exits 0 and the worktree branch is merged into the default branch` + `test_archive_with_openspec_tracked_false.bats` → `archive: openspec_tracked=true (default) preserves git merge path` |
| 7 | 改写 | `phase3-maps-gate-refusal-to-exit-7` | `test_phase3_archive_delegation.bats` → `phase3: maps archive_change exit 3 (gate refused) to exit 7` + `test_phase3_return_code_mapping.bats` |
| 8 | **退役** | — | **已被推翻** —— `.rddf/improvements/fix-lightweight-branch-and-archive.md:233-235`：「`fix-worktree-archive-path` 的 AC-8 写『lightweight 模式行为不变』，本项**有意变更**该模式」⇒ 新行为已落在 `archive-openspec-tracked-skip-commit/spec.md:44-72` 与 `archive-auto-commit/spec.md:85-107` |
| 9 | **退役** | — | **没有流程级守卫**断言 worktree/untracked 路径写入 `archive_path` / `archive_commit_sha`（untracked 路径 `_lib/archive.sh:1034` 传**空 sha**；`archive_path` **全仓无守卫**）；且与 `register-change-in-iteration` 的 `archive-sync-updates-registered-change` 重复 |
| 10 | **退役** | — | 元断言（全绿） |

### `fix-p3-verifier-gate`（9 → 7）

| AC | 处置 | 新 Requirement 名 | 守卫 |
|---|---|---|---|
| 1 | 改写 | `phase3-runs-the-archive-gate-before-archiving` | `tests/unit/test_phase3_verifier_wiring.py::phase3_has_no_default_pass_on_verifier_exit` |
| 2 | 改写 | `no-verifier-run-reference-in-code` | → `::no_verifier_run_reference_in_code` |
| 3 | 改写 | `archive-gate-runs-when-openspec-is-untracked` | `tests/integration/test_archive_gate_tracked_false.bats` → `tracked=false: archive_change refuses when no verdict cache exists` + `tracked=false: rejection comes from the AC gate, not worktree lookup` |
| 4 | 改写 | `missing-verdict-cache-fails-phase3-with-recovery-hints`（2 Scenario） | `test_rdd_builder_phase3_archive.bats` → `phase3: refuses to archive when no verdict cache exists`（**本批扩展**：加三条出路断言）+ `phase3: refuses when cached verdict is incomplete (AC set mismatch)` |
| 5 | 改写 | `skip-rdd-verifier-requires-a-bypass-reason`（2 Scenario） | → `phase3: SKIP_RDD_VERIFIER without reason fails closed` + `phase3: SKIP_RDD_VERIFIER with reason passes and writes bypass audit` + `test_rdd_verifier_skip.bats` |
| 6 | 改写 | `stale-verdict-cache-blocks-the-archive` | → `phase3: refuses when cached codebase_commit is stale` |
| 7 | 改写 | `strict-ac-gate-blocks-a-cached-ac-failure` | `test_ac_verifier_archive_gate.bats` → `archive_gate_check blocks on cached AC fail with STRICT_AC_GATE=yes` + `test_rdd_builder_phase3_archive.bats` → `phase3: cache with failed ACs blocks under STRICT_AC_GATE=yes` |
| 8 | **退役** | — | 元断言（描述测试矩阵「覆盖 complete / missing / stale-sha 三态」） |
| 9 | **退役** | — | 元断言（staging 语义不变 + 全绿） |

## 清单 promote

`tests/unit/spec_form_compliant.json`：`compliant` 1 → **4** 份 ·
`pending` 11 → **8** 份（`class_total` 12 不变）。

## 验证

| 项 | 改前 | 改后 |
|---|---|---|
| 3 份的 `acceptance-N` Requirement 名 | 27 | **0** |
| 3 份的恒真 WHEN | 27 | **0** |
| 3 份的 Requirement 数 | 27 | **19**（6 + 6 + 7） |
| `acceptance-N` 类的剩余条数（全仓） | 218 | **191** |
| `openspec validate <3 份>` | 各 1 条 Purpose WARNING | **无 WARNING** |
| `openspec validate --all --json` issue（**准确基线**） | 220 | **217**（新增 0；消失 3 条 Purpose WARNING） |
| `very long` | 62 | **62** |
| `validate --all` ERROR | 11 | **11** |
| 残留扫描器（未豁免 / 含已豁免） | 0/0/0 · 303/159/41 | **不变** |
| `pytest tests/unit/` | 3529 | **3534 passed / 3 skipped** |
| `ruff check skills/_lib/` | 绿 | **绿** |
| 被扩展的 2 个 bats 文件 | — | **全绿** |

**准确基线的重建**：`openspec/` 整树 gitignored ⇒ 无 git diff 可比。3 份 spec 各由**唯一的**归档
change 以 `## ADDED Requirements` delta 创建（critic 核实无后续修改者）⇒ 改前内容由 delta 精确重建
⇒ 重建脚本 `/tmp/opencode/rebuild_baseline_b2.py`，基线树 `/tmp/opencode/specs-baseline-b2/`。

## 回滚凭据

- 基线树：`/tmp/opencode/specs-baseline-b2/`（165 份，改前状态）
- 清单改前：`git show HEAD:tests/unit/spec_form_compliant.json`
- ⚠️ `openspec/` 整树 gitignored ⇒ spec 改动**无 git diff**，上述基线是唯一回滚凭据

## 实施期教训

1. **「无守卫子句」有两种修法：补守卫 vs 收窄契约。** 本批 2 处（branch 删除、消息三条出路）
   都选了**补守卫** —— 行为是真的、守卫是缺的 ⇒ 补守卫比削契约好。
   ⚠️ 补之前先确认**断言非空转**：branch 那条依赖 fixture 用 `-b openspec/demo` 建了分支。
2. **退役理由本身也要经得起核。** 我写「没有测试断言 `archive_commit_sha` 被写入」—— critic 核出
   **有** helper 级与 lightweight 级守卫 ⇒ 退役结论不变，但理由必须改成
   「**没有流程级守卫**断言 worktree/untracked 路径写入它」⇒ **退役理由不准确 ≠ 退役结论错**，
   但错误理由会误导后续读者。
3. **守卫引用要核对「夹具是什么」。** `test_rdd_builder_phase3_archive.bats` 的夹具是
   **lightweight 模式** ⇒ 拿它当「untracked-openspec 路径」的守卫是引错了（critic SF-3）。
4. **e2e 的 mock 型测试不算行为守卫。** 全仓唯一断言「归档后 spec 存在」的
   `test_rdd_builder_e2e.bats:89` 由 `scenarios/b_e9.json:12` 直接铺文件 ⇒ 不能当「spec 合流」的背书。

## 进 tail（本批不处置）

1. **剩余 8 份 `acceptance-N` spec**（`env-bootstrap` 44 · `objective-tracking` 33 ·
   `fix-skill-post-install-discoverability` 31 · `fix-bats-per-file-timeout` 22 ·
   `rddf-layout-manifest` 16 · `fix-script-project-root-anchoring` 16 ·
   `rfc-rddf-project-yaml-config-i10` 14 · `fix-phase3-cleanup-wiring` 13）
   ⇒ 剩 ≈4–6 h，可拆 3 批（3 + 3 + 2）。
2. **`openspec/` 是否取消 gitignore** —— 用户已决定「暂不决定，继续现状」⇒ 本系列的内容级守卫
   仍**只在本地生效**；清单级判据仍 CI 可见。
3. **`rddf archive` 缺交互确认门**（行为变更，需用户拍板）。
4. **150 份 spec 的 `## Purpose` 仍是 `TBD - created by archiving change X` 占位**（165 份中 147 份命中
   —— 本系列已修 3 份）。
5. `doc-truth-sync` 的 Requirement 主题划分 · `install.sh:27` 的 `deprecated:` 口径分叉 ·
   `docs/improvement-approved-format.md:3` · 62 条 `very long`（冻结）。
