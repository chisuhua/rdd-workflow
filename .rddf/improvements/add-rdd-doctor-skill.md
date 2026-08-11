# add-rdd-doctor-skill

**优先级**: P1 | **来源**: 用户提议 + brainstorm 2026-08-07
**阶段**: v2.1 | **分类**: infra-setup | **类型**: feature

## 架构依据

**背景**

rdd-workflow v2.1 工作流涉及多类**结构化状态文件**，分布在 gitignored / git tracked 两条路径上：

| 路径 | Git 状态 | 当前校验 |
|------|---------|---------|
| `.rddf/state/*.json`（state_vector / sessions / iteration / deps-analysis） | gitignored | 分散在各 reader，无统一校验 |
| `.rddf/plans/*.md`（TDD 5 步契约） | tracked | `execute` 读时假设格式正确，无前置 schema 校验 |
| `openspec/changes/*/roadmap-meta.yaml`（含 manual_deps ADR-0022） | tracked | deps 阶段 schema 漂移**会静默跳过**，无可见告警 |
| `proposal-suggestions.md` / `proposal-approved.md`（Markdown 表格索引） | tracked | `propose` / `guide-design` reader 自己解析，parser 改 doctor 没改就漏报 |
| `openspec/changes/*/tasks.md`（checkbox 进度） | tracked | `execute` 写回时假设一致，无外部审计 |

**已有相关基础设施（不能重复造轮子）**

- **`rdd-env-check`** skill（v1.0）：独立诊断技能，先例。检查**环境**（openspec CLI / git / branch / build dir），缓存到 `.rddf/state/.env-cache.json`。**不查文件内容**。
- **ADR-0018 (arch-quality-gate)**：arch 阶段 4 个 warning 级检查（alignment / debt / clarity / handoff），通过 `register_gate_check()` 接入 `gate.py`。**仅 arch 阶段触发，phase 末尾硬阻断**。
- **ADR-0019 (change-arch-alignment)**：同模式，change 提案层 3 个检查。**仅 plan 阶段触发**。
- **ADR-0007 (gate-mechanism)**：插件式门控机制，error/warning 两级 + `STRICT_*_GATE=yes` 升级。

**真正的 gap**

三者都是 **phase-bound hard gate**，而 doctor 需要的是 **phase-independent read-only diagnostic**：

| 维度 | 现有 gate（ADR-0018/0019） | rdd-env-check | **doctor（本提案）** |
|------|---------------------------|---------------|---------------------|
| 触发 | phase 末尾自动 | 手动 / phase 入口自动 | **手动**（用户主动跑） |
| 行为 | warning / 阻断 | 单行状态 + JSON | **分级报告 + 可选 JSON** |
| 范围 | arch-only / change-only | 环境（CLI/git/build） | **5 类结构化文件** |
| 修改文件 | 否 | 否（只写 cache） | **否（只读）** |
| 自动修复 | 否 | 否 | **否** |

**doctor 不替代现有 gate**——它是**互补层**：

1. 用户**已经做完某个 phase**后怀疑"流程哪里坏了" → 跑 doctor 排查（gate 已放过的不代表文件后续没坏）
2. gate 升级为 `STRICT_*_GATE=yes` 之前**先跑 doctor** 看会暴露多少问题（预测 CI 失败）
3. **`gitignored` 文件**（`.rddf/state/*.json`）**没有任何兜底**，doctor 是唯一防线

**复用 / 不复用原则**

- ✅ **复用**：`_lib/schemas/` 现有 JSON schema；rdd-env-check 的"单行 + JSON"双模式模板；`openspec validate` 的退出码惯例（0/1/2/3）
- ❌ **不复用**：`register_gate_check()` 插件机制（doctor 不是 gate）；`_lib/post_archive_cleanup.sh` 的白名单 + auto-commit 模式（doctor 必须只读）

## 范围

#### In Scope

