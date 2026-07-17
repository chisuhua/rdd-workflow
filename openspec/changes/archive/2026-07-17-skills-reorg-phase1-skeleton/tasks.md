# Tasks: skills-reorg-phase1-skeleton

## Phase 0: 前置 — 更新测试文件路径

先更新所有测试文件中的硬编码路径，与文件移动解耦。

### 0.1: 批量替换 test 文件中 `skills/<name>.md` → `skills/<name>/SKILL.md`

```bash
for skill in guide guide-arch guide-plan guide-ship propose execute feature status deps roadmap rddf-session spec-workflow-writing-plans; do
  find tests/ -type f \( -name '*.bats' -o -name '*.bash' -o -name '*.py' -o -name '*.md' \) \
    -exec sed -i "s|skills/${skill}\\.md|skills/${skill}/SKILL.md|g" {} +
done
```

**验证**: `grep -rn 'skills/[a-z_-]*\.md' tests/` 不应匹配任何被移动的技能（INSTALL.md 和 `_lib/` 引用除外）

### 0.2: 手动审查 extraction 测试中的行号锚定

`tests/integration/test_*_extraction.bats` 中有些测试锚定了特定行号（如 `grep -n "arch_env_check.sh" skills/guide-arch.md` 断言 L92-L189）。因为 `mv` 后文件内容不变（纯复制），行号应一致。但需要手动确认 frontmatter 长度无变化。

**验证**: 对比 `wc -l skills/guide-arch.md` 和 `wc -l skills/guide-arch/SKILL.md` 是否相等

### 0.3: 更新 `tests/smoke.bats` 第 26-35 行 + 第 38-42 行 frontmatter 检查

检查并更新 `tests/smoke.bats` 中硬编码的文件存在性断言，确保指向新路径。**特别注意**：
- L26-35 的 `[ -f "skills/X.md" ]` 断言 → 改为 `[ -f "skills/X/SKILL.md" ]`
- L38-42 的 frontmatter 检查 `for f in skills/*.md` → 扩展为同时检查 `skills/*/SKILL.md`，防止移动后检查退化为仅 INSTALL.md：

```bash
# 修改后应同时覆盖顶层 INSTALL.md 和子目录 SKILL.md
for f in skills/*.md skills/*/SKILL.md; do
  [ -f "$f" ] || continue
  head -1 "$f" | grep -q "^---$"
done
```

**验证**: `bats tests/smoke.bats` 通过，且 frontmatter 检查覆盖 13 个文件（1 个 INSTALL.md + 12 个 SKILL.md）

### 0.4: 更新 `tests/integration/test_skill_metadata_consistency.bats`

更新其中 `os.path.isfile(f'skills/{s}.md')` 为 `os.path.isfile(f'skills/{s}/SKILL.md')`。

**验证**: `bats tests/integration/test_skill_metadata_consistency.bats` 通过

---

## Task 1: 创建子目录骨架

### 1.1: 创建 per-skill 目录结构

```bash
for skill in guide guide-arch guide-plan guide-ship propose execute feature status deps roadmap rddf-session spec-workflow-writing-plans; do
  mkdir -p "skills/$skill/scripts"
  mkdir -p "skills/$skill/references"
done
```

**验证**: `ls -d skills/*/scripts/` 返回 12 个目录

### 1.2: 移动 SKILL.md 到子目录

```bash
for skill in guide guide-arch guide-plan guide-ship propose execute feature status deps roadmap rddf-session spec-workflow-writing-plans; do
  mv "skills/$skill.md" "skills/$skill/SKILL.md"
done
```

**验证**: `ls skills/*.md` 只剩 INSTALL.md

### 1.3: 更新 source 路径

因 `$(dirname ...)` 从 `skills/` 变成 `skills/<name>/`，所有 `_lib/` 引用需加 `../`：

```
旧: source "$(dirname "${BASH_SOURCE[0]:-$0}")/_lib/X.sh"
新: source "$(dirname "${BASH_SOURCE[0]:-$0}")/../_lib/X.sh"

旧: source "$SCRIPT_DIR/_lib/X.sh"
新: source "$SCRIPT_DIR/../_lib/X.sh"

旧: source "$_SCRIPT_DIR/_lib/X.sh"
新: source "$_SCRIPT_DIR/../_lib/X.sh"
```

> ⚠️ **重要**：不使用全局 `s|/_lib/|/../_lib/|g`，该模式会破坏：
> - `$REPO_ROOT/skills/_lib/X.sh`（如 `guide-ship.md` 3 处，`feature.md` 1 处）→ 变成不存在的 `$REPO_ROOT/skills/../_lib/` = `$REPO_ROOT/_lib/`
> - 文档性 prose 引用（如 `` `skills/_lib/gate.py` ``）
>
> 这些应保持原样。

