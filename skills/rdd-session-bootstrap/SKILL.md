---
name: rdd-session-bootstrap
description: |
  通用 session-bootstrap skill — 解决 cross-session continuity 问题（rdd-workflow 生态通用版）.

  替代 v0100-bootstrap (ChipForge 项目特定) 等重复造轮子的 session-bootstrap skill.
  通过 TOML profile + hook script 适配项目特定需求, 通过 5 内建 section (rdd-workflow 通用) 零配置开箱即用.

  Invoke when BOTH:
    1. New session starting on a rdd-workflow project (need state snapshot + paste-ready prompt)
    2. Project uses openspec + .rddf/ (any rdd-workflow spoke)

  Default: 3 modes — Generate (paste-ready prompt) / Review (deep state analysis) / Audit (verify saved prompt freshness).

  Underlying: bash rdd-session-bootstrap.sh + python3 tomllib (zero external deps beyond stdlib).

  Boundary ownership: see role.boundaries.owns / not_owns.
license: MIT
compatibility: Requires bash 4+, python 3.11+ (tomllib stdlib), openspec CLI v1.3.1+, git 2.25+, rdd-workflow ecosystem
metadata:
  version: "0.1.0"
  author: sisyphus
  evolved-from: "ChipForge .opencode/skills/v0100-bootstrap/SKILL.md (2026-10-09 generalization, rdd-quick PoC)"
  user-invocable: true
  status: "PoC — byte-equal validation against v0100-bootstrap.sh pending"
role:
  title: "Session Bootstrap Generator (会话引导生成器)"
  perspective: "Think in terms of state collection → template-driven synthesis → cross-session reference. Zero project state hardcoded; project specifics live in `.rddf/skill-profiles/<name>.toml` and hook scripts."
  boundaries:
    owns:
      - "skills/rdd-session-bootstrap/SKILL.md"
      - "skills/rdd-session-bootstrap/rdd-session-bootstrap.sh"
      - "skills/rdd-session-bootstrap/templates/profile.toml.example"
    not_owns:
      - ".rddf/skill-profiles/<name>.toml (project-side profile)"
      - "tools/bootstrap/sections/*.sh (project-side hooks)"
      - "tools/v0100-bootstrap.sh (legacy v0100 wrapper, project-side)"
      - ".opencode/skills/v0100-bootstrap/SKILL.md (legacy project-specific skill)"
      - "openspec/changes/*/tasks.md (project source of truth)"
      - "AGENTS.md (project doc, only read)"
    human_involvement: "low"
---

# rdd-session-bootstrap Skill (PoC v0.1.0)

> 通用 session-bootstrap skill — 解决 rdd-workflow spoke 项目的 cross-session continuity 问题.
> 把项目特定逻辑 (test families / case 决策树 / 路由表) 抽到 TOML profile + hook scripts, core skill 保持项目无关.

## What this skill solves

**Cross-session continuity problem**: AI agent sessions are stateless. Without this skill, each new session must:
1. Run `openspec list` + read state files (5+ commands)
2. Parse current state
3. Determine which hard prerequisite is blocking
4. Construct a session-start prompt manually

**Cost per project (现状, pre-PoC)**: ~600 lines bash + ~400 lines SKILL.md 重写
**Cost per project (post-PoC)**: ~30 lines TOML profile + ~50 lines hook script(s) (可选, 简单 case 零 hook)

## Quick Start

### Zero-config (any rdd-workflow project with `.rddf/skill-profiles/session-bootstrap.toml`)

```bash
# 1. 项目侧创建 profile (单文件)
cat > .rddf/skill-profiles/session-bootstrap.toml <<EOF
[profile]
name = "my-project"
title = "My Project Session Bootstrap"

[sections]
order = ["header", "active_changes", "initiative_status", "recent_commits", "workspace_health"]
custom = []
EOF

# 2. 跑引擎
bash ~/.agents/skills/rdd-session-bootstrap/rdd-session-bootstrap.sh
```

### With project-specific test families

```toml
[profile]
name = "my-project"

[sections]
order = ["header", "active_changes", "recent_commits", "test_status", "workspace_health"]

[test_status]
binary = "./build/bin/my_tests"
families = [
  { tag = "[smoke]", export = "SMOKE" },
  { tag = "[integration]", export = "INTEG" },
]

[custom]
sections = [
  { name = "preflight_reminders", script = "tools/bootstrap/preflight.sh" },
]
```

```bash
# Output: Layer 3 raw state (markdown) → agent uses SKILL.md §Output to synthesize Layer 4 paste-ready prompt
```

## Architecture: Layer 3/4 协议

