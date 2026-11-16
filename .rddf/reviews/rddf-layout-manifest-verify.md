# 验收报告：rddf-layout-manifest

> 验收者：verifier（角色）
> 验收对象：`openspec/changes/rddf-layout-manifest` @ `d173f791`（基线 `731f027`，6 个提交）
> 验收时间：2026-11-16
> **已用轮次：1 / 3**（`RDDF_VERIFIER_MAX_LOOPS=3`）

## 判定来源

按「判据来源」优先级取第一项可用的：

| 优先级 | 来源 | 采用 |
|---|---|---|
| 1 | 用户本次明确给出的验收条件 | 无（用户只说「切 verifier」） |
| 2 | `proposal.md` 的 `## Acceptance` 段 | ✅ **采用（18 条）** |
| 3 | 本次变更自身声明的行为 | 备查 |
| 4 | ADR 的 Verification 章 | 备查（ADR-0026 无 Verification 章） |

## 判据提取的一个坑（必须记录）

`proposal.md` 的段头是 `## Acceptance`。**两套解析器对它的态度不一致**：

| 解析器 | 结果 |
|---|---|
| `_lib/verifier/protocol.py::parse_acs`（归档门权威） | **18 条** ✓ |
| `rdd-verifier` SKILL.md 的段头正则（`验收标准\|Acceptance Criteria`） | **0 条** |
| `skills/rdd-verifier/scripts/run_verification.sh`（staging） | **0 条**（`ac_count: 0`） |

⇒ 若严格按 skill 的正则，本 change 会被判「无 AC」而 **pass-through（exit 0）跳过全部验收** —— 假阴性。本次验收**以 `parse_acs` 提取的 18 条为准**（与 proposal 原文逐条一致），不放行空 AC。

**这是产品缺陷**（见文末 follow-up F-1）。

## 逐条判定（18/18 pass）

| AC | 判据要点 | 证据（工具 / 命令 / 结果） | 判定 |
|---|---|---|---|
| AC-1 | `RDFF_LAYOUT` 导出；8 字段；取值域闭合；`path` 唯一且字典序 | `pytest tests/unit/test_rddf_layout.py` → 8 passed；`as_dicts()` 实测 entries=14、字段集一致=True、path 唯一=True、字典序=True、取值域闭合=True | **pass** (0.97) |
| AC-2 | `rddf layout --json` entries=14 + 8 字段 + `schema_version`/`tool_version` | `PYTHONPATH=. python3 -m _lib.cli layout --json` → entries=14 / schema_version=1 / tool_version=4.0.0 / 8 字段齐=True | **pass** (0.97) |
| AC-3 | 两次输出字节一致 + 无时间戳 + 未动 `doctor_render.py` | `cmp` 两次输出 → 一致；`grep -c timestamp` → 0；`git diff --stat 731f027..HEAD -- doctor_render.py` → 0 行 | **pass** (0.97) |
| AC-4 | 本仓 `doctor --category layout` 0 finding（含两个 backup 目录） | `doctor.sh --category layout` → All 1 categories OK；两个 `.roadmap-migrate-backup-*` 目录实际存在且未报 finding | **pass** (0.97) |
| AC-5 | 三支判据可复现 | `bats test_doctor_layout.bats` → ok 1（缺 always 条目⇒WARNING）/ ok 2（未登记⇒INFO）/ ok 3（class 不符⇒WARNING） | **pass** (0.96) |
| AC-6 | 永不 CRITICAL（exit 1 而非 2） | `bats ... #6`（never emits CRITICAL）ok；`doctor --category layout` 实测 exit=1 | **pass** (0.96) |
| AC-7 | 最小第三方 fixture 上 WARNING 集合 == `always` 集合 | 构造 `.rddf/project.yaml` + 一个 change 的 fixture → 5 WARNING `{state, improvements, plans, roadmap, roadmap.md}`、0 CRITICAL、0 INFO；集合恰等于 `always − 已存在` | **pass** (0.90) ※见偏差 D-1 |
| AC-8 | `wt/` 模式判定 | fixture 无 `wt/` → 0 处提及 wt；`mkdir .rddf/wt/x` 后 → 无 unregistered finding | **pass** (0.96) |
| AC-9 | `.rddf/` 不存在 ⇒ 0 finding | 空临时目录跑 `doctor_main.py --category layout` → All 1 categories OK、exit=0；`bats ... #4` ok | **pass** (0.97) |
| AC-10 | 断言 A/B 通过（含含 tracked 文件的目录） | `pytest -k assertion` → 2 passed；源码核对：断言 A 覆盖 `defaults` 2 条 + 5 个模块常量，断言 B 对 dir 用 `<path>/.probe` 探针、对 glob 用实际匹配目录 | **pass** (0.96) |
| AC-11 | `schema_version` 演进策略成文 | `grep -A8 'schema_version 演进策略' docs/architecture/rddf-layout.md` → 增字段/增 entry 不升版、改语义或删 entry 升版、消费方按 `path` 集合比较 | **pass** (0.95) |
| AC-12 | 首段真源声明 + 三步 + 文件级（取自代码） | 三处锚点各命中 1 次；文件级引用 `state_paths.py:34-41` / `builder_deps.py:42` / `builder_feedback_router.py:31` 共 3 处 | **pass** (0.95) |
| AC-13 | `state-and-events.md` 修成 v4 命名 | handoff 表 3 行均为 v4（`.arch-handoff` / `.planner-handoff` / `.planner-feedback`）；表格行旧名残留计数 0；`bats ... #8` ok | **pass** (0.97) |
| AC-14 | 三处散文补链到位 | `state-and-events` 1 / `extension-points` 1 / `ADR-0026` 1（仅描述性指向，未改决策） | **pass** (0.96) |
| AC-15 | README Doc Map 含 `rddf-layout.md` | `grep -n rddf-layout.md docs/architecture/README.md` → 19 行 | **pass** (0.97) |
| AC-16 | SKILL.md 去固定数字 + usage 枚举一致 + category 表含 layout | 写死数字计数 0（description 与 heading 双检）；`_CHECKERS`(25) vs usage 枚举(25) 漏列=无；category 表含 `layout` | **pass** (0.96) |
| AC-17 | 边界声明成文（`RDDF_STATE_DIR`） | `docs/architecture/rddf-layout.md:88` 明确声明重定向不在契约内，列出 3 处代码位置 | **pass** (0.96) |
| AC-18 | 回归无新增失败 + 无越界改动 | `./test.sh --full --regression` → unit 3332 passed / 2 skipped、integration 201 passed、bats 含 regression **ALL PASSED**；`git diff --stat -- src/ openspec/specs/ doctor_render.py` 空；diff 中无 `defaults.py`/`issue_reporter.py` | **pass** (0.97) |

