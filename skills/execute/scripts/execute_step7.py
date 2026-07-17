"""Step 7 final report for execute.md.

Extracted from skills/execute.md L195-L282 (~88-line inline bash block).

Generates a final report after change execution:
- Reads tasks.md progress (done/total counts)
- Syncs iteration.json (graceful failure)
- Prints next-step instructions
- Lists other worktrees using porcelain-format parsing

Public function:
- run_step7_report(project_root, change_name) -> dict
"""
import os
import subprocess
import sys


def run_step7_report(project_root: str, change_name: str) -> dict:
    """Generate Step 7 final report. Returns summary dict.

    Args:
        project_root: Absolute path to project root.
        change_name: Name of the change being executed.

    Returns:
        Dict with: change_name, done, total, complete
    """
    tasks_file = os.path.join(project_root, "openspec", "changes", change_name, "tasks.md")

    done = 0
    total = 0
    if os.path.isfile(tasks_file):
        with open(tasks_file) as f:
            content = f.read()
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("- ["):
                total += 1
                if stripped.startswith("- [x]") or stripped.startswith("- [X]"):
                    done += 1

    complete = (done == total) and total > 0

    # Sync iteration.json (graceful failure)
    try:
        from skills._lib import iteration as it_mod
        data = it_mod.load(project_root)
        data = it_mod.set_tasks_done(data, change_name, done=done, total=total)
        it_mod.save(project_root, data)
    except Exception as e:
        print(f"⚠️  iteration.json 同步失败: {e}", file=sys.stderr)

    # Print final report
    print("")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("✅ 执行完成")
    print("")
    print(f"Change: {change_name}")
    print(f"当前进度：{done}/{total}")
    print("")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📋 下一步操作：")
    print("")
    print("1. 在主 session 查看最新进度：")
    print("   skill_use(\"guide\")")
    print("   → 进入 Execute 监控模式")
    print("")
    print("2. 直接归档（如果已完成所有任务）：")
    print(f"   cd \"{project_root}\"")
    print(f"   skill_use(\"status {change_name} --archive\")")
    print("")
    print("3. 继续处理其他 worktree：")
    print("   skill_use(\"guide-ship\")   # 内部选择 change")
    print("")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("")

    # Other worktrees check — use porcelain format (more robust than awk)
    try:
        current_wt = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if current_wt.returncode == 0:
            worktrees = []
            current_path = None
            for line in current_wt.stdout.strip().split("\n"):
                if line.startswith("worktree "):
                    current_path = line.split(" ", 1)[1]
                elif line.startswith("branch ") and current_path:
                    branch = line.split(" ", 1)[1].replace("refs/heads/", "")
                    if branch.startswith("openspec/") and branch != f"openspec/{change_name}":
                        worktrees.append((current_path, branch))
                    current_path = None

            if worktrees:
                print(f"📋 发现其他 {len(worktrees)} 个 worktree:")
                for path, branch in worktrees:
                    name = branch.replace("openspec/", "")
                    print(f"   - {name} → {path}")
                print("")
                print("请选择:")
                print("1. 切换到另一个 worktree 继续执行")
                print("2. 返回主 session（skill_use(\"guide\"))")
                print("i. 其他输入")
    except Exception as e:
        print(f"⚠️  其他 worktree 扫描失败: {e}", file=sys.stderr)

    return {
        "change_name": change_name,
        "done": done,
        "total": total,
        "complete": complete,
    }
