## Context

本提案源自 rdd-workflow 用户在跨阶段特性维护与 sub-phase 独立编辑两个具体痛点。Oracle 二轮咨询（6 维度发现）确认：手工维护的 source-of-truth（不是派生视图），需要 .rddf/roadmap/ 层次化结构与 ID 引用制。

**当前状态**：
- `roadmap.md` 在项目根，单文件，单 ADR-0016 discovery schema v1（`roadmap_path: string`）
- `_lib/roadmap_state.py` 6 个函数单文件假设，6 个 consumer 全部紧耦合
- 子阶段 `phase-N.M` 仅 `advance_phase()` 聚合逻辑，文档仍是单文件

**目标状态**：
- 主 roadmap 迁 `.rddf/roadmap.md`（tracked）
- `.rddf/roadmap/{phases,features,archive}/` fragment 树
- ADR-0016 v2 schema + `roadmap_state.py` additive API
- `roadmap migrate` 9 步原子化迁移工具
- `roadmap validate-fragments` + `rdd-doctor roadmap-refs` 双入口校验

**关键约束**（不破坏现有契约）：
- 6 个现有函数签名零变化
- ADR-0016 v1 handoff 仍被 v2 code 接受（视为无 fragments）
- 所有现有 test 仍 pass
- 根 `roadmap.md` 改写为 stub（不删除，保留 ADR-0016 fallback）

## Goals / Non-Goals

**Goals:**
- 主 roadmap 文档独立可读、独立 commit、独立 review
- 跨阶段特性有独立 roadmap 文档（手工 source of truth）
- sub-phase 独立维护不触发主文档 merge
- theme 注册表留主文档（5 列表），保护 `compute_theme_coverage` 零变更
- fragment 完成/归档生命周期完整（永不删除）
- 现有 6 个 consumer（propose, add-improve, 3 tests, phase2_path_migrator）零改动

**Non-Goals:**
- **不重写** `_lib/roadmap_state.py` 现有 6 个函数
- **不修改** `iteration.json` / `deps-analysis.json` schema
- **不实现** fragment 自动从 phase 推导（特性是手工 source）
- **不引入** fragment 嵌套层级（`phase-N.M` 是独立 ID 不用目录层级）
- **不重写** `roadmap-proposal-guidance`（已 ship 的 theme + coverage 机制）
- **不自动 commit** migrate 产出（避免 AI 误操作）

## Decisions

### 1. 目录布局：主 + fragment + archive 全 tracked

**Description**: 所有 roadmap 文档都在 git 里，包括已完成的 archive/。

**Rationale**:
- 全 tracked 避免 AI session 重启、worktree 切换、队友拉代码丢失 fragment 草稿
- archive/ tracked + git history 双保险，禁止删除
- 与 `.rddf/plans/` tracked 模式对齐

**Alternatives considered**:
- 主 tracked + fragment gitignored（Oracle 拒绝）：导致跨机器/队友悬空引用
- 主 tracked + fragment 工作树分支（Cherry 拒绝）：增加复杂度无收益

### 2. Fragment 粒度：phase 默认 + sub-phase 按需 promote

**Description**: 初始按 phase 切片；sub-phase 在 phase fragment 内 as section，需要独立维护时 promote 为独立 fragment（kind: phase, id: phase-N.M）。

**Rationale**:
- 避免过度拆分（项目初期不需要 phase-N.M 全独立）
- 用户明确"sub-phase 独立维护"是按需的，不是默认
- 简单优先：先 one fragment per phase，发现不够再 promote

**Alternatives considered**:
- phase-N.M 全部独立（过度拆分：管理成本高，merge 冲突多）
- 单文件 + section 折叠（用户最初意图）：fragment 是 source of truth，不能折叠

### 3. Migrate 位置：`roadmap migrate` 子命令（不碰 rdd-doctor）

**Description**: 迁移是 mutation 操作，放在 `roadmap` skill 的子命令（已有 init/edit/validate/advance）。

**Rationale**:
- rdd-doctor 的 description 明确"不修改任何 tracked / gitignored 文件"——只读约束不能破坏
- rdd-doctor 只新增**只读** category（`roadmap-refs`），用于诊断而非迁移
- 与 `rddf migrate-improvements` 实现隔离（不共享代码）

