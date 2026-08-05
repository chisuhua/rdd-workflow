load ../test_helper

@test "execute SKILL.md defers commits" {
    grep -q 'execute 阶段不执行 commit\|execute 阶段不逐任务 commit\|defers commits\|不提交\|聚合 commit' "$PROJECT_ROOT/skills/execute/SKILL.md"
}

@test "guide-ship SKILL.md mentions aggregate commit in Phase 2.7" {
    grep -q '聚合 commit\|aggregate commit\|worktree.*commit\|Phase 2.7' "$PROJECT_ROOT/skills/guide-ship/SKILL.md"
}

@test "writing-plans SKILL.md defers commits" {
    grep -q '不提交\|defer commits\|deferring commits\|archive' "$PROJECT_ROOT/skills/rdd-workflow-writing-plans/SKILL.md"
}

@test "all three skills agree: execute defers, guide-ship aggregates" {
    grep -q 'execute 不逐任务 commit\|execute 阶段不逐任务 commit' "$PROJECT_ROOT/skills/guide-ship/SKILL.md"
    grep -q 'execute 阶段不执行 commit\|execute 阶段不逐任务 commit' "$PROJECT_ROOT/skills/execute/SKILL.md"
}