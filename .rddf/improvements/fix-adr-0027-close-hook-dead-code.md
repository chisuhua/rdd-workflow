# fix-adr-0027-close-hook-dead-code

**优先级**: P1 | **来源**: Oracle 复核 2026-08-24(G1 + G2)
**阶段**: v2.1.x | **分类**: infra-quality | **类型**: fix

## 架构依据

ADR-0027 §6(Close 环)规定:`guide-ship` Phase 3 archive 成功后,自动关闭通过 `issue_refs` 关联的 GitHub issue。第 5 环是反馈环闭环关键,但 Oracle 复核发现**实现是死代码**——所有调用恒 no-op,用户无任何报错。

### G1(核心)— Close 环整个是死代码

**事实**:`openspec archive <name>` 把 `openspec/changes/<name>/` **移动**到 `openspec/changes/archive/<name>/`。但 `_lib/archive.sh:422` 先 archive,`:428` 才调 close hook,而 `close_issues.py:133` 读的是 PRE-move 路径:

```bash
# _lib/archive.sh:422-428 (worktree 模式)
if ! openspec archive "$name" --yes; then     # ← 移动发生在此
    ...
fi
close_issues_for_change_hook "$name" "$main_root" || true  # ← hook 在后
```

```python
# _lib/close_issues.py:129-144
def _load_issue_refs(change_name, project_root):
    meta_path = Path(project_root) / "openspec" / "changes" / change_name / "roadmap-meta.yaml"
    # ↑ 永远是 archive/ 不存在的旧路径
```

**Lightweight 模式同样有 bug**:`skills/guide-ship/scripts/ship_archive.sh:239` 在 `openspec archive` 之后调同一 hook。

**测试盲区**:`tests/integration/test_archive_close_dual_mode.bats:26` 用**行号断言固化错误顺序**(断言 hook 在 archive 之后),单元测试全部用 `tmp_path` fixture 从不走真实 post-archive 布局。这共同造成:
- 修复 hook 顺序 → 测试失败
- 修复测试断言 → 行号次序改
- 永远没测试覆盖"真实 post-archive 路径下 hook 找到文件"这条路径

### G2(retention 死亡)— `closed_at` 字段永不写入

**事实**:`close_issues.py:208` 用 `dedup_hash == issue_number` 匹配来更新本地 issue 文件的 `closed_at`,但 `dedup_hash` 是 8 位 hex(从 stack trace 归一化算出)、`issue_number` 是 GitHub issue 整数——恒不匹配 → `closed_at` 永不写入 → `_is_old_closed()` 恒 false → `prune_old_issues()` 永不删 `.rddf/issues/` 中已关闭的文件 → retention 机制全死亡。

`retention_days: 30` 配置项无论怎么设都无效。

### 根因分析

`archive.sh` 把 hook 放在 archive 之后看似合理(archive 失败了不必关 issue),但 `openspec` 的 archive 命令是**移动语义**,不是"标记删除 + 删除"语义。这意味着 hook 不能简单靠"改顺序"或"重试"修复——必须在 hook 内**自身**处理路径已变的事实。

G2 则是 close 逻辑写完没考虑 dedup_hash 与 issue_number 的不匹配,简单地把两者当作 interchangeable。

## 范围

### In Scope

1. **PR-2.1**:`_lib/close_issues.py::_load_issue_refs` 加 `archive/` 回退路径(无需改 archive 主流程):
   ```python
   candidates = [
       Path(project_root) / "openspec" / "changes" / change_name / "roadmap-meta.yaml",
       Path(project_root) / "openspec" / "changes" / "archive" / change_name / "roadmap-meta.yaml",
   ]
   for meta_path in candidates:
       if meta_path.is_file():
           # parse and return
   return [], "chisuhua/rdd-workflow"
   ```
2. **PR-2.2**:`_lib/close_issues.py::_update_local_issue_files` 改匹配逻辑为按 `submitted_url` 末尾 `/issues/<N>` 反向匹配:
   ```python
   for ref in issue_refs:
       target_url_tail = f"/issues/{ref}"
       for issue_file in issues_dir.glob("*-*.md"):
           frontmatter = parse_frontmatter(issue_file)
           if frontmatter.get("submitted_url", "").endswith(target_url_tail):
               frontmatter["closed_at"] = now_iso()
               issue_file.write_text(render(frontmatter))
   ```
3. **PR-2.3**:更新 `tests/integration/test_archive_close_dual_mode.bats`:
   - **删除**:line 26 的"hook 必须在 openspec archive 之后"的断言(这条断言**强制**实现 bug)
   - **新增**:真实 post-archive 路径下 hook 找到文件并调用 `gh issue close` 的回归测试(用 `fake_openspec_archive` mock 把 archive 行为模拟为移动语义)
4. **PR-2.4**:`_lib/close_issues.py` top-level docstring 更新,说明"hook 容忍 archive 已移动"的设计

### Out of Scope

- **不**改 archive 主流程(用户已依赖现有 archive 行为)
- **不**改 `openspec archive` CLI 行为(`openspec` 是外部依赖)
- **不**新增 retry 机制(本提案只修"能找到文件",retry 由后续 PR 处理)
- **不**改 retention 策略(30 天默认值与本 PR-2.2 互补,但属另一主题)

## 关键场景

### 场景 A:worktree 模式 archive 后 close(主场景)

