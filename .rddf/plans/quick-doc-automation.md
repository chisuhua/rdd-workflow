# quick-doc-automation — Eliminate Manual Documentation Drift

> rdd-quick plan (per ADR-0047 + ADR-0048 §Decision 3 amendment).
> Bypass-path: no openspec change, no worktree, in-place execution on current branch.
> AC source = this file's `## Acceptance` section (NOT any openspec proposal).

---

## Goal

Eliminate the **3 documented documentation drift patterns** observed during B 方案 audit (2026-09-11):

1. **AGENTS.md ADR 列表 drift** — 磁盘有 ADR-0050，AGENTS.md 停在 ~0035（反向 drift，无检测）
2. **docs/schemas/README.md drift** — B-3 新建的手写索引 vs 29 个 schema 文件，未来必然漂移
3. **schema 路径误用** — `skills/_lib/schemas/` 被当 canonical 引用（B-2 已修，但无防御）

通过三件交付物闭环：
- **扩展 docs_consistency 检测**（A1 + A2 检测半 + A3 检测半）
- **schema README generator + CI diff check**（A2 生成半，**确定性 fail**）
- **CI 接 doctor step**（A3 集成）

参考 Oracle 建议（A1/A2/A3/A4 评估）+ ADR-0047/0048 + rdd-verifier v2.0 self-contained LLM verification pattern (ADR-0045)。

---

## Acceptance

> 7 个可机器验证的 AC（按 rdd-verifier VERDICT_ITEM_SCHEMA 输出）。

- [ ] **AC-1** `check_adr_list_completeness` 报告 WARNING 当 `docs/adr/` 磁盘上最大 ADR 编号 > AGENTS.md 声明的"当前最新编号"
- [ ] **AC-2** 新增 `check_schema_readme_drift` 报告 WARNING 当 `docs/schemas/README.md` 列出不在 `_lib/schemas/` 的文件 或 漏列 `_lib/schemas/` 内的文件
- [ ] **AC-3** 新增 `check_schema_path_canonical` 报告 WARNING 当 AGENTS.md / README.md 将 `skills/_lib/schemas/` 作为 canonical 路径引用（不在"shim 兼容说明"括号内）
- [ ] **AC-4** `scripts/generate_schema_index.py` 可重复执行，从 `_lib/schemas/*.json` 确定性重新生成 `docs/schemas/README.md`（相同输入产出相同输出）
- [ ] **AC-5** `tests/unit/test_docs_consistency.py` 增加 4 个新 test case（AC-1/2/3 各 1 + AC-4 集成 1），全部 PASS
- [ ] **AC-6** `.github/workflows/test.yml` 增加新 step "Documentation consistency gate (rdd-doctor)" 调 `bash skills/rdd-doctor/scripts/doctor.sh --category docs-consistency --quiet`，**WARNING 不 block**
- [ ] **AC-7** 既有 `tests/unit/`、`tests/integration/`、`bats tests/` 全部 PASS（无 regression）

---

## Files

### Create
| 路径 | 行数估算 | 用途 |
|------|----------|------|
| `scripts/generate_schema_index.py` | ~80 | 从 `_lib/schemas/*.json` 生成 `docs/schemas/README.md` |
| `.rddf/state/.quick-history.jsonl` (append) | 1 entry | rdd-quick P4 audit log |

### Modify
| 路径 | 改动 |
|------|------|
| `_lib/docs_consistency.py` | 扩展 `check_adr_list_completeness`；新增 `check_schema_readme_drift`、`check_schema_path_canonical`；注册到 `run_all()` |
| `tests/unit/test_docs_consistency.py` | 新增 4 test case |
| `.github/workflows/test.yml` | 新增 1 step（不 blocking） |

### Touch (no semantic change)
| 路径 | 用途 |
|------|------|
| `docs/schemas/README.md` | Task 2 Step 3 重生成（输出 diff 须为空） |

---

## TDD 5-Step Tasks

> Per `rdd-workflow-writing-plans` skill 内置 TDD 5 步结构（Write failing test → Verify fail → Implement → Verify pass → Commit）。
> 4 个 Task 顺序执行；Task 4 无 pytest（CI yaml 改 YAML 验证）。
> **Commit 行为**: 按 AGENTS.md "Worktree Commit Flow" §2.5，**单个聚合 commit 在 R10 报告前**，不逐任务 commit。

### Task 1 — A1: 反向 ADR drift 检测

