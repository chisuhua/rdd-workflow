# retire-status-skill 验收报告

- **验收时间**：2026-11-20
- **实现提交**：`2f428eb2`（`refactor(skills): 退役 status 子技能（归档到 docs/legacy/）`）
- **验收角色**：verifier（只验不改）
- **已用轮次**：第 1 轮 / 上限 3
- **结论**：**11/11 AC pass**，无失败项

## 判据来源（按优先级）

1. 用户本次明确要求（退役 `skills/status`；归档前检查遗留/债务）
2. `openspec/changes/retire-status-skill/proposal.md` 的 `## Acceptance` 段（AC-1 ~ AC-11）

两者一致，无冲突。

## 分流判定

命中 `rdd-verifier` skill 三条件：

| 条件 | 结果 |
|---|---|
| `openspec/changes/retire-status-skill/` 存在且 proposal 有 `## Acceptance` 段 | ✅ |
| P3 archive gate 触发（`status=in_worktree`、`tasks_done==tasks_total==74>0`、未归档） | ✅ `rddf rdd-verify --dry-run` 报 1 change |
| `skill` 可加载 `rdd-verifier` | ✅ |

⇒ 按 skill 的 LLM Verification Protocol 执行；verdict 落在
`.rddf/state/verifier/.ac-verdict-retire-status-skill.json`，
审计追加到 `.ac-verification.jsonl`。

## 逐条判定与证据

| AC | 判定 | 证据（命令 → 输出摘要） |
|---|---|---|
| AC-1 源码归档 | **pass** | `test ! -d skills/status` → 通过；`test -f docs/legacy/skills/status/SKILL.md` → 通过；`grep -n 'skills/status/' docs/legacy/README.md` → `:20`，含日期 2026-11-20 + 依据 |
| AC-2 配置 | **pass** | `python3 -c "…assert 'status' not in d['skills'] and len(d['skills'])==26"` → ok；`grep -q 'skills/status' pyrightconfig.json` → 无命中；`python3 -m json.tool pyrightconfig.json` → 通过 |
| AC-3 `status_helpers.sh` 归档 | **pass** | 正向 `test -f docs/legacy/status_helpers.sh` → 通过；反向 `_lib/` 与 `skills/_lib/` 均不存在；`ls skills/_lib/*.sh \| wc -l` → **16**；`bats test_install_lib_distribution.bats` → 全部 ok |
| AC-4 专测文件删除 + 0 命中 | **pass** | 10 个文件逐个 `test ! -e` → 全部不存在（AC 文本写 9，metis 提为 10）；`grep -rq 'skills/status' tests/ --include='*.bats' --include='*.py'` → 0 命中 |
| AC-5 三向对齐 | **pass** | `bats test_skill_metadata_consistency.bats` → `ok 1` / `ok 2` |
| AC-6 文档与计数 | **pass** | `grep 'status/SKILL.md\|status/scripts' README.md AGENTS.md` → 无；`grep '\| \`status\` \|' USAGE.md skills/INSTALL.md docs/architecture/overview.md` → 无；`grep 'skill_use("status")' README.md` → 无；磁盘 26 / `全部 26 个子技能` / `26 SKILL.md + INSTALL.md` 三方一致 |
| AC-7 四个命令 | **pass** | `rddf status` → exit 0，输出含 `Improvement proposals` + `Active changes`（各 1 次）；`rddf dashboard --plain` → exit 0；`rddf iteration --help` → exit 0；`rddf guide` → exit 0 |
| AC-8 `print_view` | **pass** | `python3 -c "from skills._lib.iteration import print_view"` → 导入成功，callable |
| AC-9 无新增失败 | **pass** | `pytest tests/unit/ -q` → 3455 passed / 3 skipped；bats 递归（全量门内）→ 新增失败 0 |
| AC-10 全量门 | **pass** | `BATS_TIMEOUT=120 BATS_TIMEOUT_RETRY=240 ./test.sh --full --regression` → `rc=0`、未评估 0、新增失败 0、`✅ ALL PASSED` |
| AC-11 归档前清理 | **pass** | 见下节 7 项逐条命令与输出 |

## AC-11：归档前遗留/债务清理（7 项逐条）