**A. 新增 skill**：`skills/rdd-doctor/`
- `SKILL.md`（frontmatter + 调用契约，对标 rdd-env-check 41 行）
- `scripts/doctor.sh`（bash 入口，~80 行，分发到 5 类检查 + 输出聚合）
- `scripts/doctor_render.py`（Python 分级聚合器，~120 行，含 `--json` 序列化）
- `scripts/checks/`（5 个 Python 检查器，每类 ~60 行）

**B. 检查覆盖（5 类）**

| # | 类别 | 检查内容 | 复用 / 新写 |
|---|------|---------|------------|
| 1 | `.rddf/state/*.json` schema | 校验 `state_vector` / `sessions` / `iteration` / `deps-analysis` 4 个 JSON file 对其 schema（`_lib/schemas/`） | **复用**现有 schema + **新写** checker |
| 2 | `.rddf/plans/*.md` TDD 5 步结构 | 校验 `rdd-workflow-writing-plans` 输出的契约结构（Write failing test / Verify fail / Implement / Verify pass / Commit） | **新写**（无现成 schema） |
| 3 | `openspec/changes/*/roadmap-meta.yaml` | 校验字段 + `manual_deps` / `manual_blocks` 类型（ADR-0022） | **新写**（deps 阶段静默跳过的根因防线） |
| 4 | `proposal-suggestions.md` / `proposal-approved.md` 表格格式 | 列数 + 必填字段 + 链接有效性 | **新写** |
| 5 | `openspec/changes/*/tasks.md` checkbox 一致性 | `- [ ]` / `- [x]` 计数 + 文件存在性 | **新写**（v1 故意不交叉验证 openspec status：openspec CLI v1.4.1 `status --change X --json` 对缺少 `schema` 字段的 change 直接报 "Invalid metadata"，且 `isComplete` 实际由 artifact 存在性而非 checkbox 进度决定，交叉验证**实质 vacuous**） |

**C. 输出模式（双模式，对标 rdd-env-check）**

- **默认模式**：人类可读分级报告（CRITICAL / WARNING / INFO 段），退出码 0/1/2/3
- **`--json` 模式**：写结构化报告到 `.rddf/state/.doctor-report.json`（gitignored），供后续 hook / CI 消费
- **`--category <name>`** 过滤：单跑某类检查（5 选 1）
- **`--quiet`**：只输出最严重级别（适合 cron / CI 噪声控制）

**D. 测试**

- `tests/integration/test_rdd_doctor.bats` ≥15 场景（每类 ≥2 + 输出模式 ≥3 + 边界 ≥2）
- `tests/unit/test_doctor_render.py` ≥6 场景（分级聚合 + JSON 序列化 + 退出码映射）

**E. 文档同步**

- `AGENTS.md` 新增「rdd-doctor 调用 + 何时该跑」段（~15 行）
- `tests/README.md` 添加一行入口引用
- **不**新增 ADR（不涉及架构决策，纯工具层）

#### Out Scope

| 不做 | 原因 |
|------|------|
| **自动修复**（包括 sed/awk/Y/N 提示） | 违反"只读诊断"原则；fix tasks.md checkbox 等于伪造状态；fix 错回滚成本高 |
| **接入 gate 系统**（`register_gate_check()`） | doctor 不是 gate；hard-block 会改变现有 phase 行为，超出 v1 范围 |
| **各 phase 入口自动调用** | 用户已确认 v1 = 仅手动；后续可作 v2 follow-up |
| **修改 `_lib/schemas/` 现有 JSON schema** | schema 漂移是用户报告的"幽灵 schema"，doctor 应**报告漂移**而非改 schema |
| **重写 `rdd-env-check`** | 两者职责清晰：env-check = 环境，doctor = 文件；不合并 |
| **检查 openspec CLI 自身行为** | rdd-env-check 已在做；重复即耦合 |
| **检查未提交 working tree dirty** | `_lib/state.sh::check_dirty_key_files` 已是 sentinel 警告层 |
| **替代现有 `plan_done_gate` / `arch_done_gate`** | gate = 阻断，doctor = 诊断，职责分明 |
| **跨 repo / 全局状态**（如 `~/.rddf/`） | v1 只查 `$PROJECT_ROOT`；全局诊断留 follow-up |
| **`add`（加新条目到 proposal-suggestions.md）能力** | doctor 只**读**这两个文件验证格式，不修改 |

