# ADR-0045: 内联 ac-verifier 到 rdd-verifier（v2.0 自包含 LLM 验证）

> **状态**: 已采纳
> **日期**: 2026-09-07
> **决策者**: rdd-workflow maintainer
> **替代**: ADR-0034 §"State Machine" Step 2a-c（ac-verifier subprocess 调用部分）
> **修订**: 2026-09-07 — The deprecated `ac-verifier` skill + `rddf ac-verify` CLI subcommand referenced in §"Migration" have been hard-removed via `remove-ac-verifier-completely` (2026-09-07 archive). All call sites MUST use `rdd-verifier` v2.0 (this ADR).

## Context

`rdd-verifier` v1.0（ADR-0034）将 LLM 验证委托给独立的 `ac-verifier` 子技能，后者通过外部 Python 进程（`ac_verifier.py` + 4 个 `llm_providers/*.py`）调用 OpenAI/Anthropic/Ollama/MiniMax SDK。实施六周后暴露五类成本：

1. **配置蔓延**：用户必须设置 `AC_LLM_PROVIDER` / `AC_LLM_BASE_URL` / `AC_LLM_API_KEY` / `AC_LLM_MODEL` / `AC_LLM_TIMEOUT` / `AC_LLM_MAX_RETRIES` / `AC_LLM_MOCK` 等环境变量 — 而执行 `skill_use("rdd-verifier")` 的 AI agent 本身就是 LLM，这些变量全部多余。
2. **外部 Python 依赖**：`_lib/cli/rdd_verify_cmd.py`、`_lib/cli/ac_verify_cmd.py`、`_lib/archive.sh`、`skills/rdd-verifier/scripts/run_verification.sh` 四处调用点都依赖 `$PROJECT_ROOT/skills/ac-verifier/scripts/ac_verifier.sh` 存在。
3. **文档与执行脱节**：验证 prompt 模板（`_SYSTEM_PROMPT_TEMPLATE`）与 verdict schema（`_VERDICT_SCHEMA`）埋在 Python 源码里，而概念上属于验证协议，应随 skill 指令演进。
4. **双层失败模式**：exit 3 混淆了"外部 LLM provider 错误"与"agent 自身失败"。
5. **CI mock 体操**：`AC_LLM_MOCK=yes` + `_MOCK_SCENARIO` 需与真实 LLM 行为手动同步。

**架构依据**:
- ADR-0034 §7.2: SHA-fingerprint verdict cache（本次保留不变）
- ADR-0028 §role model: rdd-verifier 的 `owns` 边界已包含 verdict cache 文件
- `docs/superpowers/specs/2026-08-26-rdd-verifier-design.md`（v1.0 spec）

## Decision

**将 LLM 验证协议全部内联到 `skills/rdd-verifier/SKILL.md`，废弃 `ac-verifier` 子技能，执行验证的 AI agent 自身就是 LLM。**

具体地：

1. SKILL.md 新增 "LLM Verification Protocol" 一节（AC 提取规则、证据收集工具链、verdict JSON schema、reasoning 关键词契约、持久化协议、退出码语义），作为验证协议的唯一事实源。
2. `rdd-verifier` CLI（`rddf rdd-verify`）的 llm-provider 路径从"shell 调 ac-verifier"改为"stage 上下文文件"（`.rddf/state/rdd-verify-context-<change>.json`），由 agent 按 SKILL.md 协议执行验证并写回 cache。
3. `_lib/archive.sh::archive_gate_check` 移除 ac-verifier subprocess fallback，只消费 SHA-bound verdict cache；cache 缺失/过期时 fail closed，除非 audited bypass（`SKIP_RDD_VERIFIER=yes` + `RDDF_VERIFIER_BYPASS_REASON`）。
4. `rddf ac-verify` 与 `skills/ac-verifier/` 标记 deprecated（`user-invocable: false`），保留 1-2 个 release cycle 作为向后兼容 shim，下个 minor release 移除。
5. Exit 3 语义从"ac-verifier internal error"重新定义为"LLM verification error"（agent 上下文溢出 / 工具全失败）。
6. 新建 `_lib/verifier/protocol.py` 承载协议数据层（`parse_acs`、`build_verification_context`、`stage_verification_context`、`validate_verdict_items`），取代 `ac_verifier.py` 中的对应实现。

### 影响范围

- **In Scope**: `skills/rdd-verifier/SKILL.md`、`skills/ac-verifier/`（deprecation）、`_lib/cli/rdd_verify_cmd.py`、`_lib/cli/ac_verify_cmd.py`、`_lib/archive.sh`、`_lib/verifier/{protocol,audit}.py`、`skills/rdd-verifier/scripts/run_verification.sh`、相关测试（新增 2 套 + 标记 6 套 deprecated）、`AGENTS.md`、`README.md`、`openspec/specs/verifier-lifecycle/spec.md`
- **Out Scope**: SHA cache schema v2、`_lib/verifier/{classify,cache,branch,discovery,loop_state,archive_gate,hook_runner}.py`、iteration schema v7、per-change loop state、退出码 0/1/2/4 语义

