## Context

### 当前状态

rdd-workflow v2.1 提供四阶段架构 (arch → design → plan → ship),其中:
- `guide-arch` Phase 4 (roadmap-define) 通过 `roadmap` skill 定义项目路线图 (phase/category 树)
- `guide-design` Phase 2 提供 `add-improve` → `rdd-workflow-brainstorm` 流程创建改进提案
- 两阶段之间**无结构化连接** — roadmap 节点不携带"预期改进主题"元数据,提案创建完全依赖用户心智映射

### 关键约束 (Oracle 审查确认)

- ADR-0016 (arch-handoff discovery contract v1) — guide-design 已从 `.arch-handoff.json` 拿到 `roadmap_path`,可 consume-time 直接解析
- ADR-0017 (rddf-session) — 不破坏现有 session 生命周期
- Oracle C1 安全: env-var 模式传参 (3 文件 split),禁止 `python3 -c "...$VAR..."`
- Oracle C2 关键决策: **不修改 arch-handoff schema** (v1 不动),避免 rdd-doctor CRITICAL finding
- HARD-GATE (brainstorm) — 约束模式仍强制 Step 4 逐段用户确认,严禁绕过

### 关键利益相关方

- **架构师**: 通过 roadmap 表达改进意图时希望结构化、可计算覆盖
- **设计者**: 进入 guide-design 时希望立即看到 roadmap gap
- **AI agent**: 自动从 roadmap 推导待办提案时希望减少 prompt token

## Goals / Non-Goals

### Goals

1. roadmap 节点 (category) 携带预期改进主题元数据,精确声明该节点意图覆盖哪些改进方向
2. guide-design Phase 1 自动解析 roadmap.md,展示覆盖率 + 未覆盖主题清单 (含 `~skipped~` 豁免)
3. `add-improve` 新增 `--from-roadmap` 模式,brainstorm 进入约束模式预填 5 段 scaffold
4. **保持** HARD-GATE 不被绕过,用户决策权 100% 保留
5. **保持** 向后兼容 — 旧 4 列 roadmap / 旧 v1 handoff / 无主题字段 proposal 全部不报错
6. **不引入** 自动批准机制 (Oracle Q4 警告)

### Non-Goals

- 不修改 `.arch-handoff.json` schema (v1 不动,Oracle 关键决策)
- 不修改 `openspec/changes/` 模板 (proposal-level 字段不污染 OpenSpec)
- 不在 proposal-level 强制主题字段 (可空,向后兼容)
- 不自动 derive rationale 写入 roadmap (rationale 在 brainstorm 阶段 AI 起草)
- 不引入 `DESIGN_PROPOSAL_AUTO_ACCEPT` 类 env var
- 不修改 rdd-doctor 校验逻辑 (coverage 显示在 guide-design preflight,doctor 仍专注 schema/roadmap-meta)

## Decisions

### D1: 直接 consume-time 解析 roadmap.md,不复制到 handoff

**决策**: guide-design Phase 1 preflight 在运行时直接解析 `roadmap.md`,而非在 `.arch-handoff.json` 缓存 themes。

**理由**:
- 避免 schema bump 触发 rdd-doctor CRITICAL (Oracle C2)
- 避免 staleness — roadmap edit 后 handoff 自动反映 (Oracle C3)
- ADR-0016 已通过 v1 handoff 携带 `roadmap_path`,无需新字段

**替代方案** (rejected):
- ❌ handoff v2 + `proposal_guidance` 字段 — 触发 schema bump,staleness 需额外 check
- ❌ 独立 `roadmap-proposals.yaml` 文件 — 第二 source of truth,违反 single-source-of-truth

### D2: env-var 模式传参,3 文件 split

**决策**: `--from-roadmap`, `--theme`, `--rationale` 全部经 `os.environ`,遵循 AGENTS.md Round A/B Oracle C1 修复模式。文件 split 模式:
- `add-improve/scripts/from_roadmap.sh` — bash 入口 + env-var 暴露
- `add-improve/scripts/from_roadmap.py` — Python 主逻辑
- `add-improve/scripts/from_roadmap.env.py` — env-var 接收 + 校验

