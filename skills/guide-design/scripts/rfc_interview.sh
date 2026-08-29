#!/usr/bin/env bash
# rfc_interview.sh - Interactive RFC draft generator
#
# Usage:
#   bash skills/guide-design/scripts/rfc_interview.sh <proposal_name>
#   RDDF_APPROVE_ACTOR=<user> bash ... (non-interactive; uses env var for created_by)
#
# Writes .rddf/state/.rfc-draft-<name>.json conforming to
# skills/_lib/schemas/rfc_draft_schema.json v1.
#
# Mirrors the interactive pattern of approve_proposal.sh (read -t 30 -rp).
# Re-prompts on invalid input. Returns 3 if user aborts 3 retries.

set -euo pipefail

NAME="${1:-}"
if [ -z "$NAME" ]; then
  echo "ERROR: usage: rfc_interview.sh <proposal_name>" >&2
  exit 2
fi

# Sanitize name to match schema pattern
if ! [[ "$NAME" =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}$ ]]; then
  echo "ERROR: invalid proposal_name '$NAME' (must match ^[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}$)" >&2
  exit 2
fi

ACTOR="${RDDF_APPROVE_ACTOR:-}"
if [ -z "$ACTOR" ]; then
  read -t 30 -rp "GitHub username (drafter): " _u || true
  ACTOR="$_u"
fi
if [ -z "$ACTOR" ]; then
  echo "ERROR: empty or timeout for GitHub username; set RDDF_APPROVE_ACTOR for non-interactive" >&2
  exit 4
fi

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
PROPOSAL_MD="$PROJECT_ROOT/openspec/changes/$NAME/proposal.md"
if [ -f "$PROPOSAL_MD" ]; then
    RDDF_NAME_FOR_PRECHECK="$NAME" \
    RDDF_PROPOSAL_PATH="$PROPOSAL_MD" \
    python3 - <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ.get("PROJECT_ROOT", "."))
from _lib.rfc_ambiguity import detect_ambiguity
from _lib.rfc_interview_state import save_state
items = detect_ambiguity(os.environ["RDDF_PROPOSAL_PATH"])
save_state(os.environ["RDDF_NAME_FOR_PRECHECK"],
          {"ambiguities": [{"kind": a.kind, "severity": a.severity,
                            "suggestion": a.suggestion} for a in items]})
if items:
    print(f"\n⚠️  RFC ambiguity check ({len(items)} finding(s)):")
    for a in items:
        print(f"  [{a.severity}] {a.kind}: {a.suggestion}")
else:
    print("✅ RFC precheck: no ambiguities detected.")
PYEOF
fi

# Title (required, 3-200 chars)
_title=""
for _try in 1 2 3; do
  read -t 60 -rp "RFC title (3-200 chars, prefix [RFC] recommended): " _t || true
  if [ "${#_t}" -ge 3 ] && [ "${#_t}" -le 200 ]; then
    _title="$_t"
    break
  fi
  echo "  (length=${#_t}, must be 3-200) retry $((_try + 0))/3" >&2
done
[ -n "$_title" ] || { echo "ERROR: title required" >&2; exit 3; }

# Stakeholders (comma-separated org/repo)
_stakeholders=""
for _try in 1 2 3; do
  read -t 60 -rp "Stakeholders (comma-separated org/repo, e.g. org/repo-a,org/repo-b): " _s || true
  if [ -n "$_s" ]; then
    # Validate format
    _ok=1
    IFS=',' read -ra _parts <<< "$_s"
    for p in "${_parts[@]}"; do
      p_trimmed="$(echo "$p" | xargs)"
      if ! [[ "$p_trimmed" =~ ^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$ ]]; then
        _ok=0
        echo "  (invalid format: '$p_trimmed')" >&2
        break
      fi
    done
    if [ "$_ok" = 1 ]; then
      _stakeholders="$_s"
      break
    fi
  fi
  echo "  retry $((_try + 0))/3" >&2
done
[ -n "$_stakeholders" ] || { echo "ERROR: stakeholders required" >&2; exit 3; }

# Gate (enum)
_gate="Design-Gate"
read -t 30 -rp "Gate (Arch-Gate / Design-Gate / Plan-Gate / Ship-Gate) [Design-Gate]: " _g || true
if [ -n "$_g" ]; then
  case "$_g" in
    Arch-Gate|Design-Gate|Plan-Gate|Ship-Gate) _gate="$_g" ;;
    *) echo "  (invalid, using Design-Gate)" >&2 ;;
  esac
fi

# Contract impact (enum)
_impact="Breaking-Change"
read -t 30 -rp "Contract impact (Low / Medium / High / Critical / Breaking-Change) [Breaking-Change]: " _i || true
if [ -n "$_i" ]; then
  case "$_i" in
    Low|Medium|High|Critical|Breaking-Change) _impact="$_i" ;;
    *) echo "  (invalid, using Breaking-Change)" >&2 ;;
  esac
fi

# Contract draft path (optional)
_cd_path=""
read -t 30 -rp "Contract draft path (optional, Enter to skip): " _p || true
if [ -n "$_p" ]; then
  if [ -f "$_p" ]; then
    _cd_path="$_p"
  else
    echo "  (file not found, skipping)" >&2
  fi
fi

# Build JSON via python (safe escaping)
OUT=".rddf/state/.rfc-draft-${NAME}.json"
mkdir -p ".rddf/state"

TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

python3 - "$OUT" "$NAME" "$_title" "$_stakeholders" "$_gate" "$_impact" "$_cd_path" "$ACTOR" "$TIMESTAMP" <<'PYEOF'
import json, sys, re
out, name, title, stakeholders, gate, impact, cd_path, actor, ts = sys.argv[1:10]

stakeholder_list = [s.strip() for s in stakeholders.split(",") if s.strip()]

doc = {
    "version": 1,
    "proposal_name": name,
    "title": title,
    "stakeholders": stakeholder_list,
    "gate": gate,
    "contract_impact": impact,
    "created_at": ts,
    "created_by": actor,
}
if cd_path:
    doc["contract_draft_path"] = cd_path

# Validate against schema (best-effort, skip if jsonschema unavailable)
try:
    import jsonschema, json as _json
    schema_path = ".rddf/wt/add-rfc-interview-flow/skills/_lib/schemas/rfc_draft_schema.json"
    # Resolve relative to script location
    import pathlib
    p = pathlib.Path(__file__).resolve().parent.parent.parent / "_lib" / "schemas" / "rfc_draft_schema.json"
    if p.is_file():
        schema = _json.loads(p.read_text())
        jsonschema.validate(doc, schema)
except (ImportError, FileNotFoundError):
    pass  # best-effort; runtime caller will validate
except Exception as e:
    print(f"WARNING: draft schema validation failed: {e}", file=sys.stderr)

with open(out, "w") as f:
    json.dump(doc, f, indent=2)

print(f"RFC draft written: {out}")
PYEOF

echo "✅ RFC draft generated for '$NAME'"