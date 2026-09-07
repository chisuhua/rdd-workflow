## Why

`rdd-arch gap analysis`（`skills/rdd-arch/scripts/arch_gap_analysis.sh`，86 行，2 函数）是 **deterministic template generator**——它生成 5 节 markdown skeleton（目标架构 / 当前架构 / 差距清单 / 补齐路径 / 参考资料）让人类策展者填写。当前实现重复了 PROJECT_ROOT/ARCH_DIR 解析逻辑（2 个函数）、无内容验证、无 Python 测试覆盖。

Oracle review (`ses_f84cabe64ffeBiz3XzHmFSSznc`) 在 verifier-v2-hardening 调度 `docs/superpowers/specs/verifier-protocol-template.md` 时明确指出：

> "First application candidate: rdd-arch gap analysis. Not implemented in this change; tracked as future."

本次 change 即该 future 落地。

**问题**：模板 spec 的 5 sections 是为 **LLM-as-judge verifier** 设计的（§3 staged context / §4 SHA-bound cache / §5 fail-closed gate）——但 gap analysis 是 deterministic 且 human-curated，没有 LLM、没有 verdict、没 cache。**直接套全部 5 sections 是 form over substance**：会为不存在的消费者造文件、为人写文档的完成度设置阻断 gate。

模板 spec 自身的 Boundaries 段（L120-122）已声明 "Human-dominated steps stay human-in-loop, only reasoning-assistant sub-steps may use this template"——gap analysis 落在这个排除区。**部分采用是模板语义的必然推论**。

## What Changes

### Subset 架构（per Oracle 决策）

| 模板 § | 裁决 | 本次实施 |
|--------|------|----------|
| §1 SKILL.md § Protocol | **ADOPT（适配）** | 新增 `## Arch Gap Analysis Protocol` 段；frontmatter 加 `protocol_inline: true` + `protocol_data_layer: "_lib/arch/protocol.py"`；不写 `protocol_context_file`/`protocol_cache_file`（不适用） |
| §2 Data Layer (`_lib/arch/protocol.py`) | **ADOPT** | 新建 `_lib/arch/protocol.py`（3 纯函数：`build_skeleton` / `validate_document` / `list_analyses`）+ `_lib/arch/__init__.py` |
| §3 Staged Context File | **SKIP** | 无 agent 消费者；markdown 骨架本身就是 artifact |
| §4 SHA-Bound Cache | **SKIP** | 无 LLM verdict 可绑定 SHA；gap doc 是 git-tracked durable artifact，cache 会违反 durability 边界 |
| §5 Fail-Closed Gate | **REPURPOSE → Output Contract Validation** | 两层语义：**结构一致性**（5 节齐全 + slug 格式）= deterministic 硬；**完成度**（占位符检测）= advisory status 而已 |

### 模板 spec 改名（cross-stage 真名实）

`docs/superpowers/specs/verifier-protocol-template.md` → **`cross-stage-protocol-template.md`**，内设：
- **Verifier Subset**（§1-§5 full，适用 LLM-as-judge verifier 阶段）
- **Analyzer Subset**（§1 + §2 + §5-validated，适用 deterministic human-curated analyzer 阶段）

frontmatter marker 按 subset 实际采用声明——不照抄 verifier 的 cache/context marker。新增 `protocol_output_contract: true` marker 给 Analyzer Subset 用。

### 新增 ADR-0046

`docs/adr/ADR-0046-arch-analyzer-protocol-subset.md`（短 ADR，引用而非重述模板 spec）：
- 声明 gap analysis 落地 subset 采用
- 每节一句话裁决理由（ADOPT/SKIP/REPURPOSE）
- 明确"arch-done Phase 5 接线 validation 推迟"为 out-of-scope
- Oracle session id：`ses_f84cabe64ffeBiz3XzHmFSSznc`

### 代码改动

| 文件 | 变化 | 内容 |
|------|------|------|
| `_lib/arch/__init__.py` | NEW | 空 `__init__.py` 让 `_lib.arch` 成为可导入包 |
| `_lib/arch/protocol.py` | NEW | 3 纯函数：`build_skeleton(slug, today_iso) -> str`、`validate_document(path) -> ValidationReport`、`list_analyses(arch_dir) -> list[Path]` |
| `skills/rdd-arch/scripts/arch_gap_analysis.sh` | 重写为薄 wrapper | 函数签名 `generate_gap_analysis <slug>` 与 `list_gap_analyses` **逐字节不变**；按 Oracle C1 3-file env-var pattern（参考 `_lib/plan_done_gate.sh` / `_lib/update_roadmap_progress.sh`）委托 Python；**所有现有 8 个 bats 的 observable contract 必须保留** |
| `skills/rdd-arch/SKILL.md` | 新增 § Protocol 段 | `## Arch Gap Analysis Protocol` 段引用 `_lib/arch/protocol.py`；保留 L343-L431 区域的现有 `source` + 调用逻辑 |
| `docs/superpowers/specs/verifier-protocol-template.md` | RENAME → `cross-stage-protocol-template.md` | 改名 + 改写 Verifier Subset + 新增 Analyzer Subset + 更新 Adoption Decision 段 |
| `docs/adr/ADR-0046-arch-analyzer-protocol-subset.md` | NEW | 短 ADR |
| `tests/unit/test_arch_protocol.py` | NEW | 单元测试 `build_skeleton` / `validate_document` / `list_analyses` |
| `tests/integration/test_arch_gap_analysis_extraction.bats` | 保留 + **追加** 2-3 cases | 新增：wrapper↔Python 一致性、validate_document 通过 wrapper 暴露、validate_document 检测结构破损 |
| `docs/superpowers/specs/verifier-protocol-template.md` 的 git history | 通过 `git mv` 改名 | 改名不丢历史 |

