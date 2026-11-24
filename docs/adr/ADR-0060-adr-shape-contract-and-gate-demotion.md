# ADR-0060: ADR 形态契约与门禁降级 —— 决策文档只回答「定什么 / 为什么 / 代价」

> **状态**: 已采纳 + AMENDED (2026-11-17)
> **日期**: 2026-10-28
> **决策者**: rdd-workflow maintainer
> **关联 ADR**: ADR-0016（arch artifact discovery contract）, ADR-0018（arch quality gate）, ADR-0057（ADR + theme doc 双工件模型）
> **触发来源**: 2026-10-27 对 CppHDL / ChipForge / CppTLM 三个项目近期 ADR 的形态审查（opencode 侧 `architect` 角色约束评审）
> **关联 change**: backlog: adr-0060-shape-contract-implementation（登记载体 `.rddf/improvements/adr-0060-shape-contract-implementation.md`）
> **审稿报告**: [.rddf/reviews/adr-0060-amendment-2026-11-17.md](../../.rddf/reviews/adr-0060-amendment-2026-11-17.md)（oracle + critic 双审，2026-11-17 修订）；本次「关联 change」回填的审稿见 `.rddf/reviews/adr-0060-backfill-2026-11-24.md`

## Context

2026-10-27 抽查三个项目同期产出的架构决策文档，发现**形态漂移**而非决策错误——决策本身大体成立，但文档越界成了「设计规格 + 实验记录 + 流程台账」的混合体。

### 实测数据

| 观测项 | 数据 |
|---|---|
| 体量回归 | ADR 中位体量 11.3 KB（10-25 前，n=98）→ 19.3 KB（10-25 起，n=23）；>20 KB 占比 15% → **48%** |
| 决策陈述占比 | ADR-048 **22%** / ADR-047 29% / ADR-046 31%（对照 ADR-091 53%、ADR-089 52%） |
| 过程日志混入 | ADR-048 正文命中 21 处（第 N 轮 critic / BLOCKER / SHOULD_FIX / NIT） |
| 缺独立「后果 / 代价」章 | 11/12 |
| 缺选项对比表 | 12/12 |
| 主架构重点被稀释 | ADR-088（44 KB）只有 2 个 H2；「一个模型、两个后端、一道差分门禁」只占约 10 行 |

### 现有约束为什么没拦住

| 层 | 现状 | 为什么无效 |
|---|---|---|
| `adr_gate.sh` 关键词分类 | 只匹配标题里的 `module/boundary/interface/contract/layer/abstraction` | 实测 **8/8** 近期真实架构 ADR（skid buffer / data forwarding / canonical home / backend retirement / parity gate / open-core port / coherence-domain ownership / platform charter）被判 `IMPLEMENTATION`——硬拦会挡掉最该记录的决策 |
| ADR 模板 | Context / Decision（影响范围 + 备选方案）/ Consequences / References | 无 Verification 章；备选方案表只有「备选 \| 理由」两列，无「结论」列，无体量提示 |
| `arch_quality_gate.py` | 4 项检查：引用可解析 / 无占位符 / handoff 可执行 / py 文件行数 | 无任何一项与「文档形态」相关 |

### 约束链断点

opencode 侧 `architect` 角色直接 `edit` 写 ADR，**不经过 rdd-arch 的 Phase 2**——因此模板、门禁、质量检查在该路径上全部未被走到。rdd-workflow 侧收紧形态契约是必要的，但**不能只靠收紧**：真正生效的约束在提示词层（`prompts/build.md` 的「architect 产出形态契约」），两处需同源。

## Decision

**引入「形态契约」：决策文档只回答三件事（定什么 / 为什么这么定 / 代价是什么）；模板与门禁同步收紧，关键词分类门禁降级为提示。**

具体：

1. **模板**（`docs/adr/ADR-0000-template.md`）：新增 `## Verification`（前瞻判据，非实测日志）、备选方案表改三列（备选 \| 结论 \| 理由，≥3 行）、顶部加体量与落点提示。
2. **门禁**（`skills/rdd-arch/scripts/adr_gate.sh`）：分类逻辑**不变**；新增 `ADR_GATE_MODE=advisory`（默认，输出提示到 stderr）、`ADR_GATE_MODE=block`（恢复硬拦）、`ADR_GATE_CLASS=<CLASS>`（显式覆盖）。
3. **SKILL 流程**（`skills/rdd-arch/SKILL.md` Phase 2）：advisory 模式下非 ARCHITECTURE 分类不再硬拦，改为提示 + 由用户/agent 确认；草稿锚点补 `## Verification` 与 4 条形态约束。
4. **机械检查**（`_lib/arch_quality_gate.py`）：新增 `_check_adr_shape()`——行数预算（默认 250，`ARCH_ADR_LINE_LIMIT`）、必备章节、过程日志标记、Status 行长度（默认 200，`ARCH_ADR_STATUS_MAX`）。**opt-in**：`ARCH_SHAPE_CHECK=yes` 才进入 `ArchQualityReport.verify()`；另提供 `skills/rdd-arch/scripts/adr_shape_check.sh` 独立 CLI。（2026-11-17 修订：本条的预算数值与信号集已被下方「修订 2026-11-17」节取代 —— 以该节为准。）

