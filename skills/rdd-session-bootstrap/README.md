# rdd-session-bootstrap Engine (PoC v0.1.0)

> 通用 session-bootstrap 引擎 — 把 v0100-bootstrap 等项目特定 session-bootstrap skill 通用化
> PoC v0.1.0 — byte-equal 验证 against v0100-bootstrap.sh pending

## What is this

通用 session-bootstrap 引擎，读取项目 `.rddf/skill-profiles/session-bootstrap.toml` + 跑 5 内建 section + 2 原语 + 2 逃生舱，输出 markdown (Layer 3 raw state) 到 stdout。

被 rdd-workflow 生态 spoke 项目用于解决 **cross-session continuity 问题**（每次新 session 都要重新 `openspec list` + `git log` + 读 state）。

## Quick Start (零配置)

```bash
# 1. 项目侧创建 minimal profile (单文件, 零 hook)
mkdir -p .rddf/skill-profiles
cat > .rddf/skill-profiles/session-bootstrap.toml <<'EOF'
[profile]
name = "my-project"
title = "My Project Session Bootstrap"

[sections]
order = ["header", "active_changes", "recent_commits", "workspace_health"]
test_families = []
custom_sections = []
EOF

# 2. 跑引擎
bash ~/.agents/skills/rdd-session-bootstrap/rdd-session-bootstrap.sh
```

## Quick Start (full, v0100 风格)

```bash
# 1. 项目侧创建 profile
cat > .rddf/skill-profiles/session-bootstrap.toml <<'EOF'
[profile]
name = "v0100-wave5"
title = "ChipForge v0.10.0 wave5 Session Bootstrap"

[sections]
order = [
  "header", "active_changes", "initiative_status", "recent_commits",
  "workspace_health", "test_status", "preflight_reminders", "hard_prerequisites"
]

test_families = [
  { tag = "[cpu-l1-mmu-demo]", export = "DEMO" },
  { tag = "[riscv-tests]",     export = "RISCV" },
]

custom_sections = [
  { name = "preflight_reminders", script = "tools/bootstrap/sections/preflight.sh" },
  { name = "hard_prerequisites",  script = "tools/bootstrap/sections/gates.sh" },
]
EOF

# 2. 创建 hook scripts
mkdir -p tools/bootstrap/sections
# (preflight.sh + gates.sh — 见 PoC 案例: ChipForge/tools/bootstrap/sections/)

# 3. 跑引擎
bash ~/.agents/skills/rdd-session-bootstrap/rdd-session-bootstrap.sh
```

## Architecture

```
┌─────────────────────────────────────────┐
│ rdd-workflow/spoke 项目                  │
│                                          │
│  .rddf/skill-profiles/session-bootstrap.toml  (项目 profile, TOML)
│  tools/bootstrap/sections/*.sh          (项目 hooks, 逃生舱)
│                                          │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│ rdd-workflow/skills/rdd-session-bootstrap/  (通用 core) │
│                                          │
│  rdd-session-bootstrap.sh  (引擎, ~380 行 bash)
│    - TOML 解析 (python3 tomllib, 零外部依赖)
│    - 5 内建 section (header/active_changes/...)
│    - 2 原语 (test_family/honesty_audit*)
│    - 2 逃生舱 (custom_section/review_mode*)
│    - env var 契约 (BOOTSTRAP_*)             │
│                                          │
│  SKILL.md             (协议层, ~250 行)     │
│    - Layer 3/4 协议 (bash raw + LLM 合成)   │
│    - 3 modes (Generate/Review/Audit*)      │
│    - A1-A8 审计清单                        │
│                                          │
└─────────────────────────────────────────┘
               ↓
         markdown Layer 3 raw state → stdout
         LLM 用 SKILL.md §Template 合成 Layer 4 paste-ready prompt
         LLM `write` 工具 save → `last-bootstrap-prompt.md`
```

## Schema (TOML profile)