**GIVEN** `guide-ship` Phase 3 worktree 模式,change `add-foo-feature` 有 `issue_refs: [42, 123]`
**WHEN** `archive_change add-foo-feature main` 完整执行
**THEN**
1. `openspec archive add-foo-feature --yes` 成功,`openspec/changes/add-foo-feature/` 移到 `archive/`
2. `close_issues_for_change_hook` 调 `_load_issue_refs`
3. `_load_issue_refs` 尝试 `openspec/changes/add-foo-feature/roadmap-meta.yaml`(不存在)→ 回退到 `openspec/changes/archive/add-foo-feature/roadmap-meta.yaml`(命中)→ 返回 `[42, 123], 'chisuhua/rdd-workflow'`
4. `submit_gh_close(42) + submit_gh_close(123)` 成功,exit 0
5. `.rddf/issues/flow-bug-a1b2c3d4.md` 的 frontmatter `closed_at: 2026-08-24T...` 写入(因 submitted_url 含 `/issues/42`)

### 场景 B:lightweight 模式 archive 后 close

**GIVEN** Lightweight 模式(主仓库直接 archive,不走 worktree)
**WHEN** `ship_archive.sh` 完成 `openspec archive`
**THEN** 走同一 hook,与场景 A 行为一致

### 场景 C:archive 失败

**GIVEN** `openspec archive` 失败(exit code != 0)
**WHEN** hook 仍然尝试(由 `|| true` 兜底)
**THEN**
- `roadmap-meta.yaml` 未移动 → 第一次候选路径命中 → close 正常执行
- (这是为什么 G1 修复用双路径而不是 hook 顺序的修复:即使 hook 在前 archive 在后,也能工作)

### 场景 D:无 issue_refs 的 change

**GIVEN** change 归档时 `issue_refs` 字段为空
**WHEN** hook 执行
**THEN**
- `_load_issue_refs` 返回 `([], gh_repo)`
- `close_issues_for_change` early-return
- 本地 issue 文件**不变**(不应错误地把所有 issue 标为已关闭)

## 技术约束

### 双路径回退顺序

`changes/<name>/` 必须**优先**于 `changes/archive/<name>/`——后者是 fallback。原因:某些项目可能保留 `changes/<name>/` 软链接(为了 docs 引用),不应让 archive/ 优先覆盖软链接内容。

### `_update_local_issue_files` 必须**幂等**

重复调用必须只产生一次 `closed_at` 更新。检查 `closed_at` 已存在 → 跳过。

### match 失败容错

若 `_update_local_issue_files` 找不到对应的本地 issue 文件(issue 在 GitHub 创建过但本地未保留 md,或 md 已被 retention 删除),仅记录 stderr warning,**不**阻断 close hook 主体。

### 不重新设计 close hook

保持 `_lib/archive.sh::archive_change` 现有 hook 位置(`openspec archive` 之后)和 `_lib/close_issues.py` 的 API 表面,只动内部实现。后续如有 retry/对账需求(如 archive 成功但 `gh issue close` 网络失败),由独立 PR 处理。

## 验收标准

### 功能验收

- [ ] **AC-1**:worktree 模式 archive 后 `close_issues_for_change_hook` 实际调用 `gh issue close 42`(用 mock 或真实 gh,视测试环境)
- [ ] **AC-2**:lightweight 模式行为与 worktree 模式完全一致(共享同一 hook)
- [ ] **AC-3**:`closed_at` 字段在成功 close 后**正确**写入本地 issue 文件 frontmatter
- [ ] **AC-4**:重复调用 hook 不产生副作用(幂等)
- [ ] **AC-5**:找不到本地 issue 文件时,只 stderr warn,不 return error
- [ ] **AC-6**:无 `issue_refs` 的 change 归档时,hook 早返回且 exit 0

### 测试

- [ ] **新增** 1 unit 测试 (real path layout)
  - `tests/unit/test_close_issues_post_archive.py::test_load_issue_refs_archive_fallback`
  - fixture: 模拟 post-archive 布局(`changes/archive/<name>/roadmap-meta.yaml` 存在)
- [ ] **新增** 1 unit 测试 (closed_at matching)
  - `test_update_local_issue_files_matches_by_submitted_url`
  - fixture: 用 submitted_url 含 `/issues/42` 的 md,验证 closed_at 写入
- [ ] **修改** `tests/integration/test_archive_close_dual_mode.bats`
  - **删除** line 26 "hook 必须在 archive 之后"的行号断言
  - **新增** 真实 post-archive 路径下 hook 行为的 round-trip 测试
- [ ] **新增** 1 unit 测试 (no issue_refs early-return)
  - `test_close_issues_early_return_when_no_refs`

### 向后兼容

- 不改 `close_issues_for_change_hook` 的签名和返回类型
- 不改 `_lib/close_issues.py::close_issues_for_change` 的 docstring 契约
- 不改 `_lib/archive.sh:428` 和 `skills/guide-ship/scripts/ship_archive.sh:239` 的调用方式

## 依赖

- **依赖**:`fix-adr-0027-cli-optin-gate`(PR-1)已合并——close hook 调用 `gh issue close` 也需经过 opt-in 闸门
- **阻塞**:无
- **后续**:与 PR-3 配对验证(完整 issue 文件必须含 submitted_url 字段,才能让 PR-2.2 匹配生效)

## 相关 ADR/文档

- [ADR-0027 §6](docs/adr/ADR-0027-continuous-evolution-feedback-loop.md) Close 环设计
- [Oracle 复核记录](docs/architecture/improvement-check-mechanisms.md#五oracle-复核) §5.3 G1/G2
- `_lib/close_issues.py:129-144` `_load_issue_refs` 当前实现
- `_lib/close_issues.py:208` `_update_local_issue_files` 当前实现