| # | 检查项 | 命令 | 结果 |
|---|---|---|---|
| 1 | 测试改动全貌 | `git show --stat HEAD \| grep tests/` + `ls tests/integration/test_status_*.bats` | 13 个测试文件改动（10 删 / 7 改 / 1 新增）；残留仅 `test_status_corrupt_message.bats` —— 属上一 change（`rddf-status-based-on-improvements`），测 CLI，`grep skills/status` **0 引用** ⇒ 保留正确 |
| 2 | `status_helpers.sh` 函数残留 | `grep -rn 'detect_sync_issues\|repair_sync_state' --include=*.{py,sh,bats} _lib/ skills/ tools/ tests/` | **0 命中** |
| 3 | 磁盘推导规则语义等价 | `_disk_change_status()` vs `docs/legacy/skills/status/scripts/status_render_mode_a.sh:29-48` 并排 | **等价**：worktree ⇒ `in_worktree`；committed HEAD 且无 worktree ⇒ `committed`；否则 ⇒ `planned`。两侧分支顺序不同但结果一致（worktree 存在时归档脚本首条件 `has_committed and not has_worktree` 为假 ⇒ 落 `elif has_worktree` ⇒ `in_worktree`） |
| 4 | `overview.md` 的 `guide` 行 | `grep -n '\| \`guide\` \|' docs/architecture/overview.md` | `:82` 存在 —— **既有漂移**（guide 已于 ADR-0063 归档）⇒ 只记录，本 change 不清理 |
| 5 | 子技能计数三方 | `ls skills/*/SKILL.md \| wc -l` + `len(package.json.skills)` + `grep` 文档 | 26 / 26 / 文档 26 —— **一致** |
| 6 | 本次范围内 TODO / 调试 / skip | `git show HEAD -- tests/ _lib/ skills/ \| grep -E '^\+.*(TODO\|FIXME\|breakpoint\(\|pdb\|console\.log)'`；`git show HEAD -- tests/ \| grep -E '^\+.*\bskip\b'` | 两条均 **0 命中**（无 TODO / 无新增调试 / 无新增 skip / 无未替换 mock） |
| 7 | 范围外既有遗留 | `grep -n 'status_helpers' tools/phase2_path_migrator.py`；`grep -n 'execute\|guide-ship' tests/integration/test_hook_boundary.py` | `phase2_path_migrator.py:78` 静态名单仍含 `status_helpers.sh`（零守卫、零测试校验 ⇒ 既有 debt）；`test_hook_boundary.py:9` docstring 仍提已退役的 `execute` / `guide-ship` ⇒ 既有陈旧注释。**均只记录，不清理** |

## 失败项与路由建议

无。`implementation_gap` / `proposal_drift` 均不适用。

## 备注（不阻断）

1. **AC-4 文本与实现的一致性**：AC 原文写「9 个专测文件不存在」，实际删除 10 个（metis 把 `test_skill_style_guide.bats` 判为专测后追加）。AC 判据是「不存在」⇒ 10 ⊇ 9 仍满足，不构成 drift；已在 proposal 4a 表标注原因。
2. **verdict cache 的 `codebase_commit`**：本 change 走轻量模式（无 `openspec/retire-status-skill` 分支），`resolve_implementation_commit` 返回 `None` ⇒ 写 `HEAD`（`2f428eb2`）作为实现提交，与归档时的实际落点一致。归档路径（`openspec archive` + `rddf archive-sync`）不消费 archive gate 的 branch-tip 锚点，不受影响。
3. **`iteration.json` 的 `verification` 字段**：不在 verifier 写集内（`.rddf/state/verifier/**` + `.rddf/reviews/**`），本报告不写入；如需 gate 记账由 build 侧完成。
4. **全量门覆盖最终树**：本轮门在最后一次代码改动（`test_global_install_external_project.bats` 移除 `status`）之后运行，未被后续改动破坏。

## 产物

| 产物 | 路径 |
|---|---|
| 本报告 | `.rddf/reviews/retire-status-skill-verify.md` |
| verdict cache | `.rddf/state/verifier/.ac-verdict-retire-status-skill.json` |
| 审计日志（追加） | `.rddf/state/verifier/.ac-verification.jsonl` |