### Out of Scope

- ❌ 不重写 `generate_gap_analysis` 的 markdown 内容措辞（保持人类策展的 idiomatic Chinese）
- ❌ 不把 validation 接线进 `rdd-arch/SKILL.md` Phase 5 arch-done gate（仅暴露 `validate_document` 作为 advisory helper）
- ❌ 不改 rdd-verifier v2.0 / rdd-builder / rdd-planner 主流程
- ❌ 不为 Analyzer Subset 创建 SHA-bound cache 或 staged context（永久 SKIP）

## Impact

### In Scope
- `skills/rdd-arch/scripts/arch_gap_analysis.sh`（重写为薄 wrapper）
- `_lib/arch/`（新子包，含 `__init__.py` + `protocol.py`）
- `skills/rdd-arch/SKILL.md`（新增 § Arch Gap Analysis Protocol 段）
- `docs/superpowers/specs/verifier-protocol-template.md`（git mv → `cross-stage-protocol-template.md`，内容重写）
- `docs/adr/ADR-0046-arch-analyzer-protocol-subset.md`（NEW）
- `tests/unit/test_arch_protocol.py`（NEW，Python 单元测试）
- `tests/integration/test_arch_gap_analysis_extraction.bats`（保留 8 + 新增 2-3 case）

### Out of Scope
- `rdd-arch/SKILL.md` Phase 5 arch-done gate 不消费 `validate_document`（deferred）
- 不改其他 5 个 phase 技能
- 不重写任何 markdown 内容措辞
- 不动 verifier v2.0 / ac-verifier 移除后的协议（已归档）

## Acceptance Criteria

- [ ] `_lib/arch/__init__.py` 与 `_lib/arch/protocol.py` 创建
- [ ] `_lib/arch/protocol.py` 导出 3 个纯函数 `build_skeleton` / `validate_document` / `list_analyses`，各带 docstring + type hints
- [ ] `validate_document` 返回 dataclass `ValidationReport` (含 `structural_ok: bool` + `completeness: Literal["draft", "partial", "complete"]` + `issues: list[str]`)
- [ ] `validate_document` 检测 5 节结构（硬）+ 检测占位符（advisory）
- [ ] `skills/rdd-arch/scripts/arch_gap_analysis.sh` 重写为薄 wrapper，**所有现有 8 个 bats 0 改动即通过**（证明 wrapper contract 逐字节不变）
- [ ] bash wrapper 用 Oracle C1 3-file env-var pattern（`_lib/arch/protocol.sh` + `_lib/arch/protocol.py` + `_lib/arch/protocol.env.py`）
- [ ] `skills/rdd-arch/SKILL.md` 新增 `## Arch Gap Analysis Protocol` 段（引用 `_lib/arch/protocol.py`）+ frontmatter 加 `protocol_inline: true` / `protocol_data_layer: "_lib/arch/protocol.py"`
- [ ] `docs/superpowers/specs/verifier-protocol-template.md` → `cross-stage-protocol-template.md`（git mv）
- [ ] 改名后模板含 **Verifier Subset**（§1-§5 full）+ **Analyzer Subset**（§1 + §2 + §5-validated）两节
- [ ] Analyzer Subset 显式定义 `protocol_output_contract: true` marker
- [ ] `docs/adr/ADR-0046-arch-analyzer-protocol-subset.md` 创建（含 subset 裁决、Oracle session id、out-of-scope 明确）
- [ ] `tests/unit/test_arch_protocol.py` 创建：覆盖 3 函数 + boundary cases（空 slug / 无 AC section / 已存在文件 / 占位符检测）
- [ ] `tests/integration/test_arch_gap_analysis_extraction.bats` 追加 2-3 case：wrapper↔Python 输出等价、validate_document 暴露、validate_document 检测结构破损
- [ ] `openspec validate arch-analyzer-protocol --strict` 绿
- [ ] `./test.sh --full --regression` 0 bats 新增失败
- [ ] `git grep "verifier-protocol-template" -- docs/ _lib/ skills/ tests/` 0 命中（确认改名波及面为 0）

## Reference

- 上游 change：`openspec/changes/archive/2026-09-07-verifier-v2-hardening/`（oracle Q3 调度）
- 上游 change：`openspec/changes/archive/2026-09-07-remove-ac-verifier-completely/`（oracle closure）
- 上游 change：`openspec/changes/archive/2026-09-07-inline-ac-verifier-into-rdd-verifier/`（ADR-0045）
- 模板 spec：`docs/superpowers/specs/verifier-protocol-template.md`（rename 后）
- Oracle session：`ses_f84cabe64ffeBiz3XzHmFSSznc`
- ADR 序列：ADR-0034（rdd-verifier 5 phase）+ ADR-0035（双轨边界）+ ADR-0045（inline verifier）→ ADR-0046（本）
- 仓库模式先例：Oracle C1 3-file env-var pattern（`_lib/plan_done_gate.{sh,py,env.py}` / `_lib/update_roadmap_progress.{sh,py,env.py}`）