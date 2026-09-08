# add-rdd-quick-skill — Tasks

## Phase 0 — Setup
- [ ] T01: 建 branch `openspec/add-rdd-quick-skill` (master base) — `git checkout -b openspec/add-rdd-quick-skill`
- [ ] T02: 记录 proposal.md / design.md / roadmap-meta.yaml / spec.md 的初始 sha256（零污染基线）
- [ ] T03: 记录 `select_worktree.sh` / `tasks_writeback.sh` / `_lib/archive.sh` 的初始 sha256（spec Scenario 锁定的基线）

## Phase 1 — Schema + Python 数据层（test-first）

### Step 1: 写失败单测（红）
- [ ] T04: `tests/unit/test_quick_history.py` 写 6 个 case（schema 校验 3 + 原子写 2 + 字段完整性 1），全部 RED
  - `test_schema_v1_exists_and_validates`
  - `test_entry_validates_all_required_fields`
  - `test_entry_rejects_unknown_outcome`
  - `test_append_creates_file_with_atomic_rename`
  - `test_append_preserves_existing_lines`
  - `test_name_pattern_requires_quick_prefix`

### Step 2: 实现 schema + 数据层（绿）
- [ ] T05: `_lib/schemas/quick_history_schema.json` 落盘（v1，11 required 字段，outcome enum = completed/escalated/unverified）
- [ ] T06: `_lib/quick_history.py` 实现 `validate_entry(data) -> bool` / `append_entry(entry, history_file) -> None` / `read_entries(history_file) -> list`，仅 Python stdlib
- [ ] T07: 跑 `pytest tests/unit/test_quick_history.py -q` 全绿（6/6）

## Phase 2 — SKILL.md（spec 驱动的 prose 指令）

### Step 1: 写失败结构性测试（红）
- [ ] T08: `tests/integration/test_rdd_quick.bats` 写 4 个结构性 case（frontmatter 必备字段、role.boundaries 必备条目、P0-P4 phase marker、复杂度信号清单），全部 RED
  - `rdd-quick: SKILL.md frontmatter 字段完整`
  - `rdd-quick: role.boundaries.owns 含 quick-*.md 与 .quick-history.jsonl`
  - `rdd-quick: role.boundaries.not_owns 含 openspec/ + .rddf/wt/ + iteration.json`
  - `rdd-quick: SKILL.md body 含 P0/P1/P2/P3/P4 phase marker`

### Step 2: 实现 SKILL.md（绿）
- [ ] T09: `skills/rdd-quick/SKILL.md` 写 frontmatter（`name` / `description` / `license` / `compatibility` / `metadata` / `role`，含 `role.boundaries` 的 owns/not_owns/human_involvement）
- [ ] T10: SKILL.md body 写 P0-P4 五阶段 prose 指令 + 复杂度判定原则清单（简单信号 ≥4 + 复杂信号 ≥4，无硬阈值）
- [ ] T11: SKILL.md body 写 Metis/Oracle spawn 指令（prose，对齐 ADR-0045 模式，要求 question 工具请用户确认）
- [ ] T12: SKILL.md body 写 P3 verdict JSON 协议（6 字段 + status 三值 + AC 来源说明）
- [ ] T13: SKILL.md body 写环境变量规范（`RDDF_QUICK_*` 前缀 5 个变量 + `SKIP_RDDF_QUICK_VERIFY` + 禁止读写的 2 个旧变量）
- [ ] T14: 跑 `bats tests/integration/test_rdd_quick.bats` 4 个结构性 case 全绿

### Step 3: 追加功能性 case（计划文件契约 + 验证协议）
- [ ] T15: `test_rdd_quick.bats` 新增 4 个 case（quick- 前缀 + TDD 5 marker + ## Acceptance 段 + 不读 openspec/changes/），跑 `bats` 验证全绿
  - `rdd-quick: scaffold_plan 生成的文件名以 quick- 开头`
  - `rdd-quick: scaffold_plan 生成的内容含全部 5 个 TDD marker`
  - `rdd-quick: scaffold_plan 生成的内容含 ## Acceptance 段与至少 1 checkbox`
  - `rdd-quick: SKILL.md 明确说明 P3 不读 openspec/changes/<name>/proposal.md`

## Phase 3 — 两个 Helper 脚本（test-first）

