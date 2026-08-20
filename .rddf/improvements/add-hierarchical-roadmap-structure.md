# add-hierarchical-roadmap-structure

**优先级**: P1 | **来源**: Oracle 二轮咨询（6 维度发现）+ 用户动机澄清（跨阶段特性维护 + sub-phase 独立编辑）+ `rdd-doctor` 子技能提议
**阶段**: v2.2 规划中（fallback v2.3）| **分类**: arch-design
**类型**: refactor
**主题**: 不适用（本提案为后续 roadmap 主题机制的前置基础）

> **范围定位**：本提案聚焦**目录结构 + 文档契约 + API 演进 + 迁移工具**。它**不是**单一 feature 交付，而是为后续 roadmap-proposal 主题机制、跨阶段特性追踪、sub-phase 独立维护**打地基**。后续子提案（如"按特性 roadmap 创建 change"）将构建在本提案之上。
>
> **不重复** `roadmap-proposal-guidance` 范围（主题字段 + 覆盖率计算，本提案为前置依赖）。
>
> **不破坏** 任何 rdd-workflow 现有契约（ADR-0016 v1 handoff、`roadmap_state.py` 现有函数签名、6 个 consumer 的行为）。

## 架构依据

### 动机（用户澄清）

1. **跨阶段特性维护**：一个特性（如"用户认证 v2"）可能跨 phase-2 → phase-3 → phase-4 实施。用户希望这个**特性有自己的路线图**，但又必须**与主 roadmap 的阶段节点对齐/协调**（避免脱节）。
2. **子阶段独立维护**：子阶段（如 phase-3.1）有自己的细节路线图，独立增删调整，**不希望每次改动都触发主 roadmap 文档的编辑/merge**。

→ 这两类文档是**手工维护的 source of truth**，不是派生视图（不能由 `iteration.json` / `deps-analysis.json` 推导）。

### Oracle 6 维度发现（关键约束）

| 维度 | 关键发现 |
|------|---------|
| 盲区 | 用户最初没说清痛点；子文档是 source vs view 是核心歧义；跨文件 theme 一致性无保障；fragment 生命周期无对应路径 |
| 路径/可见性 | 全 tracked 可避免 AI session 丢失草稿 + 团队共享；子 gitignored 会导致队友/worktree 悬空引用 |
| 语义边界 | 子阶段/特性是同一数据的两个维度投影，**应统一为"roadmap fragment"** 而非两类独立文档 |
| migrate 位置 | **`rdd-doctor` 是只读约束不应破坏**——迁移属于 `roadmap` skill 子命令；校验入口双路由（doctor + roadmap validate） |
| 下游兼容性 | **additive 演进**：保留 `roadmap_path` 单值，新增可选 `roadmap_fragments_dir`；schema v2 兼容 v1 |
| 与现有对齐 | 不新建 `.rddf/docs/`/`intent/`（避免第三个约定）；主文档放 `.rddf/roadmap.md` 与 `.rddf/plans/` 同根并列；frontmatter 复用 improvements 方言 |

### 设计决策（已批准）

| 决策点 | 选择 |
|------|------|
| Tracked 策略 | 主 + fragment + archive 全 tracked |
| Fragment 粒度 | phase 默认（每个 phase 一个 fragment），sub-phase 按需 promote |
| Migrate 位置 | `roadmap migrate` 子命令（不碰 `rdd-doctor`） |
| 主文档位置 | `.rddf/roadmap.md`（tracked），根目录 `roadmap.md` 留 stub 指针 |
| Scope | 拆 2 个 change（结构+迁移 / 校验+门控） |
| Theme 注册表 | 留主文档任务分类表（5 列含主题），fragment frontmatter `主题:` 仅作元信息展示，**不参与覆盖度计算** |

## 范围

### In Scope

