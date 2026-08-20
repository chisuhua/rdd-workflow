# extend-populate-roadmap-with-code-verification

**优先级**: P1 | **来源**: 用户反馈 — `populate-roadmap-from-arch` v1.0 (commit 2b0991a) 仅读 ADR 自报实施状态，未交叉验证代码；存在"自报但代码不存在"风险导致 fragment body 误导读者
**阶段**: v2.2 | **分类**: arch-design
**类型**: feature
**特性**: `extend-populate-roadmap-from-arch`（单 change 提案，扩展 v1.0 不破坏现有契约）

> **范围定位**：本提案为 `populate-roadmap-from-arch` 增加可选的代码实施验证步骤（Step 1.5），使 fragment body 标记"已实施"时同时标注验证来源（代码验证 vs 仅自报）。
>
> **不破坏** v1.0 默认行为：默认 `--code-verify=off`，与 v1.0 输出完全一致。`--code-verify=on` 是 explicit opt-in。
>
> **不重复** `rdd-doctor` / `codebase-memory-mcp` 已有的能力 — 复用其 API，本提案只做"调用 + 桥接到 fragment body"。
>
> **不修改** 现有 fragment frontmatter / 主题注册表（按 v1.0 不变性约束）。

## 架构依据

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

## 范围

### In Scope

**A. `populate_lib.py` 新增 `AdrCodeVerification` dataclass + 3 个函数**（~80 行）

```python
@dataclass
class AdrCodeVerification:
    adr_id: str
    self_claim_version: Optional[str]      # 从 ADR README 提取
    code_symbols_found: List[str]          # 在代码中实际找到的 symbol
    code_symbols_expected: List[str]       # 从 ADR 文本解析的 symbol
    verification_status: str               # "confirmed" / "self-claim-only" / "placeholder-but-exists" / "placeholder-as-claimed"
    has_discrepancy: bool                  # self_claim 与 code 不一致

def verify_adr_by_code(adr: AdrRecord, project_root: Path) -> AdrCodeVerification:
    """Step 1.5: Parse ADR text for symbol references, query codebase, classify."""

def verify_all_adrs(adrs: List[AdrRecord], project_root: Path) -> List[AdrCodeVerification]:
    """Aggregate verification across all ADRs (parallel-safe)."""

def load_supplementary_or_default(project_root: Path) -> Dict[str, AdrCodeVerification]:
    """Load .rddf/state/.populate-supplementary.json if exists, else empty dict."""
```

**B. `populate.sh` 新增 `--code-verify` flag + Step 1.5 编排**（~40 行）

```bash
# Step 1.5: verify ADR by code (only if --code-verify=on)
if [ "$CODE_VERIFY" = "on" ]; then
    verify_all_adrs > .rddf/state/.populate-supplementary.json
    if has_discrepancy ; then
        echo "⚠️  Discrepancy detected: ADR self-claim contradicts code"
        echo "   Run with --code-verify=strict to block on discrepancy"
    fi
fi
```

**C. `_format_adr_block` 增强**（~10 行修改）

```python
# Before: *（已实施 v2.0.0+）*
# After (--code-verify=on):
#   *（已实施 v2.0.0+ + 代码验证）*       # self-claim == code
#   *（已实施 v2.0.0+ 仅自报）*           # self-claim 但 code 缺失
#   *（占位 + 代码未现）*                  # self-claim 占位 + code 缺失
#   *（占位 + 代码已现 ⚠️）*             # self-claim 占位 + code 存在（矛盾）
```

**D. `tests/unit/test_populate_lib.py` 新增 ≥ 8 案例**（~150 行）

- `test_verify_adr_by_code_confirmed` — 自报 v2.0 + code 找到 → "confirmed"
- `test_verify_adr_by_code_self_claim_only` — 自报 v2.0 + code 缺失 → "self-claim-only"
- `test_verify_adr_by_code_placeholder_no_code` — 占位 + code 缺失 → "placeholder-as-claimed"
- `test_verify_adr_by_code_placeholder_contradicts` — 占位 + code 存在 → "placeholder-but-exists" + has_discrepancy=True
- `test_parse_symbols_from_adr_text` — 解析 `--name` `class Foo` `def bar()` 模式
- `test_verify_all_adrs_parallel` — 验证 5 个 ADR 不串行（如有性能要求）
- `test_load_supplementary_or_default` — 文件不存在 → 空 dict
- `test_supplementary_json_roundtrip` — 写入 → 读取 → 字段一致

**E. `tests/integration/test_populate_roadmap_from_arch.bats` 新增 ≥ 4 案例**（~80 行）

- `code-verify off: same output as v1.0` — 默认行为兼容
- `code-verify on: new badges appear` — body 标 `*（已实施 v2.0.0+ + 代码验证）*` 等
- `code-verify strict: exit 2 on discrepancy` — 矛盾时阻断
- `code-verify on fallback: grep works without mcp` — mcp 不可用时降级

**F. SKILL.md 更新**（~30 行修改）

- 新增 `--code-verify` / `--code-verify=strict` / `--no-code-verify` flag 文档
- Step 1.5 加到状态机图
- "已实施能力" 段加 4 种 badge 解释
- "已知限制" 段加 codebase-memory-mcp 可用性说明