## 关键场景

**S1 — 健康项目基线**
- GIVEN `.rddf/state/*.json` 全部符合 schema、`.rddf/plans/*.md` TDD 5 步完整、`roadmap-meta.yaml` 字段齐全、proposal 表格 5 列对齐、tasks.md checkbox 一致
- WHEN 用户跑 `skill_use("rdd-doctor")`
- THEN 输出单行 `✅ All 5 categories OK` + 退出码 0 + 不写 `.doctor-report.json`

**S2 — State JSON 致命 schema 漂移**
- GIVEN `.rddf/state/iteration.json` 缺失 `current_sprint` 必填字段（v2 schema 升级后旧文件未迁移）
- WHEN 跑 doctor
- THEN 该 finding 标 **CRITICAL**，建议 "re-run `guide-plan` 或手动补字段"；退出码 2（CRITICAL present）；分级报告按"❌ [.rddf/state/iteration.json] Line N" 格式打印

**S3 — Plan 文件 TDD 步骤缺失**
- GIVEN `.rddf/plans/foo.md` 缺失 "Step 3: Verify fail" 段落
- WHEN 跑 doctor
- THEN 该 finding 标 **WARNING**，输出"Step N missing 'Verify fail' sub-section — execute will misread"；退出码 1

**S4 — roadmap-meta.yaml 漂移（最危险路径）**
- GIVEN `openspec/changes/foo/roadmap-meta.yaml` 中 `manual_deps: "x,y"`（字符串而非数组，违反 ADR-0022 schema）
- WHEN 跑 doctor
- THEN 该 finding 标 **CRITICAL**（deps 阶段会**静默跳过**这种漂移，无任何日志）；提示"deps-driven execution mode will silently ignore this change"；退出码 2

**S5 — proposal 表格列数漂移**
- GIVEN `proposal-approved.md` 新增一行但漏写 `| date |` 列
- WHEN 跑 doctor
- THEN WARNING，输出 "Row N has 4 columns, expected 5" + 行号；退出码 1

**S6 — tasks.md checkbox 计数与文件存在性不一致（descope: 不交叉 openspec status）**
- GIVEN `openspec/changes/bar/tasks.md` 不存在，或文件存在但 `- [ ]` / `- [x]` 计数为 0（看起来"未开始"但 change 标为 active）
- WHEN 跑 doctor
- THEN WARNING，输出 "tasks.md checkbox count = 0, but change is active" 或 "tasks.md missing for active change"；退出码 1
- **degraded path**: 若 `openspec status` 在 v2 后续版本能可靠报告 checkbox 进度，可升级 S6 为交叉验证；在 v1 必须不依赖 CLI（CLI 缺失/失败时降级为 checkbox-only 仍能工作）

**S7 — `--json` 模式**
- GIVEN 任意项目状态
- WHEN 跑 `skill_use("rdd-doctor --json")`
- THEN 写结构化报告到 `.rddf/state/.doctor-report.json`（gitignored），字段包含 `timestamp` / `categories_checked` / `findings[]`（每个含 severity/category/file/line/snippet/fix_hint）/ `summary{critical,warning,info}`；stdout 仅输出单行摘要 `📋 Report: .rddf/state/.doctor-report.json`；退出码同默认模式

**S8 — `--category` 过滤**
- GIVEN 多类问题共存
- WHEN 跑 `skill_use("rdd-doctor --category state")`（仅查 `.rddf/state/*.json` schema）
- THEN 输出仅含 state 类别 finding；其他 4 类不跑（节省时间）；退出码仅反映 state 类别严重度

