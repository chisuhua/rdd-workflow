# fix-archive-iteration-sync

**优先级**: P0 | **来源**: Session 复盘 2026-08-05 — 在 UsrLinuxEmu 上 sync `stage4-l2-foundation-removal-*` 5 个 change 的 iteration.json 状态时，发现 archive commit 没有自动 patch iteration.json
**阶段**: v2.1 | **分类**: infra-setup
**类型**: bug

## 架构依据

- **ADR-0017** (已采纳): rddf-session / iteration.json 是工作流核心状态文件；任何归档动作都必须同步更新它
- **现状** (`archive-iteration-sync.md`, P0, 2026-07-21): 已经识别"archive 后 iteration 缺 archived_at"的根因，但只覆盖 `archive.sh::archive_change()` 的 worktree 模式；旁路（on-main 模式、openspec CLI 直归档、`mv openspec/changes/X archive/`）没有被覆盖
- **本提案范围**：将同步逻辑从 `archive.sh` 解耦为 **post-archive hook**（独立函数 `sync_iteration_after_archive(name)`），从所有归档入口（archive.sh、archive_on_main.sh、`rddf status --archive`、openspec archive CLI hook）调用 — 形成一个不可绕过的层

### 本仓库实际复现 (2026-08-05 UsrLinuxEmu session 已验证)

5 个 change 的 archive commit (`b819b9f` / `e1ede1b` / `e07a409` / `8e0eb21` / `6749800`) **全部没有**修改 `.rddf/state/iteration.json`。提交信息均含 `(on main mode)` 字样：

```
$ git log --oneline main | grep 'archive: stage4-l2-foundation-removal'
6749800 archive: stage4-l2-foundation-removal-stream-capture (on main mode)
8e0eb21 archive: stage4-l2-foundation-removal-mem-pool (on main mode)
e1ede1b archive: stage4-l2-foundation-removal-graph (on main mode)
e07a409 archive: stage4-l2-foundation-removal-hardware-puller-emu (on main mode)
b819b9f archive: stage4-l2-foundation-removal-gpu-queue-emu (on main mode)

$ git show 8e0eb21 -- .rddf/state/iteration.json
(empty — 该 commit 没动 iteration.json)
```

后果：用户连续 7 天看到 `rddf status` 报 5 行 divergence warnings（`iteration.json lists X as 'proposed'`），需要人工 reconcile。

## 范围

- **In Scope**:
  - `skills/_lib/iteration/post_archive.py`（新模块）：`sync_iteration_after_archive(name: str, archive_commit_sha: str | None)` 函数，从 iteration.json 找到对应 change entry，写入 `archived_at`、`tasks_done`（如果 tasks.md 在 archive 目录）、`plan_path` 字段
  - `skills/_lib/archive.sh::archive_change()` 末尾调用 `sync_iteration_after_archive`
  - `tools/archive_on_main.sh`（如果存在 / 已存在）末尾强制调用同一个 helper
  - `rddf status --archive <name>` 命令路径同样调用
  - 幂等保证：重复调用不重复写 `archived_at`（已存在的 archived_at 保留原值）
  - 单元测试：直接调用 helper，验证 iteration.json 被正确 patch；重复调用幂等；archive 失败时 helper 不被调用
- **Out Scope**:
  - 不修改 iteration.json schema（schema bump 留给 `rddf-iteration-strict-schema.md` 提案）
  - 不修改 `archive.sh::archive_change()` 的 worktree / merge 逻辑（只增加 hook 调用）
  - 不动 `split-iteration-module.md`（P1，2026-07-21）的拆分计划 — 本提案的 helper 应放在拆分后的 `iteration/store.py` 内

## 关键场景

- GIVEN `archive_change(name)` 完成 worktree merge，WHEN 进入末尾，THEN `sync_iteration_after_archive(name, archive_commit_sha=...)` 被自动调用、iteration.json 写入 `archived_at` 与 `archive_commit_sha`
- GIVEN `archive_on_main.sh` 在 main 分支直接 `mv openspec/changes/X archive/`，WHEN 脚本末尾，THEN 强制调用同一 helper（脚本失败时整个 archive 回滚 — fail closed）
- GIVEN `sync_iteration_after_archive(name)` 已经被调用过一次（archive_commit_sha 已存在），WHEN 重复调用，THEN archived_at / archive_commit_sha 保留原值，不被覆盖（幂等）
- GIVEN helper 调用时 iteration.json 中没有该 name，WHEN 找不到 entry，THEN helper 写 warning 日志并返回 1，不抛异常（避免污染 archive 主流程）

## 技术约束

- MUST 把 helper 放到独立模块（`skills/_lib/iteration/post_archive.py`），便于所有归档入口 import；不允许把逻辑塞进 archive.sh / archive_on_main.sh
- MUST 在调用前用 `jsonschema` 校验 iteration.json 现有内容合法（避免对 corrupt 文件写入导致双重损坏）
- MUST 幂等：`archived_at` 已存在时不覆盖；`archive_commit_sha` 已存在时不覆盖
- MUST NOT 阻塞 archive 主流程：helper 失败应只写 warning，不 raise
- SHOULD 提供 `rddf status --check-archive-sync` 命令，列出"archive 目录存在但 iteration.json 仍 proposed"的 change，方便人工发现历史遗留 divergence

## 验收标准

- 5 个回归测试：正常调用 / 重复幂等 / entry 不存在 / iteration.json corrupt / helper 失败不阻塞 archive
- `archive_change()` 末尾新增 1 行调用
- `archive_on_main.sh`（如果存在）末尾新增 1 行调用
- 实测 UsrLinuxEmu `git revert` 模拟：还原 archive commit 后手动调用 helper，iteration.json 自动 patch 到 archived
- 所有现有 bats / pytest 测试通过