**Step 1 (Write failing test)**: `tests/unit/test_docs_consistency.py` 增加 `test_adr_reverse_drift`：
- mock tempdir 含 `docs/adr/ADR-0050-foo.md`（磁盘有）
- mock `AGENTS.md` 内容声明"当前最新编号: **ADR-0048**"（声明落后）
- 调用 `check_adr_list_completeness()`
- 断言返回值含 `name="adr-list-reverse-drift"` 且 `severity="WARNING"`

**Step 2 (Verify fail)**: 跑 `pytest tests/unit/test_docs_consistency.py::test_adr_reverse_drift -q`，预期 **FAILED**

**Step 3 (Implement)**: 修改 `_lib/docs_consistency.py`：
- `check_adr_list_completeness` 末尾追加反向检查：若 `max(real)` > AGENTS.md 提到的 max 编号，追加 issue `{severity: WARNING, name: "adr-list-reverse-drift", detail, fix_command}`
- 用 regex `r"最新编号[:：]\s*\*\*?ADR-(\d{4})"` 提取 AGENTS.md 声明的最大编号
- 若声明缺失/无法解析，跳过反向检查（避免噪音）

**Step 4 (Verify pass)**: pytest PASS；既有 7 个 test 仍 PASS

**Step 5 (Commit)**: 推迟到 R10 聚合 commit

---

### Task 2 — A2: schema README drift 检测 + generator

**Step 1 (Write failing test)**: `tests/unit/test_docs_consistency.py` 增加 `test_schema_readme_drift`：
- mock tempdir 含 `_lib/schemas/foo.json` + `_lib/schemas/bar.json`（磁盘有 2 个）
- mock `docs/schemas/README.md` 只列出 `foo.json`（README 漏 1）
- 调用 `check_schema_readme_drift()`
- 断言返回值含 `name="schema-readme-drift"` 且 `severity="WARNING"`

**Step 2 (Verify fail)**: 预期 FAILED（函数不存在）

**Step 3 (Implement)**:
- `_lib/docs_consistency.py` 新增 `check_schema_readme_drift()`：用 `_read_text("docs/schemas/README.md")` 提取文件列表，正则匹配 `_lib/schemas/<name>.json`；对比磁盘 glob
- 新增 `scripts/generate_schema_index.py`：
  - 输入：`_lib/schemas/*.json` (排序后)
  - 提取每个 schema 的 `title` + `description`（来自 JSON metadata）
  - 按域名（schema 文件名前缀）分组 → 生成 markdown 表格
  - 输出：`docs/schemas/README.md`（写入 + `os.replace` 原子操作）
  - 加 `--check` flag：仅 diff（不写），用于 CI diff check
- 在 `run_all()` 注册新 check

**Step 4 (Verify pass)**:
- 新 test PASS
- 既有 test PASS
- 跑 generator 重生成 `docs/schemas/README.md`，`git diff` 应为空（B-3 写入时已用 generator 一致逻辑）

**Step 5 (Commit)**: 推迟

---

### Task 3 — A3 精简: schema 路径精确规则

**Step 1 (Write failing test)**: 增加 `test_schema_path_canonical_violation`：
- mock `AGENTS.md` 含行 `打开 schemas/foo.json 在 skills/_lib/schemas/`
- mock 同一文件另一处含行 `路径 _lib/schemas/ 是 canonical`
- 调用 `check_schema_path_canonical()`
- 断言：第 1 行触发 WARNING，第 2 行（`_lib/schemas/`）不触发

**Step 2 (Verify fail)**: 预期 FAILED（函数不存在）

**Step 3 (Implement)**: `_lib/docs_consistency.py` 新增 `check_schema_path_canonical()`：
- 扫描 `AGENTS.md` + `README.md`
- regex 找 `skills/_lib/schemas/`
- **白名单**: 若该字符串在同一行或前一行含 `(`, `（`, `shim`, `兼容`, `向后兼容` 等关键词 → 跳过（合法 shim 说明）
- 否则 WARNING + 修复建议 "use `_lib/schemas/` (canonical) instead"
- 在 `run_all()` 注册

**Step 4 (Verify pass)**: 新 test + 既有 test PASS

**Step 5 (Commit)**: 推迟

---

### Task 4 — CI gate wiring (无 pytest)

**Step 1**: N/A（YAML 文件无 unit test；bats mock 不必要）

**Step 2**: N/A