**A. 目录结构（Change 1）**:
- 新增 `.rddf/roadmap/` 目录树：`phases/`, `features/`, `archive/`（全 tracked）
- 新增 `.rddf/roadmap.md` 主文档（tracked）：phase 骨架表（5 列含主题）+ `<!-- AUTO-INDEX -->` sentinel（fragment 反向索引）
- 根目录 `roadmap.md` 改写为 stub 指针（1 段："本文件已迁移，详见 .rddf/roadmap.md"）

**B. ADR-0016 schema v2（Change 1）**:
- bump 到 `version: "2"`
- 新增可选字段 `roadmap_fragments_dir: string`（默认 `.rddf/roadmap`）
- 保留 `roadmap_path` 字段（值改为 `.rddf/roadmap.md` 默认）
- 兼容矩阵：consumer 接受 v1（视为无 fragments）+ v2（聚合读），继续拒绝 v0

**C. `roadmap_state.py` additive API（Change 1）**:
- 新增 `Fragment` dataclass（id, kind, status, phase_refs, theme, file_path, frontmatter, body）
- 新增函数 ≥ 6 个：`load_fragments`, `get_fragment`, `list_active_fragments`, `render_fragment_index`, `validate_fragment_refs`, `aggregate_phase_progress`
- **不修改**任何现有函数签名（6 个 consumer 零改动）

**D. `roadmap migrate` 子命令（Change 1）**:
- 9 步原子化流程：preflight → parse main → plan slice → dry-run output → backup → execute → validate → archive hint → rollback hint
- 参数：`--dry-run`（默认）/ `--execute` / `--backup-dir <path>` / `--rollback <backup-dir>` / `--yes`
- 自动 git tag `pre-roadmap-migrate-<timestamp>`（在 git 仓库时）
- 与 `rddf migrate-improvements` 实现隔离（不共享代码，避免误以为 doctor 是迁移工具）

**E. 一致性校验（Change 2）**:
- 实现 8 条规则（R1-R8：phase_refs 完整性、id 唯一性、kind 枚举、phase id 命名、feature 必须有 phase_refs 等）
- `roadmap_state.py::validate_fragment_refs` 返回 `List[ValidationError]`
- 默认 WARNING level；`STRICT_ROADMAP_REFS_GATE=yes` 升级 CRITICAL；`SKIP_ROADMAP_REFS_GATE=yes` 跳过

**F. 双入口校验（Change 2）**:
- `roadmap validate-fragments` 子命令（门控，exit code 0/1/2/3 对齐 openspec validate）
- `rdd-doctor --category roadmap-refs`（诊断，CRITICAL/WARNING/INFO 分级报告，仍只读）
- 共用同一份校验实现（`validate_fragment_refs`）

**G. plan-done gate 集成（Change 2）**:
- `guide-plan` plan-done 流程新增 step：调用 `validate_fragment_refs`
- 默认 WARNING level 不阻断 plan-done
- `STRICT_ROADMAP_REFS_GATE=yes` 升级为 CRITICAL 阻断

### Out Scope

- **不修改** `iteration.json` schema 或 `deps-analysis.json` schema
- **不修改** `feature` skill（基于 iteration/deps 派生视图的机制不变）
- **不重写** `roadmap-proposal-guidance`（主题字段 + 覆盖度计算）—— 本提案是它的前置依赖
- **不实现** fragment 自动从 phase 推导（特性是手工创建的 source of truth，工具无法推断）
- **不引入** fragment 嵌套层级（`phases/phase-3/phase-3.1.md` 禁止）
- **不修改** `_lib/roadmap_state.py` 现有 6 个函数（get_phase_themes, get_phase_categories, advance_phase, add_phase, render_status_view, validate_change, update_change_count, update_roadmap_marker）
- **不修改** 任何 `openspec/specs/*.md` 内容（仅可能新增一个 spec 记录本设计）

## 关键场景

