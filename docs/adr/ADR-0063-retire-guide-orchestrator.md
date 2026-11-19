# ADR-0063: 退役 Guide-as-Orchestrator（取代 ADR-0055 / ADR-0056）

> **Status**: 已采纳（2026-11-19，oracle + critic 双审通过；**执行前置**：跨仓 D7 + `rddf-skills.sh` 修订须先于本仓 archive）
> **Date**: 2026-11-19
> **Author**: architect
> **Parent**: 取代 ADR-0055（**仅**其决策 1/3/4/5，以及决策 2/6 中 stage_guide 专属的 per-owner `last_seen_offset` 游标部分）、ADR-0056（Guide Session 作为唯一交互入口的最小用法流程）。**events 总线本体不在此列** —— `events.jsonl` / `phase_*` 事件 / `rddf monitor` 与 `child_progress` 消费保留（见 Decision 7）
> **关联 change**: `backlog: retire-guide-orchestrator`（待 planner 立项）
> **AC 映射**: 待 change 立项后回填
> **审稿报告**: `.rddf/reviews/adr-0063.md`（收口时誊写）
> **跨仓关联**: `~/.config/opencode/.rddf/state/adr-front-agent-redesign.md` D7（「`guide` skill 不删」）需同源修订

## 背景与问题

ADR-0055 / ADR-0056 定义了「`guide` 作为唯一交互入口」的架构：`stage_guide` 长生命周期 session + `events.jsonl` 跨容器事件总线 + `guide_entry.sh` 轮询渲染子阶段进度。该架构于 2026-09-22/24 采纳并标记「已实施」。

### 实测：零使用

| 数据源 | 总量 | `stage_guide` 记录 |
|---|---|---|
| `.rddf/state/sessions.json` | 21 | 1（`completed`，2026-09-23，owner=`my-eci-group-poc_954956`，实施期 POC） |
| `.rddf/state/sessions.archive.json` | 43 | **0** |
| `.rddf/state/events.jsonl` | 20 | **0** 条含 `guide`（`guide_intent_detected` / `guide_routed` 从未产生） |
| `.rddf/state/event-log.jsonl` | 1 | 0 |
| `~/.config/opencode/.rddf/state/` | — | **0** |

同期真实在用的 kind（2026-11-16 ~ 11-18）：`stage_builder` / `stage_verify` / `stage_design` / `stage_quick`。**stage_guide 自落地起未被真实使用。**

### 架构角色已被 front agent 接管

opencode 侧 `ADR-front-agent-redesign` D7 已决定：

> front 吸收 `guide` 的交互部分：状态扫描摘要、菜单式意图路由（"下一步做什么"给 A/B/C）、新 session 开场报状态。**不吸收**执行部分：rdd-* skill 调用、状态文件写入、roadmap 变更留在工程 session。

即「唯一交互入口」这一职责已由 front agent 在**会话层**承担，`stage_guide` 在**状态层**再实现一遍是重复架构。D7 只保留了「guide skill 不删」，前提是工程 session 侧仍需要一个推荐器 —— 但推荐能力已由 `rddf guide` CLI 独立提供（见 ADR-0062）。

### 维护成本持续存在

`skills/guide/` 的 bash 实现是三份推荐实现之一（见 ADR-0062）；`stage_guide` 牵连 `rddf-session` 的 6 处实现、`rdd-doctor` 的 schema 检查、以及 28 个引用 `skills/guide` 的测试文件。零使用状态下这些全部是纯维护负担。

## Decision

**退役 Guide-as-Orchestrator 架构：归档 `skills/guide/`，退役 `stage_guide` kind 与相关接口，保留 `rddf guide` CLI 作为无 agent 场景的推荐入口。**

具体：

