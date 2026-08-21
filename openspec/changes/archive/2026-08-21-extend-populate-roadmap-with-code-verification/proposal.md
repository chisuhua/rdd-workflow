# extend-populate-roadmap-with-code-verification

## Why

### 动机（用户调研）

| 当前状况 | 用户痛点 |
|---------|---------|
| `populate-roadmap-from-arch` v1.0 读 ADR README "已实施（v2.0.X+）"段作为 `implementation_version` | 该字段是 **ADR 作者自报**，未与代码交叉验证 |
| Fragment body `## 已实施能力` 段标 `*（已实施 v2.0.0+）*` | 读者无法区分"代码确实存在" vs "ADR 自称但代码可能已删除/未落地" |
| ADR-0001 ⚠️ 状态: "已替代为 ADR-0003" 但文件仍存在 | 自报"已实施"的 ADR 可能已 superseded，代码路径也可能被重构 |
| codebase-memory-mcp / `search_graph` / `get_code_snippet` 已可用 | 但 skill v1.0 未利用 |

**实证证据**（来自 v1.0 首次执行 20260820T155324Z）：

```
phase-1: 17 个已实施 ADR（来自 ADR README 状态段）
phase-2: 16 个已实施 ADR
phase-3: 3 个已实施 ADR
phase-4: 0 个已实施 ADR / 1 个待定（ADR-0030）
```

**问题**: 17 + 16 + 3 = 36 个 ADR 都标"已实施" — 但代码 `_lib/loop/` 是否真的实现了 ADR-0004 的 5 大构建块？`_lib/roadmap_state.py` 是否真的支持 ADR-0016 v2 schema？这些都没有验证。

**风险**:
- **误报已实施**: ADR 自称 v2.0.0+ 实施，但代码可能没合并 / 被后续 change revert
- **遗漏增量**: 实施可能存在但 ADR README 状态段没人更新（特别是小修改）
- **架构漂移**: 多人长期维护下，ADR 与代码逐步脱节

### 设计决策（已批准）

| 决策点 | 选择 |
|--------|------|
| 触发方式 | `--code-verify` flag（明示 opt-in，非默认） |
| 默认行为 | `--code-verify=off`（v1.0 完全兼容，行为不变） |
| 数据源优先级 | codebase-memory-mcp 优先（fast + 已有 call graph） → grep fallback（无 server 环境） |
| 验证策略 | 解析 ADR "## 决策" / "Decision" 段中提到的 symbol（函数/类/模块名） → 在代码中查找 |
| 输出位置 | `.rddf/state/.populate-supplementary.json`（gitignored view，与 `iteration.json` 同类） |
| Fragment body 标记 | `*（已实施 v2.0.0+ + 代码验证）*` / `*（已实施 v2.0.0+ 仅自报）*` / `*（占位 + 代码未现）*` / `*（占位 + 代码已现 ⚠️）*` |
| 退出码 | 0（验证通过）/ 1（preflight 失败）/ 2（自报与代码矛盾，硬阻断，仿 `rdd-doctor` exit codes 0/1/2/3） |
| 实施版本 | `--code-verify=off` 默认；`--code-verify=on` 可选；不新增 env var（避免 Round A 风险） |
| 与 rdd-doctor 关系 | 不重复：rdd-doctor 是 read-only 校验，本提案是 populate-time 增量信号 |
| 与 codebase-memory-mcp 关系 | 复用：失败时优雅降级到 grep + 报告 warning |

### 为什么不直接重写 populate_lib.py？

- v1.0 已 12 pytest + 10 bats 锁定契约（消费者包括 commit 2b0991a 后的 fragment body）
- 重写涉及 `_extract_adr_status_and_decision` / `generate_phase_body` 等核心函数，破坏风险高
- **additive extension**（新增 Step 1.5 + 标记 badge）保持向前兼容，便于未来 deprecate

## What Changes

**In Scope**:

- **A. `populate_lib.py` 新增 `AdrCodeVerification` dataclass + 3 个函数** (~80 行)
  - `AdrCodeVerification` dataclass（`adr_id` / `self_claim_version` / `code_symbols_found` / `code_symbols_expected` / `verification_status` / `has_discrepancy`）
  - `verify_adr_by_code(adr, project_root)` — Step 1.5 核心函数
  - `verify_all_adrs(adrs, project_root)` — 聚合验证（parallel-safe）
  - `load_supplementary_or_default(project_root)` — 读取 `.populate-supplementary.json`

- **B. `populate.sh` 新增 `--code-verify` flag + Step 1.5 编排** (~40 行)
  - `--code-verify=off|on|strict` flag 解析
  - Step 1.5 编排：mcp 优先 → fallback grep → 写 supplementary.json
  - strict mode 下 exit 2 on discrepancy