```toml
[profile]
name = "..."                # 必填
title = "..."               # 必填 (人类可读)
version = "1"               # 可选, default "1"

[sections]
order = ["header", "active_changes", ...]  # 必填 (section 数组)
test_families = [
  { tag = "[xxx]", export = "XXX" },         # 可选 (空 = 无 test 原语)
]
custom_sections = [
  { name = "...", script = "..." },          # 可选 (空 = 无逃生舱)
]

# 可选段 (PoC v0.2):
# [honesty_audit]
# claim_files = ["AGENTS.md", "CHANGELOG.md"]
# families = [{ tag = "[xxx]", export = "XXX" }]
#
# [review]
# script = "tools/bootstrap/review.sh"
```

## Sections

### 5 内建 (零配置)

| Section | Source | Notes |
|---------|--------|-------|
| `header` | `date` + `git rev-parse --short HEAD` | timestamp + HEAD + DO NOT REUSE 警告 |
| `active_changes` | `openspec list` | rdd-workflow 通用 |
| `initiative_status` | `.rddf/sync_strategy_status.sh --dry-run` | rdd-workflow 通用 |
| `recent_commits` | `git log --oneline -5` | 通用 |
| `workspace_health` | `git status` + orphan changes 扫描 | rdd-workflow 通用 |

### 2 原语 (参数化)

| 原语 | Profile 配置 | Output |
|------|-------------|--------|
| `test_family` | `binary` + `families: [{tag, export}]` | Catch2 compact 3-branch 解析 + `BOOTSTRAP_<EXPORT>_PASSED/FAILED/TOTAL` |
| `honesty_audit` | `claim_files` + `families` | claimed vs measured 对账表 (PoC v0.2 planned) |

### 2 逃生舱 (项目 shell)

| 逃生舱 | Profile 配置 | 用途 |
|--------|-------------|------|
| `custom_section` | `[{name, script}]` | 引擎调 bash, 内联 stdout |
| `review_mode` | `script` | review 模式调, 消费 BOOTSTRAP_* (PoC v0.2 planned) |

## env var 契约 (引擎 → hook)

| Var | 含义 |
|-----|------|
| `BOOTSTRAP_HEADER_TIMESTAMP` | 引擎跑时 timestamp |
| `BOOTSTRAP_HEADER_HEAD` | short HEAD commit |
| `BOOTSTRAP_<EXPORT>_PASSED/FAILED/TOTAL` | test family 通过/失败/总数 |
| `BOOTSTRAP_DIRTY_FILES` | dirty working tree 文件数 |
| `BOOTSTRAP_ORPHAN_CHANGES` | orphan changes 数 |

**约定**: 引擎 export, hook 只读不反写.

## Compatibility

| 依赖 | 版本 | 备注 |
|------|------|------|
| bash | 4+ | 用了 `declare -A` 数组 |
| python | 3.11+ | tomllib stdlib (零外部依赖) |
| openspec CLI | v1.3.1+ | active_changes section 依赖 |
| git | 2.25+ | 用了 `git rev-parse --show-toplevel` |
| rdd-workflow | latest | `.rddf/` 布局 |

## Validation

```bash
# v0100 byte-equal 验证 (partially, PoC v0.1 阶段)
diff <(cd /workspace/project/ChipForge && bash tools/v0100-bootstrap.sh 2>/dev/null) \
     <(cd /workspace/project/ChipForge && bash tools/v0100-bootstrap.sh 2>/dev/null)

# rdd-workflow-e2e 零配置验证 (已 pass)
cd /workspace/main/rdd-workflow-e2e && bash /workspace/main/rdd-workflow/skills/rdd-session-bootstrap/rdd-session-bootstrap.sh
```

## Known Limitations (PoC v0.1)

- K1: `honesty_audit` 原语未实装 (planned v0.2)
- K2: `review_mode` 逃生舱未实装 (planned v0.2)
- K3: `audit` mode 完整实现未实装 (planned v0.2)
- K4: TOML 解析每次 section 重新跑 python3 (性能可接受, ~10ms)

## License

MIT