**Step 3 (Implement)**: `.github/workflows/test.yml` 在 "Python integration tests" 之后、"Bats smoke" 之前插入 step：

```yaml
- name: Documentation consistency gate (rdd-doctor, non-blocking)
  run: |
    set +e
    bash skills/rdd-doctor/scripts/doctor.sh --category docs-consistency --quiet
    EXIT=$?
    set -e
    if [ $EXIT -ge 2 ]; then
      echo "❌ docs-consistency CRITICAL (exit $EXIT)"
      exit $EXIT
    fi
    echo "✅ docs-consistency executed (exit $EXIT, warnings tolerated)"
```

**Step 4 (Verify pass)**:
- YAML syntax check: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/test.yml'))"`
- 本地跑: `bash skills/rdd-doctor/scripts/doctor.sh --category docs-consistency --quiet`，期望 exit 0（B 方案修订后当前文档已清洁）
- generator 重生成后 `git diff docs/schemas/README.md` 应为空

**Step 5 (Commit)**: 推迟

---

## Risks / Assumptions

| 项 | 描述 | 缓解 |
|---|---|---|
| 假设 1 | Oracle 已给完整架构建议（无需 Metis 重审） | 已在 P1 阶段 inline Oracle 反馈 |
| 假设 2 | 4 个新 test 不会产生 false positive | generator 确定性 + 严格 regex 白名单 |
| 假设 3 | WARNING 级不会阻塞 CI | task 4 明确 `exit` 仅 ≥ 2 阻断 |
| 风险 1 | generator 覆盖手写策展内容 | generator 输出 deterministic + CI diff gate |
| 风险 2 | path linter 误伤合法 shim 引用 | regex 显式检查括号/shim 关键词白名单 |
| 风险 3 | 既有 test 受新 run_all 影响 | 新增 check 边界独立（仅扫描特定文件/段） |

---

## Review notes (P1 self-triage)

**Complexity signal analysis**:
- ✅ Single-module contained change（仅 `_lib/docs_consistency.py` + 1 个新 script + 1 个 yaml step）
- ✅ No public interface impact（doctor CLI 行为不变，新增 check 是 additive）
- ✅ Clear automatically verifiable AC（7 个，全 PASS/FAIL 二值）
- ✅ Reversible via `git checkout`（无 schema 变化、无外部副作用）

→ **complexity = simple** → 跳过 Metis/Oracle 双审（per rdd-quick SKILL.md §"Simple branch"）

但 Oracle 咨询已在 P0 前置完成（Oracle task `bg_6d9efc57`），结论已纳入本文 Risks 段。

---

## Execution contract (P2 in-place)

执行期间：
- 不创建 `openspec/changes/quick-doc-automation/` 或 `.rddf/wt/`（rdd-quick hard constraint）
- 不调 `openspec archive` / `git worktree add` / `openspec change create`
- 不写 `iteration.json` / `sessions.json` / `roadmap-state.json`
- 仅写 `.rddf/plans/quick-doc-automation.md` (本文件，rdd-quick owns) + 修改 .py / .yml / .md
- 单聚合 commit 在 R10 前（per AGENTS.md "Worktree Commit Flow" §2.5）
- 改动文件总行数估算: ~150 行新代码 + ~50 行新 test + 1 step yaml

---

## Verification contract (P3)

按 rdd-verifier VERDICT_ITEM_SCHEMA 输出 7 条 verdict（每 AC 一条）：
- AC 描述 verbatim 取自上文 `## Acceptance` 段
- `evidence`: 列出执行命令（pytest / git diff / doctor.sh 调用）
- `reasoning`: 1-2 句总结
- `status`: pass / fail / partial
- 全部 pass → R10 写 audit log `outcome: completed`

---

## Audit log entry (P4 — 待 R10 写)

```json
{
  "name": "quick-doc-automation",
  "started_at": "<R3 plan write timestamp>",
  "ended_at": "<R10 timestamp>",
  "plan_file": ".rddf/plans/quick-doc-automation.md",
  "complexity": "simple",
  "reviewed_by": [],
  "verdict_summary": {"total": 7, "pass": 7, "fail": 0},
  "retry_count": 0,
  "outcome": "completed",
  "commit_sha": "<R10 commit sha>",
  "upgraded_to_change": null
}
```

通过 `python3 skills/rdd-quick/scripts/append_history.py` 原子追加到 `.rddf/state/.quick-history.jsonl`。
