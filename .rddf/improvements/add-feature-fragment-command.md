# add-feature-fragment-command

**优先级**: P1 | **来源**: user request (add-feature 选项) + 2 轮 Oracle 评审 (bg_03696e35, bg_b16179e9) + add-hierarchical-roadmap-structure 场景 3 补全
**阶段**: v2.2 规划中 | **分类**: arch-design
**类型**: feat
**主题**: 不适用（roadmap 操作原语补全，非 roadmap 主题机制）

> **完整设计文档**：`docs/superpowers/specs/2026-08-25-add-feature-fragment-command-design.md` (13 章节, 417 行)
> **本文件为 5 段式 improvements 提案**，用于 `guide-design` 流程的 4 维 Oracle 审查（ADR-0025 §D4 第一层）。
>
> **范围定位**：本提案聚焦**单一操作原语 `rddf roadmap add-feature`**——消掉手工写 YAML 的操作缺口。**不实现** archive/edit/delete CLI、**不重构** `add_phase` 扁平模型、**不绑定** openspec change（详见 spec §13 后续工作）。

## 架构依据

### 动机

`add-hierarchical-roadmap-structure` 提案（已实施 2026-08-20）创建了 fragment 模型基础设施：

- `.rddf/roadmap/{phases,features,archive}/` 三层目录（全 tracked）
- `.rddf/roadmap.md` 主文档含 `<!-- AUTO-INDEX -->` sentinel
- `Fragment` dataclass + 6 个 additive API（`load_fragments` / `get_fragment` / `list_active_fragments` / `render_fragment_index` / `validate_fragment_refs` / `aggregate_phase_progress`）

该提案的"关键场景 3"已显式描述手工创建 feature fragment 的 frontmatter 形态（`id: feat-<name>` + `kind: feature` + `phase_refs: [...]` + `主题: ...`），**但未提供操作入口**。

**痛点**：当前用户必须 `cat > .rddf/roadmap/features/auth-v2.md` 后手填 YAML + 手动调 `render_fragment_index`。本仓库 `.rddf/roadmap/features/` 目录因此为空，hierarchical roadmap 模型实际未被使用。

### Oracle 6 维度发现

| 维度 | 关键发现 |
|---|---|
| 位置选择 | 候选 A（新 Phase 4.5）实际**破坏**状态机（grep 契约失效、heartbeat 多一跳）；候选 B（Phase 4 子选项）才真正"不破坏" |
| CLI vs 菜单 | `_lib/cli/roadmap_cmd.py::_SUBCOMMAND_MAP` 现有 2 个 entry 全是 `.sh`，保持一致；菜单只是入口之一 |
| 与 openspec change 关系 | N:N 绑定天然跨阶段演化，arch 阶段信息不足；留给 design/plan 在 `roadmap-meta.yaml` 加 `feature_ref` 字段 |
| 与 `feature.md` view skill 关系 | 两套 source of truth（markdown 声明层 + iteration.json 运行层）不要统一 schema；单向派生增强推到后续 |
| 双门控扩展 | arch-done 现有 `ADR≥1 + roadmap.md` 不扩展（features/ 空目录是合法新项目状态） |
| ADR 必要性 | 不新立；架构决策已继承自 `add-hierarchical-roadmap-structure`，只需 ADR-0028 patch |

### 设计决策（已批准）

| 决策点 | 选择 |
|---|---|
| 入口位置 | guide-arch Phase 4 子选项 + `rddf roadmap add-feature` CLI（候选 B+E） |
| 操作原语层 | `_lib/roadmap_state.py::add_feature`（Python core），薄 shell wrapper 在 `skills/roadmap/scripts/roadmap_add_feature.sh` |
| Body 内容 | MVP 只生成 3 段骨架（概述/跨阶段拆分/验收标准），内容后续编辑 |
| Frontmatter 校验 | `phase_refs` 用 `list_active_fragments(kind="phase")` 单一读取路径，不重扫目录 |
| 原子性 | 先 fragment 后 render；render 失败时补偿式删除 fragment |
| `--force` 语义 | 完全重生成（不 merge 用户编辑 body）；无 `--force` 重名 → exit 1 |
| 双门控 | 不扩展 arch-done（features/ 空目录合法） |
| ADR-0028 patch | frontmatter `owns` 追加 `.rddf/roadmap/features/*.md`（1 行） |
| add_phase 债务 | 本次不动；后续 `add-improve` 立项"重构 add_phase 为 Fragment 模型"（潜在 ADR-0034） |

## 范围

### In Scope

- `rddf roadmap add-feature <name> --phase-refs <...> --theme "..." [--status] [--force]` CLI
- `_lib/roadmap_state.py::add_feature` Python 实现（与 Fragment 模型对齐，**不 mirror** `add_phase` 扁平模型）
- 薄 shell wrapper `skills/roadmap/scripts/roadmap_add_feature.sh`（env-var 传递，遵循 Oracle C1）
- `_lib/cli/roadmap_cmd.py` `_SUBCOMMAND_MAP` 扩展 + `_help_text()` 更新
- `skills/guide-arch/SKILL.md` Phase 4 菜单新增 "添加 feature fragment" 选项 + 4 步强制交互序列
- `skills/roadmap/SKILL.md` 登记 add-feature 子命令段
- ADR-0028 frontmatter patch（1 行 `owns` 扩展）
- 11 个测试（7 unit + 4 bats）

### Out of Scope（详见 spec §13）