**S9 — Fresh project（无文件可查）**
- GIVEN 项目刚初始化，`.rddf/state/` 不存在，无任何 active change
- WHEN 跑 doctor
- THEN 输出 5 行 `[OK] <category>: no files to check` + 总行 `✅ All 5 categories OK (5 empty)`；退出码 0；**不报错**

**S10 — `--quiet` 模式**
- GIVEN 多类问题共存（含 1 CRITICAL + 3 WARNING + 2 INFO）
- WHEN 跑 `skill_use("rdd-doctor --quiet")`
- THEN stdout 仅打印 1 行 `❌ CRITICAL: 1 (state JSON schema violation)` + 退出码 2；CRITICAL/WARNING/INFO 详情被省略

## 技术约束

#### MUST（硬要求）

1. **只读行为** — 检查器不得修改任何文件；唯一允许的写操作是 `--json` 模式下写 `.rddf/state/.doctor-report.json`（gitignored）
2. **退出码分级** — `0` 全 OK / `1` 仅有 INFO+WARNING / `2` 有 CRITICAL / `3` 内部错误（checker 自身抛异常）；分级与 `openspec validate` 对齐
3. **复用现有 JSON schema** — `.rddf/state/*.json` 检查**必须**引用 `_lib/schemas/` 下的现有 schema（state_vector / sessions / iteration / deps-analysis），不重新定义字段。**checkers 必须解析真实的 `_lib/` 路径（commit c3a90fe 之后 `skills/_lib/` 已退化为 shim），不得走 shim 间接层**
4. **双模式输出契约** — 默认模式人类可读（CRITICAL/WARNING/INFO 分段），`--json` 模式输出 `.rddf/state/.doctor-report.json` 含固定字段（`timestamp` / `categories_checked` / `findings[]` / `summary{}`）
5. **幂等** — 同一输入连续跑 N 次结果完全一致；不创建空文件、不发多余副作用
6. **手动触发 only（v1）** — 不在 `guide-arch` / `guide-design` / `guide-plan` / `guide-ship` Phase 1 自动调用；不修改这 4 个 skill 的 SKILL.md
7. **依赖 `rdd-env-check` 模式惯例** — 命名、cache 路径、退出码、JSON 字段命名风格一致；用户学一个就懂另一个
8. **skill frontmatter 合规** — `SKILL.md` 包含完整 frontmatter（`name` / `description` / `license` / `compatibility` + `metadata:` 嵌套 `author` / `version` / `user-invocable`），符合 rdd-workflow skill 文件规范
9. **Python 路径解析安全** — checker 用 env-var 模式传递参数（参考 ADR-0021 round B Oracle C1 修复），禁止 `python3 -c "..."` 内联 `$VAR` 字符串插值
10. **不重复现有检查** — 不实现 rdd-env-check 已做的（CLI/git/branch/build dir）；不实现 ADR-0018/0019 已做的（arch 阶段 alignment、change 阶段 refs）
11. **测试覆盖** — `tests/integration/test_rdd_doctor.bats` ≥15 场景；`tests/unit/test_doctor_render.py` ≥6 场景；每条关键场景（S1-S10）至少 1 个测试
12. **cat-5 必须独立于 openspec CLI** — tasks.md checkbox 检查的"必读路径"是文件存在性 + `- [ ]` / `- [x]` 计数；**禁止**作为前置依赖调用 `openspec status`。CLI 缺失/失败时降级为 checkbox-only 仍能产出有效报告（INFO 级别说明"openspec status unavailable, skipping cross-check"，不视为失败）

#### MUST NOT（禁止）

