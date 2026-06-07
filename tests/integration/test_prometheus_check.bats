#!/usr/bin/env bats
#
# test_prometheus_check.bats (DEPRECATED) - 验证 prometheus-start-work 已被正确降级
#
# 历史背景: 此文件原用于断言 prometheus-start-work 是必需依赖 (P0-6 修复前)。
# v1.1 重构后,prometheus-start-work 降级到 optionalEngines(最后回退),
# 主体实现已迁移到 prometheus-planning (见 test_prometheus_planning.bats)。
#
# 本文件保留是为了:
#   1. 防止 silent revert (有人重新把 prometheus-start-work 加回 engines)
#   2. 文档化降级契约
#   3. 一旦 prometheus-start-work 彻底移除(预计 v2.0),整文件可删除
#
# 不要在此文件中添加新测试。新功能测试请去 test_prometheus_planning.bats。

load ../test_helper

@test "package.json no longer declares prometheus-start-work in required engines (deprecation guard)" {
  [ -f "package.json" ]
  # 主要断言: JSON 解析 — 权威检查
  python3 -c "
import json
with open('package.json') as f:
    data = json.load(f)
assert 'prometheus-start-work' not in data.get('engines', {}), \
    'prometheus-start-work must NOT be in engines (use optionalEngines instead)'
print('OK')
" 2>/dev/null
}

@test "package.json no longer lists prometheus-start-work in skills array (deprecation guard)" {
  python3 -c "
import json
with open('package.json') as f:
    data = json.load(f)
assert 'prometheus-start-work' not in data.get('skills', []), \
    'prometheus-start-work must NOT be in skills[] (it lives in the external chisuhua repo, not here)'
print('OK')
" 2>/dev/null
}

@test "package.json marks prometheus-start-work as deprecated in optionalEngines" {
  python3 -c "
import json
with open('package.json') as f:
    data = json.load(f)
opt = data.get('optionalEngines', {})
# 必须存在(保留向后兼容)
assert 'prometheus-start-work' in opt, \
    'prometheus-start-work must remain in optionalEngines (last-resort fallback)'
# 必须显式标记 deprecated
assert 'deprecated' in opt['prometheus-start-work'].lower(), \
    f\"optionalEngines entry must mark deprecation: {opt['prometheus-start-work']}\"
print('OK')
" 2>/dev/null
}

@test "skills/guide-ship.md no longer requires prometheus-start-work (only historical comment allowed)" {
  [ -f "skills/guide-ship.md" ]
  # 实际调用不应再有 skill_use("prometheus-start-work")
  ! grep -qE 'skill_use\("prometheus-start-work"\)' "skills/guide-ship.md" || {
    echo "DEPRECATION REGRESSION: guide-ship.md still calls prometheus-start-work"
    return 1
  }
  # 早检(❌ 必需依赖缺失)必须被移除
  ! grep -q 'prometheus-start-work 技能未安装' "skills/guide-ship.md" || {
    echo "DEPRECATION REGRESSION: old hard-error message for prometheus-start-work still in guide-ship.md"
    return 1
  }
  # 残留的提及应仅是历史注释
  local count
  count=$(grep -c 'prometheus-start-work' "skills/guide-ship.md" || echo 0)
  [ "$count" -le 1 ] || {
    echo "expected ≤ 1 historical reference in guide-ship.md, got $count"
    return 1
  }
}

@test "README.md prerequisites no longer claim prometheus-start-work is required" {
  [ -f "README.md" ]
  # 旧措辞 "prometheus-start-work skill (必需,...)" 必须消失
  ! grep -qE '必需.*prometheus-start-work' "README.md" || {
    echo "README still claims prometheus-start-work is required"
    return 1
  }
  # 新措辞应把 prometheus-start-work 标记为 deprecated/3️⃣
  grep -qE 'deprecated|已弃用' "README.md"
}