用 4 个针对性正则替换 `skills/*/SKILL.md`:
```bash
for f in skills/*/SKILL.md; do
  # 1. $(dirname "${BASH_SOURCE[0]:-$0}")/_lib/ → ../_lib/
  sed -i 's|\$(dirname "\${BASH_SOURCE\[0\]:-\$0}")/_lib/|$(dirname "${BASH_SOURCE[0]:-$0}")/../_lib/|g' "$f"

  # 2. $SCRIPT_DIR/_lib/ → $SCRIPT_DIR/../_lib/
  sed -i 's|\$SCRIPT_DIR/_lib/|$SCRIPT_DIR/../_lib/|g' "$f"

  # 3. $_SCRIPT_DIR/_lib/ → $_SCRIPT_DIR/../_lib/
  sed -i 's|\$_SCRIPT_DIR/_lib/|$_SCRIPT_DIR/../_lib/|g' "$f"

  # 4. $(dirname "$(readlink -f "${BASH_SOURCE[0]:-$0}")")/_lib/ → ../_lib/  (guide.md 唯一使用 readlink)
  sed -i 's|\$(dirname "\$(readlink -f "\${BASH_SOURCE\[0\]:-\$0}")")/_lib/|$(dirname "$(readlink -f "${BASH_SOURCE[0]:-$0}")")/../_lib/|g' "$f"
done
```

**验证**:
- `grep -rn 'skills/\.\./_lib' skills/*/SKILL.md` → 必须为空（无 B2 类型的 sed 腐败）
- `grep -rn 'source.*REPO_ROOT.*skills/_lib' skills/*/SKILL.md` → 应保留 4 处原样（`guide-ship.md` 3 处，`feature.md` 1 处）
- 所有 `source.*_lib` 行中不应出现 `skills/_lib` 或 `skills/../_lib` 等格式（仅 `../_lib/` 模式）

### 1.4: 手动修复 `feature.md` fallback 逻辑

`feature.md` 第 45/47 行的 fallback 赋值在 piped 执行模式（BASH_SOURCE=/dev/fd/N）下 broken：sed 后 `$_SCRIPT_DIR/../_lib/X` 解析为不存在的 `$REPO_ROOT/_lib/`。需在 sed 后手动修改这两行：

```bash
# 用 sed 在所有 per-skill sed 后，对 feature.md 单独 fix
sed -i 's|_SCRIPT_DIR="$REPO_ROOT/skills"|_SCRIPT_DIR="$REPO_ROOT/skills/feature"|' skills/feature/SKILL.md
sed -i 's|_SCRIPT_DIR="$PROJECT_ROOT/skills"|_SCRIPT_DIR="$PROJECT_ROOT/skills/feature"|' skills/feature/SKILL.md
```

**验证**:
- `grep -n '_SCRIPT_DIR=' skills/feature/SKILL.md` → 应显示 L45 `_SCRIPT_DIR="$REPO_ROOT/skills/feature"` 和 L47 `_SCRIPT_DIR="$PROJECT_ROOT/skills/feature"`
- 模拟 piped 执行：`bash -c 'source <(sed -n "/^_SCRIPT_DIR=/,/^fi/p" skills/feature/SKILL.md); [ -f "$_SCRIPT_DIR/../_lib/feature_summary.sh" ] && echo OK'`

## Task 2: 更新 INSTALL.md 复制逻辑

### 2.1: 更新 Step 3 cp 命令

`skills/INSTALL.md` 第 100 行（Step 3）的 cp 从 flat glob 改为递归复制：

```bash
# 旧 (L100): cp -f "$PACKAGE_DIR/skills/"*.md "$SKILLS_DIR/skills/"
# 新: 递归复制 per-skill 子目录
for skill_dir in "$PACKAGE_DIR/skills/"*/; do
  skill_name=$(basename "$skill_dir")
  [ "$skill_name" = "_lib" ] && continue
  [ "$skill_name" = "__pycache__" ] && continue
  mkdir -p "$SKILLS_DIR/skills/$skill_name/scripts" "$SKILLS_DIR/skills/$skill_name/references"
  cp -f "$skill_dir/SKILL.md" "$SKILLS_DIR/skills/$skill_name/"
done
```

### 2.2: 更新 Step 4 metadata glob（Python 不可用时的 fallback）

`skills/INSTALL.md` 第 148 行附近（Step 4 fallback）的 `ls *.md` 依赖需改为扫描子目录：

```bash
# 旧: PKG_SKILLS=$(ls "$PACKAGE_DIR/skills/"*.md 2>/dev/null | xargs -n1 basename ... | sed 's/\.md$//')
# 新: PKG_SKILLS=$(find "$PACKAGE_DIR/skills/" -maxdepth 2 -name 'SKILL.md' 2>/dev/null | while read f; do basename "$(dirname "$f")"; done)
# 并保留 INSTALL.md 作为最后一项（来自 skills/INSTALL.md）
```

### 2.3: 更新生成的 `install-spec-workflow.sh` 模板

`skills/INSTALL.md` 第 195 行附近生成的安装脚本模板中的 cp 命令，同样改为递归复制模式：

```bash
# 旧: cp -f "$PACKAGE_DIR/skills/"*.md "..."
# 新: 同上递归复制 pattern
```

