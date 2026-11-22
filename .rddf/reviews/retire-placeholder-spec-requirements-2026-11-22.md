# retire-placeholder-spec-requirements 台账（2026-11-22）

## 范围

`openspec/specs/**` 里 **5 条零信息量的 placeholder Requirement**：1 条退役、4 条改写为对现有实现的断言；
3 份 spec 的 `## Purpose` 写实；新增 1 个守卫（判据实现放在已跟踪的 `spec_residue_scan.py`）。

## 为什么这批值得做

placeholder Requirement 的正文是自动生成的同义反复：

```
The system SHALL provide add-skill-bats-tests functionality.
- **WHEN** user invokes the feature
- **THEN** system implements add-skill-bats-tests correctly
```

它**对任何实现都恒真**（包括「功能不存在」）⇒ 零契约。但它让 `openspec validate` 报
「spec is valid」⇒ **制造「已覆盖」的错觉**。

## 审查链

| 轮 | 结论 | 处置 |
|---|---|---|
| 1 | **REJECT**（3 BLOCKER + 4 SHOULD_FIX + 2 NIT），`mergeable: no` / `scope_exceeded: false` | 3 BLOCKER **全部成立**，逐条修正 |
| 2（复审） | **APPROVE**，`mergeable: yes` / `scope_exceeded: false` | 3 BLOCKER + 4 SF + 2 NIT **全部闭合**；1 NIT（行号差 1）已修 |

### 第 1 轮 3 BLOCKER 处置

| # | finding | 处置 |
|---|---|---|
| **BLOCKER-1** | AC-2 的 Requirement 计数错误 —— 我写「现 7 / 退役后 4」，实际现 **6** | 我把 `doc-truth-sync/spec.md` 的 7 条记成了 `general` 的 ⇒ **AC-2 改为 5 条**（6 − 退役 1）。另核实 `general` **不在** `FROZEN_VERY_LONG` ⇒ 退役/改写不动冻结清单 |
| **BLOCKER-2** | 组 A 分流判据自相矛盾；「全仓零命中」被事实证伪 | 分流判据**统一**为「**行为契约是否可机械核实**」；`general-implement-deps-subagent-analysis` ⇒ 改写（8 守卫）；`general-init-adr-directory` ⇒ 改写（14 守卫）；`general-add-skill-bats-tests` ⇒ 仍退役但换判据（「一次性建设型能力，无持续可机械核实的行为契约」） |
| **BLOCKER-3** | 组 B 的「every byte outside those sentinels SHALL be unchanged」与实现矛盾 | 措辞降级为「哨兵块**之外的内容** SHALL 被保留；紧邻哨兵块的空白 **MAY** 被规范化」（与 `_lib/roadmap_state.py:1199-1205` 一致） |

### 第 1 轮 4 SF + 2 NIT 处置

| # | finding | 处置 |
|---|---|---|
| SF-1 | 守卫在 CI 空转 ⇒ 建议并入 tracked 的 `spec_residue_scan.py` | **部分采纳 + 据实修正 critic 的前提**：CI 空转的根因是 `openspec/` 整树 gitignore（`git ls-files openspec/` = **0**）⇒ CI 上不存在 `openspec/specs/` ⇒ 放进 `spec_residue_scan.py` **同样**空转。采纳的部分：判据实现放进**已跟踪**的 `spec_residue_scan.py`（**独立函数**，不动 `scan_specs` ⇒ 冻结常数不变），为将来 `git.openspec_tracked=true` 时零改动 |
| SF-2 | 两行同现漏检半截 placeholder | **两个正则独立成罪**；负向验证 3 变体全抓到 |
| SF-3 | 改写的断言需逐条有守卫背书 | 删掉两条**无守卫**的断言（「无 `SKILL.md` 的目录不安装」`install.sh:27`、「broken symlink 被清理」`install.sh:131-142`） |
| SF-4 | 组 A 表与 Capabilities 段需同步重述 | 已同步 |
| NIT-1 | 守卫用模块级 `skipif` marker 风格 | **采纳**（`requires_specs_dir`，与 `requires_general_spec` 同款） |
| NIT-2 | AC-8 的 ruff 与改动面无交集 | AC-8 改为「`pytest tests/unit/` 全绿 + ruff 全局基线不红」 |