**Alternatives considered**:
- 放 rdd-doctor 子技能（用户最初意图）：破坏只读约束
- 放新 skill：增加概念负担，无收益

### 4. ADR-0016 schema v2：additive 演进

**Description**: schema bump 到 v2，新增可选 `roadmap_fragments_dir` 字段。Consumer 接受 v1（视为无 fragments）+ v2（聚合读），继续拒绝 v0。

**Rationale**:
- v1 项目无需重写 handoff
- bump version 是项目惯例（ADR-0016 v1 定义了"字段定义改必须 bump"）
- 环境变量优先级保留（`SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR` override）

**Alternatives considered**:
- v2 强制升级（破坏性）：让所有 v1 项目必须迁移，不必要
- 不 bump（ad-hoc 字段）：违反项目惯例，消费者会拒绝

### 5. roadmap_state.py additive API

**Description**: 新增 `Fragment` dataclass + 6 个函数（`load_fragments`, `get_fragment`, `list_active_fragments`, `render_fragment_index`, `validate_fragment_refs`, `aggregate_phase_progress`），**不改**现有 6 个函数。

**Rationale**:
- 现有 6 个函数继续读主文档，行为不变
- 6 个 consumer 零改动（propose, add-improve, 3 tests, phase2_path_migrator）
- 新函数走新 handoff 字段，缺失时 fallback

**Alternatives considered**:
- 重写所有函数接受 `roadmap_files: list[str]`：破坏 6 个 consumer，PR review 困难
- 新增 `roadmap_files` 参数为可选：API 演进混乱

### 6. 校验双入口（roadmap validate + rdd-doctor）

**Description**: 同一份 `validate_fragment_refs` 实现 + 8 条规则（R1-R8），通过两个入口暴露：用户门控（roadmap validate-fragments）+ 诊断（rdd-doctor --category roadmap-refs）。

**Rationale**:
- 用户门控（plan-done）需要明确的 exit code
- 诊断入口（doctor）需要分级报告
- 共享实现避免规则定义漂移

**Alternatives considered**:
- 单入口（仅 roadmap validate）：失去 doctor 的诊断价值
- 仅 doctor：失去 plan-done 门控能力

### 7. Theme 注册表留主文档（5 列表）

**Description**: 主题三态（未覆盖/已覆盖/~skipped~）由主文档任务分类表 5 列驱动，`compute_theme_coverage` 行为不变。Fragment frontmatter `主题:` 仅作元信息展示，不参与覆盖度计算。

**Rationale**:
- 主题是注册表，主文档是唯一 source
- fragment 主题是 metadata 而非注册项（避免双事实源）
- `compute_theme_coverage` 6 个调用方零改动

**Alternatives considered**:
- Fragment 主题计入 coverage（用户最初假设）：必须聚合跨 fragment 主题，复杂度高 + 漂移风险
- 完全放弃 fragment 主题（不要 `主题:` 字段）：失去元信息展示价值

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| 全 tracked 多文件噪音 | merm 2 自动 commit（archive-like）；`render_fragment_index` 写 `<!-- AUTO-INDEX -->` sentinel，单点变更 |
| Fragment ID 拼写错误漂移 | `validate_fragment_refs` R1 规则强制 WARNING；STRICT 升级 CRITICAL 阻断 |
| 跨文件引用不一致 | ID 注册制（fragment 只能引用主文档登记的 phase ID）；校验工具双入口 |
| 跨 fragment 主题聚合 | 不做（Oracle + 用户决策：fragment 主题不参与计算） |
| `roadmap migrate` 半迁移状态 | 9 步原子化，Step 6 失败 → 保留 backup + 删除已写入 + exit 非零 |
| `.openspec.yaml` 缺 `schema` 字段（已发现） | 修复 commit `ec3aec3` 后续 PR 同步修复 `approve_proposal.sh` |
| rdd-doctor 误触发 migration | doctor description 硬约束 + 不共享迁移实现代码 |
| Acceptance Criteria "markdown checkboxes" WARNING | 这是 D5 内容审查 warning，不阻断。可后续 PR 优化 AC 格式 |