# 验收报告 — fix-test-isolation-and-hygiene

- **日期**：2026-11-04
- **验收角色**：`verifier`（source: user）
- **被验对象**：`openspec/changes/fix-test-isolation-and-hygiene`（work-tree，in-place 实施，未 commit）
- **已用轮次**：1 / 3

## 判据来源（按优先级）

1. 用户本次明确给出的验收条件：无单独声明 → 取下一层
2. `openspec/changes/fix-test-isolation-and-hygiene/proposal.md` 的 `## 验收标准`（**19 条 AC**）
3. 本次实施自己声明的内容：`tasks.md`（6 Task，**35 个 Step 全部勾选完成**）

## 分流判定（rdd-verifier skill 三条件）

| # | 条件 | 结果 |
|---|---|---|
| 1 | change 存在 + `proposal.md` 含 `## 验收标准` 段 | ✅ |
| 2 | P3 archive gate 触发（`discover_eligible()` 口径：`iteration.json` 中 `status ∈ {in_worktree, completed}` ∧ `tasks_done == tasks_total > 0`） | ❌ **不满足** —— 该 change 未登记进 `.rddf/state/iteration.json`；`./rddf rdd-verify --dry-run` 输出 `No eligible changes to verify (empty queue)` |
| 3 | `skill` 可加载 `rdd-verifier` | ✅（`rdd-skills.sh --json` → `installed: true`，`available[]` 含 `rdd-verifier`） |

→ **未命中分流，走本地验收 1–5 步**。
→ 「本地验收额外门」（`tasks_done == tasks_total > 0`）由 `tasks.md` 直接取证：**未勾选 Step = 0**，意图满足。`iteration.json` 缺条目记为观察项（verifier 不改状态，不自行登记）。

## 逐条判定

| AC | 判定 | 证据 |
|---|---|---|
| AC-1 全部调用显式传 `--cache-file` | ⚠️ **PARTIAL（proposal_drift）** | 5 个调用点、4 处传参。**用例 A（`test_rddf_cross_repo_cli.bats:46`）故意不传** —— 它正是测「默认路径不得落在 CWD」的用例，`tasks.md` Step 1.3 明文写「用例 A 除外」，且该用例结束时自清理 `rm -f "$real_cache"`。**AC 文本未同步这条例外** |
| AC-2 跑 bats 后仓库无缓存文件 | ✅ | 跑前 `ls` → No such file；`bats tests/integration/test_rddf_cross_repo_cli.bats` → 5/5 ok；跑后 `ls` → No such file |
| AC-3 默认值绝对路径落在项目根 | ✅ | `cross_repo_cli.py:43-45` → `default=str(PROJECT_ROOT / ".rddf" / "state" / ".cross-repo-deps-cache.json")`；`CWD=/tmp` 实测 `PROJECT_ROOT = <repo root>` |
| AC-4 无层数算术 | ✅ | `grep -nE '_skills_dir\|_project_root = os\.path\.dirname'` → 无命中 |
| AC-5 默认历史路径 | ✅ | `append_history.py:44` → `PROJECT_ROOT / ".rddf" / "state" / ".quick-history.jsonl"` |
| AC-6 含 `skills/_lib/` 的仓库仍落仓库根 | ✅ | 前置成立（`skills/_lib/` 存在，正是骗过旧启发式的目录）；实测 `HISTORY_FILE = <repo root>/.rddf/state/.quick-history.jsonl` |
| AC-7 resolver 归位 + identity-merge | ✅ | `_lib/_python_resolve_project_root.py` 1844 B（实现）；`skills/_lib/_python_resolve_project_root.py` 197 B（shim）；`shim is real → True` |
| AC-8 既有 importer 未改路径仍可 import | ✅ | 原 5 个 importer（`propose`×2 / `report-issue` / `sync-hub` / `watch-hub`）import 路径未改，全部 AST 可解析；`import skills._lib._python_resolve_project_root` ok |
| AC-9 `.gitignore` + `skills/.rddf` | ✅ | `.gitignore:17 skills/.rddf/`；目录不存在；`git check-ignore -v` 命中第 17 行；`git status --porcelain` 无 `skills/.rddf` |
| AC-10 根目录 0 字节文件 | ✅ | `python3` / `.gitignorebash` 均 No such file |
| AC-11 state 快照 | ✅ | `iteration.corrupt` = 0；`before-*` = 0 |
| AC-12 孤儿 worktree | ✅ | `.rddf/wt/test-change` 不存在；`git worktree list` = 2 项（主仓 + `/tmp/opencode/baseline-wt`），与删除前一致 |
| AC-13 doctor state 类 CRITICAL | ✅ | `Summary: 0 CRITICAL · 72 WARNING · 7 INFO`；引用 `cross-repo-deps-cache` 的 finding = 0；无 `[state]` 类 finding |
| AC-14 `plan-tdd` 96 → 0 | ✅ | `./rddf doctor \| grep -c 'plan-tdd'` → 0 |
| AC-15 CWD 无关性 | ✅ | `CWD=/tmp` 时 `PROJECT_ROOT = <repo root>`；`/tmp/.rddf` 不存在 |
| AC-16 `pytest tests/unit/` 无新增失败 | ✅ | 全量跑：`3220 passed, 2 skipped`（基线 `3206 passed + 1 failed`；+13 新测试全 pass，基线那 1 个失败已修） |
| AC-17 `report_regression.sh` 新增失败 = 0 | ✅ | `已知失败: 11 / 新增失败: 0 / 已修复 (zombie): 0` |
| AC-18 `openspec validate` | ✅ | `Change 'fix-test-isolation-and-hygiene' is valid` |
| AC-19 `doctor --category roadmap-feature` | ✅ | `✅ All 1 categories OK` |

