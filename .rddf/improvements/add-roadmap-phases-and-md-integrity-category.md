---
优先级: P1
来源: "rdd-doctor 当前对 `.rddf/roadmap/phases/*.md` 和 `.rddf/roadmap.md` 主表/AUTO-INDEX 完整性零诊断覆盖（用户 2026-10-07 调研触发）"
阶段: v2.2
分类: feature
类型: feature
特性: rdd-doctor-roadmap-coverage
---
**优先级**: P1 | **来源**: 用户调研（"现在 rdd-doctor 可以诊断 roadmap 的所有问题了吗？"）后盘点出的覆盖空白
**阶段**: v2.2 | **分类**: feature | **类型**: feature
**特性**: rdd-doctor-roadmap-coverage

> **范围定位**: 给 rdd-doctor 新增 2 个独立 `--category`：`roadmap-phases`（诊断 `.rddf/roadmap/phases/*.md`）+ `roadmap-md-integrity`（诊断 `.rddf/roadmap.md` 主表与 AUTO-INDEX 整体结构）。仅扩展 read-only 诊断面，不写任何文件，不修改现有 18 个 category。
>
> **不重复**: 现有 `roadmap-feature` / `roadmap-refs` / `objective-*` 的功能保持不变——它们继续管各自领域；新 category 是补盲。
>
> **不破坏**: 现有 `--help` 输出 + 现有测试、AC、SKILL.md 表格全部保持有效；新 category 是 pure addition。

## 架构依据

### 动机（用户调研）

当前 `rdd-doctor` 对 `.rddf/roadmap/` 的诊断覆盖盘点（2026-10-07）：

| `.rddf/roadmap/` 工件 | 当前覆盖 | 缺口 |
|---|---|---|
| `features/*.md` | ✅ `roadmap-feature` (frontmatter / iteration.json / AGENTS.md sync) + `roadmap-refs` (R1-R8) | 无 |
| `objectives/*.md` | ✅ `objective-structure` + `objective-lifecycle` | 无 |
| `phases/*.md` | ❌ **无任何 category 读 phases/*.md** | 删 1 个 phase 文件无诊断；frontmatter 缺失无诊断 |
| `.rddf/roadmap.md` 主表 `## Phase Skeleton` | ⚠️ 部分（仅 R1/R6 经 `_extract_main_doc_phases` 间接扫） | 行 × 列 schema、AUTO-INDEX 三段（Phases/Features/Objectives）齐全性、ADR 链接有效性 全无诊断 |
| `.rddf/roadmap.md` AUTO-INDEX Phases 段 | ❌ 无 | 段缺失/多了/字段错乱无诊断 |
| `.rddf/roadmap.md` AUTO-SPRINT 段 | ❌ 无 | sprint 信息漂移无诊断 |

**用户痛点**：之前"features 完整性 = roadmap 完整性"的隐含假设是错的——roadmap 还有 phases 主干 + 主表 markdown 自身两块没诊断覆盖。

### 设计决策（已批准）

| 决策点 | 选择 |
|---|---|
| 范围 | 新建 2 个独立 category（已与用户确认）：`roadmap-phases` + `roadmap-md-integrity` |
| 优先级 | P1（影响 roadmap 完整性闭环，但不阻塞现有功能） |
| 实现深度 | 复用现有 `_lib.roadmap_state.load_fragments` + `_REQUIRED_FIELDS` 模式；新增 1 个 `_lib.roadmap_md_integrity.py` 模块集中解析 + 校验主表 |
| 兼容性 | 保留现有 18 个 category + argparse `--category` choices 自动扩展为 20 个；不破坏 SKILL.md sync 测试 |
| 文档一致性 | SKILL.md 类别表扩 18→20 + `test_rdd_doctor_skills_md_sync.bats` 测试自动锁住 |
| 测试策略 | TDD: 先加 `test_roadmap_phases.py` + `test_roadmap_md_integrity.py` 单测（红 → 绿）|

### 关于"roadmap-meta 是否扩成统一入口"的取舍（用户可能问）

`roadmap-meta` 当前扫 `openspec/changes/*/roadmap-meta.yaml`（手动声明的依赖），与 `.rddf/roadmap/` 下产物**正交**——前者是 change-side 元数据，后者是 project-side 实际产物。本提案**不**把 roadmap-meta 改名/扩面，因为它语义清晰、命名贴切。如下次评估发现"两套 roadmap 概念确实应统一"，再单独提案。

## 范围

**In Scope**:

**A. 新增 `roadmap-phases` category** (~150 LOC)

`skills/rdd-doctor/scripts/checks/roadmap_phases_check.py`（新建）：

- **A1. phases/*.md frontmatter 必需字段**
  - 复用 `_lib.roadmap_state.load_fragments(<.rddf/roadmap>, include_archived=False)`
  - filter `kind == "phase"`
  - 复用现有 `_REQUIRED_FIELDS = ("id", "kind", "status", "phase_refs", "主题")`
  - 每缺失一个 field → WARNING（与 roadmap-feature 同样的 severity 政策；`status` 缺失升 CRITICAL）
- **A2. `.rddf/roadmap.md` AUTO-INDEX Phases 段 sync**
  - 解析 `.rddf/roadmap.md` `<!-- AUTO-INDEX -->` 段下 `### Phases` 子段
  - 模式 `-\s*`(phase-\d+(\.\d+)?)`\s*—`
  - 比对：`phases/*.md` 的 id 集合 ↔ AUTO-INDEX Phases 段 id 集合
  - drift（disk 有但 AUTO-INDEX 无） → CRITICAL
  - drift（AUTO-INDEX 有但 disk 无） → CRITICAL
