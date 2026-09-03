# Stage 3 — rdd-arch 重构与双向反馈闭环 (v2 — Oracle+Metis 修订版)

> **Status**: Pending user approval (修订 v2)
> **Date**: 2026-09-03
> **Author**: sisyphus
> **Depends on**: Stage 2.5 (rdd-planner 完整 sprint 生命周期), ADR-0016/0017/0028/0034/0037/0041

## 0. 修订摘要 (vs v1)

| 维度 | v1 错误/不足 | v2 修订 |
|---|---|---|
| handoff 版本号 | 误以为现状是 v1, 需要 bump 到 v2 | **正式化现状 v2**, 不 bump; schema 注释明确 v2 = base + v2_additive(planner_feedback 通过独立文件) |
| 反馈存储 | 写入 arch-owned `.arch-handoff.json` (角色冲突) | **独立文件 `.rddf/state/.planner-feedback.json`**, planner owns, arch 只读消费 |
| 反馈数据模型 | 瞬时诊断快照 | **持久化 review 任务**: feedback_id/status(open/acknowledged/resolved/dismissed)/severity(critical/warning/info)/fingerprint/computed_from |
| CLI `--clear` 模糊 | 含义不清 | 拆为 `--acknowledge / --resolve / --dismiss` 三命令 |
| write_arch_handoff 锁 | 假设已有 FileLock (Oracle C-1 反驳) | **Change 0 优先改造** 为 FileLock + atomic_write, 与 planner_state.py 模式一致 |
| rename blast radius | 仅提及 SKILL.md + shim | **1269 处 / 333 文件清单**, 含 `_lib/state_reader.py/gate.py/workflow_synthesizer.py`、`test_guide_arch_metadata.py`、8 个 extraction bats、AGENTS.md/README/USAGE 等活跃引用 |
| 842 行复刻 | 反模式 | **git mv** 单源, shim 仅 5 行保留 |
| CLI 路径 | 错写 `skills/_lib/cli/` | 修正为 canonical **`_lib/cli/rdd_arch_cmd.py`** (AGENTS.md #25) |
| deprecation 锚点 | "v2.3.0" (已过去) | 锚定 **"v3.x + 2 个 minor release"** (≈ 2026-12) |
| 双向联调示例 | 仅 schema | **Happy path + Revision loop 两个完整端到端示例** (含真实命令、JSON 前后状态、stdout 预期) |
| stale 检测 | 仅 `last_computed_at` | **绑定 `codebase_commit` + `arch_handoff_revision` + `planner_state_last_sync_at`**, 显示 Freshness 状态 |
| fingerprint 去重 | 缺失 | **`fingerprint = sha256(kind+proposal+theme+related_adr_ids+reason)[:16]`**, 幂等去重 |
| branch/worktree 隔离 | 缺失 | **绑定 `branch + worktree_root + codebase_commit`** (沿用 ADR-0034 模式) |
| handoff 损坏恢复 | 缺失 | **`exit 3` 不覆盖, stderr 明确, 不静默修复** |
| in-flight session 迁移 | 缺失 | **session identity 兼容矩阵** (`intent: guide-arch` 自动映射到 `rdd-arch`) |
| 回归门 | `--quick` + `report_regression.sh` | **补 `./test.sh --full --regression`** (AGENTS.md 强制), **补 consumer-side compat 测试** (v1 fixture + v2 fixture 跑现有消费者) |
| AGENTS.md #25 合规 | 路径混乱 | **identity 断言**: `_lib.planner_feedback is skills._lib.planner_feedback`, shim 模式 |
| ADR 编号冲突 | 未查 | **确认 0042 可用** (0041 已被占用) |
| ADR-0028 修订 | 未提 | **ADR-0042 显式修订 ADR-0028**: planner 拥有 `.planner-feedback.json`, arch 拥有 `.arch-handoff.json` |
| 错误策略表 | 缺失 | **6 类失败模式明确 exit code + 主流程影响** |
| 双向写入与 Schema 测试 | 缺失 | **新增 `test_planner_feedback_loop.bats`**: 端到端 happy path + revision loop |

---

## 1. 背景与动机

### 1.1 现状
- `guide-arch` (842 行 MD, 17 个 scripts/) 是五阶段架构 (arch→design→plan→ship→verify) 的第一阶段
- arch-done 写入 `.rddf/state/.arch-handoff.json` (contract v2, ADR-0016)
- Stage 2.5 `rdd-planner` 是横切编排器, 管理 sprint 生命周期 + proposal attach + history
- 两者之间**无显式双向契约**: arch 不知道 planner 的 proposal 是否已 attach, planner 不知道 arch 何时新增 ADR/roadmap 主题

### 1.2 重构目标
1. **Rename**: `guide-arch` → `rdd-arch` (per D1a Stage 3 渐进策略, 与 `rdd-planner`/`rdd-verifier` 命名对齐)
2. **双向反馈闭环**:
   - **arch 消费 planner feedback**: arch Phase 1 setup 读取 `.planner-feedback.json` 展示未解决问题摘要
   - **planner 计算并持久化反馈**: planner sync/audit 计算 review 任务, 持久化到独立文件, 带 lifecycle 与 fingerprint
3. **角色边界清晰**: planner owns `.planner-feedback.json`, arch owns `.arch-handoff.json`, 互不越界
4. **向后兼容**: 保留 `guide-arch` shim 至 v3.x + 2 minor

### 1.3 不在 Stage 3 范围
- ❌ 不修改 guide-design / guide-plan / guide-ship (Stage 3 仅 arch 阶段 + 横切 planner 接口)
- ❌ 不重命名 rdd-planner / rdd-verifier (Stage 4 才统一)
- ❌ 不修改 `.rddf/improvements/*.md` 现有 226 个文件

---

## 2. 架构设计

### 2.1 双契约载体 (修订后)

**主契约 1**: `.rddf/state/.arch-handoff.json` (正式化 contract v2, ADR-0016)
- **owner**: rdd-arch
- **现状**: schema 已是 v2 (`properties.version.enum: [1, 2]`, `title: "contract v2 additive"`), writer 写 `"version": 2`, 顶层 `additionalProperties: true`
- **v2 修订**: 在 schema 注释明确 "contract v2 = base + v2_additive(roadmap_fragments_dir + adr_regex)", 字段不变
- **planner 不写此文件**, 仅消费

**主契约 2**: `.rddf/state/.planner-feedback.json` (新增, **planner owns**)
- **owner**: rdd-planner
- **结构**: 持久化 review 任务集合 (见 §2.2)
- **写入**: planner sync/audit/feedback CLI 触发
- **读取**: rdd-arch Phase 1, `rddf planner feedback`, `rddf arch status`

**辅助契约**: `.rddf/state/.arch-quality-report.json` (新增 `planner_signals` 段)
- 把 planner_feedback 的 critical 项升级为 quality report error
- arch-done gate **不**被 planner_feedback 阻断 (避免循环依赖, advisory only)

### 2.2 planner_feedback 数据模型 (持久化 review 任务)

```json
{
  "$schema": "planner-feedback-v1",
  "version": 1,
  "owner": "rdd-planner",
  "branch": "master",
  "worktree_root": "/workspace/project/rdd-workflow",
  "codebase_commit": "abc123...",
  "arch_handoff_revision": 12,
  "planner_state_last_sync_at": "2026-09-03T10:00:00Z",
  "feedbacks": [
    {
      "feedback_id": "pf-20260904-001",
      "kind": "coverage_gap",
      "severity": "critical",
      "status": "open",
      "fingerprint": "a3f7b2c1e9d4f5a8",
      "proposal": "feat-cross-repo-auth",
      "theme": "cross-repo-protocol",
      "related_adr_ids": ["0030"],
      "message": "proposal 未映射到任何 roadmap theme",
      "suggested_action": "在 roadmap.md 新增 theme 或编辑 proposal 添加 theme_ref",
      "created_at": "2026-09-03T10:00:00Z",
      "last_seen_at": "2026-09-03T10:00:00Z",
      "acknowledged_at": null,
      "resolved_at": null,
      "resolved_by": null,
      "dismissed_at": null,
      "dismissed_by": null,
      "computed_from": {
        "planner_state_revision": 5,
        "arch_handoff_revision": 12,
        "codebase_commit": "abc123..."
      }
    }
  ],
  "summary": {
    "open_critical": 1,
    "open_warning": 2,
    "open_info": 0,
    "acknowledged": 0,
    "resolved": 0,
    "dismissed": 0
  }
}
```

**关键字段语义**:
- `fingerprint`: 幂等键, 相同输入重复 sync 不创建重复反馈, 仅更新 `last_seen_at`
- `status` lifecycle: `open` → (architect 看到) → `acknowledged` → (修复后) → `resolved` 或 (豁免) → `dismissed`
- `computed_from`: 三个稳定版本标识共同定义"陈旧", 任一变化 → feedback 标记为 `stale`
- `branch + worktree_root`: 多 worktree 隔离 (沿用 ADR-0034)
- `summary`: 计算字段, 每次写入更新, 用于 arch Phase 1 一行摘要

### 2.3 双向流程图 (修订)

```
                    ┌──────────────────────────────────┐
                    │  rdd-arch (Phase 5 arch-done)    │
                    └──────────────────┬───────────────┘
                                       │ write .arch-handoff.json (v2)
                                       │ + atomic_write + FileLock
                                       ▼
                ┌────────────────────────────────────────┐
                │  .rddf/state/.arch-handoff.json (v2)    │
                │  owner: rdd-arch                       │
                └────────────────────────────────────────┘
                                       │ read by rdd-planner (adhoc)
                                       ▼
                    ┌──────────────────────────────────┐
                    │  rdd-planner (sync / audit)       │
                    │  compute_planner_feedback()       │
                    └──────────────────┬───────────────┘
                                       │ write .planner-feedback.json (atomic)
                                       │ owner: rdd-planner
                                       ▼
                ┌────────────────────────────────────────┐
                │  .rddf/state/.planner-feedback.json   │
                │  owner: rdd-planner (NOT arch)        │
                └────────────────────────────────────────┘
                                       │ read by rdd-arch Phase 1
                                       ▼
                    ┌──────────────────────────────────┐
                    │  rdd-arch Phase 1 display:        │
                    │  "Planner: N critical, M warning, │
                    │   K stale, all in T commits ago"   │
                    └──────────────────────────────────┘
```

### 2.4 CLI 接口 (修订)

```bash
# rdd-arch (rename from guide-arch)
rddf arch                          # 启动向导 (Phase 1-6 状态机)
rddf arch status                   # 一行状态: "Sprint: sprint-2026-09 | Planner: N critical, M warning, K stale"
rddf arch handoff                  # 输出当前 .arch-handoff.json
rddf arch feedback                 # 输出当前 .planner-feedback.json 摘要 (read-only)

# rdd-planner 扩展
rddf planner feedback              # 输出当前持久化反馈列表
rddf planner feedback --json       # JSON 格式输出
rddf planner feedback --status open|acknowledged|resolved|dismissed  # 过滤
rddf planner feedback --kind unmapped_proposal|coverage_gap|adr_drift|roadmap_staleness  # 过滤
rddf planner feedback --acknowledge <feedback_id>    # 标记已读
rddf planner feedback --resolve <feedback_id> [--note "..."]   # 标记已解决
rddf planner feedback --dismiss <feedback_id> [--reason "..."] # 标记豁免
rddf planner feedback --recompute  # 强制重新计算 (非 sync 触发)
rddf planner feedback --prune-resolved   # 清理 resolved/dismissed 历史
```

### 2.5 写入语义 (修订)

| 操作方 | 写入文件 | 锁 | 频率 | 原子性 |
|---|---|---|---|---|
| rdd-arch Phase 6 | `.arch-handoff.json` | `.arch-handoff.json.lock` (FileLock) | 一次性 | atomic_write (tmp + rename) |
| rdd-planner sync/audit/recompute | `.planner-feedback.json` | `.planner-feedback.json.lock` (FileLock) | 每次计算 | atomic_write (tmp + rename) |
| 读侧 | rdd-arch Phase 1 / `rddf arch status` / `rddf planner feedback` | 无锁 | — | — |

**关键不变量**:
- rdd-arch **不写** `.planner-feedback.json` (角色边界, ADR-0028)
- rdd-planner **不写** `.arch-handoff.json` (角色边界)
- 两文件独立 FileLock, 互不阻塞
- 写入均 atomic_write, 损坏恢复策略见 §5 错误策略表

### 2.6 Session 兼容矩阵 (修订)

| 用户入口 | canonical | legacy shim 行为 | session identity |
|---|---|---|---|
| `rddf arch` | `rdd-arch` | — | 创建/恢复 `intent: rdd-arch` |
| `skill_use("rdd-arch")` | `rdd-arch` | — | 同上 |
| `skill_use("guide-arch")` | — | shim: 打印 DEPRECATED warning, 转发到 `rdd-arch`, session 复用现有 `intent: guide-arch` 或新建 `intent: rdd-arch` (可配置) | 向后兼容 |
| `rddf guide-arch` (历史 CLI) | — | shim: exit 0, 输出 "deprecated, use rddf arch" | — |
| `report-issue --phase guide-arch` | — | shim: 接受, 内部映射 `rdd-arch` | — |

---

## 3. 端到端双向联调示例 (Metis 1.1 补救)

### 3.1 Happy Path (完全匹配)

```bash
# Step 1: 架构师定义 ADR + roadmap theme
cat > docs/adr/ADR-0042-foo.md <<EOF
> **状态**: 已采纳 (2026-09-03)
> **主题**: cross-repo-protocol
EOF

# roadmap.md 已包含:
# | phase-1 | cross-repo-protocol | active | | |

# Step 2: 改进提案带 theme_ref
cat > .rddf/improvements/feat-cross-repo-auth.md <<EOF
---
name: feat-cross-repo-auth
priority: P1
theme_ref: cross-repo-protocol
---
# feat-cross-repo-auth
EOF

# Step 3: arch-done
rddf arch   # Phase 1-6 → 写 .arch-handoff.json v2

# Step 4: planner 同步
rddf planner sync --apply
# stdout: ✓ State synced (0 newly unmapped)
# stdout: ✓ Planner feedback: 0 open, 0 stale

# Step 5: 验证
rddf planner feedback
# stdout: No active planner feedback.
```

### 3.2 Revision Loop (新增 ADR + planner 反馈 + 修订)

```bash
# Step 1: 初始状态 - 提案未映射
cat > .rddf/improvements/feat-cross-repo-auth.md <<EOF
---
name: feat-cross-repo-auth
priority: P1
# 故意不写 theme_ref, 触发 unmapped
---
EOF

# Step 2: planner sync 检测
rddf planner sync --apply
# stderr: ⚠ Planner feedback written: 1 critical (unmapped_proposal: feat-cross-repo-auth)

# Step 3: 架构师看到反馈
rddf arch status
# stdout: Sprint: sprint-2026-09 | Planner: 1 critical, 0 warning, 0 stale

rddf arch feedback
# stdout:
#   [critical] pf-20260904-001 (unmapped_proposal, open)
#     Proposal: feat-cross-repo-auth
#     Theme: <none>
#     Suggested: 在 roadmap.md 新增 theme 或编辑 proposal 添加 theme_ref

# Step 4: 架构师修订 - 添加 ADR + roadmap theme + proposal theme_ref
rddf arch   # Phase 2 创建 ADR-0042-foo.md, Phase 4 编辑 roadmap
sed -i 's/^---$/---\nname: feat-cross-repo-auth\ntheme_ref: cross-repo-protocol/' \
  .rddf/improvements/feat-cross-repo-auth.md

# Step 5: 重新 arch-done
rddf arch   # Phase 6 → 写 .arch-handoff.json (revision+1)

# Step 6: planner 重新 sync
rddf planner sync --apply
# stdout: ✓ State synced (resolved 1 feedback, 0 newly unmapped)
# 自动把 pf-20260904-001 从 open → resolved (fingerprint 命中, computed_from 更新)

# Step 7: 验证 - 反馈已解决
rddf planner feedback --status resolved
# stdout: pf-20260904-001 (resolved, last seen 2026-09-03)

# Step 8: 清理历史
rddf planner feedback --prune-resolved
# stdout: ✓ Pruned 1 resolved feedback
```

### 3.3 Stale Detection 流程

```bash
# Step 1: planner 写反馈时绑定 commit
rddf planner sync --apply
# .planner-feedback.json: codebase_commit: "abc123"

# Step 2: 架构师 commit 切换分支或修改 ADR
git checkout other-branch

# Step 3: 架构师启动 arch
rddf arch
# stdout:
#   Planner: 1 critical (stale: commit abc123 → current def456, 5 commits behind)
#   显示但不阻断

# Step 4: 重新 sync 刷新 computed_from
rddf planner sync --apply
# stdout: ✓ Refreshed 1 stale feedback (recomputed codebase_commit)
```

---

## 4. 实施变更 (6 changes)

### Change 0: write_arch_handoff.py FileLock + atomic_write 改造 [Oracle C-1 blocker]

**前置**: 任何 planner_feedback 写入通道的设计前提。**必须先做**。

**TDD (red)**:
- `tests/unit/test_write_arch_handoff_locked.py::test_write_uses_filelock`
- `tests/unit/test_write_arch_handoff_locked.py::test_write_is_atomic_via_tmp_rename`
- `tests/unit/test_write_arch_handoff_locked.py::test_concurrent_writers_no_data_loss`
- `tests/unit/test_write_arch_handoff_locked.py::test_lock_path_matches_planner_state_convention`

**Impl**:
- `_lib/write_arch_handoff.py`: 用 `_lib/core/lock.FileLock` + `_lib/core/atomic_write.atomic_write_json` 替换裸 `open(w)+json.dump`
- 锁路径 `.arch-handoff.json.lock` (与 planner_state 惯例一致)

**验证**: 现有 extraction bats 与 guide-plan intake 测试不破坏 (consumer-side compat)

### Change 1: rdd-arch rename (git mv + blast radius) [Oracle A-1]

**TDD (red)**:
- `tests/integration/test_rdd_arch_cli.bats::rddf: arch status command works`
- `tests/unit/test_rdd_arch_metadata.py::rdd-arch frontmatter name == rdd-arch` (新)
- `tests/integration/test_legacy_guide_arch_shim.bats::skill_use guide-arch forwards to rdd-arch`
- `tests/integration/test_session_identity_migration.bats::intent guide-arch resolves to rdd-arch session`

**Impl 步骤**:
1. `git mv skills/guide-arch skills/rdd-arch`
2. 新建 `_lib/cli/rdd_arch_cmd.py` (新 CLI 模块, 用 `from _lib.planner_feedback import ...`)
3. 编辑 `skills/rdd-arch/SKILL.md`:
   - frontmatter `name: rdd-arch`, `version: 2.1.0`
   - 全文 `guide-arch` → `rdd-arch` (sed 仅活跃文件)
   - role.boundaries 不变
4. `skills/guide-arch/SKILL.md` 替换为 5 行 shim: `name: guide-arch (DEPRECATED)`, body 转发到 `rdd-arch`
5. 全局 `~/.agents/skills/` 同步 (install.sh 幂等迁移)
6. **活跃引用更新** (见 §7 清单):
   - `tests/unit/test_guide_arch_metadata.py` → 拆为 `test_rdd_arch_metadata.py` + `test_legacy_guide_arch_shim.py`
   - 8 个 `test_arch_*_extraction.bats` → 路径断言改为 `skills/rdd-arch/scripts/`
   - `skills/guide/scripts/scan-state.sh` 推荐字符串更新
   - `skills/rddf-session/scripts/rddf_session_hooks.sh` skill arg 双值接受
   - `skills/guide-ship/scripts/ship_review.sh` 更新
   - `_lib/state_reader.py` / `_lib/gate.py` / `_lib/workflow_synthesizer.py` 仅 display text 更新
   - AGENTS.md / README.md / USAGE.md / CHANGELOG.md (活跃 section, archive 不动)
   - `package.json` skill names 列表
7. deprecation 锚定 **"v3.x + 2 minor release"** (≈ 2026-12)

**shim 行为**:
```yaml
# skills/guide-arch/SKILL.md (5 行 shim)
---
name: guide-arch
metadata:
  evolved-from: "renamed to rdd-arch in Stage 3"
  user-invocable: true
  deprecated: "use rdd-arch"
---
> ⚠️ DEPRECATED since Stage 3 (2026-09-03). Use `skill_use("rdd-arch")` or `rddf arch`.
> This shim will be removed in v3.x + 2 minor releases.
```

### Change 2: .planner-feedback.json 独立文件 + 持久化模型 [Metis 1.2, 4.1]

**TDD (red)**:
- `tests/unit/test_planner_feedback_model.py::test_feedback_required_fields`
- `tests/unit/test_planner_feedback_model.py::test_fingerprint_is_deterministic`
- `tests/unit/test_planner_feedback_model.py::test_fingerprint_changes_when_input_changes`
- `tests/unit/test_planner_feedback_model.py::test_summary_computed_correctly`
- `tests/unit/test_planner_feedback_model.py::test_branch_field_isolation`
- `tests/unit/test_planner_feedback_model.py::test_computed_from_three_identifiers`
- `tests/unit/test_planner_feedback_writer.py::test_write_uses_filelock_and_atomic`
- `tests/unit/test_planner_feedback_writer.py::test_compute_planner_feedback_creates_new_feedback`
- `tests/unit/test_planner_feedback_writer.py::test_compute_planner_feedback_updates_last_seen_for_existing`
- `tests/unit/test_planner_feedback_writer.py::test_compute_planner_feedback_handles_missing_handoff`
- `tests/unit/test_planner_feedback_writer.py::test_compute_planner_feedback_marks_stale_on_commit_mismatch`
- `tests/unit/test_planner_feedback_writer.py::test_compute_planner_feedback_handles_corrupted_feedback_file`

**Impl**:
- `_lib/schemas/planner_feedback_schema.json` — 新建 v1 schema
- `_lib/planner_feedback.py` — 新建模块:
  - `FeedbackEntry` dataclass + `fingerprint()` 函数
  - `compute_planner_feedback(project_root, *, force_recompute=False)` — 扫描 proposals + ADR + roadmap, 计算三类反馈
  - `read_planner_feedback(project_root)` / `write_planner_feedback(project_root, data)`
  - `acknowledge_feedback(id)` / `resolve_feedback(id, by, note)` / `dismiss_feedback(id, by, reason)`
  - `prune_resolved_feedback(project_root)` — 清理 resolved/dismissed
- `tests/conftest.py` 加 `_lib.planner_feedback is skills._lib.planner_feedback` identity 测试

### Change 3: planner CLI 子命令 [Metis 1.2 模糊]

**TDD (red)**:
- `tests/integration/test_planner_feedback_cli.bats::planner: feedback lists open by default`
- `tests/integration/test_planner_feedback_cli.bats::planner: feedback --status open filters correctly`
- `tests/integration/test_planner_feedback_cli.bats::planner: feedback --acknowledge updates status`
- `tests/integration/test_planner_feedback_cli.bats::planner: feedback --resolve transitions to resolved`
- `tests/integration/test_planner_feedback_cli.bats::planner: feedback --dismiss transitions to dismissed`
- `tests/integration/test_planner_feedback_cli.bats::planner: feedback --prune-resolved removes resolved/dismissed`
- `tests/integration/test_planner_feedback_loop.bats::happy-path: arch → planner → arch 闭环`
- `tests/integration/test_planner_feedback_loop.bats::revision-loop: 反馈创建→解决→prune`

**Impl**:
- `_lib/cli/planner_cmd.py`: 新增 `feedback [--json] [--status] [--kind] [--acknowledge ID] [--resolve ID] [--dismiss ID] [--recompute] [--prune-resolved]`
- `--acknowledge/--resolve/--dismiss` 互斥, 缺 id 报错

### Change 4: rdd-arch Phase 1 读取 planner feedback 摘要 [Metis 1.1]

**TDD (red)**:
- `tests/unit/test_rdd_arch_status.py::test_arch_status_includes_planner_summary`
- `tests/unit/test_rdd_arch_status.py::test_arch_status_shows_stale_indicator`
- `tests/integration/test_rdd_arch_cli.bats::rddf arch status 显示 Planner summary`

**Impl**:
- `_lib/rdd_arch_status.py` — 新建模块, 聚合 arch-handoff + planner-feedback 状态
- `_lib/cli/rdd_arch_cmd.py` — `status` 子命令
- `skills/rdd-arch/SKILL.md` Phase 1 setup — 在 env check 后插入 planner_feedback 摘要展示 (不阻断, 仅 advisory)
- `rddf arch feedback` — read-only 详细输出命令

### Change 5: ADR-0042 落盘 + consumer-side compat 测试 + 集成文档 [Oracle E, Metis 4.4]

**TDD (red)**:
- `tests/unit/test_arch_handoff_v2_schema.py::test_v1_payload_still_validates` (向后兼容 v1)
- `tests/integration/test_arch_handoff_compat.bats::v2 handoff accepted by guide-plan intake`
- `tests/integration/test_arch_handoff_compat.bats::v2 handoff accepted by detectors and actions`

**Impl**:
- `_lib/schemas/arch_handoff_schema.json` 注释修订: "contract v2 = base + v2_additive (roadmap_fragments_dir, adr_regex) + v2_additive_routing (planner_feedback 在独立文件)"
- ADR-0042 落盘 (修订 ADR-0016/0028/0038/0041):
  - ADR-0016 → handoff schema 注释更新
  - ADR-0028 → role ownership: planner owns `.planner-feedback.json`
  - ADR-0038 → planner 扩展职责
  - ADR-0041 → 无变更
- `docs/architecture/rdd-arch-rdd-planner-integration.md` — 集成文档 (含 §3 完整示例)
- 重新生成 `docs/adr/README.md` ADR 索引
- `docs/adr/ADR-0042-rdd-arch-rdd-planner-bidirectional-feedback.md`

### Change 6: 回归门 + 全链路验证

执行以下全量门 (AGENTS.md Archive 前全量回归门):

```bash
# 1. 聚焦回归
python3 -m pytest tests/unit/test_write_arch_handoff_locked.py \
  tests/unit/test_planner_feedback_model.py \
  tests/unit/test_planner_feedback_writer.py \
  tests/unit/test_rdd_arch_metadata.py \
  tests/unit/test_rdd_arch_status.py \
  tests/unit/test_arch_handoff_v2_schema.py \
  tests/unit/test_planner_state.py \
  tests/unit/test_planner_sync.py \
  tests/unit/test_planner_cli.py \
  tests/unit/test_adr_index_gate.py -q

# 2. 集成测试
bats tests/integration/test_rdd_arch_cli.bats \
     tests/integration/test_legacy_guide_arch_shim.bats \
     tests/integration/test_planner_feedback_cli.bats \
     tests/integration/test_planner_feedback_loop.bats \
     tests/integration/test_arch_handoff_compat.bats \
     tests/integration/test_planner_cmd.bats

# 3. 全量快速回归
./test.sh --quick

# 4. 全量回归 (AGENTS.md Archive 前强制门)
./test.sh --full --regression

# 5. 不变量验证
git status --short .rddf/improvements/        # 应为空 (零触动)
bash tests/scripts/report_regression.sh       # vs KNOWN_FAILURES baseline

# 6. Identity 一致性 (AGENTS.md #25)
python3 -c "import _lib.planner_feedback as a; import skills._lib.planner_feedback as b; assert a is b"
```

---

## 5. 风险与缓解 (修订)

| 风险 | 缓解 | 来源 |
|---|---|---|
| planner_feedback 与 arch-handoff 双契约混淆角色 | 独立文件 + FileLock 独立 + schema 注释明确 + ADR-0042 修订 ADR-0028 | Metis 4.1 |
| rename blast radius 漏改 | 列出 15 个活跃文件清单 + 提取为 Change 1 步骤 6 + extraction bats 测试锁定 | Oracle A-1 |
| 842 行复刻反模式 | `git mv` 单源 + shim 仅 5 行 | Oracle A-1 |
| write_arch_handoff 无锁 CAS 设计失效 | **Change 0 优先** 改造 + FileLock + atomic_write + planner_state 模式 | Oracle C-1 |
| 反馈陈旧导致 architect 行动错位 | 三标识绑定 (commit + arch_handoff_revision + planner_state_last_sync_at) + Freshness 显示 | Metis 3.3 |
| 重复反馈刷屏 | fingerprint 幂等去重 + last_seen_at 更新 | Metis 3.4 |
| 多 worktree 反馈串扰 | branch + worktree_root 字段 + ADR-0034 模式 | Metis 3.5 |
| in-flight session 中断 | session identity 兼容矩阵 + 自动迁移 intent 字段 | Metis 3.6 |
| handoff/feedback 损坏 | `exit 3` + stderr 明确 + 不静默覆盖 + 保留 .tmp 备份 | Metis 3.2 |
| v1 consumer 不接受 v2 handoff | consumer-side compat 测试 + existing tests 跑 v2 fixture | Oracle E |
| 测试文件命名混乱 | 拆为 test_rdd_arch_metadata.py + test_legacy_guide_arch_shim.py 双轨 | Oracle A-1 |
| install.sh --global symlink 残留 | install.sh 幂等迁移脚本 + 文档化手动步骤 | Oracle E |

### 错误策略表 (Metis 5.4)

| 情况 | planner feedback write exit | arch-done gate | 主状态写入 | 反馈写入 |
|---|---:|---|---|---|
| handoff 缺失 | 0 (warning) | unchanged | 正常 | 写 (computed_from arch_handoff_revision=null) |
| handoff 损坏 | 3 | unchanged | 不覆盖 | 不写 |
| feedback 文件损坏 | 2 (rebuild) | unchanged | 不覆盖 | 重建为空 + 重新 compute |
| feedback lock 超时 (5s) | 3 | unchanged | 不覆盖 | 不写 |
| planner_state schema 不匹配 | 3 | unchanged | 不写 | 不写 |
| compute_planner_feedback 异常 | 3 | unchanged | 保留旧 state | 不写 |
| ack/resolve/dismiss 反馈 id 不存在 | 2 | unchanged | — | 不写 |

---

## 6. 关键决策点 (用户已批准)

| 决策 | 选择 | 影响 |
|---|---|---|
| 反馈生命周期 | **持久化 review 任务** | feedback_id/status/severity/fingerprint/computed_from, --acknowledge/--resolve/--dismiss 三命令 |
| 角色边界 | **独立文件** | planner owns `.planner-feedback.json`, arch owns `.arch-handoff.json`, ADR-0028 修订 |
| handoff 版本 | **正式化 v2** | schema 注释明确, 不改 version 字段, 现有 consumer 零迁移 |

---

## 7. Rename Blast Radius 清单 (Oracle A-1 补救)

**活跃文件需更新 (15 个)**:

| 文件 | 更新类型 |
|---|---|
| `skills/guide-arch/SKILL.md` | `git mv` → `skills/rdd-arch/SKILL.md`, 全文 rename + frontmatter |
| `skills/guide-arch/scripts/*.sh` (17) | `git mv` 整个目录到 `skills/rdd-arch/scripts/` |
| `skills/guide-arch/scripts/*.py` (3) | 同上 |
| `skills/guide-arch/scripts/*.env.py` (1) | 同上 |
| `tests/unit/test_guide_arch_metadata.py` | 拆分为 `test_rdd_arch_metadata.py` + `test_legacy_guide_arch_shim.py` |
| `tests/integration/test_arch_*_extraction.bats` (8) | 路径断言改为 `skills/rdd-arch/scripts/` |
| `skills/guide/scripts/scan-state.sh` | 推荐字符串 + 路径 |
| `skills/rddf-session/scripts/rddf_session_hooks.sh` | skill arg 双值接受 (guide-arch + rdd-arch) |
| `skills/guide-ship/scripts/ship_review.sh` | 引用路径 |
| `_lib/state_reader.py` | display text (不改 logic) |
| `_lib/gate.py` | display text |
| `_lib/workflow_synthesizer.py` | phase name reference |
| `AGENTS.md` (活跃 section) | 23 处 → rdd-arch (sed 限定段落, 不动 archive/ 历史) |
| `README.md` (活跃 section) | 10 处 |
| `USAGE.md` | 15 处 |
| `CHANGELOG.md` | 新增 v3.x entry (不改历史) |
| `package.json` | skill names 列表 |
| `install.sh` | 幂等迁移脚本 (检测 ~/.agents/skills/guide-arch 残留) |

**archive/ 与 openspec/changes/archive/ 不动** (1269 处中大部分)

---

## 8. 交付清单

- [x] plan 文档 (v2, 本文件)
- [x] Oracle 评审回复 (3 个 blocker 已识别)
- [x] Metis 评审回复 (7 个阻塞已识别)
- [x] 3 个核心决策 (用户已批准: 持久化/独立文件/正式化v2)
- [ ] 用户审批 plan v2
- [ ] Change 0 (write_arch_handoff 锁改造) — **Oracle blocker, 必须先做**
- [ ] Change 1 (rename git mv + blast radius)
- [ ] Change 2 (独立文件 + 持久化模型)
- [ ] Change 3 (planner CLI 三命令)
- [ ] Change 4 (arch Phase 1 读取)
- [ ] Change 5 (ADR-0042 + compat + 集成文档)
- [ ] Change 6 (全量回归门)
- [ ] `./test.sh --full --regression` 全绿

---

## 9. 用户最终审批前请确认

请用户在实施前最后确认：

1. **blast radius 清单 §7** 包含 15 个活跃文件是否完整？
2. **deprecation 锚定** "v3.x + 2 minor release" (≈ 2026-12) 是否合适？
3. **Change 0 优先** (write_arch_handoff 锁改造) 是否同意作为前置？
4. **archive/ 与历史文件不动原则** 是否同意？
5. **持久化反馈** 用 `.rddf/state/.planner-feedback.json` 路径是否合适？