- `rddf roadmap edit-feature` / `archive-feature` / `delete-feature` 子命令（后续独立 change）
- `feature.md` skill view 增强（read fragment theme/phase_refs enrichment）
- `feature_ref` 字段加到 `roadmap-meta.yaml`（change ↔ fragment 绑定）
- `add_phase` 重构为 Fragment 模型（潜在 ADR-0034，独立提案）
- Hierarchical feature 嵌套（`features/auth-v2/sso.md` 禁止）
- 修改 `iteration.json` / `deps-analysis.json` schema
- 任何 `openspec/specs/*.md` 内容修改

## 关键场景

### 场景 1: arch 阶段用户创建新 feature

**GIVEN** arch-done 已完成，`.rddf/roadmap.md` 存在，`phases/phase-2.md` + `phases/phase-3.md` 已有
**WHEN** arch 阶段用户在 Phase 4 菜单选 "添加 feature fragment"，输入 `auth-v2` / `RBAC 权限模型` / 勾选 phase-2+phase-3，确认 preview
**THEN**
- 创建 `.rddf/roadmap/features/feat-auth-v2.md`（frontmatter + 3 段骨架）
- `.rddf/roadmap.md` AUTO-INDEX 块新增 Features 区块 + `feat-auth-v2` 条目
- 用户可在文件编辑器中填充 `## 概述` / `## 验收标准` 内容

### 场景 2: 非 arch 场景复用 CLI 原语

**GIVEN** 用户在 guide-design 阶段需要回补一个 feature fragment
**WHEN** 用户运行 `rddf roadmap add-feature cross-repo-sync --phase-refs phase-3,phase-4 --theme "..."`
**THEN** 同样产出 fragment + AUTO-INDEX 刷新（不依赖 guide-arch 状态机）

### 场景 3: 重复创建拒绝

**GIVEN** `feat-auth-v2.md` 已存在
**WHEN** 用户运行 `rddf roadmap add-feature auth-v2 --phase-refs phase-2 ...` 无 `--force`
**THEN** exit 1, stderr "feat-auth-v2.md 已存在，使用 --force 覆盖"，不写入任何文件

### 场景 4: phase_refs 校验失败

**GIVEN** 用户传入 `--phase-refs phase-2,phase-99`，phase-99 不在 `list_active_fragments(kind="phase")` 中
**WHEN** 调用 add-feature
**THEN** exit 1, stderr 列出无效 phase id，不写入 fragment

### 场景 5: render_fragment_index 失败的补偿回滚

**GIVEN**（mock）`render_fragment_index` 抛异常
**WHEN** 调用 add-feature（fragment 写入已成功）
**THEN** fragment 文件被补偿删除；exit 1；stderr "compensation: fragment removed, retry or report issue"

### 场景 6: 幂等性

**GIVEN** 完整 add-feature 调用成功
**WHEN** 用相同参数再调用一次
**THEN** 主文档 AUTO-INDEX 块 byte-equal（`render_fragment_index` 已声明幂等，测试锁定）

### 场景 7: 紧急跳过路径

**GIVEN** 用户在 hotfix 中需要创建 feature 但缺 rddf CLI
**WHEN** 用户手工 `cat > .rddf/roadmap/features/<name>.md` 后不调 render_fragment_index
**THEN** 主文档 AUTO-INDEX 不更新；下次 `guide-plan` intake 读取时会调用 `load_fragments` 但不重渲染（fragment 不会被自动加入 AUTO-INDEX）。这是**已知行为**：CLI 是显式入口；手工路径需要用户自负责任

## 技术约束

- **Shell wrapper 必须 env-var 传递**（Oracle C1 安全规范）——禁止 `python3 -c "...$VAR..."` 内联 bash 字符串插值
- **`load_fragments` 必须容错 `features/` 子目录缺失**（已实现，spec §7.1 测试 #7 锁定回归）
- **不修改** `_lib/roadmap_state.py` 现有 6 个 Fragment API 函数签名
- **不修改** `.arch-handoff.json` schema（v1 保持向后兼容）
- **不引入新状态字段**（仅新增可选 view file）
- **不破坏** 现有 140 个 arch/ADR 测试

## 验收标准

实施完成判定（spec §12 展开版）：

- [ ] `rddf roadmap add-feature <name> --phase-refs ... --theme ...` 创建 fragment 含合法 frontmatter
- [ ] `.rddf/roadmap.md` AUTO-INDEX 块新增 Features 条目
- [ ] 无效 `--phase-refs` → exit 1，无文件写入
- [ ] 同参数两次调用 → 主文档 byte-equal 幂等
- [ ] `--force` 完全重生成（不 merge body）
- [ ] render 失败 → fragment 补偿删除
- [ ] `guide-arch` Phase 4 菜单显示 "添加 feature" 选项 + 4 步流程
- [ ] `rddf roadmap --help` 列出 `add-feature`
- [ ] 11 个测试全过（`./test.sh --python` + `bats tests/integration/test_roadmap_add_feature.bats`）
- [ ] ADR-0028 frontmatter 含 `.rddf/roadmap/features/*.md`
- [ ] 无回归（现有 140 测试不变）

## 参考

- 完整 spec：`docs/superpowers/specs/2026-08-25-add-feature-fragment-command-design.md` (417 行, 13 章)
- 父提案：`.rddf/improvements/add-hierarchical-roadmap-structure.md` (已实施 2026-08-20)
- ADRs：0003（三阶段）/ 0016（arch discovery）/ 0025（design proposal）/ 0028（role model）
- Oracle 评审：bg_03696e35（位置 + 内容模型）/ bg_b16179e9（完整 8-section 设计）
- 相关代码：`_lib/roadmap_state.py::Fragment` + 6 个 additive API；`_lib/cli/roadmap_cmd.py::_SUBCOMMAND_MAP`