- **A3. phases/*.md ↔ main doc Phase Skeleton 一致性**
  - 复用 `_lib.roadmap_validate._extract_main_doc_phases` 拿 main doc 里的 phase id
  - 比对：`phases/*.md` 的 id 集合 ⊆ main doc Phase Skeleton 里的 id 集合
  - 缺少 → CRITICAL（main doc 引用了 phase 但文件不在）
- **A4. phases/*.md phase_refs 内部一致性**
  - phase_refs 应该是空列表 `[]`（phase 不引用其他 phase）
  - 非空 → WARNING（可能是误填）

输出 `roadmap-phases.{frontmatter,index-drift,main-doc-missing,ref-misuse}` 子 category 的 Finding 列表。

**B. 新增 `roadmap-md-integrity` category** (~200 LOC)

`skills/rdd-doctor/scripts/checks/roadmap_md_integrity_check.py`（新建）+ `_lib/roadmap_md_integrity.py`（新建，~120 LOC）：

- **B1. 主表 `## Phase Skeleton` 完整性**
  - 必须存在 `## Phase Skeleton` 段
  - 表格列 schema 必须 = `| Phase | Theme | Status | Started | Done |`（5 列）
  - 每行必须 match `\|\s*(phase-\d+(\.\d+)?)\s*\|`
  - Status 字段必须 ∈ {active, deferred, completed, archived}
- **B2. AUTO-INDEX 段齐全性**
  - 必须存在 `<!-- AUTO-INDEX -->` 哨兵
  - 必须存在 3 个子段：`### Phases` / `### Features` / `### Objectives`
  - 缺任一子段 → WARNING（advisory，不阻断）
- **B3. AUTO-INDEX 三段 ↔ 磁盘目录 sync**
  - Phases 段 id 集 vs `.rddf/roadmap/phases/*.md` 文件名
  - Features 段 id 集 vs `.rddf/roadmap/features/*.md` 文件名
  - Objectives 段 id 集 vs `.rddf/roadmap/objectives/*.md` 文件名（如 OBJECTIVE 段存在则必同步）
- **B4. 主表 ADR 链接有效性**
  - 解析 `| <...> `[ADR-NNNN](../../docs/adr/ADR-NNNN-*.md)` <...> |` 行内 markdown links
  - 每个 link 的 target 必须在 `docs/adr/` 实际存在
  - 失效 → WARNING（链接漂移）
- **B5. AUTO-SPRINT 段存在性 + 一致性**（可选，advisory）
  - 必须存在 `<!-- AUTO-SPRINT-START -->` 哨兵（roadmap.md 模板应有）
  - Current Sprint 表格的 phase 列必须 ⊆ AUTO-INDEX Phases 段

输出 `roadmap-md-integrity.{table-schema,index-segment,index-sync,adr-links,sprint-drift}`。

**D. 接入 rdd-doctor 主调度** (~3 LOC 改动)

- `skills/rdd-doctor/scripts/doctor_main.py::_CHECKERS` 字典加 2 行：
  ```python
  "roadmap-phases": roadmap_phases_check.run,
  "roadmap-md-integrity": roadmap_md_integrity_check.run,
  ```
- 顶部 import 同步加 2 个 check 模块

**E. SKILL.md 同步** (~10 LOC)

- `skills/rdd-doctor/SKILL.md` 第 26 行 `--category` list 扩 18→20
- 第 51 行 `## 18 类检查概览` 表头改 `## 20 类检查概览`
- 表内追加 2 行
- `.rddf/roadmap/` 文档诊断速查段追加 2 个 case 演示

**F. 同步锁定测试**（白送，必有）

- `tests/integration/test_rdd_doctor_skills_md_sync.bats` 已经动态 parse `_CHECKERS` 和 SKILL.md 表，**自动**锁定 20 类 sync——无需改测试逻辑
- 验证：跑新加 category → `bats tests/integration/test_rdd_doctor_skills_md_sync.bats` 必须仍 6/6 通过

**H. 单元测试**（新增 ~150 LOC）

- `tests/unit/test_roadmap_phases.py` — 4 个 case（happy / frontmatter 缺失 / AUTO-INDEX 漂移 / main doc 缺 phase）
- `tests/unit/test_roadmap_md_integrity.py` — 6 个 case（happy / table 列错 / AUTO-INDEX 缺段 / 三段 sync / ADR 链接失效 / sprint drift）
- 跑全套 pytest 必须 ≥3127 + 10 新 case 全绿，无新失败

**Out Scope**:
- 修改 `roadmap-feature` / `roadmap-refs` / `objective-*` / `roadmap-meta` 现有逻辑
- 不修 `.rddf/roadmap.md` 本身的内容（doctor 是 read-only；写修是 `rddf roadmap` 命令的事）
- 不动 `validate_fragment_refs` 的 R1-R8 规则
- 不重新组织 `.rddf/roadmap/` 目录结构
- 不为 `.backup/` 历史备份加诊断（白名单）
- 不写新的 `rddf roadmap` CLI 子命令（仅诊断）
- 不联动 `AGENTS.md`（已有 `roadmap-feature._check_agents_md_auto_block` 覆盖，重复会职责膨胀）
- 不支持 `--user-data-dir`（per `test_full_workflow_e2e` 已是 out scope）

## 验收标准

| AC | 描述 |
|----|------|
| AC-1 | `bash skills/rdd-doctor/scripts/doctor.sh --help` 输出含 `roadmap-phases` + `roadmap-md-integrity` 两个新 choice |
| AC-2 | `bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-phases` exit ≤ 1（master 同步无 CRITICAL）|
| AC-3 | `bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-md-integrity` exit ≤ 1 |
| AC-4 | `skills/rdd-doctor/scripts/checks/roadmap_phases_check.py` 存在，函数 `run(project_root) -> List[Finding]` |
| AC-5 | `skills/rdd-doctor/scripts/checks/roadmap_md_integrity_check.py` 同 |
| AC-6 | `_lib/roadmap_md_integrity.py` 存在并提供至少 `parse_main_doc_table` / `parse_auto_index_segments` / `validate_adr_links` 三个 public 函数 |
| AC-7 | `doctor_main.py::_CHECKERS` 字典条目数 == 20（原 18 + 新 2）|
| AC-8 | `SKILL.md` 第 51 行表头为 `## 20 类检查概览` 且表格行数 == 20 |
| AC-9 | `bats tests/integration/test_rdd_doctor_skills_md_sync.bats` 6/6 PASS（含自动锁定的 20 类 sync）|
| AC-10 | `pytest tests/unit/test_roadmap_phases.py` 4/4 PASS |
| AC-11 | `pytest tests/unit/test_roadmap_md_integrity.py` 6/6 PASS |
| AC-12 | `pytest tests/unit/` 总数 ≥3127 + 10 新 case = ≥3137 PASS（不计 2 个 pre-existing monitor_watch 失败）|
| AC-13 | `./test.sh --quick` 通过，无新失败
| AC-14 | `git diff --stat` 显示本次改动 ≤20 文件、净增 LOC ≤ 600 |

## 关键场景

### 场景 1: 用户诊断 phases/*.md 健康度

```bash
# 旧：删一个 phase 文件无诊断
$ rm .rddf/roadmap/phases/phase-2.md
$ bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-refs
✅ All 1 categories OK    # R1/R6 通过（main doc 仍提 phase-2；但 phase-2.md 没了）

# 新：
$ bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-phases
❌ CRITICAL: phase-2: missing phase file .rddf/roadmap/phases/phase-2.md
```

### 场景 2: 主表列 schema 漂移

```bash
# 旧：列被删 / 重命名无诊断
$ # ".rddf/roadmap.md" 中 "Done" 列被删
$ bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-refs
✅ All 1 categories OK

# 新：
$ bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-md-integrity
❌ CRITICAL: table-schema: expected 5 columns (Phase / Theme / Status / Started / Done) at line 16
```

### 场景 3: 主表 ADR 链接失效

```bash
# 旧：删 ADR 后表格里的链接失效，无诊断
$ git mv docs/adr/ADR-0010-multi-session-management.md docs/adr/archive/
$ bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-feature
✅ All 1 categories OK

# 新：
$ bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-md-integrity
⚠️ WARNING: adr-links: ADR-0010 link target docs/adr/ADR-0010-multi-session-management.md not found
```

### 场景 4: AUTO-INDEX Phases 段漂移

```bash
# 旧：AUTO-INDEX Phases 段丢了 phase-4，但 phases/phase-4.md 还在
$ # 手编 .rddf/roadmap.md，删除 "### Phases" 段下 phase-4 行
$ bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-feature
✅ All 1 categories OK    # 只查 Features 段，不查 Phases 段

# 新：
$ bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-phases
❌ CRITICAL: phase-4: disk fragment exists but missing from .rddf/roadmap.md AUTO-INDEX Phases section
```

### 场景 5: AUTO-SPRINT 段漂移

```bash
# 旧：Current Sprint 段提到了不存在的 phase
$ # 编辑 AUTO-SPRINT 表格加 phase-99
$ bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-refs
✅ All 1 categories OK    # 不扫 AUTO-SPRINT 段

# 新：
$ bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-md-integrity
⚠️ WARNING: sprint-drift: phase-99 in Current Sprint but not in AUTO-INDEX Phases segment
```

## 技术约束

| 约束 | 说明 |
|---|---|
| 路径解析 | 复用 `_PROJECT_ROOT = Path(__file__).resolve().parents[5]`（与 roadmap-refs_check 修复后一致）|
| Read-only | doctor 不写任何文件（per AC-2.10）；所有修复建议输出到 stderr 不动文件 |
| 复用现有 helper | `_lib.roadmap_state.load_fragments` / `_REQUIRED_FIELDS` / `_extract_main_doc_phases` |
| Severity 政策 | 与 `roadmap-feature` 对齐：缺失 `status` 升 CRITICAL；其他字段缺失 WARNING；漂移 CRITICAL；advisory WARNING |
| 现有测试 | `test_rdd_doctor_skills_md_sync.bats` 必须仍 6/6（动态 parse，自动覆盖新类别）|
| 现有 SKILL.md sync | 自动通过测试，无需手动维护——`_CHECKERS` dict 是单一事实源 |
| pytest unit 全过 | 不增加任何失败；现有 3127 + 新增 10 必须全绿（不计 2 monitor_watch pre-existing）|
| 性能 | 单 category 运行 < 500ms（read-only 文件扫描，无 subprocess）|
| Module-parse | 5 层 `.parent` 必须 work（per 上次 `_PROJECT_ROOT` 修复经验）|
| 不引入新依赖 | 复用 `pathlib` / `re` / `json` / `dataclass`（stdlib）|

## Lifecycle

### 1. Proposal creation

本文件 `.rddf/improvements/add-roadmap-phases-and-md-integrity-category.md`。
注册到 `improvement-suggestions.md` 表格（`rddf roadmap add-feature` 或手工）。

### 2. Design review (`rdd-planner`)

按 v4 流程审查；如果 reviewer 觉得"roadmap-meta 应一并扩展"，回到 proposal 在 ADR-0052 之后做单独立项。

### 3. Plan (`rdd-builder` P1)

生成 `.rddf/plans/<name>.md`，包含 TDD 5 步结构：
- T1: 写 `test_roadmap_phases.py` 4 case → verify fail（红）
- T2: 实现 `roadmap_phases_check.py` → verify pass（绿）
- T3: 写 `test_roadmap_md_integrity.py` 6 case → verify fail（红）
- T4: 实现 `roadmap_md_integrity_check.py` + `_lib/roadmap_md_integrity.py` → verify pass（绿）
- T5: 接入 `doctor_main.py::_CHECKERS` + SKILL.md 同步 → verify `test_rdd_doctor_skills_md_sync.bats` 仍 6/6
- T6: `./test.sh --quick` 全套回归

### 4. Ship (`rdd-builder` P2)

执行 change。完成所有 task 后跑 `./test.sh --full --regression`（MANDATORY gate per `add-full-regression-gate`）。

### 5. Archive

archive → `openspec/changes/archive/2026-10-XX-add-roadmap-phases-and-md-integrity-category/`。

## 风险与回滚

| 风险 | 概率 | 影响 | 缓解 | 回滚 |
|------|------|------|------|------|
| 路径解析 5 层错（重蹈 roadmap-feature 错误） | 低 | ModuleNotFoundError 阻断 doctor | 复制 `roadmap-refs_check.py:17` 已验证的 5-层模式；新测试第一时间跑 | 单 commit revert |
| SKILL.md 表格行数 == 20 不锁 | 自验 | reviewer 一眼错 | 跑 `test_rdd_doctor_skills_md_sync.bats`；6/6 PASS 证明 sync | 单 commit revert |
| ADR 链接解析对中文/带空格的 theme 不鲁棒 | 中 | 误报 | regex 限定 `[\w./-]+` + 严格 mode 只在 `\[\]\(\.\./\.\./docs/adr/...\)` 模式触发 | 单 commit revert |
| AUTO-SPRINT 段格式变更（rddf roadmap 改 schema） | 中 | future regression | B5 advisory（WARNING）即使 schema 变也只在文本差异时报 | 加 version field 后续硬化 |
| `_CHECKERS` 字典 dict 顺序破坏测试断言 | 极低 | 测试假阳/假阴 | 已用 `frozenset` 比对（`tests/unit/test_doctor_main.py` 第 21 行）+ 锁 18 时已 OK | N/A |
| `.rddf/roadmap.md` 实际 1000+ 行 markdown 解析慢 | 极低 | < 500ms 单文件 read + regex | `read_text()` 一次 + 多次 `re.finditer` 复用 | N/A |
| 历史 archive docs/superpowers/plans/ 的硬编码路径回潮 | 接受 | accept by design | "respect user data" 白名单 | N/A |

**回滚方案**（单 commit revert）：

```bash
git revert <commit-sha>
# 移除 2 个 check 文件 + 1 个 _lib 模块 + _CHECKERS 字典 2 行 + SKILL.md 表 2 行
```

零副作用，回滚 < 5 分钟。

## 实施计划 (估算)

| Task | 内容 | LOC |
|------|------|-----|
| T1 | `tests/unit/test_roadmap_phases.py` (4 case, 红) | ~50 |
| T2 | `_lib/roadmap_md_integrity.py` skeleton + `tests/unit/test_roadmap_md_integrity.py` (6 case, 红) | ~80 |
| T3 | `skills/rdd-doctor/scripts/checks/roadmap_phases_check.py` (实现, 绿) | ~150 |
| T4 | `skills/rdd-doctor/scripts/checks/roadmap_md_integrity_check.py` (实现, 绿) | ~80 |
| T5 | `skills/rdd-doctor/scripts/doctor_main.py::_CHECKERS` + imports (2 行 + 2 import) | +5 |
| T6 | `skills/rdd-doctor/SKILL.md` 表头 + 表行 + 速查段 | +10 |
| T7 | `./test.sh --quick` 全套回归 | — |
| **Total** | 7 tasks | **~375 LOC 净增** |

**预估工期**: 2-3 小时（含 TDD 5 步 + 单元测试 + SKILL.md 同步 + 文档）。

## 相关 ADR

- ADR-0027 continuous evolution — rdd-doctor 持续扩面与本次方向一致
- ADR-0054 objective 工件 — `.rddf/roadmap/objectives/*.md` 已有 objective-* 覆盖；本提案补 `.rddf/roadmap/phases/*.md` 同级结构
- ADR-0036 project.yaml 配置 — 未来如要把 phases/*.md 路径 configurable，沿用 project.yaml
- 与 `fix-rdd-doctor-hardcoded-paths-and-skills-md-drift` 提案衔接 — 上次扩 18 类 + SKILL.md sync 自动锁定；本次扩 20 类，自动 lock 同步覆盖
- 与 `add-full-regression-gate`（P0, 2026-07-28）相关 — ship 前必跑 `./test.sh --full --regression`