### 场景 1: `roadmap migrate --dry-run` 预览切片
- **GIVEN** 现有项目根 `roadmap.md` 含 phase-1/2/3 骨架 + 任务分类表 + 主题列
- **WHEN** 用户运行 `skill_use("roadmap migrate")` 或 `rddf roadmap migrate --dry-run`
- **THEN**
  - 解析现有 roadmap.md，输出主文档瘦身前后 diff
  - 输出每个 `phases/phase-N.md` 片段预览（frontmatter + body）
  - 输出 `archive/` 创建路径 + 根目录 stub 指针预览
  - 等待用户确认；不写入任何文件

### 场景 2: `roadmap migrate --execute` 完成迁移
- **GIVEN** 场景 1 已 dry-run 且用户确认
- **WHEN** 用户运行 `rddf roadmap migrate --execute --yes`
- **THEN**
  - 备份原 `roadmap.md` 到 `.rddf/.roadmap-migrate-backup-<timestamp>/`
  - git tag `pre-roadmap-migrate-<timestamp>`（如在 git 仓库）
  - 创建 `.rddf/roadmap/{phases,features,archive}/` 目录
  - 写入 `.rddf/roadmap.md`（瘦身版本：phase 骨架 + 任务分类表 + AUTO-INDEX sentinel）
  - 写入每个 `phases/phase-N.md` fragment（frontmatter 含 id/kind/status/主题）
  - 改写根目录 `roadmap.md` 为 stub 指针
  - 更新 `.rddf/state/.arch-handoff.json`：bump v2 + `roadmap_path: ".rddf/roadmap.md"` + `roadmap_fragments_dir: ".rddf/roadmap"`
  - 运行 post-migration `validate_fragment_refs`，输出 CRITICAL/WARNING/INFO 报告（不阻塞迁移）

### 场景 3: 跨阶段特性手工创建
- **GIVEN** `.rddf/roadmap.md` 已存在，phase-2/3/4 已注册
- **WHEN** 用户手工创建 `.rddf/roadmap/features/auth-v2.md`，frontmatter 含 `id: feat-auth-v2` + `kind: feature` + `phase_refs: [phase-2, phase-3, phase-4]` + `主题: RBAC 权限模型`
- **THEN**
  - `list_active_fragments(.rddf/roadmap, kind="feature")` 返回该 fragment
  - 主文档 `<!-- AUTO-INDEX -->` 渲染时包含反向引用
  - `validate_fragment_refs` 校验 R1（phase_refs 引用主文档已注册 phase）通过
  - `guide-design` preflight 后续可识别该特性 fragment（roadmap-proposal-guidance 后续提案）

### 场景 4: 子阶段独立维护（fragment 内 section）
- **GIVEN** `.rddf/roadmap/phases/phase-3.md` 含 ## 7.A GPU 基础设施 section
- **WHEN** 用户编辑该 section 添加新任务，不动主文档
- **THEN**
  - git commit 仅触及 `.rddf/roadmap/phases/phase-3.md`，无主文档冲突
  - 主文档 `<!-- AUTO-INDEX -->` 仍引用该 fragment（未变更，无需重新渲染）
  - 6 个现有 consumer（propose, add-improve, tests × 3, phase2_path_migrator）行为不变

### 场景 5: 子阶段 promote 为独立 fragment
- **GIVEN** `phase-3.1` 在 `phases/phase-3.md` 内 section 中不断增长，独立维护价值显现
- **WHEN** 用户创建 `.rddf/roadmap/phases/phase-3.1.md`，frontmatter 含 `id: phase-3.1` + `kind: phase` + `phase_refs: [phase-3]`，并从 `phase-3.md` 删除对应 section
- **THEN**
  - `validate_fragment_refs` 校验 R4（phase id 命名匹配 `phase-N(.M)?`）通过
  - `list_active_fragments(.rddf/roadmap, kind="phase")` 现在包含两个 phase fragment
  - `aggregate_phase_progress` 聚合 phase-3 完成度时合并两个 fragment 贡献

