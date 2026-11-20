# 验收报告 — fix-v4-doc-drift-live-invocations

- **change**：`openspec/changes/fix-v4-doc-drift-live-invocations/`
- **验收时间**：2026-11-20
- **实现提交**：`（待提交）`
- **判据来源**：`openspec/changes/fix-v4-doc-drift-live-invocations/proposal.md` 的 `## Acceptance`（AC-1 ~ AC-11）

## 审查链（实施前）

| 环节 | 结论 | 处置 |
|---|---|---|
| critic（`review_profile: build, plan`） | **APPROVE_WITH_CONDITIONS**，mergeable: yes，scope_exceeded: false | 4 条 SHOULD_FIX 全部纳入：① `_lib/wave_scheduler_hooks.sh:38,72` 的运行时 print（漏网的活指令发射器）；② `USAGE.md:428/445/474` 三处祈使句并入 Part 3；③ 计数推算需 T2.0 取证 + `INSTALL.md:18` 的「带日期版本史」裁决；④ `:484` 的 `guide-plan-noninteractive` 是真实归档 change 名 ⇒ 改加注保留。另采纳 3 条 NIT |

**BLOCKER**：无。

## 逐条判定与证据

| AC | 判定 | 证据（命令 → 输出摘要） |
|---|---|---|
| AC-1 `skill_use("guide")` 零残留 | **pass** | `grep -rn 'skill_use("guide")' skills/ README.md USAGE.md install.sh improvement-suggestions.md _lib/templates/` → **0 命中**；`grep -n '\| \`guide\` \|' USAGE.md` → 子技能表行已删 |
| AC-2 计数三方一致 | **pass** | 磁盘 `skills/*/SKILL.md` = **26**；`package.json::skills[]` = **26**；`USAGE.md` 的「**26** 个 per-skill 子目录」；`skills/INSTALL.md` 的「当前 **26** 个」；**否定判据** `grep -c '27 个子技能' skills/INSTALL.md` = **0** |
| AC-3 活指令形态零残留 | **pass** | 按活指令形态匹配（`skill_use("guide-design")\|...\|--phase guide-ship\|运行 guide-ship\|调用 \`guide-ship\``）扫 `skills/ README.md USAGE.md install.sh improvement-suggestions.md _lib/ _lib/templates/ docs/architecture/` → **0 命中**。**`docs/migration/*` 已从判据排除**：`v3-to-v4.md:103-105` 的 `sed -e 's/skill_use("guide-design")/skill_use("rdd-planner")/g'` 是**迁移指引的替换目标**（左侧必含旧名），属正当命中 |
| AC-4 失效平台 API 零残留 | **pass** | `grep -rn 'subagent_type=\|run_in_background=false\|load_skills=' skills/` → **0 命中**；`grep -c 'guide-plan\|guide-ship' _lib/wave_scheduler_hooks.sh` → **0**；`bash -n _lib/wave_scheduler_hooks.sh` → OK |
| AC-5 守卫禁止名单含 standalone `guide` | **pass** | `grep -q 'guide\|guide-arch' tests/integration/test_v4_doc_drift_contracts.bats` → 名单现为 `guide-arch\|guide-design\|guide-plan\|guide-ship\|guide-spec\|execute\|status\|guide`（`guide` 置末避免正则回溯优先匹配 `guide-*`）；测试名同步为 `no live guide*/execute/status ...` |
| AC-6 新守卫「`skills/*/SKILL.md` 无活 `skill_use("guide*")`」能红 | **pass** | 新文件 `tests/integration/test_v4_drift_guards.bats`。**红测**：往 `skills/roadmap/SKILL.md` 注入 `skill_use("guide")` ⇒ `not ok 2 drift_guards: skills/*/SKILL.md have no live retired-skill invocations`；备份还原后 ⇒ `ok 2`。**未用 `git checkout` 还原**（会丢本 change 对同一文件的改动）⇒ 用 `/tmp` 备份 |
| AC-7 计数一致性守卫能红 | **pass** | 扩展 `tests/integration/test_skill_metadata_consistency.bats`（新增第 3 条 `prose skill counts in USAGE.md / INSTALL.md match disk`）。**红测**：`USAGE.md` 的 26 → 27 ⇒ `not ok 3`；备份还原后 ⇒ `ok 3`。判据**钉哨兵短语**（`(\d+)\s*个 per-skill 子目录` / `当前\s*(\d+)\s*个`）而非泛扫「N 个」—— 否则 `INSTALL.md` 的带日期版本史行将来必然误伤 |
| AC-8 关键 bats 绿 | **pass** | `bats test_v4_doc_drift_contracts.bats test_v4_drift_guards.bats test_skill_metadata_consistency.bats test_usage_freshness.bats test_doc_phase_consistency.bats test_skill_description_convention.bats` → 仅 **`not ok 36 every SKILL.md description references role.boundaries`**，该条在 `tests/KNOWN_FAILURES.txt:70`（`feat-doc-drift-cleanup`，`skills/rdd-env-bootstrap/SKILL.md` 缺 `role.boundaries`）⇒ **基线已知失败，可放行**。其余全绿 |
| AC-9 无新增失败 | **pass** | `python3 -m pytest tests/unit/ -q` → **3455 passed, 3 skipped**（与基线一致） |
| AC-10 全量门 | **pass** | `BATS_TIMEOUT=120 BATS_TIMEOUT_RETRY=240 ./test.sh --full --regression` → **`GATE_RC=0` / `✅ ALL PASSED`**。分项：isolation gate OK / ruff OK / mypy strict OK / rdd-doctor structural 10 类全过（2 类 warning）/ **bats regression: 评估 229/229（含本 change 新增的 `test_v4_drift_guards.bats`），未评估 0，新增失败 0（403s）** / pytest unit OK / pytest integration OK |
| AC-11 原子性 | **pass** | rdd-workflow 仓单提交（提交后确认） |