**理由**:
- 避免 bash string interpolation 注入 (AGENTS.md 历史教训)
- 与 `write_arch_handoff_env.py` 等现有模式一致
- env-var 名 `ADD_IMPROVE_FROM_ROADMAP` / `ADD_IMPROVE_THEME` / `BRAINSTORM_RATIONALE_DRAFT` 大写蛇形,用 `unset` 清理避免污染 shell

**替代方案** (rejected):
- ❌ CLI 参数直接传 bash 字符串 — 重蹈 Oracle C1 漏洞
- ❌ 临时文件传递 — 增加 IO 开销和复杂度

### D3: 主题状态词汇 `未覆盖 / 已覆盖 / ~skipped~`

**决策**: 主题三态明确,`~skipped~` 是显式豁免标记。

**理由**:
- "已覆盖" 通过 `**主题**:` 字段精确字符串匹配计算
- "~skipped~" 排除出覆盖率分母,允许 roadmap 与现实脱节时优雅退出
- 与 markdown TODO 习惯的 `~skip~` 标记一致,降低学习成本

**替代方案** (rejected):
- ❌ 仅 `已覆盖 / 未覆盖` 二态 — 无法处理"已知不需要"的情况
- ❌ 用 `status:` 字段在 proposal 内 — 分散状态,难统一管理

### D4: HARD-GATE 完整性保留

**决策**: 约束模式下 brainstorm Step 4 仍强制 5 段逐段用户确认,仅预填 scaffold 不自动批准。

**理由**:
- brainstorm HARD-GATE 是用户决策权保障 (rdd-workflow-brainstorm/SKILL.md:28-30)
- 自动批准会绕过用户对范围/场景/约束的判断,与 v2.1 设计哲学冲突
- Oracle Q4 明确警告严禁引入 `DESIGN_PROPOSAL_AUTO_ACCEPT`

**替代方案** (rejected):
- ❌ 全自动生成 proposal 文件 — 违反 hard-gate
- ❌ 约束模式下减少确认步骤 — 削弱决策权

### D5: 不修改 openspec/changes/ 模板

**决策**: `**主题**:` 字段仅在 `.rddf/improvements/<name>.md` proposal front matter,不入 `openspec/changes/<name>/proposal.md`。

**理由**:
- 关注点分离 — rdd-workflow 内部元数据 vs OpenSpec artifacts 模板
- OpenSpec 模板是上游依赖,修改会影响其他项目
- proposal-level 字段足够 guide-design 内部消费

### D6: 解析器向后兼容 4 列 / 5 列

**决策**: `roadmap_state.py::get_phase_themes()` 检测表格列数,4 列返回空列表 (无约束),5 列解析第 5 列。

**理由**:
- 旧项目升级零成本
- 混合表格兼容 (部分 phase 4 列,部分 phase 5 列)
- regex `\|\s*([^\s|]+)\s*\|\s*([^|]+?)\s*\|` 已验证容忍额外列 (`roadmap_state.py:249/466`)

### D7: 覆盖率算法 — 精确字符串匹配

**决策**: theme → proposal 的 `**主题**:` 字段严格相等,不做 fuzzy。

**理由**:
- 主题是用户声明的精确语义,fuzzy 匹配会产生误判
- 跨 category 同名 theme 独立计数 (避免合并冲突)
- 用户可手动调整 proposal 主题字段

**替代方案** (rejected):
- ❌ fuzzy 字符串匹配 — 误判不可避免
- ❌ 主题 ID 化 (UUID) — 增加用户填写负担

## Risks / Trade-offs

### R1: 旧 proposal 无主题字段 → 假警 → **缓解**: coverage 显示"未标注主题 K 个"独立统计,排除出分母。**backfill 工具可选** (`rddf improvements backfill-themes --interactive`)。

### R2: 跨 phase/category 同名 theme 误合并 → **缓解**: 主题 key 为 `phase/category/theme` 三元组,严格匹配按三元组。proposal `**主题**:` 字段可只写 theme 名,但 coverage 计算按 `(phase, category, theme)` 三元组比较。

### R3: roadmap cell 语法过重 → **缓解**: 单元格仅 `主题1；主题2` 分号分隔,`get_phase_themes()` 容忍空 cell / 空白 / 多分号。**rationale 移到 brainstorm AI 起草**,roadmap 保持简洁。

