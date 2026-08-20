# roadmap-hierarchy Specification

## Purpose
TBD - created by archiving change add-hierarchical-roadmap-structure. Update Purpose after archive.
## Requirements
### Requirement: 主 roadmap 文档位于 `.rddf/roadmap.md`

roadmap 主文档 SHALL 位于 `.rddf/roadmap.md`（git tracked），不再是项目根 `roadmap.md`。

#### Scenario: 新项目初始化
- **WHEN** 用户运行 `skill_use("roadmap init")` 在空项目
- **THEN** 在 `.rddf/roadmap.md` 创建主文档（不是项目根）
- **AND** 主文档含 phase 骨架表 + 任务分类表（5 列含主题）

#### Scenario: 旧项目升级
- **WHEN** 用户运行 `rddf roadmap migrate --execute`
- **THEN** 备份原根 `roadmap.md` 到 `.rddf/.roadmap-migrate-backup-<timestamp>/`
- **AND** 创建 `.rddf/roadmap.md` 含 phase 骨架 + 主题表
- **AND** 改写根 `roadmap.md` 为 stub 指针（1 段）

### Requirement: Fragment 文档通过 kind 区分 phase 与 feature

`.rddf/roadmap/{phases,features}/<id>.md` fragment frontmatter `kind` 字段 SHALL 取值为 `phase` 或 `feature`，定义文档语义。

#### Scenario: Phase fragment 创建
- **WHEN** 用户创建 `.rddf/roadmap/phases/phase-3.md`，frontmatter `kind: phase`
- **THEN** `list_active_fragments(.rddf/roadmap, kind="phase")` 返回该 fragment
- **AND** 主文档 `<!-- AUTO-INDEX -->` 渲染时归入"phases"分组

#### Scenario: Feature fragment 创建
- **WHEN** 用户创建 `.rddf/roadmap/features/auth-v2.md`，frontmatter `kind: feature`
- **AND** frontmatter `phase_refs: [phase-2, phase-3, phase-4]`
- **THEN** 主文档 `<!-- AUTO-INDEX -->` 渲染时归入"features"分组
- **AND** `validate_fragment_refs` 校验 `phase_refs` 引用主文档已注册 phase

### Requirement: Fragment ID 引用制（无 free-text）

Fragment frontmatter `phase_refs` 数组中每个 ID MUST 存在于主文档 phase 表。`phase_refs` 中**禁止**使用 free-text phase 名称（如 "Phase 3: GPU"），只许使用 `phase-N(.M)?` 形式 ID。

#### Scenario: 合法引用通过校验
- **WHEN** feature fragment `phase_refs: [phase-3, phase-4]` 且主文档已注册 phase-3/4
- **THEN** `validate_fragment_refs` 不报错
- **AND** `list_active_fragments` 返回该 fragment

#### Scenario: 引用未注册 phase 触发 WARNING
- **WHEN** feature fragment `phase_refs: [phase-99]` 但主文档 phase-99 不存在
- **THEN** `validate_fragment_refs` 返回 WARNING（R1 规则）
- **AND** `STRICT_ROADMAP_REFS_GATE=yes` 升级为 CRITICAL 阻断 plan-done

### Requirement: Fragment 不嵌套

`.rddf/roadmap/phases/` 下 MUST **禁止**层级子目录（如 `phase-3/phase-3.1.md`）。sub-phase 表达 MUST 靠独立 fragment + `phase_refs` 归属，不靠文件系统层级。

#### Scenario: 禁止嵌套检测
- **WHEN** 用户创建 `.rddf/roadmap/phases/phase-3/phase-3.1.md`
- **THEN** `validate_fragment_refs` 返回 CRITICAL（R9 规则：fragment 不嵌套）
- **AND** 错误信息明确指示"独立 fragment + phase_refs 表达"

### Requirement: Fragment 永不删除，仅归档