- **C. `_format_adr_block` 增强** (~10 行修改)
  - `--code-verify=off` 时输出与 v1.0 一致
  - `--code-verify=on|strict` 时使用 4 种新 badge（confirmed / self-claim-only / placeholder-but-exists / placeholder-as-claimed）

- **D. `tests/unit/test_populate_lib.py` 新增 ≥ 8 案例** (~150 行)
  - `test_verify_adr_by_code_confirmed` — 自报 v2.0 + code 找到 → "confirmed"
  - `test_verify_adr_by_code_self_claim_only` — 自报 v2.0 + code 缺失 → "self-claim-only"
  - `test_verify_adr_by_code_placeholder_no_code` — 占位 + code 缺失 → "placeholder-as-claimed"
  - `test_verify_adr_by_code_placeholder_contradicts` — 占位 + code 存在 → "placeholder-but-exists" + has_discrepancy=True
  - `test_parse_symbols_from_adr_text` — 解析 `--name` `class Foo` `def bar()` 模式
  - `test_verify_all_adrs_parallel` — 验证 5 个 ADR 不串行
  - `test_load_supplementary_or_default` — 文件不存在 → 空 dict
  - `test_supplementary_json_roundtrip` — 写入 → 读取 → 字段一致

- **E. `tests/integration/test_populate_roadmap_from_arch.bats` 新增 ≥ 4 案例** (~80 行)
  - `code-verify off: same output as v1.0` — 默认行为兼容
  - `code-verify on: new badges appear` — body 标新 badge
  - `code-verify strict: exit 2 on discrepancy` — 矛盾时阻断
  - `code-verify on fallback: grep works without mcp` — mcp 不可用时降级

- **F. SKILL.md 更新** (~30 行修改)
  - 新增 `--code-verify` / `--code-verify=strict` / `--no-code-verify` flag 文档
  - Step 1.5 加到状态机图
  - "已实施能力" 段加 4 种 badge 解释
  - "已知限制" 段加 codebase-memory-mcp 可用性说明

- **G. 新 schema 文件** `skills/_lib/schemas/populate_supplementary_schema.json`（~30 行，v1 schema）

### 关键场景

### 场景 1: 默认行为（v1.0 完全兼容）

```bash
$ rddf populate-roadmap-from-arch --help
Usage: populate.sh [--phase phase-N] [--dry-run] [--no-backup] [--yes]
                   [--code-verify=off|on|strict]   # 新增，默认 off

$ rddf populate-roadmap-from-arch --yes
# 输出与 v1.0 完全一致（fragment body 仍用 `*（已实施 v2.0.0+）*`）
```

### 场景 2: 启用代码验证

```bash
$ rddf populate-roadmap-from-arch --yes --code-verify=on
▶ Step 1.5: Verify ADR by code (4 ADRs in 1.2s)
  ✅ ADR-0001: confirmed (3/3 symbols found: SessionManager, SessionCoordinator, sessions.json)
  ✅ ADR-0004: confirmed (5/5 symbols found: loop_engine, action, detector, state_vector, event_log)
  ⚠️ ADR-0009: placeholder-but-exists (代码找到 _lib/schedulers/cron_scheduler.py 但 ADR 自报"占位")
▶ Supplementary: .rddf/state/.populate-supplementary.json (4 records)
▶ Writing fragments...
  ✅ phase-1 (含 4 个 badge: ✅ 已实施 + 代码验证 / ⚠️ 占位 + 代码已现)
```

### 场景 3: 严格模式（矛盾时硬阻断）

```bash
$ rddf populate-roadmap-from-arch --yes --code-verify=strict
▶ Step 1.5: Verify ADR by code...
  ❌ ADR-0009: placeholder-but-exists (代码找到 symbols 但 ADR 自报"占位")
❌ STRICT mode: 1 discrepancy detected — committing would archive conflicting state
   Run with --code-verify=on to continue with warning, or fix ADR/README first.
EXIT 2
```

### 场景 4: mcp 不可用时降级

```bash
$ rddf populate-roadmap-from-arch --yes --code-verify=on
▶ Step 1.5: codebase-memory-mcp unavailable, falling back to grep
  ⚠️ ADR-0001: 11 symbols expected, 3 found via grep (78% miss rate — 可能 mcp 索引更准)
  ⚠️ ADR-0004: 7 symbols expected, 2 found via grep (71% miss rate)
▶ Supplementary: .rddf/state/.populate-supplementary.json (4 records, with warning metadata)
```

**Out of Scope**:

- **修改 fragment 已有的 6 段结构**（仅在 `## 已实施能力` 段加 badge，其余 5 段不动）
- **修改 `rdd-doctor` roadmap-refs 类别**（rdd-doctor 仍是 read-only 单源验证，不复用 populate-time 信号）
- **CI 集成**（`--code-verify=strict` 可在 CI 跑，但本提案不提供 GitHub Actions 配置 — follow-up；建议在 SKILL.md 加 "Recommended CI Integration" 章节作为指引）
- **跨仓库代码验证**（按 ADR-0030，跨仓代码走 Hub，本提案只验证本仓库代码）
- **任何 LLM 语义验证**（仅基于 symbol 匹配，不做"语义实施"判断 — 语义层交给 `ac-verifier` skill）
- **历史数据回填**（已有 fragment body 不重写，直到下次 `populate` 调用；不主动 patch 既有 fragment）

## Capabilities

- **existing**: `_lib/roadmap_state.py`（Fragment dataclass）/ `populate_lib.py`（AdrRecord）/ codebase-memory-mcp / `bash` / `python3.11+`
- **no new external deps**: 不引入 `tree-sitter` / `ast-grep` 等重型 parser
- **mcp 可用性**: codebase-memory-mcp 不可用时优雅降级到 grep（不阻断）
- 单 ADR 验证: < 1s（mcp 命中）/ < 5s（grep fallback）
- 33 个 ADR 总验证: < 30s（mcp 命中）/ < 3min（grep fallback）
- 与原 Step 1-3 catalog (< 2s) 相比，Step 1.5 是新瓶颈但仍可接受
- **API 稳定**: v1.0 公共函数（catalog_sources / classify_adrs_by_phase / generate_phase_body）签名不变
- **CLI 兼容**: `--code-verify` 是新增 flag，无现有 flag 被修改
- **frontmatter 不变**: 按 v1.0 不变约束，fragment frontmatter 字段不变
- **测试不破坏**: v1.0 12 pytest + 10 bats 全部继续 pass

## Impact

- **受影响的下游消费者**:
  - `populate.sh` 用户（CLI flag 新增，默认行为不变）
  - fragment body 读者（新增 4 种 badge，可读性提升）
  - `rdd-doctor`（不修改，按"不重复"原则保持 read-only 单源验证）
  - CI 流水线（潜在 strict mode 集成点，本提案不提供 yml，follow-up）

- **新增 gitignored 状态文件**: `.rddf/state/.populate-supplementary.json`（v1 schema，按 ADR-0016 路径约束）
  - 类似 `iteration.json` / `deps-analysis.json`，多 hook 可写
  - 写入方：`populate.sh` Step 1.5（`--code-verify=on|strict` 时）
  - 读取方：`populate.sh` Step 2 渲染 fragment body 时按 ADR ID 查询

- **新增受版本控制的契约文件**:
  - `skills/_lib/schemas/populate_supplementary_schema.json`（v1, ~30 行）
  - schema 字段定义改必须 bump version; 消费者拒绝 version=0 payload（对齐 `_lib/schemas/` 既有约束）

- **受影响的测试套件**:
  - `tests/unit/test_populate_lib.py` + ≥8 新案例
  - `tests/integration/test_populate_roadmap_from_arch.bats` + ≥4 新案例
  - 现有 v1.0 的 12 pytest + 10 bats 不破坏

- **无 breaking change**:
  - v1.0 公共 API 签名不变
  - CLI 仅新增 flag
  - fragment frontmatter 字段不变
  - 默认 `--code-verify=off` 时输出 diff against 2b0991a 为空

## Acceptance

### 必达（must-have）

1. **≥ 8 pytest 案例** 覆盖 4 种 verification_status + 解析 + roundtrip
2. **≥ 4 bats 案例** 覆盖 --code-verify off/on/strict + mcp 降级
3. **v1.0 所有 12+10 测试继续 pass**（不破坏现有契约）
4. **默认行为**: `populate.sh --yes` 输出与 v1.0 完全一致（diff against 2b0991a 应为空）
5. **strict mode 阻断 discrepancy**: 矛盾时 exit 2，stderr 明确说明哪个 ADR 矛盾
6. **supplementary JSON 存在**: `--code-verify=on` 时写 `.rddf/state/.populate-supplementary.json`
7. **fragment body 标记**: `--code-verify=on` 时 `## 已实施能力` 段使用 4 种新 badge

### 加分（nice-to-have）

1. **mcp 降级友好**: mcp 不可用时警告但不阻断
2. **dry-run 兼容**: `--dry-run --code-verify=on` 不写 supplementary.json
3. **parallel verify**: 多 ADR 并行验证（用 `concurrent.futures`），减少总耗时

### 风险缓解

1. **mcp 不可用真实场景**: CI 环境可能没起 mcp server → grep fallback 必须可用
2. **codebase 巨大时性能**: 本仓库 1193 行 arch + ~5000 行 _lib/ + ~5000 行 skills/，grep fallback 仍 < 3min
3. **false positive**: grep 可能匹配到同名但无关的 symbol → 缓解：仅匹配 ADR 文本中显式提及的 `code` / `` `code` `` / `函数名()`

