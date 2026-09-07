# arch-analyzer-protocol — Tasks

## Phase 0 — Setup
- [x] T01: 建 branch `openspec/arch-analyzer-protocol` (master base)
- [x] T02: Oracle 决策 (subset 架构 + 改名 + ADR-0046)
- [x] T03: 检查引用面 grep verifier-protocol-template → 0 命中
- [x] T04: 读 8 个现有 bats 锁定 wrapper contract (Oracle 风险 #3)
- [x] T05: 写 design.md (architectural impact + 11 acceptance criteria)
- [x] T06: 写 tasks.md (本文)
- [x] T07: 写 specs/arch-analyzer-protocol/spec.md (7 Requirement + Scenario)
- [x] T08: `openspec validate arch-analyzer-protocol --strict` 绿
- [x] T09: commit artifacts (`feat(arch-analyzer-protocol): propose subset adoption`)

## Phase 1 — Python 数据层 (`_lib/arch/protocol.py`)
- [ ] T10: `_lib/arch/__init__.py` 创建（空）
- [ ] T11: `_lib/arch/protocol.py` 3 纯函数：
  - `build_skeleton(slug: str, today_iso: str = "") -> str`
  - `validate_document(path: Path) -> ValidationReport`
  - `list_analyses(arch_dir: Path) -> list[Path]`
- [ ] T12: `ValidationReport` dataclass：
  - `structural_ok: bool` (5 节齐全？)
  - `completeness: Literal["draft", "partial", "complete"]` (占位符密度)
  - `issues: list[str]`
- [ ] T13: `build_skeleton` 输出与现有 bash heredoc **逐字节相同**（用 `git show HEAD:skills/rdd-arch/scripts/arch_gap_analysis.sh | sed -n '28,57p'` 对比）
- [ ] T14: `validate_document` 检测 5 节 (## 目标架构 / ## 当前架构 / ## 差距清单 / ## 补齐路径 / ## 参考资料)
- [ ] T15: `validate_document` 检测占位符（`(待补充)` / `(描述...)` / `(描述 ADR 中定义的目标架构)` 等）
- [ ] T16: `validate_document` slug 校验 (kebab-case)

## Phase 2 — Bash Wrapper 薄化（Oracle C1 3-file env-var pattern）
- [ ] T17: `_lib/arch/protocol.sh` wrapper bash 函数（env var 入口）
- [ ] T18: `_lib/arch/protocol.env.py` env var schema（`ARCH_GAP_SLUG`, `ARCH_GAP_TODAY`, `ARCH_GAP_ACTION` ∈ {generate,list,validate}, `ARCH_GAP_ARCH_DIR`）
- [ ] T19: `skills/rdd-arch/scripts/arch_gap_analysis.sh` 重写为 1 行 `source _lib/arch/protocol.sh` + 委托 dispatch
- [ ] T20: 8 个现有 bats **0 改动**全部通过（Oracle 风险 #3 验证）

## Phase 3 — SKILL.md § Protocol 段（§1 ADOPT）
- [ ] T21: `skills/rdd-arch/SKILL.md` frontmatter 加 `metadata.protocol_inline: true` + `metadata.protocol_data_layer: "_lib/arch/protocol.py"`
- [ ] T22: `skills/rdd-arch/SKILL.md` 新增 `## Arch Gap Analysis Protocol` 段（引用 `_lib/arch/protocol.py` + 5 节契约）
- [ ] T23: SKILL.md 中现有 `source scripts/arch_gap_analysis.sh` + `generate_gap_analysis` + `list_gap_analyses` 调用保留（test 3 锁定）

## Phase 4 — 模板改名 + Analyzer Subset
- [ ] T24: `git mv docs/superpowers/specs/verifier-protocol-template.md docs/superpowers/specs/cross-stage-protocol-template.md`
- [ ] T25: 改名后 spec 标题改为 "Cross-Stage Protocol Template"（移除 "verifier-protocol" 误导性命名）
- [ ] T26: Verifier Subset 段保留原 §1-§5 full 描述（适用于 LLM-as-judge verifier 阶段）
- [ ] T27: **新增 Analyzer Subset 段**（§1 + §2 + §5-validated + protocol_output_contract marker 解释）
- [ ] T28: Adoption Decision 段更新：first application 从"future"改为"arch gap analysis, subset adoption (ADR-0046)"
- [ ] T29: `git grep "verifier-protocol-template"` → 0 命中（确认改名波及面为 0）

## Phase 5 — ADR-0046
- [ ] T30: `docs/adr/ADR-0046-arch-analyzer-protocol-subset.md` 创建
- [ ] T31: ADR 内容：状态 / 日期 / 决策者 / 关联 ADR-0045 / 上下文（oracle Q3 + template spec 改名）/ §1-§5 逐节裁决（含一句话理由）/ out-of-scope 明确（arch-done 接线 deferred）/ Oracle session id
- [ ] T32: ADR 控制在 ≤80 行（短 ADR，引用而非重述模板 spec）

## Phase 6 — 测试
- [ ] T33: `tests/unit/test_arch_protocol.py` 创建
- [ ] T34: Unit cases：build_skeleton 输出 5 节 / validate_document 5-section-detect / validate_document placeholder-detect / validate_document non-kebab-slug-detect / list_analyses empty / list_analyses sorted
- [ ] T35: `tests/integration/test_arch_gap_analysis_extraction.bats` 追加 case 9：wrapper↔Python 输出 byte-equal（`diff <(wrapper) <(python)`）
- [ ] T36: 追加 case 10：`validate_document` 通过 wrapper 暴露（`ARCH_GAP_ACTION=validate`）
- [ ] T37: 追加 case 11：`validate_document` 检测结构破损（手动改一个 ## header 为 ### 后 validation fails）

## Phase 7 — 全量回归 + 归档
- [ ] T38: `./test.sh --full --regression` → 0 bats 新增失败
- [ ] T39: `git add -A && git commit -m "feat(arch-analyzer-protocol): rename template + Python data layer + ADR-0046"` (主 commit)
- [ ] T40: `openspec archive arch-analyzer-protocol --yes` → 自动 commit
- [ ] T41: `git checkout master && git merge --no-ff openspec/arch-analyzer-protocol`
- [ ] T42: `git branch -d openspec/arch-analyzer-protocol`
- [ ] T43: 验证 branch cleanup + 最终 git log