Fragment 完成生命周期 SHALL 走路径：`active → done → archived`。MUST NOT `git rm` 或 `rm` fragment 文件；完成即移动到 `archive/` 目录。

#### Scenario: 主动归档
- **WHEN** 用户运行 `skill_use("roadmap archive-fragment phase-3")`
- **THEN** `.rddf/roadmap/phases/phase-3.md` 移动到 `.rddf/roadmap/archive/`
- **AND** frontmatter `status: archived`
- **AND** 主文档 `<!-- AUTO-INDEX -->` 重新渲染时不再列出该 fragment

#### Scenario: phase advance 自动归档
- **WHEN** 用户运行 `skill_use("roadmap advance")` 且 phase-3 完成
- **THEN** 所有归属 phase-3 的 fragment 自动调用 `archive-fragment`
- **AND** iteration.json 同步更新（已实现 `mark_iteration_archived`）

### Requirement: ADR-0016 schema v2 新增 roadmap_fragments_dir

`.rddf/state/.arch-handoff.json` v2 schema SHALL 含 `roadmap_fragments_dir: string` 字段，指向含 `phases/`、`features/`、`archive/` 三子目录的目录。

#### Scenario: v2 handoff 接受
- **WHEN** `.arch-handoff.json` 含 `roadmap_fragments_dir: ".rddf/roadmap"` + `version: "2"`
- **THEN** `roadmap_state.py::load_fragments(<dir>)` 聚合读取该目录
- **AND** consumer（propose, add-improve）兼容接受

#### Scenario: v1 handoff 兼容（视为无 fragments）
- **WHEN** `.arch-handoff.json` 是 v1 schema，无 `roadmap_fragments_dir` 字段
- **THEN** `load_fragments(<dir>)` 返回空列表（fallback 行为）
- **AND** 所有现有 consumer（6 个）行为不变
- **AND** `roadmap migrate` 可随时运行升级

### Requirement: roadmap_state.py additive API

`_lib/roadmap_state.py` SHALL 新增 6 个函数 + `Fragment` dataclass，**不修改**任何现有函数签名。

#### Scenario: Fragment dataclass 字段
- **WHEN** `load_fragments` 读取 `.rddf/roadmap/phases/phase-3.md`
- **THEN** 返回 `Fragment(id="phase-3", kind="phase", status="active", phase_refs=[], theme=["..."], file_path=Path(...), frontmatter={...}, body="...")`

#### Scenario: validate_fragment_refs 返回 ValidationError 列表
- **WHEN** 调用 `validate_fragment_refs(roadmap_file, fragments_dir)`
- **THEN** 返回 `List[ValidationError]` 含每条违规的 (rule_id, severity, fragment_id, message)
- **AND** `roadmap validate-fragments` 消费该输出 + 对齐 openspec validate exit code（0/1/2/3）

#### Scenario: 现有 6 个函数签名不变
- **WHEN** 检查 `_lib/roadmap_state.py` git diff
- **THEN** `def get_phase_themes(` / `def get_phase_categories(` / `def advance_phase(` / `def add_phase(` / `def render_status_view(` / `def validate_change(` 签名零变化

### Requirement: roadmap migrate 子命令 9 步原子化

`roadmap migrate` 子命令 SHALL 按 9 步流程执行，每步可独立验证，**任何写入失败保留 backup + 删除部分写入 + exit 非零**。

#### Scenario: dry-run 不写文件
- **WHEN** 用户运行 `rddf roadmap migrate --dry-run`
- **THEN** 终端输出主文档瘦身 diff + 每个 fragment 预览 + archive 路径
- **AND** 不修改任何文件
- **AND** 等待用户确认

