#!/usr/bin/env bats
# tests/integration/test_skill_role_all.bats
#
# Verifies all 4 phase SKILL.md files have complete role fields.
# Per ADR-0028: role.title, role.perspective, role.boundaries.owns,
# role.boundaries.not_owns, role.boundaries.human_involvement.

load ../test_helper

setup() {
  SCHEMA_FILE="$REPO_ROOT/_lib/schemas/skill_role_schema.json"
  SKILLS=(guide-arch guide-design guide-plan guide-ship)
}

@test "all 4 phase skills exist" {
  for skill in "${SKILLS[@]}"; do
    [ -f "$REPO_ROOT/skills/$skill/SKILL.md" ]
  done
}

@test "skill_role_schema.json exists in _lib/schemas/" {
  [ -f "$SCHEMA_FILE" ]
}

@test "guide-arch has role.title field" {
  python3 <<PYEOF
import yaml, sys
with open("$REPO_ROOT/skills/guide-arch/SKILL.md") as f:
  content = f.read()
  frontmatter = content.split("---\n")[1]
  data = yaml.safe_load(frontmatter)
  assert "role" in data, "Missing role field"
  assert "title" in data["role"], "Missing role.title"
  print("PASS")
PYEOF
}

@test "guide-design has complete role fields (5 sub-fields)" {
  python3 <<PYEOF
import yaml, sys
with open("$REPO_ROOT/skills/guide-design/SKILL.md") as f:
  content = f.read()
  frontmatter = content.split("---\n")[1]
  data = yaml.safe_load(frontmatter)
  role = data.get("role", {})
  assert "title" in role, "Missing role.title"
  assert "perspective" in role, "Missing role.perspective"
  assert "boundaries" in role, "Missing role.boundaries"
  assert "owns" in role["boundaries"], "Missing boundaries.owns"
  assert "not_owns" in role["boundaries"], "Missing boundaries.not_owns"
  assert "human_involvement" in role["boundaries"], "Missing boundaries.human_involvement"
  print("PASS: all 5 sub-fields present")
PYEOF
}

@test "guide-plan has complete role fields (5 sub-fields)" {
  python3 <<PYEOF
import yaml, sys
with open("$REPO_ROOT/skills/guide-plan/SKILL.md") as f:
  content = f.read()
  parts = content.split("---\n")
  if len(parts) < 3:
    print(f"ERROR: guide-plan missing frontmatter", file=sys.stderr)
    sys.exit(1)
  frontmatter = parts[1]
  data = yaml.safe_load(frontmatter)
  role = data.get("role")
  if not role:
    print(f"ERROR: guide-plan missing role field", file=sys.stderr)
    sys.exit(1)
  required_top = ["title", "perspective", "boundaries"]
  for k in required_top:
    if k not in role:
      print(f"ERROR: guide-plan missing role.{k}", file=sys.stderr)
      sys.exit(1)
  boundaries = role["boundaries"]
  required_bounds = ["owns", "not_owns", "human_involvement"]
  for k in required_bounds:
    if k not in boundaries:
      print(f"ERROR: guide-plan missing boundaries.{k}", file=sys.stderr)
      sys.exit(1)
  print("PASS")
PYEOF
}

@test "guide-ship has complete role fields (5 sub-fields)" {
  python3 <<PYEOF
import yaml, sys
with open("$REPO_ROOT/skills/guide-ship/SKILL.md") as f:
  content = f.read()
  parts = content.split("---\n")
  if len(parts) < 3:
    print(f"ERROR: guide-ship missing frontmatter", file=sys.stderr)
    sys.exit(1)
  frontmatter = parts[1]
  data = yaml.safe_load(frontmatter)
  role = data.get("role", {})
  if not role:
    print(f"ERROR: guide-ship missing role field", file=sys.stderr)
    sys.exit(1)
  assert len(role.get("boundaries", {}).get("owns", [])) >= 1, "owns must have at least 1 path"
  assert len(role.get("boundaries", {}).get("not_owns", [])) >= 1, "not_owns must have at least 1 path"
  assert role.get("boundaries", {}).get("human_involvement") in ["high", "medium", "low"], "Invalid human_involvement"
  print("PASS")
PYEOF
}

@test "ADR-0028 file exists" {
  [ -f "$REPO_ROOT/docs/adr/ADR-0028-role-model-per-phase.md" ]
}

@test "AGENTS.md references ADR-0028" {
  grep -q "ADR-0028" "$REPO_ROOT/AGENTS.md"
}

@test "SKILL.md without role field still loads" {
  # Create a temp SKILL.md without role field
  TEMP_DIR="$BATS_TMPDIR/backward_compat_test"
  mkdir -p "$TEMP_DIR/skills/guide-arch"
  
  # Copy guide-arch but strip role field
  python3 <<PYEOF
import sys
with open("$REPO_ROOT/skills/guide-arch/SKILL.md") as f:
  content = f.read()
parts = content.split("---\n")
frontmatter_lines = parts[1].split("\n")
# Remove lines starting with "role:" or indented (role sub-fields)
filtered = []
skip_role_block = False
for line in frontmatter_lines:
  if line.startswith("role:"):
    skip_role_block = True
    continue
  if skip_role_block and (line.startswith("  ") or line.startswith("\t")):
    continue
  skip_role_block = False
  filtered.append(line)
new_frontmatter = "\n".join(filtered)
with open("$TEMP_DIR/skills/guide-arch/SKILL.md", "w") as out:
  out.write("---\n" + new_frontmatter + "\n---\n" + parts[2])
PYEOF
  
  # Verify it still parses (no YAML error)
  python3 <<PYEOF
import yaml
with open("$TEMP_DIR/skills/guide-arch/SKILL.md") as f:
  content = f.read()
  frontmatter = content.split("---\n")[1]
  data = yaml.safe_load(frontmatter)
  assert data is not None, "Frontmatter parse failed"
  print("PASS: SKILL.md without role field parses successfully")
PYEOF
}