### 影响范围

- **In Scope**：`docs/adr/ADR-0000-template.md`、`skills/rdd-arch/SKILL.md`（Phase 2）、`skills/rdd-arch/scripts/adr_gate.sh`、`skills/rdd-arch/scripts/adr_shape_check.sh`（新增）、`_lib/arch_quality_gate.py`、相关单元与 bats 测试。
- **Out Scope**：既有 ADR 的存量改写（**不追溯**）；`adr_gate.sh` 的关键词表本身；`arch_done` gate 既有 4 项检查的语义；opencode 侧提示词约束（另一仓库，同源同步）。

### 备选方案

| 备选 | 结论 | 理由 |
|---|---|---|
| A. 继续给 `adr_gate.sh` 加架构关键词 | **拒绝** | 真实架构决策的标题恰恰不含架构词（skid buffer / backend retirement 都不含）；关键词越多误判越多 |
| B. 保持硬拦，靠人手动绕过 | **拒绝** | 现状即如此——门禁被绕过导致约束真空，同时又挡住了纯治理类之外的真实决策 |
| C. 模板（骨架）+ 提示词（判断）+ 机械检查（回归）三层同时收紧 | **接受** | 三层职责不同：模板给骨架，提示词给判断力，机械检查给可回归的判据；缺任一层就出现盲区 |
| D. 形态检查默认开启并阻断 | **拒绝** | 本仓库 60 份既有 ADR 中 13 份超 300 行、22 份缺备选方案 → 默认开启会把存量债变成 CI 阻断（数据口径：**按修订前的 300 行预算**统计；按 2026-11-17 修订后的 250 行口径，超行数与缺项只会更多，结论不变） |
| E. 只改提示词层，rdd-workflow 不动 | **拒绝** | 走 rdd-arch 流程的项目将无任何形态约束；两条入口路径必须同时收口 |

### 修订 2026-11-17（形态门与散文契约同源化）

**触发**：2026-11-17 的文档审查发现「散文契约（`ADR-0000-template.md` 与 opencode 侧 architect 形态契约的 ≤250 行 + 四要素）与机械门（默认 300 行、且不检查 Verification 与备选表形态）**不同源**」；同时本仓真实漂移形态（`## v3 修订日志` / `## Implementation Status` / `## Post-hoc Fix Record` / `## Implementation`）不在过程日志正则覆盖内 —— 门禁给出的是**假保证**。

**改动**（全部是原决策的参数与信号补全，**不重开备选 D**：仍 opt-in、仍 warning 级、仍不接 CI）。三个方向：

1. **同源化预算**：行数预算默认值 300 → **250**，与模板及 opencode 侧「正文目标 ≤250 行」取同一个数。
2. **补齐信号**：Verification 章（h2 级 + 章内至少 1 条可勾选判据）、备选方案表（缺表 / 数据行 < 3 / 缺「结论」列）、标题级过程日志（过程·版本史 / 越界成实施细节两族）。
3. **单一真源**：判定逻辑抽成 `adr_shape_findings()` 一级 API，gate 与 CLI 共用；CLI 不再内联复制判定、不再硬编码默认值，且无参=用法错误、`--all`=全量、`--strict` 才 exit 1；扫描 0 份 ADR 报显式 finding 而非静默通过。

> 逐项「原 → 现」对照与存量债基线（162 项 findings / 60 份语料的分项计数）记在 `.rddf/reviews/adr-0060-amendment-2026-11-17.md` —— 可枚举改动清单与实测数据不进决策正文。

**关键理由**：机械门若比散文契约**松**，会让 250~300 行、缺 Verification、缺结论列的文档通过 —— 门禁于是成为假保证。三层（模板 / 提示词 / 机械检查）必须是**同一个数、同一组要素**；任一层单独收紧都留盲区。

**边界不变**：非 h2 的同名标题（如 `### 验证 ADR-0048 + ADR-0049 零 regression`）不算 Verification 章 —— 它是散文子标题，计为验收章会假阴性放行。行数仍按**全文物理行数**计（模板的「正文」口径不含推导/证据，两者只在保守方向可比，已在代码 docstring 注明）。

## Consequences

### 正面

- 新 ADR 有了可执行边界：行数预算、必备章节、Verification 前瞻性，且不靠人自觉。
- 门禁不再误杀真实架构决策——判定权回到架构师与用户。
- 存量不追溯：既有 ADR 不受影响，`arch_done` gate 在 `STRICT_ARCH_GATE=yes` 下不会因形态检查新增阻断。

### 负面 / 风险