### 场景 6: phase advance 自动归档 fragment
- **GIVEN** `phase-3.md` 已标 `status: done`，所有 phase-3 的子 fragment 也 `status: done`
- **WHEN** 用户运行 `skill_use("roadmap advance")`，phase-3 advance 成功
- **THEN**
  - 钩子触发（Change 2 实现）：`roadmap archive-fragments --phase phase-3` 自动移动 phase-3 相关 fragment 到 `archive/`
  - archive 内 fragment frontmatter `status: archived`
  - 主文档 `<!-- AUTO-INDEX -->` 重新渲染时不再列出 archived fragment

### 场景 7: `roadmap validate-fragments` 校验失败（STRICT 阻断）
- **GIVEN** `.rddf/roadmap/features/auth-v2.md` frontmatter `phase_refs: [phase-99]`，但 phase-99 不在主文档
- **AND** `STRICT_ROADMAP_REFS_GATE=yes` 已设置
- **WHEN** `guide-plan` plan-done 调用校验
- **THEN**
  - `validate_fragment_refs` 返回 CRITICAL: "feature 'feat-auth-v2' 引用 phase-99 不存在于主文档"
  - plan-done gate 阻断（exit 1）
  - 用户修复（删除 phase_refs 中不存在的 ID 或在主文档添加 phase-99）

### 场景 8: `rdd-doctor --category roadmap-refs` 诊断报告
- **GIVEN** 某 fragment `kind: invalid-value`（违反 R3）
- **WHEN** 用户运行 `bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-refs`
- **THEN**
  - 输出分级报告：CRITICAL 列出 kind 非法值
  - doctor 退出码 = 1（对齐 openspec validate）
  - doctor **不修复**（仍只读），仅报告 + 给出 Fix 命令行建议
  - 建议：`rddf roadmap validate-fragments --help` 查看修复选项

### 场景 9: 升级路径——handoff v1 项目兼容
- **GIVEN** 旧项目 `.rddf/state/.arch-handoff.json` 是 v1，无 `roadmap_fragments_dir` 字段
- **AND** 旧项目根 `roadmap.md` 存在
- **WHEN** 升级到 v2.2（已安装本提案）但未运行 `roadmap migrate`
- **THEN**
  - `load_fragments("")` 返回空列表（fallback）
  - 所有现有 consumer 行为不变
  - `roadmap migrate` 可随时运行（向后兼容 v1 handoff）
  - 文档提示："建议运行 `roadmap migrate` 升级到层次化结构"

## 技术约束

### MUST

- `roadmap_state.py` 现有 6 个函数签名零变化（additive only）
- ADR-0016 schema v1 consumer 必须接受 v2 handoff（视为无 fragments）；v2 consumer 必须接受 v1（fallback 行为）
- 主文档 `<!-- AUTO-INDEX -->` sentinel 必须用原子化写入（tmp + rename），同 `roadmap_sprint.py::update_roadmap` 模式
- fragment frontmatter `id` 必须在文件创建时校验唯一性（id 冲突 = 致命错误）
- `kind` 字段必须是 `phase` 或 `feature`，其他值 CRITICAL 阻断
- `kind: feature` fragment 必须有非空 `phase_refs`，否则 WARNING（R5）
- `phase_refs` 中每个 ID 必须存在于主文档 phase 表，否则 WARNING（R1）→ STRICT 升级 CRITICAL
- `roadmap migrate` 必须支持 `--rollback`，从 backup 完整恢复原 roadmap.md + 删除新建的 `.rddf/roadmap*`
- `roadmap migrate` 任何写入失败必须保留 backup + 删除已写入的部分文件 + exit 非零（不留半迁移状态）
- `roadmap migrate` **不自动 git commit**，仅打印建议（避免 AI 误操作）
- `rdd-doctor --category roadmap-refs` 必须保持只读原则（不修改任何 tracked / gitignored 文件）
- `validate_fragment_refs` 必须**可独立调用**（roadmap validate-fragments 与 rdd-doctor 共用同一实现）
- `STRICT_ROADMAP_REFS_GATE=yes` 必须提升 WARNING → CRITICAL；`SKIP_ROADMAP_REFS_GATE=yes` 必须跳过校验 + 输出 "gate skipped" warning
- fragment **不嵌套**：禁止 `phases/phase-3/phase-3.1.md` 这种层级结构
- fragment **不删除**：完成 → archive/；永不 `git rm`
- 根目录 `roadmap.md` 改写为 stub 后**必须保留 1 段指针内容**（"本文件已迁移，详见 .rddf/roadmap.md"），不删除（避免破坏外部文档链接 + ADR-0016 默认 fallback）

