#!/usr/bin/env bash
# Unit tests for check_design_done_gate 前缀匹配逻辑
set -euo pipefail

TEST_DIR=$(mktemp -d)
trap 'rm -rf "$TEST_DIR"' EXIT

source "$(git rev-parse --show-toplevel)/skills/guide-design/scripts/design_done_check.sh" 2>/dev/null || \
  source skills/guide-design/scripts/design_done_check.sh

cat > "$TEST_DIR/suggestions-pass.md" <<'EOF'
# 测试

| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
| 修复1 | P0 | test | 2026-09-01 | 已批准 |
| 修复2 | P0 | test | 2026-09-01 | 已批准 (2026-09-01, 关联 phase-4) |
| 跳过 | P2 | test | 2026-09-01 | 延迟 (2026-08-28, 维持 v3.2 deferred 决策) |
EOF

cat > "$TEST_DIR/suggestions-fail.md" <<'EOF'
# 测试

| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
| 待审 | P1 | test | 2026-09-01 | 待审查 |
EOF

cat > "$TEST_DIR/suggestions-mix.md" <<'EOF'
# 测试

| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
| 修1 | P0 | test | 2026-09-01 | 已批准 |
| 跳1 | P2 | test | 2026-09-01 | 延迟 (2026-08-28) |
| 待1 | P1 | test | 2026-09-01 | 待审查 |
EOF

# Test 1: exact 已批准 passes
if check_design_done_gate "$TEST_DIR/suggestions-pass.md" > /dev/null 2>&1; then
    echo "✅ test 1 PASS: exact 已批准"
else
    echo "❌ test 1 FAIL"; exit 1
fi

# Test 2: 已批准 with suffix passes (regression test for this bug)
if check_design_done_gate "$TEST_DIR/suggestions-mix.md" > /dev/null 2>&1; then
    echo "❌ test 2 FAIL: should fail (待审查 present)"; exit 1
else
    echo "✅ test 2 PASS: mix correctly fails"
fi

# Test 3: 延迟 with suffix passes
cat > "$TEST_DIR/suggestions-deferred.md" <<'EOF'
| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
| 跳 | P2 | test | 2026-09-01 | 延迟 (2026-08-28, 维持 v3.2 deferred 决策) |
EOF
if check_design_done_gate "$TEST_DIR/suggestions-deferred.md" > /dev/null 2>&1; then
    echo "✅ test 3 PASS: 延迟 with suffix passes"
else
    echo "❌ test 3 FAIL"; exit 1
fi

# Test 4: 待审查 fails
if check_design_done_gate "$TEST_DIR/suggestions-fail.md" > /dev/null 2>&1; then
    echo "❌ test 4 FAIL: should fail"; exit 1
else
    echo "✅ test 4 PASS: 待审查 correctly fails"
fi

# Test 5: empty status cell fails
cat > "$TEST_DIR/suggestions-blank.md" <<EOF
| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
| 空 | P1 | test | 2026-09-01 |  |
EOF
if check_design_done_gate "$TEST_DIR/suggestions-blank.md" > /dev/null 2>&1; then
    echo "❌ test 5 FAIL: should fail"; exit 1
else
    echo "✅ test 5 PASS: empty status correctly fails"
fi

echo "✅ 5/5 unit tests PASS"