#### Scenario: execute 完成迁移
- **WHEN** 用户运行 `rddf roadmap migrate --execute --yes`
- **THEN** backup 原 roadmap.md + git tag `pre-roadmap-migrate-<timestamp>`
- **AND** 创建 `.rddf/roadmap/{phases,features,archive}/`
- **AND** 写入 `.rddf/roadmap.md` + 各 fragment + 根 stub
- **AND** 更新 `.arch-handoff.json` 到 v2
- **AND** 跑 post-migration `validate_fragment_refs`，输出报告（不阻塞）

#### Scenario: rollback 恢复原状态
- **WHEN** 用户运行 `rddf roadmap migrate --rollback <backup-dir>`
- **THEN** 从 backup 恢复原根 `roadmap.md`
- **AND** 删除 `.rddf/roadmap*` 新建内容
- **AND** `.arch-handoff.json` 复位到 v1（如果迁移前是 v1）

### Requirement: 双入口校验（roadmap validate + rdd-doctor）

一致性校验 SHALL 同时通过两个入口暴露，**共享**同一份实现（`validate_fragment_refs`）。

#### Scenario: roadmap validate-fragments 门控
- **WHEN** 用户运行 `skill_use("roadmap validate-fragments")`
- **THEN** 调用 `validate_fragment_refs`，按 R1-R8 规则检查
- **AND** 默认 WARNING level 不阻断（exit 0）
- **AND** `STRICT_ROADMAP_REFS_GATE=yes` 升级为 CRITICAL（exit 1）

#### Scenario: rdd-doctor --category roadmap-refs 诊断
- **WHEN** 用户运行 `bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-refs`
- **THEN** 调用同一 `validate_fragment_refs` 函数
- **AND** 输出分级报告（CRITICAL/WARNING/INFO）
- **AND** doctor **不修复**任何文件（保持只读原则）
- **AND** doctor exit code = 1 当有 CRITICAL（对齐 openspec validate）

### Requirement: plan-done gate 集成 fragment 校验

`guide-plan` plan-done 流程 SHALL 调用 `validate_fragment_refs`，**默认** WARNING level 不阻断。

#### Scenario: 默认行为（warning only）
- **WHEN** plan-done 调用 validate_fragment_refs，有 N 条 WARNING
- **THEN** plan-done gate 输出 warning 列表但通过（exit 0）
- **AND** 写入 `.plan-handoff.json` v2 含 warnings 字段

#### Scenario: STRICT 模式阻断
- **WHEN** `STRICT_ROADMAP_REFS_GATE=yes` 且有 CRITICAL
- **THEN** plan-done gate 阻断（exit 1）
- **AND** 输出未通过规则列表 + 建议修复命令

#### Scenario: SKIP 临时绕过
- **WHEN** `SKIP_ROADMAP_REFS_GATE=yes`
- **THEN** plan-done 跳过校验（exit 0）
- **AND** 输出 "gate skipped" warning

### Requirement: 主题状态词汇不参与 fragment 校验

Fragment frontmatter `主题:` 字段 SHALL 仅作元信息展示，MUST NOT 参与 `compute_theme_coverage` 计算。主题三态（未覆盖/已覆盖/~skipped~）仍由主文档 5 列表驱动。

#### Scenario: fragment 主题不计入覆盖率
- **WHEN** fragment frontmatter `主题: "RBAC权限模型"` 但主文档任务分类表无此主题
- **THEN** `compute_theme_coverage` 不计入该 fragment 主题
- **AND** `validate_fragment_refs` 不因主题不匹配报错
- **AND** fragment 主题仅在主文档 `--render` 时作为 metadata 显示

### Requirement: Frontmatter 复用 improvements 方言

Fragment frontmatter SHALL 复用 `.rddf/improvements/*.md` 的元数据方言：`id` / `kind` / `status` / `phase_refs` / `主题` / `优先级` / `更新日期` / `owner`。

#### Scenario: 字段映射一致
- **WHEN** 解析 fragment frontmatter
- **THEN** `id` / `kind` / `status` 必填且类型对齐 improvements
- **AND** `主题` 字段在两种文档类型中语义对齐（roadmap 主题名）