1. **归档 `skills/guide/`** → `docs/legacy/skills/guide/`（沿用 `docs/legacy/` 既有考古先例；不新建顶层 `archive/`）。SKILL.md / `guide_entry.sh` / `scan-state.sh` 整体移入，不再作为可加载 skill。
2. **`stage_guide` 退役**：`sessions_schema.json` 的 `kind` 枚举移除 `stage_guide`、`intent` 枚举移除 `guide-orchestrator`、`goal.last_seen_offset` 标注 legacy；`rddf-session` 移除 `guide-entry` / `guide-close` 子命令与 `_reset_stage_guide_offsets`；`parent_kind_map` 去掉 `stage_guide` 映射；`rdd-doctor` 移除对应 schema 检查。
3. **保留 `rddf guide` CLI**：`_lib/cli/guide_cmd.py` 不删。它提供的是推荐能力，不是 orchestrator 会话；**非 agent 环境**（全局安装的纯 CLI 使用、无 opencode 的前端）仍需该入口。注意：`.github/workflows/` 中并无 `rddf guide` 调用，因此不以「CI 需要」作为论据。
4. **归档 `docs/architecture/guide-orchestrator-flow.md`** → `docs/legacy/`；`docs/architecture/README.md` 索引同步；ADR-0055 / ADR-0056 的 Status 标 `Superseded by ADR-0063`。`docs/legacy/` 增加一行 README 说明「考古保留，不参与 install / pyright」，防止未来 `pyrightconfig.include` 扩大时误扫。
5. **跨仓同源（先行）**：`ADR-front-agent-redesign` D7 的「`guide` skill 不删」修订为「guide skill 已归档；交互职责由 front 承担，推荐能力由 `rddf guide` 承担」；`rddf-skills.sh` 内置清单移除 `guide`。**这两个文件均在 `~/.config/opencode` 仓，时序上必须先于本仓 archive 落地**（治理面 oracle→critic 周期较长）；若治理面被卡住，本 ADR 保持 Draft、不进入 builder，避免「本仓说已退役、治理面说不删」的矛盾窗口。
6. **存量数据（先于 schema 收窄）**：`.rddf/state/sessions.json` 现有 1 条 `completed` 的 `stage_guide` 记录。实施顺序**必须**是「先迁移或容忍该记录 → 再收窄 `kind` 枚举」，否则 `rdd-doctor` 的 `state_schema_check.py` 会在中间态持续报错。迁移方式二选一写入 change 的 `design.md`；**不要求跨项目 migration 脚本**（无活跃数据）。
7. **事件总线保留（不属于退役范围）**：`events.jsonl` / `_lib/core/event_log.py` 的 `phase_started` / `phase_completed` 事件、`rddf monitor` 的消费、`workflow_synthesizer._read_events_for_children` 的 `child_progress` 聚合 **全部保留**。理由：这些服务于**所有** stage（builder/verify/design/quick 的 hook 都会写事件），不是 stage_guide 专属；删除会直接破坏 ADR-0062 保留的 synthesizer 消费者 `rddf monitor`。本 ADR 只退役 stage_guide 对事件总线的**专属用法**：`goal.last_seen_offset` per-owner 游标、`rddf_session_hook_poll_events`、`guide_entry.sh` 的轮询渲染。
8. **ADR-0051 引用链声明**：ADR-0051 Decision 2 把「反触发 SSOT」定位于 `guide` 推荐器。归档 `skills/guide/` 后，该 SSOT 的**载体**迁移到 ADR-0062 收敛后的单一推荐实现（`rddf guide` CLI 为其入口），Decision 2 的语义不被违反；实施时在 ADR-0051 的 References 补一行指针即可，不重写其决策。

### 影响范围

**本仓 In Scope**：

- `skills/guide/` 归档 → `docs/legacy/skills/guide/`
- `package.json::skills[]`；`pyrightconfig.json`（含 `{"root": "skills/guide"}` executionEnvironment 条目）
- `skills/rddf-session/` 的 stage_guide 实现：`parent_kind_map`（含 `stage_arch → stage_guide`、`stage_quick → stage_guide` 两条；退役后 `stage_arch` 无 parent、`stage_quick` 挂 `stage_ship` 或 null，在 design.md 定）、`guide-entry`/`guide-close`、`_reset_stage_guide_offsets`、`rddf_session_hook_poll_events`（`rddf_session_hooks.sh:748-770`）、`update_last_seen_offset`（`rddf_session.py:129`）、`RDDF_GUIDE_SESSION_ENABLED`
- `skills/rdd-doctor/scripts/checks/state_schema_check.py` 的 stage_guide 检查
- `_lib/schemas/sessions_schema.json`（kind / intent / last_seen_offset）
- `docs/architecture/` 快照与索引；ADR-0055 / ADR-0056 状态行
- 测试：实测 **28 个文件引用 `skills/guide`** = **14 删除**（专测被归档脚本）+ **11 改造**（能力保留、去引用）+ **3 fixture/断言调整**（`test_skill.bats` / `smoke.bats` / `test_global_install_external_project.bats`）
- `docs/legacy/README`（新增一行说明）

**跨仓 In Scope（`~/.config/opencode`）**：

- `scripts/rdd-skills.sh:45` 内置清单移除 `guide`
- `.rddf/state/adr-front-agent-redesign.md` D7 修订

**Out Scope**：`rddf guide` 的推荐逻辑（ADR-0062 管辖）；ADR-0044 未收口的注释类残留（独立 change A）；`docs/adr/` 历史正文的追溯改写。

### 选项对比表

| 方案 | 结论 | 理由 |
|---|---|---|
| **A. 归档 skill + 退役 stage_guide，保留 `rddf guide` CLI**（选中） | 采用 | 零使用数据支持退役 orchestrator；保留推荐能力覆盖 front 不在场的场景；与 ADR-0062 的单一实现收敛方向一致 |
| B. 保持现状（guide 全保留） | 拒绝 | 零使用 + 三实现漂移已被证明产生缺陷 + 与 front 的交互职责重复；维护成本永久化 |
| C. 彻底删除（含 `rddf guide` CLI + synthesizer） | 拒绝 | front 的 D7 明确要求底层有状态摘要/推荐能力；纯 CLI / 非 agent 环境没有 agent 可代劳 |
| D. 仅标 `deprecated:` 不归档 | 拒绝 | `stage_guide` 死代码、28 个测试、6 处实现继续维护；`deprecated:` 不阻止加载，不构成退役 |
| E. 只归档 skill，保留 stage_guide | 拒绝 | `guide_entry.sh` 是 stage_guide 长会话的唯一创建者；删掉它后 stage_guide 成为不可达 schema |

