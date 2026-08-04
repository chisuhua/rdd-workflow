"""Helpers for comparing pytest failure output against a known-failures baseline."""
from pathlib import Path
from typing import Any, Dict, List


def _load_baseline(path: Path) -> List[str]:
    if not path.exists():
        return []
    names = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, _, _ = line.partition(" #")
        names.append(name.strip())
    return names


def parse_failed_tests(output: str) -> List[str]:
    failed = []
    for line in output.splitlines():
        if line.startswith("FAILED "):
            failed.append(line[len("FAILED "):].strip().split(" ")[0])
    return sorted(set(failed))


def compare_failures(actual: List[str], baseline_path: Path) -> Dict[str, Any]:
    baseline = set(_load_baseline(baseline_path))
    actual_set = set(actual)
    return {
        "known": sorted(actual_set & baseline),
        "new": sorted(actual_set - baseline),
        "stale": sorted(baseline - actual_set),
        "known_count": len(actual_set & baseline),
        "new_count": len(actual_set - baseline),
        "stale_count": len(baseline - actual_set),
    }