### 备选方案

| 备选 | 理由 |
|------|------|
| 保留 ac-verifier 作为薄 Python wrapper，仅删 `AC_LLM_PROVIDER` | 拒绝：prompt 仍埋在 Python，shell↔Python 桥接复杂度仍在 |
| prompt 移到独立 `prompts/verify.md` 由 SKILL.md 引用 | 拒绝：制造第二事实源；SKILL.md 指令块就是验证协议的正确归属 |
| 立即删除 ac-verifier | 拒绝：`rddf ac-verify` 外部调用方与 `_lib/archive.sh` fallback 依赖仍在，一次性删除回归面过大 |
| agent 失败计为 halted (exit 4) | 拒绝：halt 语义意味着重试预算耗尽；agent 首次失败不应消耗 loop 计数 |

## Consequences

### 正面

- 零 LLM provider 配置：任何能跑 OpenCode 的环境开箱即用。
- 验证协议（prompt、schema、关键词契约）随 SKILL.md 单点演进，Markdown 即代码。
- 减少一层进程桥接与 4 个 provider SDK 依赖（保留期后移除）。
- CI 不再需要 mock LLM 场景（数据层契约由纯函数单测锁定）。

### 负面 / 风险

- prompt 从 Python 字符串变为 Markdown 指令，行为确定性略降 — 用 e2e fixture 测试（`test_rdd_verifier_self_contained.bats`）锁定。
- 丢失 provider 级 429/5xx 指数退避重试 — 依赖 agent 自身重试语义。
- 丢失确定性 mock 验证 — CI 聚焦数据层契约，agent 全流程走 nightly。
- 缓存 miss 时 archive gate 从"warning 放行"变为"fail closed"，用户必须先跑 `rddf rdd-verify` 或显式 bypass — 有意为之的收紧（见 spec `verifier-archive-gate` 修订）。
- 启发式分类依赖英文关键词：agent 若用中文写 reasoning，conservative default 仍是安全的 `implementation_gap`（SKILL.md 已要求 reasoning 嵌入英文关键词）。

### 兼容性窗口

- `rddf ac-verify <change>`：shim 重定向到 v2.0 协议（cache 评估 / stage context），exit code 映射保持 0/1/2/3。
- `ac_verifier.{sh,py}` 与 4 个 provider：保留可运行，标记 deprecated，下个 minor release 删除。
- 历史 verdict cache：schema v2 未变，`_lib/verifier/cache.py` 原样读取。

## References

- Change: `openspec/changes/inline-ac-verifier-into-rdd-verifier/`
- Superseded: ADR-0034 §"State Machine" Step 2a-c、§"Sub-Skills Referenced" 的 ac-verifier 行
- 保留: ADR-0034 其余章节（5 阶段定位、loop state、审计）
- 新测试: `tests/unit/test_rdd_verifier_protocol.py`、`tests/integration/test_rdd_verifier_self_contained.bats`、`tests/integration/test_archive_gate_no_ac_fallback.bats`

---

## v2.0 closure fix addendum

This addendum is appended by change `verifier-v2-hardening` (oracle
review session `ses_f8610cbf6ffeVLcEjlRw3s2COt`).

After archiving v1.0 → v2.0, oracle scored 84/100 and listed 5 risks
that constitute the v2.0 closure:

- **P1**: `verdict_length == ac_count` is now CODE-enforced via
  `_lib/verifier/protocol.py::`validate_verdict_completeness`.
  Without this, an agent writing [AC-1 pass] for a 5-AC proposal would
  have silently passed `archive_gate_check`.
- **P2**: `VERDICT_ITEM_SCHEMA` strict: `evidence` `minItems:1`,
  `reasoning` `minLength:1`, fail/partial reasoning MUST contain a
  drift/gap keyword.
- **P2**: `_lib/cli/rdd_verify_cmd.py:332` `skills._lib` import replaced
  with `_lib.verifier` per AGENTS.md rule 25.
- **P2**: `run_one_change` exit-2 now maps to `pending` (was
  `skipped/halted`), aligned with `rddf ac-verify` shim semantics.
- **P3**: `stage_verification_context` is now atomic (temp + rename).
  `read_verdict_cache` rejects `schema_version != 2` with None.
  `validate_verdict_items` no longer silently degrades when `jsonschema`
  is missing.

The next step is `remove-ac-verifier-completely` (scheduled via
manual_deps in `roadmap-meta.yaml`) which deletes the `ac-verifier`
skill after the shim window closes.