**合计：18 ✅ / 1 ⚠️ / 0 ❌**

> AC-16/17 引用的全量跑（`/tmp/opencode/regress-C.txt`）在**最终代码态**执行：bats 1305 s + unit 124 s + integration 135 s，`ALL PASSED`。该跑之后仓储代码零改动（仅 `tasks.md` checkbox 与 CHANGELOG 文本变动，不影响测试面）。

## 遗留清扫复核

| 项 | 结果 |
|---|---|
| TODO / FIXME / XXX / HACK / 临时标记 | 无 |
| 注释掉的代码 / `breakpoint()` / `pdb` / DEBUG 打印 | 无 |
| 被 skip / xfail 的测试 | 无（3 个新单测 + 1 个 bats 均无 skip） |
| 未替换的 mock | 无（`monkeypatch` 均为 pytest 标准 fixture，非临时打桩） |
| 临时 fallback | 无。`_fallback_root()` 是**设计内**的非 git 回落（docstring 说明了它锚点语义与历史 `os.getcwd()` 的关系），非临时补丁 |
| `tasks.md` 未完成的 Step | 0 |

## 失败项与路由建议

| # | 项 | 分类 | 路由 |
|---|---|---|---|
| 1 | **AC-1 文本过宽**：写「全部调用显式传 `--cache-file`」，实现有 1 处显式例外（用例 A 专测默认路径，且自清理）。`tasks.md` Step 1.3 已写明例外，**只有 proposal 的 AC 文本没同步** | `proposal_drift`（实现与 AC 不符，但实现是对的） | 回 `builder` 改 **AC 文本**（不是改代码）：收窄为「除专门测默认路径的用例外，全部调用显式传 `--cache-file`」 |

**无 `implementation_gap`，无需回改代码。**

## 观察项（不阻断，供后续 change 参考）

1. **`iteration.json` 未登记该 change** → `rdd-verifier` 的 `discover_eligible()` 永远返回空，skill 无法接管验收（本次只能走本地验收）。根因：3 个 change 都是手工创建的，没经过 `rdd-planner` 的登记流程。**这不属于本 change 的缺陷**，是流程层缺口（治理层规则明令禁止为凑前置条件而伪造 handoff，所以本报告不做补登记）。
2. **工作区混两条工作线**：`git status` 里 `skills/rdd-arch/scripts/adr_shape_check.sh`、`docs/adr/ADR-0060-*`、`_lib/arch_quality_gate.py` 等属另一条在途工作线（`fix-agent-interface-contracts`），不在本次验收范围。提交时必须选择性 stage。
3. `doctor` WARNING 由 71 → 72：新增的 feature fragment 引入了 1 条非 state 类 WARNING，不影响 AC-13（只判 state 类）。

## 结论

**PASS（实现层）**，附 1 条 `proposal_drift`（AC 文本收窄）。3 个真 bug 全部修复且有工具证据：
- 测试不再污染真实 `.rddf/state/`（缓存文件跑完 bats 后不存在）
- `rdd-quick` 审计日志从 `<repo>/skills/.rddf/` 回到 `<repo>/.rddf/`，且 CWD 无关
- resolver 的 CWD 基准缺陷由「探针锚点」消除，契约测试未回归

遗留清扫全清，无 skip / TODO / 临时调试。可直接进入提交与 B/C 后续 change。