### Layer 3 (raw state, engine output)
- **What**: bash engine 跑 5 内建 section + N 原语 + M 逃生舱 hook, 输出 markdown 到 stdout
- **When**: 每次 invoke (refresh state)
- **Source of truth**: 项目实况 (git HEAD, openspec list, test results)

### Layer 4 (synthesized prompt, LLM output)
- **What**: LLM 用 SKILL.md §Template 合成 Layer 3 raw state → paste-ready session-start prompt
- **When**: 每次 invoke (regenerate)
- **Adds**: 必读路由 / "不要做" 列表 / smart recommendations / 启动清单 6 步

### Why split?
- Layer 3 是 deterministic (脚本跑), 可 shellcheck + 测试
- Layer 4 是 creative (LLM 决策), 不可自动化但可模板化
- 拆分让**核心协议 (SKILL.md) 与项目实况 (engine output) 互不污染**

## 3 Modes

### Generate mode (default)
产出 2 artifacts:
1. **Saved file** `last-bootstrap-prompt.md` (via LLM write tool, Layer 4 完整合成)
2. **Inline markdown code block** (同内容, 供 copy-paste fallback)

### Review mode (`--review`)
产出 structured review report: state summary + hard prereqs + recent changes + risk assessment + recommendations + questions for user.

### Audit mode (`--audit <file>`)
审计已保存 prompt (per A1-A8 清单): timestamp / HEAD / paths / boot checklist / "不要做" / honesty / smart-recs / metadata.

## 5 内建 Section (零配置)

| Section | Source | Notes |
|---------|--------|-------|
| `header` | `date` + `git rev-parse --short HEAD` | timestamp + HEAD + DO NOT REUSE 警告 |
| `active_changes` | `openspec list` | rdd-workflow 通用 |
| `initiative_status` | `.rddf/sync_strategy_status.sh --dry-run` | rdd-workflow 通用 (兼容老 `tools/sync_strategy_status.sh` 1 周过渡期) |
| `recent_commits` | `git log --oneline -5` | 通用 |
| `workspace_health` | `git status --porcelain` + orphan changes 扫描 | rdd-workflow 通用 (`openspec/changes/*/tasks.md` 含 `## 9.` 标记的 archive 候选) |

## 2 原语 (参数化)

| 原语 | Profile 配置 | 输出 |
|------|-------------|------|
| `test_family` | `binary` + `families: [{tag, export}]` | per-family Catch2 compact 解析 + `BOOTSTRAP_<EXPORT>_PASSED/FAILED/TOTAL` env vars |
| `honesty_audit` | `claim_files: [AGENTS.md, CHANGELOG.md]` + `families: [{tag, export}]` | claimed vs measured 对账表 (✅/🟡 stale/❌) (PoC v0.1: 暂未实装, planned v0.2) |

## 2 逃生舱 (项目 shell script)

| 逃生舱 | Profile 配置 | 调用约定 |
|--------|-------------|---------|
| `custom_section` | `[{name, script}]` | 引擎调 `bash <script>`, 内联 stdout 到 markdown `## <name>` 段 |
| `review_mode` | `script` | review 模式下调脚本, 消费 `BOOTSTRAP_*` env vars, 输出 smart recommendations (e.g. Case A-E 决策树) (PoC v0.1: 暂未实装, planned v0.2) |

## env var 契约 (引擎 → hook)

引擎统一导出 `BOOTSTRAP_<NAME>_*` 命名空间, hook 脚本消费:

| Env var | 含义 | 来源 |
|---------|------|------|
| `BOOTSTRAP_HEADER_TIMESTAMP` | 引擎跑时 timestamp | header section |
| `BOOTSTRAP_HEADER_HEAD` | short HEAD commit | header section |
| `BOOTSTRAP_<EXPORT>_PASSED` | test family 通过数 | test_family 原语 |
| `BOOTSTRAP_<EXPORT>_FAILED` | test family 失败数 | test_family 原语 |
| `BOOTSTRAP_<EXPORT>_TOTAL` | test family 总数 | test_family 原语 |
| `BOOTSTRAP_DIRTY_FILES` | dirty working tree 文件数 | workspace_health section |
| `BOOTSTRAP_ORPHAN_CHANGES` | orphan changes 数 | workspace_health section |

**约定**: 引擎导出, hook 只读不反写.

## Self-Verification 协议

**每次 compose Layer 4 prompt 后**:
1. 确认 prompt 内 HEAD = `git rev-parse --short HEAD` (避免 stale)
2. 确认 timestamp ≤ 4 小时前 (避免 reuse)
3. write tool save → read tool verify (避免 race / 截断)

**失败时**: regenerate, 不要 reuse 旧 prompt.

## Audit Checklist A1-A8 (Audit mode)