### R4: guide-design preflight 解析 roadmap 增加延迟 → **缓解**: roadmap.md ≤ 100 行,正则解析 < 10ms。整体 preflight 延迟 +50ms 内,用户可接受。

### R5: add-improve `--from-roadmap` 模式破坏现有测试 → **缓解**: 模式是 opt-in,默认 free-form 行为不变。现有 bats 测试零回归。**新增** `tests/integration/test_add_improve_from_roadmap.bats` 覆盖新模式。

### R6: brainstorm env-var 注入风险 → **缓解**: env-var 命名规范 + `unset` 清理 + 输入校验 (theme 名禁止 `$`, 反引号等)。**新增** `tests/unit/test_from_roadmap_env_validation.py` 覆盖恶意输入。

### R7: rdd-doctor 检查 vs 新字段兼容性 → **缓解**: doctor 检查 schema / roadmap-meta / tasks checkbox,不涉及 improvements 文件。**新增** `--coverage-report` 子命令扩展 doctor 可选视图 (out of scope, 留作 future work)。

### R8: STRICT_PROPOSAL_COVERAGE 误触发 → **缓解**: 默认 warning,`SKIP_PROPOSAL_COVERAGE=yes` 临时绕过,`~skipped~` 显式豁免。文档化在 `guide-design/SKILL.md` Phase 4 章节。

## Migration Plan

### 阶段 1 — 内部扩展 (1-2 天)

1. 修改 `roadmap_state.py::add_phase()` 模板,加 5 列
2. 新增 `roadmap_state.py::get_phase_themes()` 函数
3. 修改 `rdd-workflow-brainstorm/SKILL.md` 5 段模板加 `**主题**:` 字段
4. 现有用户升级零感知 — 旧 4 列表格保持工作

### 阶段 2 — consume-time 解析 (3-4 天)

5. `guide-design/scripts/design_preflight.sh` 新增 theme 解析 + coverage 计算
6. `guide-design/SKILL.md` Phase 1 章节更新显示逻辑
7. 新增 unit test: `tests/unit/test_guide_design_preflight_themes.py`

### 阶段 3 — 约束注入 (5-7 天)

8. `add-improve/scripts/from_roadmap.{sh,py,env.py}` 3 文件 split
9. `rdd-workflow-brainstorm/SKILL.md` 文档化新 env-var 契约 + 约束模式分支
10. `guide-design/SKILL.md` Phase 2 菜单新增选项 2
11. 新增 bats: `test_roadmap_5col_parsing.bats`, `test_add_improve_from_roadmap.bats`

### 阶段 4 — 门控扩展 (按需)

12. `guide-design/scripts/design_proposal_review.sh` Phase 4 加 `STRICT_PROPOSAL_COVERAGE` 分支
13. CHANGELOG / AGENTS.md 关键约定更新
14. **回归测试**: `./test.sh --full --regression` 全绿

### Rollback 策略

- 所有改动是**增量**,无破坏性 schema 变更
- 任意中间版本可回滚 `git revert` 不影响现有用户
- `STRICT_PROPOSAL_COVERAGE=yes` 默认 OFF,即使 ship 也不影响现有 CI

## Open Questions

1. **proposal-suggestions.md 第 6 列"主题"是否默认启用?**
   - 选项 A: 启用 (统一索引) — 增加 front matter 复杂度
   - 选项 B: 不启用 (向后兼容最佳) — 覆盖率仅依赖 `improvements/<name>.md` 解析
   - **倾向 B**,待 design-done 时决策

2. **backfill 工具是否本期交付?**
   - 选项 A: 本期 (帮助旧项目升级) — 增加 scope
   - 选项 B: 后续提案 (独立 backfill-themes) — 保持本提案聚焦
   - **倾向 B**,用户体验留作迭代

3. **coverage 显示在 rdd-doctor 还是 guide-design?**
   - 选项 A: guide-design preflight (本次设计) — 上下文内即时反馈
   - 选项 B: rdd-doctor `--coverage` 子命令 — 统一诊断视图
   - **倾向 A**,Oracle 建议 doctor 不动;后续可作 follow-up 扩展 doctor