### 第 2 轮 1 NIT

`test_global_install_external_project.bats:191` → 实际 `@test` 声明在 `:190` ⇒ 已改。

## 5 条 placeholder 的分流核算

| Requirement | 处置 | 依据 |
|---|---|---|
| `general-add-skill-bats-tests` | **退役** | **一次性建设型能力**（新增 skill 时补 bats 测试），**无持续可机械核实的行为契约** —— `tests/smoke.bats:19/:25/:42` 只动态检查 skill 文件存在 + frontmatter 合法，**不检查**「每个 skill 有 bats 覆盖」 |
| `general-implement-deps-subagent-analysis` → `general-deps-subagent-semantic-analysis` | **改写** | `tests/integration/test_deps_subagent.bats` **8 例**：Step 3 subagent 调用语法 · 三工件引用（`proposal.md`/`design.md`/`tasks.md`）· 失败降级路径已文档化 · Step 5 动态分支（`AI_RESULT_FILE` 或 fallback）· fallback 保留 `AI 语义分析未启用` · 无 `TODO` 残留 |
| `general-init-adr-directory` → `general-adr-directory-structure` | **改写** | `tests/integration/test_adr_directory.bats` **14 例**：`docs/adr/` + `ADR-0000-template.md` + `README.md` 三件套 · 模板 frontmatter + 4 必含段 · 每个真实 ADR 的 `# ADR-NNNN:` / 决策段 / `## Context` / status+date · README 记载 ADR-NNN §N.M 引用格式 |
| `sync-agents-md-five-stage` | **改写** | `tests/unit/test_roadmap_refresh_fragments.py` **5 例**：哨兵块重写 · 块外内容保留 · 幂等 · 新 feature 出现 · 目录缺失非零退出。实现链：`skills/roadmap/scripts/roadmap_update_agent_md.sh:44-48` → `_lib/roadmap_state_wrapper.py:171` → `_lib/roadmap_state.py:1124`；哨兵常量 `_lib/roadmap_state.py:1049` |
| `sync-package-skills-to-disk` | **改写** | `tests/integration/test_global_install_external_project.bats:190`（逐 skill `[ -L ]` + `readlink -f` + `[ -f "$target/SKILL.md" ]`）+ `tests/integration/test_install_lib_distribution.bats`（`skills/__init__.py` · `_lib/__init__.py` · `_lib/*.py` 递归 · `_lib/*.sh` · 排除 `__pycache__`/`plugins`/`schedulers`） |

**改名安全性**：2 条 `general-*` 的原名是**变更名**（不是能力名），全仓**仅出现在本 spec**（无跨文件引用）⇒ 改名安全。

## 组 D —— 守卫

**判据实现**（已跟踪）：`skills/rdd-doctor/scripts/spec_residue_scan.py` 新增**独立函数**
`scan_placeholder_requirements(specs_root)` —— **不动** `scan_specs` ⇒
`test_v4_residue_check.py` 的冻结常数（303/159/41）**不变**。

**两个正则独立成罪**（SF-2）：

| 正则 | 抓什么 |
|---|---|
| `^The system SHALL provide [a-z0-9][a-z0-9-]* functionality\.$` | 零信息的 Requirement 正文（**kebab-case 能力名**） |
| `- \*\*WHEN\*\* user invokes the (feature\|change)` 紧跟 `- \*\*THEN\*\* system implements .* correctly` | 零信息的 Scenario 体 |

**pytest 包装**（已跟踪）：`tests/unit/test_doc_contracts.py::test_no_spec_contains_placeholder_requirement_body`，
模块级 `requires_specs_dir` skipif marker（`openspec/` 缺失时 skip —— 与既有
`requires_general_spec` / `requires_doc_truth_spec` 同款）。