1. ❌ **自动修复任何 finding** — 不生成 sed/awk 命令、不弹 Y/N 应用提示、不调用 `_lib/post_archive_cleanup.sh` 任何功能
2. ❌ **修改 gitignored state 文件**（`.rddf/state/*.json`）— 即便发现 schema 漂移也只报告，不动文件
3. ❌ **修改 git tracked 文件**（`.rddf/plans/*.md` / `proposal-*.md` / `tasks.md` / `roadmap-meta.yaml`）— 同上
4. ❌ **替代现有 gate 系统**（`arch_done_gate` / `plan_done_gate` / `change_arch_alignment`）— doctor 是诊断，不是 gate
5. ❌ **跨 repo 扫描** — 只查 `$PROJECT_ROOT`；不动 `~/.rddf/` / `~/.agents/skills/`
6. ❌ **打印敏感信息** — 路径可显示（用户已在 cwd），但 `git remote url` / token / `.env` 内容不进 stdout
7. ❌ **写入 `.rddf/state/.doctor-report.json` 之外的任何路径** — 不污染 working tree、不写 `openspec/` / `docs/` / 仓库根
8. ❌ **改 `_lib/schemas/` 现有 schema** — 漂移报告 ≠ schema 修正；schema 修正需另开提案
9. ❌ **依赖外部 skill**（superpowers / oh-my-opencode）— 与 rdd-workflow v2.0 自包含原则对齐
10. ❌ **未注册到 `tests/smoke.bats` 的新 skill** — 必须加入 smoke 矩阵（v2.0.3+ 强制约束）

#### SHOULD（软建议 / 后续可加）

1. **TTY 颜色输出** — stdout 是 TTY 时 CRITICAL/WARNING/INFO 加色（red/yellow/blue），非 TTY 时纯文本（CI 友好）
2. **`SKIP_DOCTOR=yes` 旁路** — 测试 / 紧急 escape；CI 默认开启，强制让 doctor 跑
3. **`DRY_RUN_DOCTOR=yes` 模式** — 所有 checker 只 echo 不写 `.doctor-report.json`，便于排查 checker 自身 bug
4. **`--category` 接受逗号分隔列表** — `rdd-doctor --category state,plans` 跑两类；v1 不强求
5. **每个 finding 含 `fix_hint`** — 人类可读提示"如何修复"，帮助用户决策（不是 auto-fix，只是建议）
6. **JSON 报告含 `next_step` 字段** — 顶层 `next_step: "rerun_guide_plan"` / `"manual_review"` / `"no_action"`，给后续 hook / agent 留消费口
7. **性能预算** — 单次完整跑 < 3s（5 类检查合计）；`--category` 单类 < 1s

## 验收标准

所有条目都**可被命令验证**。✅ = 可自动化；🔍 = 需人工 review。

#### AC1 — 新增测试覆盖（量化）

- [ ] ✅ `tests/integration/test_rdd_doctor.bats` 存在，**≥15 个 @test**
- [ ] ✅ 5 类检查各覆盖 ≥2 场景（成功 + 失败路径）
- [ ] ✅ 输出模式覆盖 ≥3 场景（默认 / `--json` / `--category` / `--quiet` 任选 3）
- [ ] ✅ 退出码映射覆盖 ≥3 场景（0 / 1 / 2 各自 1+）
- [ ] ✅ `tests/unit/test_doctor_render.py` 存在，**≥6 个测试**
- [ ] ✅ 关键场景 S1-S10 每条至少 1 个测试对应
- [ ] 🔍 CI grep 守卫 `grep -rn "assert.*or True\|assert True" tests/integration/test_rdd_doctor.bats` 无命中（v2.0.3+ 恒真断言门控）

#### AC2 — 现有回归（全绿）

- [ ] ✅ `npm test`（bats 全量）通过，无新增 failure
- [ ] ✅ `pytest tests/unit/ -q` 通过，无新增 failure
- [ ] ✅ `pytest tests/integration/ -q` 通过，无新增 failure
- [ ] ✅ `./test.sh --full --regression` 通过（区分新增失败 vs `tests/KNOWN_FAILURES.txt` baseline）

#### AC3 — 根因验证（针对 S4 关键路径）

