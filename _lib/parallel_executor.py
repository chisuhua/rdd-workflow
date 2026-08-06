#!/usr/bin/env python3
"""Parallel wave execution helper.

Executes multiple independent changes in parallel using multiprocessing.
"""
import subprocess
import sys
import json
from pathlib import Path
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_wave_changes(project_root: str, wave_num: str) -> List[str]:
    """Get changes for a specific wave from plan-handoff."""
    handoff_path = Path(project_root) / ".rddf/state/.plan-handoff.json"
    if not handoff_path.exists():
        return []
    
    with open(handoff_path) as f:
        handoff = json.load(f)
    
    return handoff.get("wave_order", {}).get(wave_num, [])


def get_independent_changes(project_root: str, changes: List[str]) -> List[str]:
    """Filter changes that have no blockers (can run in parallel)."""
    deps_path = Path(project_root) / ".rddf/state/deps-analysis.json"
    if not deps_path.exists():
        return changes  # Assume all independent if no deps analysis
    
    with open(deps_path) as f:
        deps = json.load(f)
    
    independent = []
    for name in changes:
        # Check if change has no blockers
        change_deps = deps.get("dependencies", {}).get(name, {})
        blockers = change_deps.get("blocked_by", [])
        if not blockers:
            independent.append(name)
    
    return independent


def execute_change(project_root: str, change_name: str, dry_run: bool = False) -> Tuple[str, bool, str]:
    """Execute a single change. Returns (name, success, output)."""
    if dry_run:
        return (change_name, True, f"[DRY-RUN] Would execute {change_name}")
    
    # In a real implementation, this would call guide-ship or execute
    # For now, just return success
    cmd = ["echo", f"Executing {change_name}"]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
    
    return (change_name, result.returncode == 0, result.stdout + result.stderr)


def execute_wave_parallel(
    project_root: str,
    wave_num: str,
    max_workers: int = 3,
    dry_run: bool = False
) -> Dict[str, Tuple[bool, str]]:
    """Execute all independent changes in a wave in parallel.
    
    Returns dict of {change_name: (success, output)}.
    """
    changes = get_wave_changes(project_root, wave_num)
    if not changes:
        return {}
    
    independent = get_independent_changes(project_root, changes)
    if not independent:
        print(f"No independent changes in Wave {wave_num}")
        return {}
    
    print(f"🚀 Executing Wave {wave_num} in parallel ({len(independent)} changes)")
    
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(execute_change, project_root, name, dry_run): name
            for name in independent
        }
        
        for future in as_completed(futures):
            name = futures[future]
            try:
                _, success, output = future.result()
                results[name] = (success, output)
                icon = "✅" if success else "❌"
                print(f"  {icon} {name}")
            except Exception as e:
                results[name] = (False, str(e))
                print(f"  ❌ {name}: {e}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Parallel wave executor")
    parser.add_argument("--wave", required=True, help="Wave number (1, 2, 3)")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--max-workers", type=int, default=3, help="Max parallel workers")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be executed")
    
    args = parser.parse_args()
    
    results = execute_wave_parallel(
        args.project_root,
        args.wave,
        args.max_workers,
        args.dry_run
    )
    
    success_count = sum(1 for _, (ok, _) in results.items() if ok)
    print(f"\n📊 Results: {success_count}/{len(results)} successful")
