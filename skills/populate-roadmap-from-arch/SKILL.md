---
name: populate-roadmap-from-arch
description: 从 ADR + 架构文档生成 phase fragment 的 body 内容。被用户在新项目 / 季度 review / 新增 ADR 后调用,自动填充 .rddf/roadmap/phases/*.md 的内容(不修改主文档 .rddf/roadmap.md,不改 frontmatter)。
license: MIT
compatibility: Requires rdd-workflow v2.1+ (层次化 roadmap 启用后) + Python 3.11+ + 现有 ADR-0016 v2 handoff
metadata:
  version: "1.0"
  author: sisyphus
  evolved-from: "manually-composed phase fragments during add-hierarchical-roadmap-structure"
---

# Populate Roadmap From Arch (v1.0)

## 职责

从 `docs/adr/` + `docs/architecture/` + `.rddf/roadmap.md` 主文档的 phase skeleton 表格 → 生成 `.rddf/roadmap/phases/<phase>.md` 的 body 内容。

**不变性约束**（用户设计决策）：
- **不修改** 主文档 `.rddf/roadmap.md`（保持"手工 source of truth"，按 ADR-0027 主题注册表约束）
- **不修改** fragment frontmatter（`id` / `kind` / `status` / `phase_refs` / `主题` 由 `roadmap migrate` 阶段生成）
- **不创建** 新 fragment 文件（只覆盖已存在的 phase fragment body）
- **不 commit**（skill 只改 working tree；用户决定何时提交）
- **不删除** 现有 fragment body 内的非 skill 生成内容（按 atomic replace 模式：`---` frontmatter 闭合行 → `## <phase-id> content (migrated from root roadmap.md)` 占位 marker 之间是 body 区域，skill 只替换 body 区域）

## 触发场景

| 场景 | 调用方式 |
|------|---------|
| **初次启用层次化 roadmap 后**，fragment body 是空的（"migrated from root roadmap.md"） | `skill_use("populate-roadmap-from-arch")` |
| **新增 ADR 后**，想刷新 fragment body 包含新 ADR | `skill_use("populate-roadmap-from-arch")` |
| **季度 review**，重新对齐 fragment 与 ADR/arch 文档 | `skill_use("populate-roadmap-from-arch")` |
| **跨项目 fork**，想复用本仓库的 ADR/arch doc 内容 | `skill_use("populate-roadmap-from-arch")` |

## 工作流位置

```
guide-arch (生成 ADR + arch doc)
    ↓
roadmap migrate (生成空 fragment + 主文档 10 行 phase skeleton)
    ↓
populate-roadmap-from-arch（本技能）  ← 填充 fragment body
    ↓
rdd-doctor --category roadmap-refs (验证 8 条规则)
```

## 命令

| 命令 | 说明 |
|------|------|
| `populate` | 一次性生成全部 4 个 phase fragment body（带 backup + diff） |
| `populate --phase phase-1` | 只生成单个 phase |
| `populate --dry-run` | 预览生成内容，不写文件 |
| `populate --no-backup` | 跳过 backup 步骤（覆盖现有内容时不保留旧版本） |

## 状态机（7 步）

### Step 0: preflight

检查先决条件：
1. `.rddf/roadmap/` 目录结构存在（`phases/` + `features/` + `archive/`）
2. 4 个 phase fragment 文件存在（`phase-1.md` ... `phase-4.md`）
3. `.rddf/state/.arch-handoff.json` 存在且 version=2
4. `docs/adr/ADR-*.md` 至少 1 个
5. `docs/architecture/*.md` 至少 1 个
6. 主文档 `.rddf/roadmap.md` 含 `## Phase Skeleton` 段

失败：exit 1 + stderr 提示哪个先决条件缺失。

### Step 1: catalog sources

读取并归类源文件：

**ADR catalog**：
- 扫描 `docs/adr/ADR-*.md`
- 提取每个 ADR 的 frontmatter / 标题 / 状态 / 关键决策
- 输出：`List[AdrRecord]`（含 id, title, status, 关键决策 1-2 句）

**架构文档 catalog**：
- 扫描 `docs/architecture/*.md`
- 提取每个 arch doc 的首段概要（≤ 200 字）
- 输出：`List[ArchDocRecord]`（含 path, title, summary）

**主文档 phase skeleton 解析**：
- 解析 `.rddf/roadmap.md` 的 `## Phase Skeleton` 表格
- 输出：`Dict[phase_id, List[theme]]`（如 `phase-1` → 3 个 theme）

### Step 2: classify ADRs by phase

按以下规则将每个 ADR 分配到 1 个或多个 phase：

1. **显式引用优先**：扫描 ADR 正文中的"实施版本 v2.0.X"段，与主文档 4 个 phase 的 theme 双向匹配
2. **主题关键词 fallback**：根据 ADR 标题 + 关键决策中的关键词匹配 phase theme
   - phase-1 theme 关键词：多会话 / rddf-session / 跨仓 / 联邦 / 提案 / issue / 触发
   - phase-2 theme 关键词：审批 / RFC / 内容审查 / design / plan / 编排 / 步骤 / skeleton / per-skill / manual_deps / deps / execution / quality gate
   - phase-3 theme 关键词：定制 / 演进 / 反馈 / 闭环 / 自动发 / 流程 / 触发器 / 步骤引擎
   - phase-4 theme 关键词：多方 / 回归 / P1-P3 / 后续 / Hub / Spoke / cross-repo

输出：`Dict[phase_id, List[AdrRecord]]`（每个 ADR 至少出现在 1 个 phase）

### Step 3: generate fragment body

对每个 phase fragment，按以下 6 段结构生成 markdown body：

1. **`## <phase-id> 概览`** — 1 段描述（从 phase 标题 + theme 表汇总）
2. **`## 已实施能力`** — 按 sub-theme 分组（每个 theme 一段，含 ADR 引用 + 代码锚点）
3. **`## 架构文档锚点`** — 表格列出相关 arch doc（来自 Step 1 catalog）
4. **`## 占位 / 未实施`** — 列出该 phase 内属于"已采纳未实施"或"设计稿"状态的 ADR（含状态 + 阻碍原因 + 后续步骤）
5. **`## 主题注册表映射`** — 主文档 `## Phase Skeleton` 表格中 phase-N 的 N 行 theme → fragment body 章节的交叉引用
6. **`## 相关变更历史`** — 与该 phase 相关的已归档 change 列表（从 `openspec/changes/archive/` 提取）
7. **`## 下一步`** — 链接到下一 phase fragment

### Step 4: backup + diff 确认

**（默认行为，除非 `--no-backup`）**

1. 为每个将被覆盖的 fragment 创建 backup：
   ```bash
   BACKUP_DIR=".rddf/roadmap/.backup/$(date -u +%Y%m%dT%H%M%SZ)"
   mkdir -p "$BACKUP_DIR/phases"
   cp -p .rddf/roadmap/phases/*.md "$BACKUP_DIR/phases/"
   ```
2. 输出 backup 路径 + 列出每个 fragment 的 diff（OLD vs NEW 字节数 / 行数）
3. **prompt 等待用户确认**（除非 `--yes` flag）：
   - `[Y/n]` 继续写入
   - `[d]` 查看详细 diff
   - `[b]` 跳到 backup 目录
   - `[q]` 退出（保留 backup）
4. 用户输入 `[Y]` 后继续 Step 5

### Step 5: write fragments

按 atomic write 模式（tmp + rename）写入：

```bash
for phase in phase-1 phase-2 phase-3 phase-4; do
    NEW_BODY="$(generate_body_for $phase)"  # from Step 3
    EXISTING=".rddf/roadmap/phases/$phase.md"
    
    # Extract frontmatter (between first --- pair)
    FRONTMATTER="$(sed -n '/^---$/,/^---$/p' "$EXISTING")"
    
    # Build new file: FRONTMATTER + "\n" + NEW_BODY
    TMP="$(mktemp)"
    printf '%s\n\n%s\n' "$FRONTMATTER" "$NEW_BODY" > "$TMP"
    mv "$TMP" "$EXISTING"
done
```

### Step 6: validate

跑两个验证：

1. **`rdd-doctor --category roadmap-refs`** — 8 条规则（R1-R8）必须全部通过
2. **`python3 -c "from _lib.roadmap_state import load_fragments; frags = load_fragments('.rddf/roadmap/'); print(f'{len(frags)} fragments')"`** — 确保 4 个 fragment 全部可解析

任一失败：exit 1 + stderr 提示哪个验证失败。

### Step 7: report

输出每个 fragment 的写入统计：

```
✅ Populated 4 phase fragments in 1.2s

phase-1: 142 lines, 4.8 KB (was 9 lines, 0.3 KB) — 3 themes, 4 ADRs, 2 arch docs, 1 placeholder
phase-2: 158 lines, 5.2 KB (was 9 lines, 0.3 KB) — 3 themes, 9 ADRs, 1 arch docs, 0 placeholders
phase-3: 124 lines, 4.1 KB (was 9 lines, 0.3 KB) — 2 themes, 3 ADRs, 1 arch docs, 4 placeholders
phase-4: 132 lines, 4.4 KB (was 9 lines, 0.3 KB) — 1 theme, 3 ADRs, 2 arch docs, 0 placeholders

Backup: .rddf/roadmap/.backup/20260820T161200Z/
Validation: ✅ rdd-doctor roadmap-refs | ✅ load_fragments

ℹ️ Working tree has changes — review with `git diff .rddf/roadmap/` and commit when ready.
   Suggested commit: chore(roadmap): populate 4 phase fragments from ADR + arch docs
```

---

## 实现结构

```
skills/populate-roadmap-from-arch/
├── SKILL.md                          ← 本文件
└── scripts/
    ├── populate.sh                   ← bash wrapper (Step 0/4/5/6/7)
    └── populate_lib.py               ← Python (Step 1/2/3)
```

## 关键约定

1. **frontmatter 不变**：skill **不修改** fragment frontmatter。`id` / `kind` / `status` / `phase_refs` / `主题:` 由 `roadmap migrate` 阶段负责。skill 只写 body。
2. **占位 ADR 必须可见**：所有"已采纳未实施"或"设计稿"状态的 ADR 在 fragment body 的 `## 占位 / 未实施` 段可见，按用户决策保留。
3. **主文档表格不动**：用户手工维护主文档 `## Phase Skeleton` 表格（按 ADR-0027 主题注册表约束）。
4. **idempotent**：skill 可重复调用，每次都基于当前 ADR/arch doc 重新生成。但有 backup + diff 保护。
5. **commit 由用户决定**：skill 不自动 commit。`--yes` flag 只跳过 diff 确认 prompt，不跳过 commit。
6. **scope 限于 phase fragments**：不修改 `features/*.md`（用户当前选择"phase 粒度 + 能力填充"；feature fragments 后续 promote 时单独处理）。
7. **依赖 ADR-0016 v2 handoff**：读 `.rddf/state/.arch-handoff.json` 取 `adr_dir` / `roadmap_path` / `roadmap_fragments_dir`，不能用硬编码路径。
8. **依赖 roadmap_state.py API**：用 `load_fragments` / `Fragment` dataclass 做验证，不自己解析 YAML。

## 触发此 skill 的 ADR

- ADR-0016 v2 (Arch Artifact Discovery Contract)：提供 `roadmap_fragments_dir` 字段
- ADR-0027 (Continuous Evolution Feedback Loop)：主题注册表（保证 skill 不破坏主文档表格）
- ADR-0028 (Role Model Per Phase)：本 skill 属于 plan/ship 之间的人类介入点

## 不兼容性 / 已知限制

- 不支持 cross-repo ADR 同步（跨仓库 ADR 引用走 ADR-0030 Hub-and-Spoke 通道）
- 不支持 fragment body 中嵌入 mermaid 图（如果需要可后续扩展）
- 不支持 fragment body 多语言（仅 zh-CN + en 段落混排，不做完整 i18n）

## 相关 skill / 文件

- `skills/roadmap/scripts/roadmap_migrate.sh` — 本 skill 的"前置"步骤（生成空 fragment + 主文档表格）
- `skills/roadmap/scripts/roadmap_validate_fragments.sh` — 本 skill 的"后续"步骤（8 条规则验证）
- `_lib/roadmap_state.py` — `Fragment` dataclass + `load_fragments` 等 API（本 skill 验证步骤用）
- `_lib/roadmap_validate.py` — `validate_fragment_refs`（被 rdd-doctor roadmap-refs 调用）
- `docs/adr/` — 输入源
- `docs/architecture/` — 输入源
- `.rddf/roadmap.md` — 主文档（不被 skill 修改）
- `.rddf/roadmap/phases/*.md` — 输出目标