- [ ] ✅ 测试 `test_roadmap_meta_yaml_drift_detected` 构造 `manual_deps: "x,y"` 字符串场景，断言 doctor 报告 CRITICAL + 退出码 2 + 提示含"silently ignore"
- [ ] ✅ 验证现有 deps 行为：doctor 报 CRITICAL 时，`deps` skill 对该 change **实际**输出"skipping drift"，证明 doctor 抓的就是真问题
- [ ] ✅ 同样对 S2 / S3 / S5 / S6 各构造 1 个根因测试，确认报告精确

#### AC4 — 只读行为验证（针对 MUST NOT #1-3）

- [ ] ✅ 跑 doctor 前对所有 5 类目标路径做 `find ... -newer <marker> -print`，跑 doctor 后断言无新文件（除 `.rddf/state/.doctor-report.json` if `--json`）
- [ ] ✅ `git status --porcelain` 在 doctor 跑前后内容**完全一致**（git tracked 文件零修改）
- [ ] ✅ 特别测试：checker 触发 CRITICAL 时**不**调用任何 `git rm` / `rm -f` / `mv`（用 `bats` 的 `assert_no_command_called` 或 `which rm` shadow 验证）

#### AC5 — 输出契约验证

- [ ] ✅ `--json` 模式输出 `.rddf/state/.doctor-report.json`，pytest `test_json_schema_validation` 验证固定字段（`timestamp` ISO8601 / `categories_checked` list of 5 / `findings[]` 含 severity+category+file+line+fix_hint / `summary{critical,warning,info}` 整数）
- [ ] ✅ 默认模式 stdout 格式 `assert_output --partial "✅ All 5 categories OK"`（S1 场景）
- [ ] ✅ `--quiet` 模式 stdout 行数 ≤ 1（S10 场景）
- [ ] ✅ 退出码矩阵：fresh project → 0 / 1 WARNING → 1 / 1 CRITICAL → 2 / checker exception → 3
- [ ] ✅ **cat-5 degraded path**: 测试 `PATH=$BATS_TMPDIR/empty_bin:$PATH`（让 `openspec` 找不到）跑 doctor，断言 cat-5 仍能产出有效报告（INFO 级别 "openspec status unavailable, skipping cross-check"），不报"checker exception"或退出码 3

#### AC6 — smoke.bats 注册验证（针对 MUST NOT #10）

- [ ] ✅ `grep -q "rdd-doctor" tests/smoke.bats` 命中
- [ ] ✅ `bats tests/smoke.bats` 通过且含 `rdd-doctor: <description>` 测试行

#### AC7 — 文档同步

- [ ] ✅ `AGENTS.md` 新增「rdd-doctor」段，包含调用方式 + 何时该跑（≥15 行新增）
- [ ] ✅ `tests/README.md` 新增一行入口引用 `rdd-doctor`
- [ ] ✅ `package.json` 的 skill 清单（如有）新增 `rdd-doctor` 条目
- [ ] ✅ **不**新增 ADR（本次属工具层，无需新决策）

#### AC8 — 架构边界验证（确保不串扰）

- [ ] ✅ `rdd-env-check` 行为**不变**：`SKIP_AUTO_DISCOVERY=yes` 等既有 env var 仍生效
- [ ] ✅ `arch_done_gate` / `plan_done_gate` **行为不变**：bats 全量测试覆盖
- [ ] ✅ `guide-arch` / `guide-design` / `guide-plan` / `guide-ship` 4 个 SKILL.md **不被修改**（git diff 验证）

#### AC9 — 性能预算

- [ ] ✅ 完整 5 类检查 < 3s（`time rdd-doctor` 在 fixture 项目上）
- [ ] ✅ `--category <name>` 单类 < 1s
- [ ] ✅ `--json` 模式额外开销 < 0.5s（序列化时间）

#### AC10 — 手动触发验证（针对 MUST #6）

- [ ] ✅ `guide-arch` 入口跑测试，确认 `rdd-env-check` 被调用但 `rdd-doctor` **不被调用**
- [ ] ✅ 同样对 `guide-plan` / `guide-ship` 验证
- [ ] ✅ `grep -r "rdd-doctor" skills/guide-*/SKILL.md` **无命中**