## 后果 / 代价

### 正面

- 删除一套从未被使用的会话架构（`stage_guide` + 轮询 + 跨容器可见性），`rddf-session` 的状态机分支显著减少。
- 推荐实现从三份收敛为一份（ADR-0062 的前提），漂移根因消失。
- 与 front agent 的职责边界清晰化：会话层交互归 front，状态层推荐归 `rddf guide`。
- 28 个引用测试文件的维护负担移除（14 删除 + 11 改造 + 3 fixture/断言调整）。

### 负面 / 风险

- **已发布接口消失**：`rddf-session guide-entry` / `guide-close` 是 v4.1 发布过的子命令。即使零使用，删除对外部用户仍是 breaking change —— 需在 CHANGELOG 标注并在 migration 文档注明替代路径。全局安装用户若设过 `RDDF_GUIDE_SESSION_ENABLED`，该环境变量同时失效，需一并在 migration 文档覆盖。
- **跨仓同步**：D7 与 `rddf-skills.sh` 的修订在 `~/.config/opencode` 仓，两边审稿节奏不同。**时序为治理面先行、本仓 archive 后置**（见 Decision 5）；若治理面未合入，本仓不得归档。
- **`docs/legacy/` 落点**：现有 `docs/legacy/` 只有单文件脚本（`rddf-legacy-v2.0.7.sh`），整目录归档需确认不干扰 `pyright` / 打包与 `install.sh` 的 `skills/*/` 遍历。已核实：`install.sh:22,238` 只遍历 `$PACKAGE_DIR/skills/*/`；`pyrightconfig.json` 的 `include` 仅 `["skills","_lib","tests"]` —— 当前配置下安全，但需新增 `docs/legacy/README` 把该边界写下来。
- **环境假设**：零使用结论基于本仓与 opencode 仓的 `.rddf/state`。若其他项目/机器仍在跑 guide（尤其设了 `RDDF_GUIDE_SESSION_ENABLED` 的全局安装），本 ADR 的前提不成立。

## Verification

- [ ] **V-1** `ls skills/guide 2>/dev/null` ⇒ 不存在；`ls docs/legacy/skills/guide/SKILL.md` ⇒ 存在
- [ ] **V-2** `python3 -c "import json;d=json.load(open('package.json'));assert 'guide' not in d['skills']"` ⇒ 通过
- [ ] **V-3**（**跨仓，人工验证**）`~/.config/opencode/scripts/rdd-skills.sh --json | grep -c '"guide"'` ⇒ 0
- [ ] **V-4** `rddf guide` 仍可执行并输出 RECOMMEND（保留能力的证据）
- [ ] **V-5** `grep -rn 'stage_guide' _lib/schemas/sessions_schema.json skills/rddf-session/` ⇒ 0 命中（或以 `legacy` 注释标注的容忍项 ≤1 处）
- [ ] **V-6** `python3 -m pytest tests/unit/ -q` 与 `bats tests/ --recursive` 无新增失败（对照 `tests/KNOWN_FAILURES.txt`）
- [ ] **V-7** `docs/architecture/README.md` 中 guide-orchestrator-flow 行已移除；该文件存在于 `docs/legacy/`
- [ ] **V-8** ADR-0055 / ADR-0056 的 Status 行含 `Superseded by ADR-0063`
- [ ] **V-9**（**跨仓，人工验证**）`~/.config/opencode/.rddf/state/adr-front-agent-redesign.md` 的 D7 文本不再含「`guide` skill 不删」的未修订表述，且保留「front 吸收交互部分」的决策
- [ ] **V-10** 事件总线未退化：`grep -c 'phase_started' skills/rddf-session/scripts/rddf_session_hooks.sh` ≥ 1；`python3 -c "from skills._lib.workflow_synthesizer import _read_events_for_children"` 可导入；`rddf monitor` 输出仍有 `Child Progress` 段（zero-IO guard 行为不变）
- [ ] **V-11** `parent_kind_map` 退役后无 `stage_guide` 键；`stage_quick` 的 parent 值在 change 的 `design.md` 定稿后回填为可判定断言（本项在立项时标记为「待 design.md 回填」）

## References

- ADR-0055 —— Guide-as-Orchestrator Session + Cross-Container Event Bus（被取代）
- ADR-0056 —— Guide Session 作为唯一交互入口的最小用法流程（被取代）
- ADR-0044 —— v4 Wave 3 硬移除（guide-* 目录删除先例）
- ADR-0062 —— 推荐器决策树收敛到单一实现（本 ADR 的前置）
- `~/.config/opencode/.rddf/state/adr-front-agent-redesign.md` D7 —— front 吸收 guide 交互部分
- `docs/architecture/guide-orchestrator-flow.md` —— 待归档的架构快照
