"""``rddf validate`` subcommand handler.

Runs 4 quality gate checks (informational only, never blocks):

  1. openspec CLI availability + version
  2. git repository check
  3. state file existence (iteration.json, deps-analysis.json, .arch-handoff.json, .plan-handoff.json)
  4. ``openspec validate --all --json`` (only if openspec CLI is available)

Inspired by the old bash implementation at ``rddf`` lines 914-974.
Returns 0 always (informational, no blocking).
"""
from __future__ import annotations

import json
import os
import subprocess


def cmd_validate(args: list[str]) -> int:
    """Run quality gate checks and print results.

    Args:
        args: CLI args after ``validate`` token (currently unused).

    Returns:
        0 always (informational — quality gates never block).
    """
    project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    state_dir = os.path.join(project_root, ".rddf", "state")

    print()
    print("🔍 质量门控检查")
    print("──")

    # ── Check 1: openspec CLI ─────────────────────────────────
    cli_ok = False
    cli_version = "?"
    try:
        r = subprocess.run(
            ["openspec", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        cli_ok = r.returncode == 0
        if cli_ok:
            cli_version = r.stdout.strip()
            print(f"  ✓ openspec CLI: {cli_version}")
        else:
            print(f"  ✗ openspec CLI: 返回码 {r.returncode}")
    except FileNotFoundError:
        print("  ✗ openspec CLI: 未安装")
    except subprocess.TimeoutExpired:
        print("  ✗ openspec CLI: 超时")
    except Exception as e:
        print(f"  ✗ openspec CLI: {e}")

    # ── Check 2: git repository ────────────────────────────────
    git_ok = False
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project_root,
        )
        git_ok = r.returncode == 0
        if git_ok:
            print("  ✓ git 仓库")
        else:
            print(f"  ✗ git 仓库: {r.stderr.strip()}")
    except FileNotFoundError:
        print("  ✗ git 仓库: git 未安装")
    except subprocess.TimeoutExpired:
        print("  ✗ git 仓库: 超时")
    except Exception as e:
        print(f"  ✗ git 仓库: {e}")

    # ── Check 3: state files ───────────────────────────────────
    state_files = {
        "iteration.json": os.path.join(state_dir, "iteration.json"),
        "deps-analysis.json": os.path.join(state_dir, "deps-analysis.json"),
        ".arch-handoff.json": os.path.join(state_dir, ".arch-handoff.json"),
        ".plan-handoff.json": os.path.join(state_dir, ".plan-handoff.json"),
    }
    for label, path in state_files.items():
        exists = os.path.isfile(path)
        icon = "✓" if exists else "−"
        print(f"  {icon} .rddf/state/{label}")

    # ── Check 4: openspec validate (only if CLI is available) ──
    if cli_ok and git_ok:
        try:
            r = subprocess.run(
                ["openspec", "validate", "--all", "--json"],
                capture_output=True,
                text=True,
                cwd=project_root,
                timeout=30,
            )
            if r.returncode == 0:
                result = json.loads(r.stdout)
                totals = result.get("summary", {}).get("totals", {})
                passed = totals.get("passed", 0)
                failed = totals.get("failed", 0)
                print(f"  openspec validate: {passed} passed, {failed} failed")
            else:
                print(f"  ⚠ openspec validate 返回码: {r.returncode}")
        except json.JSONDecodeError:
            print("  ⚠ openspec validate: JSON 解析失败")
        except subprocess.TimeoutExpired:
            print("  ⚠ openspec validate: 超时")
        except Exception as e:
            print(f"  ⚠ openspec validate 异常: {e}")
    else:
        print("  − openspec validate: 跳过（CLI 或 git 不可用）")

    print()
    return 0


__all__ = ["cmd_validate"]