### MUST NOT

- 不修改 `_lib/roadmap_state.py` 现有 6 个函数（get_phase_themes, get_phase_categories, advance_phase, add_phase, render_status_view, validate_change）
- 不修改 `iteration.json` / `deps-analysis.json` / `feature_view` / `arch_handoff` 之外的其他 schema（arch_handoff 仅新增 `roadmap_fragments_dir` + bump version）
- 不在 fragment 内嵌入 shell 脚本或可执行内容（仅 markdown）
- 不引入 fragment 自动从 phase 推导的机制（特性是手工 source of truth）
- 不重写 `roadmap-proposal-guidance` 范围（主题字段 + 覆盖度计算留给后续提案）
- 不在 `roadmap migrate` 内自动 commit（避免 AI 静默提交）
- 不破坏现有 rdd-workflow 测试（bats + pytest 必须仍全绿）

### SHOULD

- fragment frontmatter 复用 improvements 方言（主题 / 优先级 / 更新日期）
- `load_fragments` 支持 `include_archived: bool = False` 默认值过滤
- `roadmap validate-fragments` 输出与 `openspec validate` 退出码对齐（0/1/2/3）
- `rdd-doctor --category roadmap-refs` 输出格式与现有 5 个 category 一致（CRITICAL/WARNING/INFO）
- fragment 文件命名 = id（`.md` 后缀），如 `phase-3.md` / `auth-v2.md`
- 主文档 `<!-- AUTO-INDEX -->` 渲染时按 fragment `kind` 分组（phases first, features second）
- `roadmap migrate --dry-run` 输出可用 diff 工具友好的格式
- `roadmap migrate --rollback` 支持从任意 backup-dir 恢复（不仅最新一次）

## 验收标准

### Change 1（结构 + API + 迁移）—— `hierarchical-roadmap-foundation`

#### 功能验收

- **AC-1.1**: `.rddf/roadmap/` 目录树（phases/, features/, archive/）存在且 git tracked
- **AC-1.2**: `.rddf/roadmap.md` 主文档存在且 git tracked，含 phase 骨架表 + `<!-- AUTO-INDEX -->` sentinel
- **AC-1.3**: 根目录 `roadmap.md` 仍存在但内容是 1 段 stub 指针
- **AC-1.4**: ADR-0016 schema v2 落地，`.arch-handoff.json` 含 `roadmap_fragments_dir` 字段
- **AC-1.5**: `roadmap_state.py` 至少新增 6 个函数：`load_fragments`, `get_fragment`, `list_active_fragments`, `render_fragment_index`, `validate_fragment_refs`, `aggregate_phase_progress`
- **AC-1.6**: `Fragment` dataclass 包含至少 8 个字段（id, kind, status, phase_refs, theme, file_path, frontmatter, body）
- **AC-1.7**: `roadmap migrate` 子命令支持 `--dry-run` / `--execute` / `--rollback` / `--backup-dir` / `--yes` 参数
- **AC-1.8**: `roadmap migrate --dry-run` 输出可读的切片预览，不修改任何文件
- **AC-1.9**: `roadmap migrate --execute` 在自家项目（本仓库）成功完成迁移，所有现有 test 仍 pass
- **AC-1.10**: `roadmap migrate --rollback` 从 backup 完整恢复原状态