### Out of Scope

- **修改 fragment 已有的 6 段结构**（仅在 `## 已实施能力` 段加 badge）
- **修改 `rdd-doctor` roadmap-refs 类别**（rdd-doctor 仍是 read-only 单源验证）
- **CI 集成**（`--code-verify=strict` 可在 CI 跑，但本提案不提供 GitHub Actions 配置 — follow-up）
- **跨仓库代码验证**（按 ADR-0030，跨仓代码走 Hub，本提案只验证本仓库代码）
- **任何 LLM 语义验证**（仅基于 symbol 匹配，不做"语义实施"判断）
- **历史数据回填**（已有 fragment body 不重写，直到下次 `populate` 调用）

## 关键场景

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

## 技术约束

### 依赖

- **existing**: `_lib/roadmap_state.py`（Fragment dataclass）/ `populate_lib.py`（AdrRecord）/ codebase-memory-mcp / `bash` / `python3.11+`
- **no new external deps**: 不引入 `tree-sitter` / `ast-grep` 等重型 parser
- **mcp 可用性**: codebase-memory-mcp 不可用时优雅降级到 grep（不阻断）

### 性能预算

- 单 ADR 验证: < 1s（mcp 命中）/ < 5s（grep fallback）
- 33 个 ADR 总验证: < 30s（mcp 命中）/ < 3min（grep fallback）
- 与原 Step 1-3 catalog (< 2s) 相比，Step 1.5 是新瓶颈但仍可接受

### 兼容性

- **API 稳定**: v1.0 公共函数（catalog_sources / classify_adrs_by_phase / generate_phase_body）签名不变
- **CLI 兼容**: `--code-verify` 是新增 flag，无现有 flag 被修改
- **frontmatter 不变**: 按 v1.0 不变约束，fragment frontmatter 字段不变
- **测试不破坏**: v1.0 12 pytest + 10 bats 全部继续 pass

### 数据契约

```json
// .rddf/state/.populate-supplementary.json (gitignored, view file)
{
  "schema_version": "v1",
  "verified_at": "2026-08-21T02:30:00Z",
  "verification_source": "codebase-memory-mcp",  // or "grep-fallback"
  "verifications": {
    "ADR-0001": {
      "self_claim_version": "v2.0.1+",
      "symbols_expected": ["SessionManager", "SessionCoordinator", "sessions.json"],
      "symbols_found": ["SessionManager", "SessionCoordinator", "sessions.json"],
      "verification_status": "confirmed",
      "has_discrepancy": false
    },
    "ADR-0009": {
      "self_claim_version": null,
      "symbols_expected": ["scheduled_triggers", "cron_scheduler"],
      "symbols_found": ["cron_scheduler"],
      "verification_status": "placeholder-but-exists",
      "has_discrepancy": true
    }
  }
}
```

**schema 位置**: `skills/_lib/schemas/populate_supplementary_schema.json`（新文件，~30 行）

## 验收标准

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

## 依赖与阻塞

- **依赖**: `populate-roadmap-from-arch` v1.0 (commit 2b0991a) 已实施
- **依赖**: `codebase-memory-mcp` 服务（fallback grep 路径不依赖 mcp）
- **依赖**: `_lib/roadmap_state.py` Fragment dataclass（已存在）
- **不阻塞**: `rdd-doctor` roadmap-refs 类别（read-only 校验）
- **不阻塞**: 其他 changes

## 复杂度评估

- **代码行数**: ~190 行（80 populate_lib + 40 populate.sh + 10 _format_adr_block + 60 schema/doc）
- **测试行数**: ~230 行（150 pytest + 80 bats）
- **新文件**: 3 个（schema.json + 1 个 fixture + 1 个 bash helper）
- **修改文件**: 3 个（populate_lib.py + populate.sh + SKILL.md）
- **commit 数**: 1 commit（feature scope 单一）
- **预期实施时长**: 1 个 session（2-3 小时，包括测试 + 验证）

## 为什么不合并到 v1.0 主提案？

- v1.0 (add-hierarchical-roadmap-structure) 已 approve + 归档（51ca983 + 2b0991a），scope 是 "create fragment + migrate + 8 rules"
- 本提案 scope 是 "verify code against ADR self-claim" — 独立关注点
- 合并会导致 v1.0 PR 推迟，且 v1.0 已有 4 commit + 24 task（49 spec test）
- add-improve 流程（v2.0.6+）支持"完成一阶段后追加新提案"，这是标准模式

## 后续（out of scope, 留给 follow-up）

- **CI integration**: `.github/workflows/code-verify.yml`（跑 `--code-verify=strict`）
- **跨仓库验证**: Hub 端 `rddf code-verify cross-repo --spokes ...`
- **LLM 语义验证**: 用 `ac-verifier` skill 做"ADR 决策是否真的实施"（不只是 symbol 匹配）
- **历史回填**: 给 2b0991a 之前的 fragment body 补 verification badge
- **trend 报表**: `.rddf/state/.verification-history.json` 跟踪多次 populate 之间的 verification delta
