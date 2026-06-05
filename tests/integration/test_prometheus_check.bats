#!/usr/bin/env bats

load ../test_helper

@test "package.json declares prometheus-start-work in skills array" {
  [ -f "package.json" ]
  grep -q '"prometheus-start-work"' "package.json"
}

@test "package.json engines references prometheus-start-work" {
  grep -q "prometheus-start-work" "package.json"
  # Should be in engines block (not just anywhere)
  python3 -c "
import json
with open('package.json') as f:
    data = json.load(f)
assert 'prometheus-start-work' in data.get('engines', {}), 'prometheus-start-work not in engines'
print('OK')
" 2>/dev/null
}

@test "README documents prometheus install command" {
  [ -f "README.md" ]
  grep -q "npx skills add chisuhua/prometheus" "README.md"
}

@test "guide-ship.md has early check with clear install message" {
  [ -f "skills/guide-ship.md" ]
  grep -q "prometheus-start-work 技能未安装" "skills/guide-ship.md"
  # Verify the check is BEFORE the actual call
  CHECK_LINE=$(grep -n "prometheus-start-work 技能未安装" "skills/guide-ship.md" | head -1 | cut -d: -f1)
  CALL_LINE=$(grep -n 'if skill_use("prometheus-start-work") 2>/dev/null' "skills/guide-ship.md" | head -1 | cut -d: -f1)
  [ -n "$CHECK_LINE" ] && [ -n "$CALL_LINE" ] && [ "$CHECK_LINE" -lt "$CALL_LINE" ]
}
