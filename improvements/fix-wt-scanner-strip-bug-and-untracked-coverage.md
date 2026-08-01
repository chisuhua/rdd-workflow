# fix-wt-scanner-strip-bug-and-untracked-coverage

**优先级**: P1 | **来源**: session 2026-08-01 `skill_use("guide")` — `_detect_working_tree_issues()` 把工作树修改 (` M` 前缀) 误判为 staged (`M `),并截断 path 首字符; 小型 untracked 文件 (improvements/*.md 类) 完全未上报
**阶段**: default | **分类**: infra-setup
**类型**: bug

## 架构依据

- **ADR-0013**（已采纳）: scan-state 提取到 `skills/_lib/scan-state.sh` + Python synthesizer 在 `skills/_lib/workflow_synthesizer.py`
- **ADR-0018**（已采纳）: arch-quality-gate 强调 "正确性优先于覆盖率" — 错误/截断数据比"漏报"更具误导性
- **触发事件**: session 2026-08-01,主仓库 master (`34b9a95` 之前) 有 ` M proposal-suggestions.md` + `?? improvements/check-project-setup.md` (124 行) + `?? improvements/fix-scanner-fallback-and-orphan-archival.md` (94 行). Scanner `wt_issues` 仅返回 1 条且 category=`staged`、path=`"roposal-suggestions.md"` (缺首字符 `p`); 2 个新 untracked 文件完全未提及
- **复现脚本** (主仓库当前已修复,因为工作树干净,但代码仍在):
  ```bash
  cd /workspace/project/rdd-workflow
  echo "test" >> improvements/check-project-setup.md
  SKILL_DIR=skills/guide bash -c 'source "$SKILL_DIR/scripts/guide_entry.sh" && guide_entry --json' 2>&1 \
    | sed -n '/---BEGIN_RECO_JSON---/,/---END_RECO_JSON---/p' | sed '1d;$d' \
    | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin)['wt_issues'], indent=2, ensure_ascii=False))"
  ```
  **期望** (` M` 才是 working tree only):
  ```json
  [{"category": "modified", "path": "improvements/check-project-setup.md", ...}]
  ```
  **实际**:
  ```json
  [{"category": "staged", "path": "mprovements/check-project-setup.md", "detail": "已暂存但未提交", ...}]
  ```

## 根因 (2 个独立 bug)

### 根因 1: misplaced `.strip()` 吞掉状态码首字符

`skills/_lib/workflow_synthesizer.py:725` (`_detect_working_tree_issues`):
```python
lines = result.stdout.strip().split("\n")  # ← BUG
```

`git status --short` 用前 2 字符作为状态码 (` M` / `M ` / `MM` / `??` / 等). 调用 `.strip()` 在 split 之前,会同时去掉**首字符的空格**(` M` 变成 `M `) 和**末字符的换行**. 结果:
- 前缀错位:` M` → `M ` → Python 误判为 "已暂存"
- 路径截断:`line[3:]` 仍按原索引切,在新行上变成了"跳过第一个有效字符":
  - 原 ` M improvements/check-project-setup.md` 去掉首空格 → `M improvements/...`
  - `line[:2] = "M "`,`line[3:] = "mprovements/..."` ← 丢了 `i`

**修复** 1 行 (用 `splitlines()` 替代 `strip().split("\n")`,只切不剥):
```python
lines = result.stdout.splitlines()
```

### 根因 2: untracked 文件被完全漏报 (除非 >10MB)

`skills/_lib/workflow_synthesizer.py:771-797` (untracked 处理):
```python
untracked = subprocess.run(
    ["git", "ls-files", "--others", "--exclude-standard", "--directory"], ...
)
...
for entry in untracked.stdout.strip().split("\n"):
    if not entry.endswith("/") or entry.startswith("."):
        continue  # ← 仅处理目录且非隐藏
    ...
    if size_mb > 10:
        issues.append(...)
```

**问题**:
- 只处理**以 `/` 结尾的目录条目** (`--directory` flag 让 `ls-files` 把未跟踪目录折叠成单个 `dirname/` 行)
- 单文件 (improvements/*.md 类) 因为不带尾斜杠被 `if` 过滤掉
- 即使是目录,也只在 >10MB 时才发 issue

**修复** 移除 `--directory` flag + 移除 `endswith("/")` 过滤,并按 severity 分类:
```python
untracked = subprocess.run(
    ["git", "ls-files", "--others", "--exclude-standard"], ...
)
for entry in untracked.stdout.splitlines():
    if not entry or entry.startswith(".git/"):
        continue
    # 单文件 (e.g. improvements/*.md): severity=info,提示用户登记到 suggestions 表
    # 大目录 (>10MB): severity=safe_auto_fix,提示加入 .gitignore
    if os.path.isfile(os.path.join(project_root, entry)):
        issues.append(WorkingTreeIssue(
            "untracked_file", entry,
            "未跟踪的新文件 (考虑 git add 或登记到 proposal-suggestions.md)",
            severity="info",  # 不阻塞入口
        ))
```

## 范围

**In Scope**:
1. `skills/_lib/workflow_synthesizer.py:725` — `.strip().split("\n")` → `.splitlines()`
2. `skills/_lib/workflow_synthesizer.py:771-797` — untracked 检测:移除 `--directory` flag,加 `untracked_file` category
3. `skills/_lib/workflow_synthesizer.py` `WorkingTreeIssue` 文档字符串 (L124) — category 枚举增补 `"untracked_file"`
4. 新增/扩充测试:
   - `tests/unit/test_wt_scanner_strip_bug.py`: 3 case (input 前导空格 / ` M` / `M ` 各种组合)
   - `tests/unit/test_wt_scanner_untracked.py`: 4 case (单文件 / 目录 / 隐藏目录 / 已知 >10MB 目录)
5. `tests/integration/test_guide_entry_wt_issues.bats`: 端到端验证 `guide_entry --json` 输出
6. AGENTS.md "状态文件" 表格 + docs/adr/ADR-0013 不需要更新 (逻辑层,非契约层)

**Out Scope**:
- 不重写整个 scanner 算法 (1 行 + 1 段改动即可)
- 不修改 `check_dirty_key_files` (bash 层,逻辑独立,本 bug 仅在 Python layer)
- 不修改 `git ls-files` 的其他参数 (如 `--exclude-standard` 行为保持)
- 不引入 file hash / 增量检测等额外功能
- 不动 `wt_issues` JSON schema (向后兼容,只新增 category 值)
- 不为 `??` 前缀单独建模 (untracked_file category 覆盖所有非隐藏未跟踪条目,语义已足够)

## 关键场景

**场景 1** (根因 1 修复 — ` M` 正确分类):
- GIVEN 工作树有一个仅修改的文件 (`git status --short` 输出 ` M foo.md`)
- WHEN 调用 `_detect_working_tree_issues(PROJECT_ROOT)`
- THEN 返回 1 条 issue, `category="modified"`, `path="foo.md"` (无截断), `detail="有未暂存的修改"`

**场景 2** (根因 1 修复 — 真 staged 也正确分类):
- GIVEN 暂存一个修改 (`git add foo.md` → `git status` 输出 `M  foo.md`)
- WHEN 调用 scanner
- THEN 返回 1 条 issue, `category="staged"`, `path="foo.md"`, `detail="已暂存但未提交"`

**场景 3** (根因 2 修复 — untracked 单文件被检测):
- GIVEN 工作树有新 `improvements/foo.md` (124 行, ~3KB)
- WHEN 调用 scanner
- THEN 返回 1 条 issue, `category="untracked_file"`, `path="improvements/foo.md"`, `severity="info"`

**场景 4** (根因 2 修复 — 大目录未跟踪仍触发 safe_auto_fix):
- GIVEN `build/` 目录 50MB (未在 .gitignore)
- WHEN 调用 scanner
- THEN 返回 1 条 issue, `category="untracked_dirs"`, `path="build/"`, `severity="safe_auto_fix"`, `fix_command="echo \"build/\" >> .gitignore"`

**场景 5** (端到端 — `guide_entry --json` 不变 schema):
- GIVEN 主仓库 master (干净)
- WHEN 调用 `guide_entry --json`
- THEN `wt_issues` 是空数组, RECOMMEND/REASON/CONFIDENCE/ALL_OPTIONS_JSON 与修复前**字节完全一致** (回归零)

**场景 6** (向后兼容 — 已存在的 `category` 值不变):
- GIVEN 现有 `all_options` JSON 消费者 (例如 AI prompt 解析逻辑)
- WHEN scanner 引入新 category `"untracked_file"`
- THEN 现有消费者对未知 category 做 "skip / display raw" 处理时无回归; 且新 issue `severity=info` 不影响 gate 触发

## 技术约束

**MUST**:
- `.splitlines()` 替代 `.strip().split("\n")` (修根因 1)
- 移除 `--directory` flag,保留 `--exclude-standard` (兼容现有 .gitignore + .git/info/exclude)
- 单文件 untracked 的 severity **必须** `info` (不阻塞入口 menu,不污染 gate)
- 新增 `WorkingTreeIssue` category `"untracked_file"` 时同步更新 dataclass docstring (L124) + 现有 consumes list (e.g. `workflow_synthesizer.py:519-521` 的 `safe_auto_fix/modified/staged/deleted` 计数)
- 测试用现有 `pytest tests/unit/` 和 `bats tests/integration/` 框架,无新增依赖
- 测试夹具:用 `git init` + `echo` + `git add` 在 tmpdir 构造 git 状态,不依赖外部 fixture

**MUST NOT**:
- 不得引入 `--ignored` / `--modified` 等额外 `git status` 参数 (避免双计数/语义重叠)
- 不得让 `untracked_file` issue 触发任何 gate (info-only by design)
- 不得修改 `WT_ISSUES_JSON` 的 JSON 序列化顺序 (现有消费者按 `category/path` 排序)
- 不得修改 `_deduplicate_issues()` (L806) 的去重 key (新 issue 走 `severity != "safe_auto_fix"` 分支,无 fix_command key 风险)
- 不得对 `.rddf/state/` 下其他 JSON 联动修改
- 不得回退到 `os.path.join + byte offset` 等 hack 修复 path 截断 (根因明确,改 split 即可)

**SHOULD**:
- 路径截断 bug 修好后,**SHOULD** 在 `tests/unit/test_wt_scanner_strip_bug.py` 加 1 个 `assert path[0] == expected_first_char` 显式断言,锁住回归
- `untracked_dirs` 检测保留目录大小计算 (`os.walk`),但应缓存 (大目录会慢; 用 `lru_cache(maxsize=128)` 或记入 set)
- 文档里**SHOULD** 标注修复日期 + session hash (`2026-08-01 / my-eci-group_2044384`),方便审计追溯

## 验收标准

1. **根因 1 修好**: `tests/unit/test_wt_scanner_strip_bug.py` 3 case 全 PASS:
   - ` M foo.md` → `category=modified, path=foo.md`
   - `M  foo.md` → `category=staged, path=foo.md`
   - `?? bar.md` (注意替换逻辑后) → category=`untracked_file`, path=`bar.md` (验证 path 不截断)
2. **根因 2 修好**: `tests/unit/test_wt_scanner_untracked.py` 4 case 全 PASS:
   - 单文件 `improvements/foo.md` → category=`untracked_file`, severity=`info`
   - 目录 `build/` (>10MB) → category=`untracked_dirs`, severity=`safe_auto_fix`
   - 隐藏目录 `.venv/` → 不出现
   - 已在 .gitignore 的目录 → 不出现
3. **回归零字节**: 主仓库干净时,`guide_entry --json` 输出 diff = 0 (与未修改代码完全一致)
4. **不阻塞入口**: `untracked_file` severity=info 时,gate 不触发 (wt_issues 中含 info-only 项时,RECOMMEND 输出无变化)
5. **现有测试零修改 PASS**: `tests/unit/test_workflow_synthesizer*.py` + `tests/integration/test_*.bats` 全 PASS (若有失败,需在 commit message 中标注)
6. **CI 流程**: `bats tests/integration/` + `python3 -m pytest tests/unit/ -q` 双绿
7. **行数约束**: 总共 ≤20 行代码变更 (1 行 split + ~10 行 untracked 重写 + ~9 行 dataclass/test additions)
8. **向后兼容**: 现有 JSON 消费者 (guide.md prompt + subagent 调用方) 无破坏,新 category `"untracked_file"` 是 additive
9. **文档**: PR description 列出两个 bug 的复现命令 + 修复前后 diff

## 关联

- 修复后能让 session 2026-08-01 的 cleanup menu 行为更准确 (当时误报 staged + 漏报 2 个 untracked → AI 已独立验证才纠正)
- 与 `fix-scanner-fallback-and-orphan-archival.md` 互补:后者修的是"scanner 不存在" (helper 加载失败), 本改进修的是 "scanner 存在但输出错"
- 未来 `guide-entry` 可结合 `untracked_file` 自动建议 `add-improve` (新文件多半是 improvements/*.md),但这超出本改进 scope
