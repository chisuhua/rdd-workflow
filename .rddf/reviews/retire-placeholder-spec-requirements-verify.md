# retire-placeholder-spec-requirements 验收报告

**change**: `retire-placeholder-spec-requirements`
**判据来源**: `openspec/changes/retire-placeholder-spec-requirements/proposal.md` 的 `## Acceptance`（AC-1 ~ AC-9）
**已用轮次**: 2（critic 2 轮 + 本验收）

## 逐条判定

| AC | 判定 | 证据 |
|---|---|---|
| **AC-1** placeholder Requirement 体命中数 = **0** | **PASS** | `scan_placeholder_requirements(Path('openspec/specs'))` ⇒ `扫描 165 份 spec，占位命中 0 处`。同一扫描器在**改前备份**上命中 **10 处** ⇒ 有判别力 |
| **AC-2** `general/spec.md` 退役 1 条、改写 2 条；剩余 Requirement 数 = **5** | **PASS** | `grep -n '^### Requirement:' openspec/specs/general/spec.md` ⇒ 5 条（`general-deps-subagent-semantic-analysis` / `general-adr-directory-structure` / `general-harden-doc-consistency` / `general-docs-match-code` / `general-add-env-cache-arch-discovery`） |
| **AC-3** **4 条**改写的断言逐条有守卫背书，且逐条可在当前实现上核实为真 | **PASS** | 台账「5 条 placeholder 的分流核算」表逐条列出**守卫测试名**：`test_deps_subagent.bats`（实测 8 例）· `test_adr_directory.bats`（实测 14 例）· `test_roadmap_refresh_fragments.py`（5 例）· `test_global_install_external_project.bats:190` + `test_install_lib_distribution.bats`。**两条无守卫的实现行为被明确排除**（「无 `SKILL.md` 的目录不安装」`install.sh:27`、「broken symlink 被清理」`install.sh:131-142`） |
| **AC-4** 3 份 spec 的 `## Purpose` 不再是 `TBD` 占位 | **PASS** | `openspec validate general` / `sync-agents-md-five-stage` / `sync-package-skills-to-disk` ⇒ 各自只输出 `Specification '<x>' is valid`，**无 Purpose WARNING**（改前各报 1 条） |
| **AC-5** 新守卫生效，且能抓住回归（负向验证） | **PASS** | 逐个注入并复测：完整 placeholder ✅抓到 / 半截①（只有 Requirement 正文）✅抓到 / 半截②（只有 Scenario 体）✅抓到；恢复正常后 `pytest tests/unit/test_doc_contracts.py -q` ⇒ 25 passed |
| **AC-6** `validate --all --json` issue 多重集只减不增；ERROR 不增；`very long` 不新增 | **PASS** | 新旧 specs 各拷进临时项目跑 `openspec validate --all --json` ⇒ **改前 224 条 / 改后 221 条**；`新增: 无`；`消失: 3 条 Purpose WARNING`；`very long: 62 → 62`；`openspec validate --all` ERROR **11 → 11** |
| **AC-7** 残留扫描器命中数不变 | **PASS** | `scan_specs(Path('.'))` ⇒ `未豁免 0/0/0`、`含已豁免 303/159/41`、豁免 303（新增 `scan_placeholder_requirements` 是**独立入口**，不动 `scan_specs` ⇒ `test_v4_residue_check.py` 的冻结常数不变） |
| **AC-8** `pytest tests/unit/` 全绿；`ruff check skills/_lib/` 全绿 | **PASS** | `pytest tests/unit/ -q` ⇒ **3523 passed, 3 skipped**（3522 + 1 新守卫）；`ruff check skills/_lib/` ⇒ **All checks passed!**；`ruff check` 本批改动文件（`spec_residue_scan.py` / `test_doc_contracts.py`）⇒ **All checks passed!** |
| **AC-9** `./test.sh --full --regression` 全绿 | **见下** | 见「全量门」 |

## 全量门

`BATS_TIMEOUT=120 BATS_TIMEOUT_RETRY=240 ./test.sh --full --regression`

结果：见「全量门」段。

## 遗留清扫

| 项 | 结果 |
|---|---|
| 本次范围内的 TODO / 半截实现 | 无 |
| 注释掉的代码 | 无新增 |
| 临时调试日志 | 无（实施脚本在 `/tmp/opencode/`，不入仓） |
| 被 skip 的测试 | 无新增 skip（本守卫在 `openspec/` 缺失时 skip —— 与既有 `requires_general_spec` 同款） |
| 未替换的 mock | 不涉及 |
| 临时 fallback 分支 | 无 |
| 未采纳的 finding | 无（3 BLOCKER + 4 SF + 2 NIT 全采纳；第 2 轮 1 NIT 也已修） |

## 实施期教训

1. **判据的「退役」与「改写」分流必须用「有没有可机械核实的行为契约」，不能用「名字在不在」。**
   我第一版用「全仓零命中」判退役 ⇒ 被 critic 证伪：deps 的 subagent 分析与 ADR 目录结构
   **能力都在、守卫都在**，只是**不以此名存在**。⇒ 改用「行为契约是否可机械核实」后，
   3 条里 2 条该改写、1 条才该退役。
2. **把 docstring / 实现细节写成「字节级不变」会冻错契约。**
   我写「every byte outside those sentinels SHALL be unchanged」，但
   `_lib/roadmap_state.py:1199-1205` 在哨兵边界做空白规范化 ⇒ 该断言在非规范空白输入下为假，
   且**无守卫**断言 byte-identity。⇒ 降级为「内容保留 + 紧邻空白 MAY 被规范化」。
3. **「有实现」不等于「有契约」。** `install.sh` 里「无 `SKILL.md` 的目录不安装」与
   「broken symlink 被清理」都有实现，但**没有守卫**⇒ 按本 change 自己的原则
   不能写进 spec（否则就是**凭空造契约**）。⇒ 明确排除并记录。
4. **黑名单正则要按「形态」而非「宽松通配」写。** 初版
   `The system SHALL provide .* functionality\.` 误伤了合法 Requirement
   （`cross-repo-deps/spec.md:228`，后面跟的是真 Scenario）⇒ 收紧为 **kebab-case 能力名**
   （`[a-z0-9][a-z0-9-]*`）⇒ 形态判据既精确又不误伤。
5. **「同处一个已跟踪模块」≠「CI 有牙齿」。** critic 建议把守卫并入已跟踪的
   `spec_residue_scan.py` 以解决 CI 空转 —— 但 `openspec/` 整树 gitignore
   （`git ls-files openspec/` = **0**）⇒ CI 上**根本没有** `openspec/specs/`
   ⇒ 放哪都空转。⇒ 能做的是「为将来 `git.openspec_tracked=true` 时零改动」，
   并把「CI 空转是既有立场」据实记入台账，而不是假装解决。

## 路由建议

无需返工。本批可归档。tail 的 2 条实现缺口（`rddf status` 缺 `review` 渲染、
`rddf archive` 缺交互确认门）属 `implementation_gap`，独立立项。