#### 兼容性验收

- **AC-1.11**: `_lib/roadmap_state.py` 现有 6 个函数签名零变化（git diff 无 `def <name>(` 修改）
- **AC-1.12**: 现有 6 个 consumer（propose, add-improve, 3 个 tests, phase2_path_migrator）零改动
- **AC-1.13**: ADR-0016 v1 handoff 仍被 v2 code 接受（视为无 fragments）
- **AC-1.14**: `npm test` + `./test.sh --quick` + `./test.sh --python` 三个测试入口全部仍绿

#### 测试验收

- **AC-1.15**: ≥ 15 个 unit tests 覆盖新增 API（Fragment dataclass, 6 函数），每个函数 ≥ 2 个 case
- **AC-1.16**: ≥ 5 个 bats integration tests 覆盖 `roadmap migrate` 9 步流程（dry-run / execute / rollback / 失败恢复 / 备份保留）
- **AC-1.17**: ≥ 2 个 bats integration tests 覆盖 discover-arch-artifacts.sh 新增 `roadmap_fragments_dir` env var

### Change 2（校验 + 门控）—— `hierarchical-roadmap-validation`

#### 功能验收

- **AC-2.1**: `validate_fragment_refs` 实现 8 条规则（R1-R8），每条 ≥ 1 个 unit test
- **AC-2.2**: `roadmap validate-fragments` 子命令存在，exit code 0/1/2/3 对齐 openspec validate
- **AC-2.3**: `rdd-doctor --category roadmap-refs` 新增 category，仅报告不修复
- **AC-2.4**: `guide-plan` plan-done gate 集成 `validate_fragment_refs`，默认 WARNING level 不阻断
- **AC-2.5**: `STRICT_ROADMAP_REFS_GATE=yes` 升级 WARNING → CRITICAL 阻断 plan-done
- **AC-2.6**: `SKIP_ROADMAP_REFS_GATE=yes` 跳过校验 + 输出 "gate skipped" warning

#### 测试验收

- **AC-2.7**: ≥ 10 个 unit tests 锁定 8 条规则判定边界（含正常 + 异常 case）
- **AC-2.8**: ≥ 3 个 bats integration tests 覆盖 `roadmap validate-fragments` + `rdd-doctor roadmap-refs` 双入口
- **AC-2.9**: ≥ 1 个 bats integration test 覆盖 plan-done gate STRICT 阻断（模拟 R1 违反）
- **AC-2.10**: ≥ 1 个 bats integration test 覆盖 doctor 只读原则（运行后无任何 tracked/gitignored 文件修改）

### 依赖与治理

- **AC-3.1**: Change 2 显式声明依赖 Change 1（plan 阶段必须先 ship Change 1）
- **AC-3.2**: Change 1 自家仓库执行迁移后产出 1+ commit（tracked `.rddf/roadmap*`）
- **AC-3.3**: 提案批准后从 `proposal-suggestions.md` 移除（由 `sync_suggestions()` 自动）
- **AC-3.4**: `skills/roadmap/SKILL.md` 新增 `migrate` / `validate-fragments` 子命令章节
- **AC-3.5**: `openspec/specs/roadmap-hierarchy/spec.md` 新增（与 roadmap-proposal-guidance spec 并列）

### 升级路径

- **AC-4.1**: 旧项目（v1 handoff + 根 `roadmap.md`）升级到 v2.2 后仍正常工作（场景 9）
- **AC-4.2**: 旧项目运行 `roadmap migrate` 升级到层次化结构可选，不强制
- **AC-4.3**: v2.4 deprecate 根目录 `roadmap.md` 默认 fallback（仍兜底但发 warning）；v2.5 移除（在本提案范围之外，但写在 ADR-0016 v2 deprecation note）