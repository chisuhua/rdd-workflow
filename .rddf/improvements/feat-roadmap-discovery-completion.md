---
优先级: P1
来源: 2026-09-22 improve-roadmap-feature-discovery proposal AC-4/AC-5/AC-8 deferred items
阶段: phase-1
分类: governance
类型: improvement
主题: 完成 improve-roadmap-feature-discovery 提案（AC-4/AC-5/AC-8）
---

**优先级**: P1 | **来源**: 2026-09-22 improve-roadmap-feature-discovery 提案 deferred items
**阶段**: phase-1 | **分类**: governance | **类型**: improvement

**主题**: 完成 improve-roadmap-feature-discovery 提案（AC-4/AC-5/AC-8）

## 架构依据

2026-09-22 ship 的 `feat(roadmap): ship improve-roadmap-feature-discovery`（commit `eb774f3` + fix `12068d2`）完成了 6/9 个 AC，3 个 deferred：

- AC-4：`rdd-arch` Phase 1 输出 feature fragments 列表作为 context — **未实施**
- AC-5：`rdd-doctor --category roadmap-feature` 巡检（检查 feature fragment 格式 + AGENTS.md 一致性）— **未实施**
- AC-8：`rdd-arch/SKILL.md` Phase 1 步骤更新 — **未实施**

后续 Oracle audit 发现 2 个 critical fix（YAML shape + bats whitelist，已 fix in commit `12068d2`）。deferred AC 现在补齐。

后果：
- AI agent 启动 rdd-arch 时不知道当前活跃 feature fragments（不知道哪些 feature 含未完成 sub-proposal）
- 没有巡检守护：未来 fragment 格式 drift / AGENTS.md 不一致会再次发生（per Oracle audit issue #1: YAML shape 不 match JSON shape 的"契约违反"类 bug）
- `.rddf/roadmap/features/*.md` 与 `.rddf/state/iteration.json::feature_view` 可能不一致（已在 commit `76b9261` 修复，但无守护）

期望行为：rdd-arch Phase 1 输出活跃 features；rdd-doctor 守护 fragment 格式契约；SKILL.md 反映新步骤。

## 范围

**In Scope**：
- 新增 `_lib/cli/doctor_cmd.py::_CHECKERS["roadmap-feature"]` 巡检类
- 实现 `skills/rdd-doctor/scripts/checks/roadmap_feature_check.py`：
  - 校验 `.rddf/roadmap/features/*.md` frontmatter 完整 (id/kind/status/phase_refs/主题 5 字段)
  - 校验 `.rddf/state/iteration.json::feature_view.features` 包含所有 active feature id（CRITICAL 否则）
  - 校验 AGENTS.md AUTO 哨兵段（如存在）反映当前 features（CRITICAL 否则）
- `skills/rdd-arch/SKILL.md` Phase 1 增加 list-features 输出 prose 段
- 加 4 个 unit test 覆盖新 check 正常 / 异常路径
- 加 1 个 integration test (bats) 验证 `rddf doctor --category roadmap-feature` 端到端

**Out of Scope**：
- 改 `_lib/roadmap_state.py::update_agent_md` 内部（已 ship + fix，不需要再改）
- 改 `rdd-builder P1`（虽然 builder 也会受益，但不在本次范围）
- 反向：从 AGENTS.md 解析 feature（只单向写入）
- AC-1/AC-2/AC-3/AC-6/AC-7/AC-9：已 ship + fix

## 关键场景

- GIVEN `.rddf/roadmap/features/feat-x.md` 存在但 frontmatter 缺 `主题` 字段
  WHEN `rddf doctor --category roadmap-feature` 跑
  THEN 输出 1 个 WARNING finding, exit code 1

- GIVEN `.rddf/roadmap/features/feat-x.md` 存在，AGENTS.md 缺 AUTO 段
  WHEN `rddf doctor --category roadmap-feature` 跑
  THEN 不报错（无 AUTO 段不算 drift；只当 AUTO 段存在但 stale 才报）

- GIVEN AGENTS.md AUTO 段存在但含未在 `.rddf/roadmap/features/` 中的 feature id
  WHEN `rddf doctor --category roadmap-feature` 跑
  THEN 输出 1 个 CRITICAL finding, exit code 2

- GIVEN iteration.json feature_view 缺 active feature id
  WHEN `rddf doctor --category roadmap-feature` 跑
  THEN 输出 1 个 CRITICAL finding, exit code 2

## 技术约束

- MUST: checker 函数签名 `def run(project_root: Path | None = None) -> List[Finding]`
- MUST: checker 不修改任何 tracked 或 gitignored 文件（READ-ONLY）
- MUST: 复用 `load_fragments()` from `_lib/roadmap_state.py` (避免重新解析 YAML)
- MUST: AGENTS.md 不存在时返回空 findings (不报错)
- MUST: 复用 `_lib/roadmap_state.AGENTS_AUTO_SENTINEL_START/END` 常量

## 验收标准

- [ ] `rddf doctor --category roadmap-feature` 命令实现, exit code 0/1/2/3 对齐 `openspec validate`
- [ ] 4 个 unit test 覆盖 scenarios:
    - 正常 features 无 finding (exit 0)
    - 缺 frontmatter 字段 → WARNING
    - AGENTS.md AUTO 段含 stale feature id → CRITICAL
    - iteration.json feature_view 缺 active feature → CRITICAL
- [ ] `skills/rdd-arch/SKILL.md` Phase 1 增加 list-features prose 输出段 (AC-4)
- [ ] `rddf doctor --help` 输出包含 "roadmap-feature"
- [ ] `skills/rdd-doctor/scripts/doctor_main.py::_CHECKERS["roadmap-feature"]` 注册成功
- [ ] 现有 doctor bats integration test 不回归 (rdd-doctor 默认跑全 category)
- [ ] commit message 含 `feat(roadmap-feature): complete improve-roadmap-feature-discovery AC-4/5/8`

## 相关

- 关联: `.rddf/improvements/improve-roadmap-feature-discovery.md` (proposal)
- 关联: commit `eb774f3` (original ship) + commit `12068d2` (Oracle critical fix)
- 关联: `_lib/roadmap_state.py::list_features` + `update_agent_md`
- 关联: `skills/rdd-doctor/scripts/checks/roadmap_meta_check.py` (template)
- 关联: `skills/rdd-doctor/scripts/checks/roadmap_refs_check.py` (template)
- 关联: `skills/rdd-arch/SKILL.md` Phase 1 (target prose update)