- 机械检查是启发式：正文里正常提到 `BLOCKER` 一词会被计为过程日志标记（当前按 warning 级处理，可接受）。
- 提示词层约束依赖 LLM 遵守，无强制力——机械检查是兜底而非替代。
- rdd-workflow 与 opencode 两处约束需同步维护，存在措辞漂移风险。
- （2026-11-17 修订）新增的三类启发式信号都会在存量语料上产生假阳性：Verification 章判定依赖 h2 层级、备选表「结论列」依赖列名白名单、标题锚定正则依赖标题形态。它们按 warning 级 + opt-in + 增量默认扫描处理，**不产生阻断**；存量收敛前不得接入 CI。

### 后续待办

- [ ] **未来参考**：既有 ADR 的存量收敛（拆分 / 瘦身 / 补要素）单独立项，不在本 ADR 范围。
- [ ] **未来参考**：`adr_shape_check.sh` 接入 CI —— 等存量清零后再启用 `ARCH_SHAPE_CHECK`。
- [ ] **暂不修复**：`adr_gate.sh` 关键词表本身维持原样（分类仅作提示，不再承担判定职责）。
- [ ] **未来参考**（修订 2026-11-17）：修订后全量扫描的存量债基线已记录在 `.rddf/reviews/adr-0060-amendment-2026-11-17.md`；收敛（尤其 57 份缺 Verification 章）单独立项，本 ADR 不追溯。

## Verification

- [ ] **V-1** `bash skills/rdd-arch/scripts/adr_gate.sh "rv32i-fetch-skid-buffer"` ⇒ stdout 仍为 `IMPLEMENTATION`（分类逻辑未变），stderr 含 `advisory`
- [ ] **V-2** `ADR_GATE_MODE=block bash ... adr_gate.sh "Fix typo"` ⇒ stderr **无** advisory
- [ ] **V-3** `ADR_GATE_CLASS=ARCHITECTURE bash ... adr_gate.sh "rv32i-fetch-skid-buffer"` ⇒ stdout 为 `ARCHITECTURE`（显式覆盖生效）
- [ ] **V-4** `python3 -m pytest tests/unit/test_arch_quality_gate.py -q` ⇒ 全部通过（含 `_check_adr_shape` 的 8 项新测试）
- [ ] **V-5** `bats tests/integration/test_adr_gate.bats tests/integration/test_adr_gate_flow.bats` ⇒ 全部通过（含 advisory 模式与形态约束锚点断言）
- [ ] **V-6** `ARCH_SHAPE_CHECK=yes` 时 `ArchQualityReport.verify()` 出现 `adr_shape` 项；未设该变量时**不出现**
- [ ] **V-7** 新建一份正文 > 250 行的 ADR ⇒ `adr_shape_check.sh <file>` 报出该文件与 `line_budget`
- [ ] **V-8** `docs/adr/ADR-0000-template.md` 仍含 `## Context` / `## Decision` / `## Consequences` / `## References` 四段（既有 bats 断言不破）
- [ ] **V-9**（修订 2026-11-17）`python3 -c "from skills._lib.arch_quality_gate import _DEFAULT_ADR_LINE_LIMIT as L; assert L == 250"` ⇒ 通过；且模板里 `≤ N 行` 抽出的 N 与它相等（同源断言，见 `tests/unit/test_arch_quality_gate.py`）
- [ ] **V-10**（修订 2026-11-17）同一批 ADR 下，`ARCH_ADR_LINE_LIMIT=300 adr_shape_check.sh --all` 的 `line_budget` 项数**严格小于**默认预算（250）下的项数 ⇒ 证明环境变量覆盖确实生效（两侧相等即说明 env 被忽略）。**不在此固定具体计数**——语料随 ADR 增补而变，点值判据会无故变红。
- [ ] **V-11**（修订 2026-11-17）`adr_shape_check.sh <一份仅有 h3「### 验证 …」的 ADR>` ⇒ 报 `missing_verification`；`<一份有 ## 验证 + 勾选项的 ADR>` ⇒ **不**报
- [ ] **V-12**（修订 2026-11-17）`adr_shape_check.sh <一份两列「备选 | 理由」表的 ADR>` ⇒ 报 `alternatives_table_no_conclusion_column`；`<一份四列「方案|优点|缺点|是否采用」的 ADR>` ⇒ **不**报
- [ ] **V-13**（修订 2026-11-17）`adr_shape_check.sh --all` 在无 ADR 的目录 ⇒ 报 `no_adr_files_scanned`（不静默通过）；无参调用 ⇒ exit 2

## References

- ADR-0016 —— arch artifact discovery contract
- ADR-0018 —— arch quality gate（本文扩展其检查面）
- ADR-0057 —— ADR（atomic decision record）+ theme doc（topic snapshot）双工件模型
- `skills/rdd-arch/SKILL.md` —— Phase 2 adr-create
- opencode 侧同源约束：`~/.config/opencode/prompts/build.md`「architect 产出形态契约」
