# quick-ci-green-shrink-only

**Goal**: 让 `.github/workflows/test.yml` 的三处缺陷不再把 CI 判红/假绿 ——
① 断言质量门自匹配（永不可能通过）；② shrink-only 基线在 master push 上是自比较（假绿）；
③ checkout 深度不足（PR 上基线取不到）。

**Architecture**: 只改 CI 配置与一处脚本注释 —— 删掉重复的断言 gate step（判据留在
`tests/scripts/check_test_isolation.sh` 的 check #4，它自排除）；checkout 改 `fetch-depth: 0`；
两个 shrink-only step 的基线顺序改为 `HEAD~1` 优先、`origin/master` 兜底。

**Tech Stack**: GitHub Actions YAML、bash、git。

---

### Task 1: 删掉自匹配的 Assertion quality gate

**Files:** Modify: `.github/workflows/test.yml` / `tests/scripts/check_test_isolation.sh`（头注释）/ `test.sh`（NOT_MIRRORED）

- [x] **Step 1: Write the failing test** —— 判据：CI 的断言 step 在干净树上必须能通过。
- [x] **Step 2: Run test to verify it fails** —— 实测 run 44456236815：`❌ Tautologies: tests/scripts/check_test_isolation.sh:135,140`（匹配到自己的 grep 模式）。
- [x] **Step 3: Write minimal implementation** —— 删 step；同一判据只留 check #4（脚本内 `grep -v "^${SELF_SCRIPT}:"` 自排除）；头注释与 `NOT_MIRRORED` 同步。
- [x] **Step 4: Run test to verify it passes** —— `bash tests/scripts/check_test_isolation.sh` ⇒ exit 0；`tests/unit/test_ci_local_mirror.py` 12 passed（覆盖台账/反向两层仍成立）。
- [x] **Step 5: Defer commit**

### Task 2: shrink-only 基线取法（假绿 + PR 红）

**Files:** Modify: `.github/workflows/test.yml`

- [x] **Step 1: Write the failing test** —— 判据：在「push 到 master」语义下，给基线文件加一行 ⇒ step 必须红。
- [x] **Step 2: Run test to verify it fails** —— 旧口径下 `origin/master` == 被推提交（CI 日志原文 `+<sha>:refs/remotes/origin/master`）⇒ 基线 == 当前文件 ⇒ 假绿。
- [x] **Step 3: Write minimal implementation** —— `fetch-depth: 0` + `HEAD~1` 优先、`origin/master` 兜底（顺序是修法的一部分）。
- [x] **Step 4: Run test to verify it passes** —— 完整历史克隆里：基线 16 行 / 83 行（真实）；注入增长 ⇒ 两条都红；恢复 ⇒ 绿。
- [x] **Step 5: Defer commit**

## Acceptance

- [x] AC-1: `check_test_isolation.sh` exit 0（断言质量检查仍生效且不匹配自己）
- [x] AC-2: workflow 里不再有裸 grep 的断言 step；`NOT_MIRRORED` 与 yml 双向一致（契约测试 12 passed）
- [x] AC-3: 完整历史下两个 shrink-only step 基线非空（16 / 83 行）且注入增长即红
- [x] AC-4: `./test.sh --gates` 4 道门全绿
- [x] AC-5: 全量门 `./test.sh --full --regression` 绿（未评估 0 / 新增失败 0）
- [x] AC-6: push 后 CI 实际 run 全绿（本地无法替代，需实际触发）

## 本次不做（记录）

1. **`${{ github.event.before }}` 替换 `HEAD~1`**：语义更准（push 前 tip，可覆盖多提交 push），
   但 `pull_request` 事件下该字段取值不稳 ⇒ 不在本次引入。
2. **lint/type 覆盖漏洞**（ruff 只查 shim 层 / mypy 只查 0-def shim）⇒ 另案，见
   `.rddf/improvements/fix-lint-deferred-findings.md` 的 Out of Scope。
3. **37 个被推迟的 lint 发现** ⇒ 同上债务工件，不在此顺手修。
