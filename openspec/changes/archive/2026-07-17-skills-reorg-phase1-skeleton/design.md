# Design: skills-reorg-phase1-skeleton

## Decision 1: 子目录布局

采用 PKGM-Wiki 模式：`skills/<name>/SKILL.md` + `scripts/` + `references/`。

```
skills/
  guide/           # 原 skills/guide.md
    SKILL.md
    scripts/       # 空, Phase 2 填充
    references/    # 空, Phase 4 填充
  guide-arch/      # 原 skills/guide-arch.md
    SKILL.md
    scripts/
    references/
  ...
  _lib/            # 保持原位
  __init__.py      # 保持原位
  loop_engine.py   # 保持原位
```

## Decision 2: 路径兼容性保障

移动 `skills/guide.md` → `skills/guide/SKILL.md` 后，关键的路径解析无需更改：

```
旧: source "$(dirname "${BASH_SOURCE[0]:-$0}")/_lib/X.sh"
  → $(dirname skills/guide.md) = skills/
  → skills/_lib/X.sh                    ✅

新: source "$(dirname "${BASH_SOURCE[0]:-$0}")/_lib/X.sh"
  → $(dirname skills/guide/SKILL.md) = skills/guide/
  → skills/guide/_lib/X.sh              ❌ 不对!

修正: source "$(dirname "${BASH_SOURCE[0]:-$0}")/../_lib/X.sh"
  → $(dirname skills/guide/SKILL.md) = skills/guide/
  → skills/guide/../_lib/X.sh = skills/_lib/X.sh  ✅
```

**Phase 1 不改任何路径，依然用 `_lib/`。所以现有的 `source ... _lib/X.sh` 必须加 `../`**。

不，等一下。Phase 1 的承诺是"不改任何路径"。但 `$(dirname ...)` 从 `skills/` 变成了 `skills/guide/`，相对路径 `_lib/` 不再有效。

**修正方案**: Phase 1 必须更新 source 路径，或者保持 SKILL.md 在 `skills/` 顶层。

**Decision 2 修订**: Phase 1 确实需要更新 ~15 处 `source` 路径（将 `_lib/X.sh` 改为 `../_lib/X.sh`）。这个是纯文本替换，不会断链，也不涉及 _lib/ 内部变化。回滚时除了 `mv` 回去，还需 reverse-sed 还原路径。

## Decision 3: INSTALL.md 处理

选项 A: `skills/INSTALL/` + `SKILL.md`（作为独立技能）  
选项 B: `skills/INSTALL.md` 保持原位（因为它是安装器，不属于运行时 skill）

**选 B**。INSTALL.md 是安装脚本而非运行时技能，在 `skills/` 顶层保持特殊地位更合理。Phase 1 不移动 INSTALL.md。

## Decision 4: `spec-workflow-writing-plans.md` 处理

该文件是纯参考文档（0 个 `_lib/` 依赖），放在 `skills/spec-workflow-writing-plans/SKILL.md`。

## Decision 5: package.json 兼容性

`package.json` 的 `"skills"` 数组使用 skill `name` 字段（来自 frontmatter），不依赖文件路径。移动 SKILL.md 不影响 skill 识别。

## 回滚方案

```bash
# Step 1: reverse-sed 还原路径（mv 前做，用 4 个精确 pattern 而非 broad 替换，避免误改 prose）
for f in skills/*/SKILL.md; do
  # Pattern 1 reverse
  sed -i 's|\$(dirname "\${BASH_SOURCE\[0\]:-\$0}")/../_lib/|$(dirname "${BASH_SOURCE[0]:-$0}")/_lib/|g' "$f"
  # Pattern 2 reverse
  sed -i 's|\$SCRIPT_DIR/../_lib/|$SCRIPT_DIR/_lib/|g' "$f"
  # Pattern 3 reverse
  sed -i 's|\$_SCRIPT_DIR/../_lib/|$_SCRIPT_DIR/_lib/|g' "$f"
  # Pattern 4 reverse (readlink)
  sed -i 's|\$(dirname "\$(readlink -f "\${BASH_SOURCE\[0\]:-\$0}")")/../_lib/|$(dirname "$(readlink -f "${BASH_SOURCE[0]:-$0}")")/_lib/|g' "$f"
done

# Step 1.5: reverse feature.md manual fix
sed -i 's|_SCRIPT_DIR="$REPO_ROOT/skills/feature"|_SCRIPT_DIR="$REPO_ROOT/skills"|' skills/feature/SKILL.md
sed -i 's|_SCRIPT_DIR="$PROJECT_ROOT/skills/feature"|_SCRIPT_DIR="$PROJECT_ROOT/skills"|' skills/feature/SKILL.md

# Step 2: 移动文件回顶层 + 删除子目录
for dir in skills/*/; do
  name=$(basename "$dir")
  [ "$name" = "_lib" ] && continue
  [ "$name" = "__pycache__" ] && continue
  mv "$dir/SKILL.md" "skills/$name.md"
  rm -rf "$dir"
done

# Step 3: 还原 test 文件路径
for skill in guide guide-arch guide-plan guide-ship propose execute feature status deps roadmap rddf-session spec-workflow-writing-plans; do
  find tests/ -type f \( -name '*.bats' -o -name '*.bash' -o -name '*.py' -o -name '*.md' \) \
    -exec sed -i "s|skills/${skill}/SKILL.md|skills/${skill}.md|g" {} +
done
```
