#!/usr/bin/env bats
#
# test_prometheus_planning.bats - 验证 prometheus-planning 技能替换 prometheus-start-work
# 覆盖范围:
#   - 文件存在性 + frontmatter 完整性
#   - package.json 声明正确(必需 + 可选)
#   - guide-ship.md 委托给 prometheus-planning
#   - README 文档反映新架构
#   - 三级回退链逻辑分支都被文档化

load ../test_helper

# === 1. 技能文件存在性与元数据 ===

@test "prometheus-planning.md exists in skills/" {
  assert_file_exists "$REPO_ROOT/skills/prometheus-planning.md"
}

@test "prometheus-planning.md has valid frontmatter" {
  local f="$REPO_ROOT/skills/prometheus-planning.md"
  # 必须有 YAML frontmatter 起始
  head -1 "$f" | grep -q '^---$'
  # 必须有 name 字段
  grep -qE '^name:[[:space:]]*prometheus-planning' "$f"
  # 必须有 description
  grep -qE '^description:' "$f"
  # 必须有 version
  grep -qE '^[[:space:]]+version:[[:space:]]*"[0-9]+\.[0-9]+"' "$f"
  # 必须声明 evolved-from (追溯来源)
  grep -qE 'evolved-from:' "$f"
  # 必须标记 replaces (取代对象)
  grep -qE 'replaces:[[:space:]]*"prometheus-start-work' "$f"
}

@test "prometheus-planning.md documents the three-tier fallback chain" {
  local f="$REPO_ROOT/skills/prometheus-planning.md"
  # 1️⃣ 内置 Prometheus
  grep -qE '内置.*Prometheus|oh-my-opencode.*plan|builtin' "$f"
  # 2️⃣ superpowers/writing-plans 回退
  grep -qE 'superpowers/writing-plans|writing-plans' "$f"
  # 3️⃣ 报错/退出分支
  grep -qE 'none|不可用|exit 1' "$f"
}

@test "prometheus-planning.md detection logic checks config file and tries subagent" {
  local f="$REPO_ROOT/skills/prometheus-planning.md"
  # 配置文件探测
  grep -qE 'opencode\.json|oh-my-opencode.*plugin' "$f"
  # 试调子代理 (关键的二次验证步骤)
  grep -qE 'task\(subagent_type="plan"|试调.*plan|ping' "$f"
}

# === 2. package.json 声明正确性 ===

@test "package.json declares prometheus-planning in skills array" {
  python3 -c "
import json
with open('$REPO_ROOT/package.json') as f:
    data = json.load(f)
assert 'prometheus-planning' in data.get('skills', []), 'prometheus-planning missing from skills[]'
print('OK')
" 2>/dev/null
}

@test "package.json engines references oh-my-opencode (required)" {
  python3 -c "
import json
with open('$REPO_ROOT/package.json') as f:
    data = json.load(f)
engines = data.get('engines', {})
assert 'oh-my-opencode' in engines, 'oh-my-opencode not in engines'
# 必须含 semver 约束
import re
assert re.match(r'>=[\d.]+', engines['oh-my-opencode']), f\"engines.oh-my-opencode must use semver: {engines['oh-my-opencode']}\"
print('OK')
" 2>/dev/null
}

@test "package.json moves prometheus-start-work to optionalEngines (deprecated)" {
  python3 -c "
import json
with open('$REPO_ROOT/package.json') as f:
    data = json.load(f)
# 必需 engines 不应再含 prometheus-start-work
assert 'prometheus-start-work' not in data.get('engines', {}), 'prometheus-start-work should be REMOVED from engines'
# 应在 optionalEngines 中(带 deprecated 标记)
opt = data.get('optionalEngines', {})
assert 'prometheus-start-work' in opt, 'prometheus-start-work must remain in optionalEngines for back-compat'
assert 'deprecated' in opt['prometheus-start-work'].lower(), 'optionalEngines entry must mark deprecated status'
print('OK')
" 2>/dev/null
}

@test "package.json skills array removes prometheus-start-work" {
  python3 -c "
import json
with open('$REPO_ROOT/package.json') as f:
    data = json.load(f)
assert 'prometheus-start-work' not in data.get('skills', []), 'prometheus-start-work should be REMOVED from skills[] (not a real skill in this package)'
print('OK')
" 2>/dev/null
}