## 首次全量门失败的处置记录

第一次全量门（`full_gate_B.log`）报 `GATE_RC=1`，**1 个新增失败**：`setup ai-context: 5 structure segments present`。

**根因**：`tests/integration/test_setup_ai_context.bats:70` 的断言 `grep -q "skill_use.*guide" "$TMPDIR/AGENTS.md"` —— 它固化「Layer 0 模板必须含 `skill_use("guide")`」。本 change 把模板的推荐入口从 skill 改成 `rddf guide` CLI ⇒ 断言失效。

**处置**：改为 `grep -qF "rddf guide"`（入口从 skill 变 CLI），测试名与注释同步。**这是修一个固化了已退役 skill 的断言，不是绕过测试** —— 与本 change 修 `test_usage_freshness.bats:36` 是同一类（那个断言强制 USAGE.md 必须含 `skill_use("guide")`）。

**预检**：修完后扫了 `tests/` 全目录的 `skill_use.*guide` 断言，确认无第三处同类固化（其余均为对 `rddf guide` 的正向使用或 `v4_residue_check.py` 的检测器 fixture）。

## 实施中修正的判据/断言缺陷

1. **AC-3 判据把迁移指引误判为漂移** —— `docs/migration/v3-to-v4.md:103-105` 的 `sed -e 's/skill_use("guide-design")/skill_use("rdd-planner")/g'` 含 `skill_use("guide-design")` 形态，但它是**替换目标**（左侧必含旧名）。critic 已预先指出「守卫不扫 `docs/migration/` 正确」，实施时据此把 `docs/migration/*` 从 AC-3 扫描路径移除，并回写 proposal/tasks。
2. **`test_usage_freshness.bats:36` 的断言固化了已退役 skill** —— 原断言 `grep -qE 'skill_use\("guide"\)' USAGE.md` 强制 USAGE.md 必须展示 `skill_use("guide")`，与「guide 已退役」直接矛盾。改为 `grep -qF 'rddf guide' USAGE.md`（入口从 skill 变为 CLI），测试名同步更新。**这是修一个固化了漂移的断言，不是绕过测试**。

## 遗留清扫

- 本次范围内（T6.6）：`git diff HEAD | grep -E '^\+.*(TODO|FIXME|breakpoint\(|pdb\.|console\.log)'` → **0 命中**；`git diff HEAD -- tests/ | grep -E '^\+.*\bskip\b'` → **0 命中**。
- 范围外既有遗留（**只记录，本 change 不承担**，已在 proposal 的 Out of Scope 逐条登记）：
  - `docs/architecture/**` 6 处（**architect 管辖**）
  - `USAGE.md` 剩余 7 处 `guide-ship` 历史性引用
  - 运行时数据词汇：`_lib/state.sh:175,567`、`_lib/feedback_appender.py:34`
  - `openspec/specs/**` 18 份 spec 的约 40 处 MUST（Change C）
  - `skills/propose/scripts/propose_quality_check.py:205`

## 失败项与路由建议

无。`implementation_gap` / `proposal_drift` 均不适用。

## 备注（不阻断）

1. **critic 的 4 条 SHOULD_FIX 全部落地**：`wave_scheduler_hooks.sh:38,72` 的运行时 print（漏网项）、`USAGE.md:428/445/474` 三处、计数取证与 `INSTALL.md:18` 裁决、`:484` 的溯源标识改加注。
2. **一条新发现**：`test_usage_freshness.bats:36` 与 `test_setup_ai_context.bats:70` 是**两处固化了已退役 skill 的断言**（强制断言 `skill_use("guide")` 存在）。它们让「退役 guide」这件事在测试层被锁死 —— 属需要随退役一并更新的断言，已修改。
3. **范围外既有遗留（记 tail，已在 proposal 的 Out of Scope 逐条登记）**：`docs/architecture/**` 6 处（architect）、`USAGE.md` 剩余 7 处 `guide-ship`、运行时数据词汇（`_lib/state.sh:175,567` / `_lib/feedback_appender.py:34`）、`openspec/specs/**`（Change C）、`skills/propose/scripts/propose_quality_check.py:205`。
