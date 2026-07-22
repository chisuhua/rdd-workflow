---
SCOPE: shared
STATUS: PROPOSED
---

## Why

OpenSpec 工作流在 `add-spec-validation-gates` ship 流程(2026-07-15)暴露了一个 ship-flow 缺陷:`openspec archive <name>` 移动文件后**不自动 commit**,导致每个归档步骤都留下 dirty working tree。

**复现路径**(已验证):

```bash
$ git status   # 干净
$ openspec archive add-spec-validation-gates --yes
$ git status
On branch master
Changes not staged for commit:
  deleted:    openspec/changes/add-spec-validation-gates/.openspec.yaml
  deleted:    openspec/changes/add-spec-validation-gates/design.md
  deleted:    openspec/changes/add-spec-validation-gates/proposal.md
  deleted:    openspec/changes/add-spec-validation-gates/specs/spec-validation-gates/spec.md
  deleted:    openspec/changes/add-spec-validation-gates/tasks.md

Untracked files:
  openspec/changes/archive/2026-07-15-add-spec-validation-gates/
  openspec/specs/spec-validation-gates/
```

**这是手工 ship 流程最后一个遗忘点**:实现 commits 全干净,openspec archive 成功,但 5+ 个文件等待手工 `git add` + 手工写 commit message。本次我自己差点遗忘 — 在 regression 总结轮才发现 working tree 不干净。

**根本原因**:`openspec` CLI 把"归档"视为文件操作,而非 git 操作。`skills/_lib/archive.sh` 的 `archive_change` 函数已经做了:pre-merge check → checkout default → merge → openspec archive → cleanup → mark iteration,**唯独缺了 git commit 这一步**。轻量模式(`guide-ship.md` Phase 3)直接 inline 调用 `openspec archive`,同样问题。

**影响**:
- 每归档一次就要手工构造 `archive(<name>): archive completed` 消息,消息格式不一致
- 用户容易遗忘,可能推到 origin 时 working tree 还在 archive 移动后状态
- 与 `mark_iteration_archived` 等已有 post-archive 钩子设计不一致

## What Changes

新增 1 个 helper + 在 2 处调用的 ship 端钩子 + 1 个 bats 集成测试 + 文档更新。

| 文件 | 变更类型 | 职责 |
|---|---|---|
| `skills/_lib/archive.sh` | **新增 helper** + 修改 | `commit_archive_moves <name> <main_root>` (stages 3 paths + commits); `archive_change` 在 `openspec archive` 后调用 |
| `skills/guide-ship.md` | 修改 | Phase 3 轻量模式 inline 调用 `openspec archive` 后调用 helper |
| `tests/integration/test_commit_archive_moves.bats` | **新增** | 集成测试:模拟归档流程,验证产生 auto-commit |
| `AGENTS.md` | 修改 | 在"归档流程"段追加 1 段说明新行为 + opt-out env var |

### Capabilities

#### New Capabilities

- **`archive-auto-commit`**: `skills/_lib/archive.sh::commit_archive_moves <name> <main_root>` helper
  - 检测 `SKIP_ARCHIVE_AUTO_COMMIT=yes` → 跳过(opt-out)
  - 检测 working tree 干净(已归档)→ 跳过(idempotent)
  - 否则 stage 3 个路径:`openspec/changes/<name>/` (deletion) + `openspec/changes/archive/<date>-<name>/` (新增 archive dir) + `openspec/specs/<new-cap>/` (新主 spec)
  - git commit 消息:`archive(<name>): archive completed` (匹配 commit `0d6ba45` 的 repo convention)
  - 失败时:`git reset HEAD` 回滚 stage,不污染 index

#### Modified Capabilities

- `skills/_lib/archive.sh::archive_change` 流程末尾在 `openspec archive` 之后、`cleanup worktree/branch` 之前调用 helper
- `skills/guide-ship.md` Phase 3 轻量模式段在 `openspec archive "$CHANGE_NAME" --yes` 之后调用 helper

## Impact

- **影响文件**:
  - `skills/_lib/archive.sh` +30 LOC(helper function + hook call)
  - `skills/guide-ship.md` +8 LOC(轻量模式追加 helper call)
  - `tests/integration/` 新增 1 个 .bats 文件 ~50 LOC
  - `AGENTS.md` +5 LOC(说明段落)
- **破坏性变更**: 无。失败时仅 opt-out (env var) 或写日志。
- **API 变更**: 无。helper 是内部 bash 函数,不暴露 skill 接口。
- **外部依赖**: 无新增。纯 git + bash。
- **跨仓影响**: 无。rdd-workflow meta-repo only。

## Acceptance Criteria

- [ ] `commit_archive_moves` 在 archive.sh 头部列出 export 名单
- [ ] `archive_change` 自动 commit archive 后产生 exactly 1 个新 commit 在 default branch
- [ ] `guide-ship.md` Phase 3 轻量模式自动 commit
- [ ] `SKIP_ARCHIVE_AUTO_COMMIT=yes` 完整跳过 helper(no stage, no commit)
- [ ] helper idempotent:已 commit 后再调用 → exits 0,无新 commit,无 working tree 改动
- [ ] commit 消息格式:`archive(<name>): archive completed` (匹配 `0d6ba45 archive(status-guide-revision)`)
- [ ] helper 在 stage/insert 失败时调用 `git reset HEAD` 防止污染 index
- [ ] bats 测试覆盖:正常路径、SKIP env var、idempotent、commit message 断言
- [ ] 所有现有测试通过(551 unit + 76 integration + bats)
- [ ] CI 不被破坏
- [ ] AGENTS.md 新段落说明行为

## Risk

- **误 commit 风险**(低):若 helper 把不想 commit 的文件一起 stage,会污染。**Mitigation**:严格只 stage 3 个明确路径,不 stage 全 `openspec/`。
- **commit message 错误格式**(低):helper 写死的消息,但用户可能想自定义。**Mitigation**:无 flag,env var 跳过即可。
- **race condition**(低):helper 调用时若有并发 git 操作可能冲突。**Mitigation**:helper 在 ship 流程串行调用,无并发场景。
- **测试环境耦合**(中):bats 集成测试需要 `git init` + `openspec new change` CLI 可用。**Mitigation**:用 skip helper 包裹缺失依赖,CI 环境完整。

## Supersession / Dependencies

- **不 supersede** 任何现有 change
- **依赖** `archive.sh` 已存在的 `archive_change` 函数(本次修改它)
- **依赖** `worktree.sh` 的 `main_repo_root` 函数
- **依赖** `openspec` CLI v1.4.1+
- **解锁**:未来可加 `harden-ship-auto-push` change(helper 的 push 版本)
