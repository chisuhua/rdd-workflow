---
name: rdd-doctor
description: 手动触发的只读诊断工具 — 校验 5 类结构化文件（`.rddf/state/*.json` schema / `.rddf/plans/*.md` TDD 5 步 / `openspec/changes/*/roadmap-meta.yaml` / `proposal-*.md` 表格 / `openspec/changes/*/tasks.md` checkbox）。输出分级报告（CRITICAL/WARNING/INFO）+ 可选 JSON 写入 `.rddf/state/.doctor-report.json`。退出码对齐 `openspec validate` (0/1/2/3)。**手动触发 only**，不修改任何 tracked / gitignored 文件（除了 `--json` 输出）。
license: MIT
compatibility: Requires bash + git + python3.11+ + jsonschema + pyyaml
metadata:
  author: rdd-workflow
  version: 0.1.0
  user-invocable: true
---

# rdd-doctor

## 调用

```bash
bash skills/rdd-doctor/scripts/doctor.sh [--json] [--category state|plan-tdd|roadmap-meta|proposal-table|tasks-checkbox] [--quiet] [--help] [--version]
```

## 何时该跑

1. **感觉"流程哪里不对"** → 5 秒排查入口
2. **修改 `_lib/schemas/` 后** → 跑 `--category state` 看是否有旧 state 文件需要迁移
3. **CI 升级 `STRICT_ARCH_GATE=yes` 之前** → 跑一次预估会暴露多少问题
4. **接手别人工作树** → 跑一次看 `.rddf/state/*.json` 是否干净

## 退出码

| Code | 含义 |
|------|------|
| 0 | 所有 5 类 OK |
| 1 | 仅 INFO + WARNING，无 CRITICAL |
| 2 | 至少 1 个 CRITICAL |
| 3 | checker 内部异常（其他类仍能报告） |

## 关键约束（不要违反）

- **只读** — 不修改任何 tracked / gitignored 文件（除了 `--json` 输出 `.rddf/state/.doctor-report.json`）
- **手动触发 only** — 不接入任何 phase gate / 自动调用
- **cat-5 独立于 openspec CLI** — `openspec` 缺失时降级为 checkbox-only，输出 INFO 而非 silent skip

## 5 类检查概览

| 类别 | 检查什么 |
|------|---------|
| `state` | `.rddf/state/*.json` 对 `_lib/schemas/*.json` schema |
| `plan-tdd` | `.rddf/plans/*.md` 含 5 个 TDD step markers |
| `roadmap-meta` | `openspec/changes/*/roadmap-meta.yaml` 字段 + 类型（**manual_deps 漂移会静默忽略**，doctor 报 CRITICAL） |
| `proposal-table` | `proposal-suggestions.md` / `proposal-approved.md` Markdown 表格列数 + 链接有效性 |
| `tasks-checkbox` | `openspec/changes/*/tasks.md` checkbox 计数（独立于 openspec CLI） |
| `migration-residue` | `AGENTS.md` / `README.md` / `USAGE.md` / `docs/proposal-*-format.md` 里的 stale `improvements/X` 引用和 `.rddf/.rddf/improvements/X` 双前缀 bug（WARNING）。`Fix:` 行直接给出 `rddf migrate-improvements --include-docs [--allow-source-repo]` 完整命令 |

## 路径解析（MUST 行为）

doctor 总是从**真实的 `_lib/`**（`<project_root>/_lib/`）读取 schema，**不**走 `skills/_lib/` shim 路径——这是 commit c3a90fe 之后所有代码必须遵循的规则，doctor 是其中第一个强制执行者。

## AI 助手编排协议（v0.2.0 新增）

当 `skill_use("rdd-doctor")` 被调用时，AI 助手（OpenCode / Claude Code / Cursor / etc.）**必须**遵循以下流程。**用户不需要手工跑任何命令行**——AI 会执行。

### Step 1 — 收集 findings

```bash
bash skills/rdd-doctor/scripts/doctor.sh --json
```

解析 `.rddf/state/.doctor-report.json`（或 stdout）得到 findings 列表。如果 AI 是被 `guide` 推荐器调起的，可以用 `--category <name>` 缩小范围。

### Step 2 — 展示给用户

按严重度分组展示：

```
=== CRITICAL (N) ===
  ❌ [category] file:line — snippet
      Fix: hint
=== WARNING (N) ===
  ⚠️ ...
=== INFO (N) ===
  ℹ️ ...
```

**不允许**默默跳过任何严重度。CRITICAL 必须显眼（用户问题严重）。

### Step 3 — 询问用户授权

```
检测到 N 个 findings。要修复吗？
  y — 全部修
  n — 不修（仅记录）
  p — 选择性修（用户逐个标）
```

**铁律**：**用户没明确授权前，禁止执行任何修复**。"修" 意味着调用会写文件的命令（rddf migrate-improvements 等），不是只读的 doctor 本身。

### Step 4 — 执行修复（按 category 映射）

| finding.category | 修复动作（AI 调用）|
|------------------|---------------------|
| `migration-residue` | `rddf migrate-improvements [--include-docs] [--allow-source-repo]`（dry-run → 确认 → 跑）|
| `state`（schema drift）| 提示用户重跑对应 phase（doctor 没有执行动作） |
| `plan-tdd`（缺 step marker） | 提示手工补全或 reject plan |
| `proposal-table`（列数不符） | 提示手工调整表格格式 |
| `tasks-checkbox` | 提示运行 execute 或手工 fix tasks.md |
| `roadmap-meta`（manual_deps drift）| 提示手工调整或重跑 plan |

**所有写操作必须先 `--dry-run`**，让用户看到会改什么再决定。例如：

```bash
# 不直接跑 rddf migrate-improvements
rddf migrate-improvements --dry-run --include-docs
# 展示输出给用户
# 用户确认后
rddf migrate-improvements --include-docs
```

**合并**：同 category 的多个 findings 合并为一次执行（migrate-improvements 一次跑就能修所有 migration-residue）。

### Step 5 — 验证

修复完成后**必须**再跑一次 doctor，确认 findings 清零：

```bash
bash skills/rdd-doctor/scripts/doctor.sh
```

向用户报告最终状态：
- 修了哪些（X 个 category / Y 个 finding）
- 还剩哪些（哪些 finding 用户选择跳过，或无执行动作）

### 关键约束

- **doctor 本身永远是只读的** — AI 严禁修改 doctor.py / doctor.sh / *_check.py 来"自动化"修复
- 修复通过**单独的写命令**（rddf migrate-improvements 等）实现，保持单一职责
- **任何用户没明确授权的修复**，禁止执行
- 用户可随时说"只报告不修"，AI 必须尊重

### 第三方纯 CLI 用户（非 AI 助手场景）

无 AI 编排时，rdd-doctor 仍可单独使用：

```bash
bash skills/rdd-doctor/scripts/doctor.sh   # 看报告
rddf migrate-improvements --help          # 找对应 flag
rddf migrate-improvements --dry-run       # 预览
rddf migrate-improvements                 # 执行
```

doctor 的 `Fix:` 行已经写了完整命令，直接复制即可。