| # | 检查项 | 通过标准 | FAIL 行动 |
|---|--------|---------|----------|
| A1 | 时间戳新鲜度 | timestamp ≤ 4 小时前 | 建议 regenerate |
| A2 | HEAD 一致性 | prompt 内 HEAD = `git rev-parse --short HEAD` | regenerate |
| A3 | 路由表路径可达 | 所有 `docs/research/*.md` 等存在 | 标 ❌ + 修复建议 |
| A4 | 启动清单完整 | 6 步齐 (openspec list / §5 read / tasks phase / tests / 3 CI scripts / report) | 标 ❌ + 补缺失 |
| A5 | "不要做" 防御层 | ≥ 10 条 + 含 archive/vexii/tools-scope/CHANGELOG-stale 等关键禁止 | 补缺 |
| A6 | Honesty audit 全 ✅ | 4 项对账全 ✅ (无 ❌) | Case E 触发: 报告失配 + 不 implement |
| A7 | Smart recs 与 hard_prerequisites 一致 | demo PASS + cycle-precision 降级 → 推荐主路径正确 | 不一致: 重写 |
| A8 | 修订 metadata 存在 | 文件末尾 "修订要点 N 处" + 来源 + 日期 | 加 metadata |

## §What NOT to do

- ❌ 在 engine (rdd-session-bootstrap.sh) 内硬编码项目特定 paths / commands / test families → 走 profile + hook
- ❌ 把项目特定 case 决策树 (e.g. v0100 Case A-E) 写进 core SKILL.md → 走 profile.review_script hook
- ❌ 直接 edit Layer 3 raw state 当作 Layer 4 prompt → 永远用 SKILL.md §Template 合成
- ❌ Reuse 旧 prompt 而不 regenerate → timestamp + HEAD verification 是 hard requirement
- ❌ commit `last-bootstrap-prompt.md` (session-local, gitignored)
- ❌ 改 profile schema 而不更新 `templates/profile.toml.example` + `engine_profile_loader()`
- ❌ 把 core skill 强加于非 rdd-workflow 项目 (boundary check per role.boundaries.not_owns)

## §Maintenance

### When to update SKILL.md
- 模式契约 (Generate/Review/Audit) 变化
- env var 契约变化
- A1-A8 清单变化
- 5 内建 section 增删 (影响所有 spoke)

### When to update engine (rdd-session-bootstrap.sh)
- TOML schema 字段增删
- 内建 section 实现变化
- 原语解析逻辑变化
- env var 命名变化

### When to update project profile (`.rddf/skill-profiles/session-bootstrap.toml`)
- 项目加新 test family
- 项目加新 custom section
- review decision tree 变化
- 不影响其他项目 (project-local)

## Known Issues (PoC v0.1)

| # | Issue | 临时绕过 | 长期修法 |
|---|-------|---------|---------|
| K1 | honesty_audit 原语未实装 (planned v0.2) | 项目用 custom_section 逃生舱 | v0.2: 实现 extract_claim + 对账表 (原语) |
| K2 | review_mode 逃生舱未实装 (planned v0.2) | 项目写自己的 review_script | v0.2: 实现 review mode dispatcher |
| K3 | TOML 解析用 `python3 -c tomllib`, 每次 section 调用重新解析 | 性能可接受 (单 profile < 1ms) | v0.2: 缓存解析结果到 `$BOOTSTRAP_PROFILE_CACHE` |
| K4 | `[profile]` 段必须存在, 无 default fallback | 项目 template 提供 | v0.2: 加 schema validator, 缺失字段时报错而非静默 |

## Underlying tools

| Layer | Tool | Source |
|-------|------|--------|
| Engine | `rdd-session-bootstrap.sh` | skill 自带 (~250 行 bash + python3 tomllib call) |
| State sources | `openspec list`, `git log/status`, `bash .rddf/sync_strategy_status.sh` | rdd-workflow 生态标准 |
| Profile schema | TOML v1.0 | python3.11+ tomllib stdlib (zero external deps) |
| Hook scripts | 项目 `tools/bootstrap/sections/*.sh` | 项目侧, git-tracked |

## Migration from v0100-bootstrap

详见 `templates/v0100-migration-notes.md` (PoC v0.1 暂未提供, planned v0.2).

Quick path (PoC 期间):
1. 复制 `v0100-bootstrap.sh` 旧输出到 `/tmp/v0100-baseline.md` 作为对照
2. 创建 `.rddf/skill-profiles/session-bootstrap.toml` (PoC 模板从 `templates/profile.toml.example`)
3. 创建 `tools/bootstrap/sections/<原 v0100 硬前置段>.sh` (从 v0100 旧 bash 提取)
4. 跑引擎, diff vs baseline
5. 反复迭代直到 byte-equal (允许 [WARN] 标记, 不允许内容缺失)

## License

MIT