**实施期发现（正则收紧）**：初版 `The system SHALL provide .* functionality\.` **误伤**合法 Requirement
`cross-repo-deps/spec.md:228`（「The system SHALL provide comprehensive test coverage for
cross-repo dependency functionality.」—— 后面跟的是**真** Scenario）⇒ 收紧为 **kebab-case 能力名**
⇒ 合法散文不再命中。

**判别力验证**：改前备份上跑新守卫 ⇒ 命中 **10 处**（3 份 spec 的 5 条 Requirement）⇒ 有判别力。

**负向验证（3 变体，逐个注入并复测）**：完整 placeholder ✅ / 半截①（只有 Requirement 正文）✅ /
半截②（只有 Scenario 体）✅。

⚠️ **CI 空转（据实）**：本仓 `git.openspec_tracked=false` ⇒ `git ls-files openspec/` = **0**
⇒ CI 上**不存在** `openspec/specs/` ⇒ **任何**扫 `openspec/specs/` 的检查在 CI 都空转
（本守卫与既有 `requires_general_spec` 同款）。⇒ 这不是守卫放错位置，而是既有立场。

## 验证

| 项 | 改前 | 改后 |
|---|---|---|
| placeholder Requirement 体命中 | **10 处 / 3 份 spec** | **0** |
| `openspec validate --all --json` issue | 224 | **221**（3 个 Purpose WARNING 消失；**新增 0**） |
| `very long` | 62 | **62**（改写后的 Requirement 正文均 ≤ 500 字符） |
| `validate --all` ERROR | 11 | **11** |
| 残留扫描器（未豁免 / 含已豁免） | 0/0/0 · 303/159/41 | **不变** |
| `general/spec.md` Requirement 数 | 6 | **5** |
| `pytest tests/unit/` | 3522 | **3523 passed / 3 skipped**（+1 守卫） |
| `ruff`（门范围 + 本批改动文件） | 绿 | **绿** |
| `openspec validate <3 份 spec>` | 各 1 条 Purpose WARNING | **无 WARNING** |

## 回滚凭据

- 整树备份：`/tmp/opencode/specs-backup-rpsr-<ts>/`（165 份）
- 单文件快照：`/tmp/opencode/rpsr-before/{general-spec.md,sync-agents-md-five-stage-spec.md,sync-package-skills-to-disk-spec.md}`
- 实施脚本：`/tmp/opencode/rpsr_apply.py`（内容匹配 + `count(old)==1` 断言，可 `--dry-run`）
- ⚠️ `openspec/` 整树 gitignored ⇒ spec 改动**无 git diff**，上述备份是唯一回滚凭据

## 进 tail（本批不处置）

1. **150 份 spec 的 `## Purpose` 仍是 `TBD - created by archiving change X` 占位**
   （实测 165 份中 150 份命中）⇒ `openspec validate` 对每份都报 Purpose WARNING。
   本批只修被触碰的 3 份；其余 147 份需**逐份写实**（不能机械替换）⇒ 独立立项。
2. **`doc-truth-sync` 的 Requirement 主题划分**（`fix-doc-truth-sync-false-assertions` 第 2 轮 critic NIT-1）。
3. **`rddf status` 缺 `review` 状态渲染**（实现缺口）：`_lib/cli/status_cmd.py:58-65`
   的 `_STATUS_ICON` 无 `review` 键（iteration schema 枚举里仍有 `review`）。
4. **`rddf archive` 缺交互确认门**（实现缺口）：`_lib/archive.sh:1025` 无条件
   `openspec archive "$name" --yes`。
5. `install.sh:27` 与 `_count_skill_files()` 的 `deprecated:` 口径分叉 ·
   `docs/improvement-approved-format.md:3` · `rfc-rddf` 的 14 个 `acceptance-N` ·
   62 条 `very long`（冻结）· CI 上 `openspec/` 不存在导致 spec 校验空转。