### Step 1: 写失败测试（红）
- [ ] T16: `test_rdd_quick.bats` 新增 2 个 case（scaffold_plan + append_history），跑 `bats` 验证 RED
  - `rdd-quick: scaffold_plan.sh --name foo 输出 .rddf/plans/quick-foo.md 含 TDD 5 marker + ## Acceptance`
  - `rdd-quick: append_history.py 在已有 .quick-history.jsonl 上原子追加不丢失旧行`

### Step 2: scaffold_plan.sh（绿）
- [ ] T17: `skills/rdd-quick/scripts/scaffold_plan.sh` 实现，bash 调 python3 仅用 stdlib，60 行内
  - 入参：`--name <kebab-case>` + `--proposal <text>`（或 stdin）
  - 行为：渲染模板（`# quick-<name>` + Goal 段 + ## Files 段 + 5 个 TDD marker 段 + ## Acceptance 段）到 `.rddf/plans/quick-<name>.md`
  - 校验：name 必须 kebab-case；目标文件不存在则拒绝（防覆盖）

### Step 3: append_history.py（绿）
- [ ] T18: `skills/rdd-quick/scripts/append_history.py` 实现，仅 stdlib，80 行内
  - 入参：从 stdin 读 JSON entry
  - 行为：调 `_lib.quick_history.validate_entry()` 校验 → temp file 写完整 JSONL（old + new） → rename 覆盖
  - 错误：校验失败或 schema 不匹配 → exit 1 + stderr

### Step 4: 跑全部 helper 测试（绿）
- [ ] T19: 跑 `bats tests/integration/test_rdd_quick.bats` 全 8 case（4 结构 + 2 scaffold + 2 append_history）全绿

## Phase 4 — ADR + 文档

- [ ] T20: `docs/adr/ADR-0047-rdd-quick-bypass-path.md` 落盘（已采纳状态，含四概念区分表 + 与 `guide-ship-quick-finish` 边界）
- [ ] T21: `AGENTS.md` 加 rdd-quick 段（含 4 概念区分表 + 5 个 `RDDF_QUICK_*` 环境变量清单 + 1 个 `SKIP_RDDF_QUICK_VERIFY`）
- [ ] T22: `README.md` 技能列表加 `rdd-quick/SKILL.md` 一行
- [ ] T23: `skills/rdd-planner/SKILL.md` `## See also` 段追加 `- [rdd-quick](../rdd-quick/SKILL.md)` 一行（其余逐字节不变）

## Phase 5 — 零污染验证（hash 锁定）

### Step 1: 写失败验证测试（红）
- [ ] T24: `tests/integration/test_rdd_quick_isolation.bats` 写 4 个 case，跑 `bats` 验证 RED
  - `rdd-quick: select_worktree.sh 内容 sha256 不变`
  - `rdd-quick: tasks_writeback.sh 内容 sha256 不变`
  - `rdd-quick: _lib/archive.sh 内容 sha256 不变`
  - `rdd-quick: rdd-planner/SKILL.md 的 role: 段 sha256 不变`

### Step 2: 固化 hash（绿）
- [ ] T25: 跑 `sha256sum` 记录 4 个文件的当前 hash，写入 test 文件的断言
- [ ] T26: 跑 `bats tests/integration/test_rdd_quick_isolation.bats` 4 case 全绿

## Phase 6 — 全量回归门（MANDATORY per AGENTS.md）

- [ ] T27: 跑 `./test.sh --quick` 全绿（pytest unit + bats smoke ~45s）
- [ ] T28: 跑 `./test.sh --full --regression` 全绿（bats recursive + pytest unit+integration，无新增失败）
- [ ] T29: 若有新增失败必须修；与 KNOWN_FAILURES.txt 比对，仅 baseline 已知失败可放行

## Phase 7 — Archive

- [ ] T30: 跑 `openspec validate add-rdd-quick-skill --strict` 全绿
- [ ] T31: commit 所有 artifacts（含 T01-T29 全部勾选）
  - 单一 commit subject：`feat(rdd-quick): add bypass-path skill with P0-P4 state machine`
- [ ] T32: `openspec archive add-rdd-quick-skill --yes` 触发 Phase 7 归档
- [ ] T33: 跑 `./test.sh --quick` 确认 archive 后仍全绿