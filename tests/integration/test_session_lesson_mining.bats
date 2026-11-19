#!/usr/bin/env bats

load ../test_helper

# 新技能 session-lesson-mining：把它的自测接进 CI。
#
# 为什么必须接线：`scripts/selftest.sh` 若只存在于磁盘上，就是「入库但无人执行」的第四态
# —— 这正是本仓 2026-11 反复吃过的亏（tests/README.md 的 arch-docs 用例有同类注释）。

@test "session-lesson-mining: 挖掘器/导出器自测通过（7 检测器 + 不误报 + 导出完整性）" {
    run bash "$REPO_ROOT/skills/session-lesson-mining/scripts/selftest.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"自测通过"* ]]
    # 自测里必须真的点到 7 个检测器（防止有人把某个检测器"注释掉"后自测仍绿）
    for d in tool_error failure_signature test_failure retry_loop \
             user_correction self_correction guard_selfhit; do
        [[ "$output" == *"✓ $d:"* ]] || { echo "自测未覆盖检测器：$d" >&2; return 1; }
    done
}

@test "session-lesson-mining: package.json 发布该技能且 SKILL.md 有 canonical 前置条件" {
    run python3 -c "
import json, pathlib
pkg = json.load(open('$REPO_ROOT/package.json'))
assert 'session-lesson-mining' in pkg['skills'], 'package.json::skills[] 未发布该技能'
skill = pathlib.Path('$REPO_ROOT/skills/session-lesson-mining/SKILL.md').read_text(encoding='utf-8')
assert 'Invoke when BOTH' in skill, 'SKILL.md 缺 canonical 前置条件段'
assert 'skip' in skill, 'SKILL.md 缺 skip≠pass 约束'
print('OK')
"
    [ "$status" -eq 0 ]
    [[ "$output" == *"OK"* ]]
}
