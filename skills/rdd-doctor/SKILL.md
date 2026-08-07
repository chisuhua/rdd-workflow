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

## 路径解析（MUST 行为）

doctor 总是从**真实的 `_lib/`**（`<project_root>/_lib/`）读取 schema，**不**走 `skills/_lib/` shim 路径——这是 commit c3a90fe 之后所有代码必须遵循的规则，doctor 是其中第一个强制执行者。