@test "package.json peerDependenciesMeta declares superpowers as optional fallback" {
  python3 -c "
import json
with open('$REPO_ROOT/package.json') as f:
    data = json.load(f)
pdm = data.get('peerDependenciesMeta', {})
assert 'superpowers' in pdm, 'superpowers peer dep meta missing'
assert pdm['superpowers'].get('optional') is True, 'superpowers must be marked optional'
print('OK')
" 2>/dev/null
}

# === 3. guide-ship.md 委托正确性 ===

@test "guide-ship.md delegates to prometheus-planning (not prometheus-start-work)" {
  local f="$REPO_ROOT/skills/guide-ship.md"
  # 必须调用新技能
  grep -qE 'skill_use\("prometheus-planning"\)' "$f"
  # 旧调用应仅出现在历史注释中
  # 统计 grep -c "prometheus-start-work" 必须 ≤ 1 (仅注释)
  local count
  count=$(grep -c 'prometheus-start-work' "$f" || echo 0)
  [ "$count" -le 1 ] || { echo "expected ≤ 1 historical reference, got $count"; return 1; }
}

@test "guide-ship.md honors SKIP_PROMETHEUS_PLANNING bypass env var" {
  local f="$REPO_ROOT/skills/guide-ship.md"
  grep -qE 'SKIP_PROMETHEUS_PLANNING' "$f"
}

@test "guide-ship.md compatibility field no longer mentions prometheus-start-work" {
  local f="$REPO_ROOT/skills/guide-ship.md"
  # 提取 compatibility 行,断言不含 prometheus-start-work
  local compat
  compat=$(grep -E '^compatibility:' "$f" | head -1)
  if echo "$compat" | grep -q 'prometheus-start-work'; then
    echo "compatibility field still references deprecated skill: $compat"
    return 1
  fi
  # 必须提及新技能
  echo "$compat" | grep -qE 'prometheus-planning'
}

# === 4. README 文档反映新架构 ===

@test "README.md prerequisites section explains the three-tier fallback" {
  local f="$REPO_ROOT/README.md"
  # 必须有"实施计划生成器"或类似小节
  grep -qE '实施计划生成器|三级回退|fallback' "$f"
  # 必须列三档
  grep -qE 'oh-my-opencode' "$f"
  grep -qE 'superpowers/writing-plans|writing-plans' "$f"
  # 必须标记 prometheus-start-work 为 deprecated
  grep -qE 'deprecated|已弃用' "$f"
}

@test "README.md no longer claims prometheus-start-work is required" {
  local f="$REPO_ROOT/README.md"
  # 旧描述:"prometheus-start-work skill (必需...)"  必须被替换
  ! grep -qE '必需.*prometheus-start-work|prometheus-start-work.*必需' "$f" || {
    echo "README still claims prometheus-start-work is required"
    return 1
  }
}

@test "README.md documents SKIP_PROMETHEUS_PLANNING escape hatch" {
  local f="$REPO_ROOT/README.md"
  grep -qE 'SKIP_PROMETHEUS_PLANNING' "$f"
}

@test "README.md directory structure includes prometheus-planning.md" {
  local f="$REPO_ROOT/README.md"
  # 在目录树块内
  grep -qE 'prometheus-planning\.md' "$f"
}

# === 5. 跨文件一致性 ===

@test "all references to the new skill use consistent spelling (prometheus-planning)" {
  # 扫描所有 .md 文件,统计 prometheus-planning 提及次数
  local count_skill
  count_skill=$(grep -rE 'prometheus-planning' "$REPO_ROOT/skills/" "$REPO_ROOT/README.md" "$REPO_ROOT/package.json" 2>/dev/null | wc -l)
  [ "$count_skill" -ge 5 ] || { echo "expected ≥ 5 references to new skill across files, got $count_skill"; return 1; }
}

# 注: 原 #18 测试 (no test file re-asserts...) 与 #8 ("package.json skills array removes
# prometheus-start-work") 完全冗余 — 后者已通过 JSON 解析直接断言 skills[] 数组不含
# prometheus-start-work。删除冗余测试以避免自指失败。
