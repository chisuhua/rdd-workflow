#!/usr/bin/env bats
# Dynamic skill registration contract: package.json and INSTALL.md sub-skill
# table must agree with the disk-derived skill set without hard-coded names.

load ../test_helper

setup() {
  cd "$REPO_ROOT"
}

@test "skill consistency: package.json and INSTALL.md align with disk" {
  run python3 - <<'PY'
import json
from pathlib import Path

pkg = json.loads(Path("package.json").read_text())
declared = [s.strip() for s in pkg.get("skills", [])]

# Sub-skill SKILL.md only — INSTALL.md is the installer (not a sub-skill),
# matches test_doc_contracts.py::_count_skill_files() semantics (per
# fix-skill-count-and-table-schema 2026-08-25).
disk = set()
for path in Path("skills").glob("*/SKILL.md"):
    disk.add(path.parent.name)

if sorted(declared) != sorted(disk):
    raise SystemExit(
        f"package.json drift: declared={sorted(declared)} disk={sorted(disk)}"
    )

install = Path("skills/INSTALL.md").read_text()
table_names = set()
in_table = False
for raw in install.splitlines():
    line = raw.strip()
    if not line.startswith("|"):
        in_table = False
        continue
    cells = [cell.strip() for cell in line.strip("|").split("|")]
    if not cells:
        continue
    first = cells[0]
    if first.startswith("技能名称"):
        in_table = True
        continue
    if not in_table:
        continue
    if set(first) <= set("-—"):
        continue
    cleaned = first.strip("`").strip()
    if cleaned:
        table_names.add(cleaned)

if table_names != disk:
    raise SystemExit(
        f"INSTALL.md sub-skill table drift: rows={sorted(table_names)} disk={sorted(disk)}"
    )

print(f"✅ {len(disk)} skills aligned across package.json and INSTALL.md")
PY
  [ "$status" -eq 0 ]
}

@test "skill consistency: package.json skills[] entries all map to disk files" {
  run python3 - <<'PY'
import json
from pathlib import Path

pkg = json.loads(Path("package.json").read_text())
missing = []
for s in pkg.get("skills", []):
    candidates = [Path(f"skills/{s}/SKILL.md"), Path(f"skills/{s}.md")]
    if not any(p.exists() for p in candidates):
        missing.append(s)
if missing:
    raise SystemExit(f"package.json skills[] entries missing on disk: {missing}")
print("✅ all package.json skills[] entries map to disk")
PY
  [ "$status" -eq 0 ]
}

# Prose count-phrase guard (2026-11-20, fix-v4-doc-drift-live-invocations):
# USAGE.md and skills/INSTALL.md both claimed 27 sub-skills while disk had 26.
# Pin the *sentinel phrases* rather than scanning for a bare "N 个" — the
# dated version-history line in INSTALL.md must not be flagged when the skill
# set changes in a future release.
@test "skill consistency: prose skill counts in USAGE.md / INSTALL.md match disk" {
  run python3 - <<'PY'
import json, re
from pathlib import Path

disk = sorted(p.parent.name for p in Path("skills").glob("*/SKILL.md"))
pkg = json.loads(Path("package.json").read_text())
declared = sorted(s.strip() for s in pkg.get("skills", []))
expected = len(disk)
if len(declared) != expected:
    raise SystemExit(f"package.json count {len(declared)} != disk {expected}")

sentinels = [
    ("USAGE.md", r"(\d+)\s*个 per-skill 子目录"),
    ("skills/INSTALL.md", r"当前\s*(\d+)\s*个"),
]
for rel, pattern in sentinels:
    text = Path(rel).read_text()
    m = re.search(pattern, text)
    if not m:
        raise SystemExit(f"{rel}: sentinel phrase not found ({pattern})")
    got = int(m.group(1))
    if got != expected:
        raise SystemExit(f"{rel}: prose count {got} != disk {expected}")
    print(f"✅ {rel}: {got} == disk {expected}")
PY
  [ "$status" -eq 0 ]
}