**结论：18/18 pass，`verification_state: passed`，`failed_acs: []`。**

归档门完整性校验：`{"complete": true, "problems": [], "schema_version": 2}` ✓
verdict cache：`.rddf/state/verifier/.ac-verdict-rddf-layout-manifest.json`（`codebase_commit = d173f791`）
audit log：`.rddf/state/verifier/.ac-verification.jsonl` 追加 1 行

## 判据本身的偏差（不改变 pass 判定，但需记录）

**D-1（AC-7 措辞）**：AC 原文写「WARNING 集合**恰好等于** `required_when=always` 的条目集合」，但 fixture 里的 `project.yaml` 本身**也属 `always` 且已被创建** ⇒ 实测集合是 `always − {project.yaml}`。
判定按更严格的语义（「等于 always 中缺失的项」）执行并 pass。**建议把 AC 措辞改成「恰好等于 `always` 中缺失的条目集合」**，否则该判据无法字面满足。

**D-2（fix_hint 措辞）**：`layout_check.py` 的 missing-required fix_hint 对 **file 类型**条目也加尾斜杠 ⇒ 实测输出 `create .rddf/roadmap.md/`（`roadmap.md` 是文件）。
不影响判定逻辑与 severity，但会误导用户。属 follow-up F-2。

## 遗留清扫复核

| 检查项 | 结果 |
|---|---|
| 新增文件里的 TODO / FIXME / 调试打印 | `_lib/core/rddf_layout.py`、`_lib/cli/layout_cmd.py`、`checks/layout_check.py` 均无；唯一的 `print(` 是 `layout_cmd.py` 的 JSON 输出本体 |
| 半截实现 / 注释掉的代码 | 无 |
| 被 skip 的测试 | 本 change 的 16 个 pytest + 11 个 bats 全部执行，无 skip |
| 未替换的 mock | 仅 `test_doctor_layout_checker.py` 的 import 失败注入（有意，`monkeypatch` 且 `finally` 里 undo + reload） |
| 临时 fallback 分支 | `_MANIFEST_ERROR` 降级路径（有测试覆盖，非临时） |
| 越界改动 | `src/` / `openspec/specs/` / `doctor_render.py` 均未动 |

## 失败项与路由建议

无失败项，无需路由。

## 本轮发现的产品缺陷（转 follow-up，不阻断本 change 归档）

| # | 缺陷 | 证据 | 建议 |
|---|---|---|---|
| **F-1** | `rdd-verifier` skill 的 AC 段头正则只认 `验收标准\|Acceptance Criteria`，不认 `## Acceptance` ⇒ 该格式的 proposal 会被判「无 AC」并 pass-through 跳过验收 | 本 change `staged` 的 `ac_count: 0`，而 `parse_acs` 得 18 | 统一用 `_lib.verifier.protocol.parse_acs` 作为唯一解析器（归档门已用它） |
| **F-2** | `layout_check.py` 的 missing-required `fix_hint` 对 file 条目加尾斜杠 | 实测 `create .rddf/roadmap.md/` | 按 `kind` 分支生成 fix_hint |
| **F-3** | `phase3_archive.sh:24` 查 `verifier_run.sh`（实际文件是 `run_verification.sh`）⇒ P3 的 verifier 预调用**永远被跳过** | `ls skills/rdd-verifier/scripts/` 无 `verifier_run.sh` | 见 F-4 |
| **F-4** | 即使改对文件名也不能修：`run_verification.sh` 是 **staging** 脚本，exit 0 = "agent verification pending"；`phase3_archive.sh` 会把它当「验收通过」⇒ 假阳性。按 ADR-0045「agent IS the LLM」，bash 层无法完成验收 | 脚本头注释明写 "Exit: 0 = context staged (agent verification pending)" | P3 不应期待 bash 完成验收；应由 agent 走 `rdd-verifier` skill（本报告即该路径） |
| **F-5** | `rddf rdd-verify --dry-run` 仍执行遗留状态迁移 | 实测 dry-run 输出 27 行 `moved legacy verifier state` | `_migrate_legacy_state` 应受 dry-run 控制 |
| **F-6** | rdd-builder 的 phase 脚本从不把 change 注册进 `iteration.json` ⇒ feature 名下的 change 必须手工注册，否则 `roadmap-feature` 报 CRITICAL | 本 change 手工注册（`a974c7c`） | P0/P1 加一步注册 |

## 结论

**18/18 AC pass，verdict cache 完整且被归档门接受，可进入 P3 归档。**

F-1~F-6 均为本 change 执行过程中暴露的**产品侧缺陷**，与本 change 的验收判据无关，登记为 follow-up（是否立项由用户决定）。