### 2.4: 更新 INSTALL_NOTES.txt

更新 L119-127 的提示文字，"skills/ 目录结构" → 反映新的子目录布局。

**验证**: `bats tests/integration/test_install_skill.bats`

## Task 3: 验证

### 3.1: 运行全部测试

```bash
# 单元测试
python3 -m pytest tests/unit/ -q --tb=short
python3 -m pytest tests/integration/ -q --tb=short

# 集成测试（bats）
bats tests/smoke.bats
bats tests/integration/test_skill_metadata_consistency.bats
bats tests/integration/test_install_skill.bats

# 验证 sed 无腐败（B2 检查）
! grep -rn 'skills/\.\./_lib' skills/*/SKILL.md && echo "✓ 无 sed 腐败"

# 验证 $REPO_ROOT 路径保持原样
grep -rn 'REPO_ROOT/skills/_lib' skills/*/SKILL.md | grep -v '^.*:#'

# 验证 Python 导入解析
python3 -c "
from skills._lib.rddf_session import RddfSessionCoordinator
from skills._lib.gate import GateMechanism
from skills._lib.state_vector import StateVector
from skills._lib.event_log import EventLog
from skills._lib.tribunal import Tribunal
print('✓ Python 导入全部正常')
"

# 验证 guide-ship 运行时（source 路径正确性）
if [ -f "skills/guide-ship/SKILL.md" ]; then
  bash -c '
    REPO_ROOT=$(pwd)
    source skills/guide-ship/SKILL.md 2>/dev/null || true
    type ship_plan >/dev/null 2>&1 && echo "✓ guide-ship: ship_plan 可加载" || echo "⚠ guide-ship: ship_plan 未定义（可能缺少依赖）"
  '
fi
```

### 3.2: 验证 source 路径可解析（实际文件存在性检查）

```bash
errors=0
for f in skills/*/SKILL.md; do
  SCRIPT_DIR_ACTUAL="$(cd "$(dirname "$f")" 2>/dev/null && pwd)"
  # 使用 process substitution 而非 pipe，避免 subshell 内 errors 变量丢失
  while IFS= read -r line; do
    # 提取 source 路径（支持双引号和单引号）
    path=$(echo "$line" | sed -E "s/.*source[\"']([^\"']+)[\"'].*/\1/" \
      | sed "s|\\\$(dirname \"\\\${BASH_SOURCE\\[0\\]:-\\\$0\\}\")|$SCRIPT_DIR_ACTUAL|g" \
      | sed "s|\\\$SCRIPT_DIR|$SCRIPT_DIR_ACTUAL|g" \
      | sed "s|\\\$_SCRIPT_DIR|$SCRIPT_DIR_ACTUAL|g" \
      | sed "s|\\\$REPO_ROOT|$SCRIPT_DIR_ACTUAL/..|g")
    if [ ! -f "$path" ]; then
      echo "❌ BROKEN: $f → $line → $path (不存在)"
      errors=$((errors + 1))
    fi
  done < <(grep -E 'source.*_lib/' "$f")
done
[ "$errors" -eq 0 ] && echo "✓ 所有 source 路径可解析"
exit $errors
```

### 3.3: 确认 skill_use 不受影响

`skill_use("guide-ship")` 通过 skill name 查找,不依赖文件路径。验证 `package.json` skills 数组未变。

```bash
python3 -c "
import json
with open('package.json') as f:
    skills = json.load(f)['skills']
print(f'技能数: {len(skills)}')
assert 'guide-ship' in skills, 'guide-ship 缺失'
assert 'INSTALL' in skills, 'INSTALL 缺失'
print('✓ package.json skills 数组正常')
"

# 验证 frontmatter name 字段
for f in skills/*/SKILL.md; do
  name=$(basename "$(dirname "$f")")
  grep -q "^name: $name" "$f" && echo "✓ $f → name: $name" || echo "⚠ $f → name 不匹配"
done
```

### 3.4: 回滚验证（round-trip）

```bash
# 暂存当前更改 → 执行 design.md 中的回滚脚本 → 测试 → 恢复
git stash
# 手动执行 design.md 中的回滚脚本
bats tests/smoke.bats
git stash pop
```

## Task 5: commit

```bash
git add skills/ tests/ openspec/changes/skills-reorg-phase1-skeleton/
git commit -m "refactor(skills): Phase 1 — per-skill subdirectory skeleton

- Add Phase 0: bulk-update tests/ paths (skills/<name>.md → skills/<name>/SKILL.md)
- Move 12 skill .md files into skills/<name>/SKILL.md
- Create scripts/ and references/ directories per skill
- Update source paths with 4 targeted sed patterns (skip REPO_ROOT lines)
- Manual fix feature.md fallback: _SCRIPT_DIR adds /feature suffix
- Update INSTALL.md copy logic: Step 3 cp, Step 4 glob, generated install.sh
- skills/INSTALL.md and skills/_lib/ remain at top level
- No _lib/ file changes, no Python import changes
- Strengthened validation: path existence check, sed corruption check, runtime check"
```
