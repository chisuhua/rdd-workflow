#!/usr/bin/env bash
# populate-roadmap-from-arch: bash wrapper (Step 0/4/5/6/7).
#
# Sourceable from SKILL.md flow, or runnable standalone:
#   bash skills/populate-roadmap-from-arch/scripts/populate.sh                  # all 4 phases
#   bash skills/populate-roadmap-from-arch/scripts/populate.sh --phase phase-1  # single phase
#   bash skills/populate-roadmap-from-arch/scripts/populate.sh --dry-run        # preview only
#   bash skills/populate-roadmap-from-arch/scripts/populate.sh --no-backup      # skip backup
#   bash skills/populate-roadmap-from-arch/scripts/populate.sh --yes            # skip diff prompt
#
# Per skill metadata: version 1.0.
#
# Sourced-only entry: populate_main (defined below; call after sourcing)

set -euo pipefail

# --- Resolve paths ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# --- Step 0: preflight ---
preflight() {
    local PROJECT_ROOT="$1"

    [ -d "$PROJECT_ROOT/.rddf/roadmap" ] \
        || { echo "❌ .rddf/roadmap/ 目录不存在。请先运行 'roadmap migrate'。" >&2; return 1; }

    for phase in phase-1 phase-2 phase-3 phase-4; do
        [ -f "$PROJECT_ROOT/.rddf/roadmap/phases/$phase.md" ] \
            || { echo "❌ .rddf/roadmap/phases/$phase.md 不存在。请先运行 'roadmap migrate'。" >&2; return 1; }
    done

    [ -f "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" ] \
        || { echo "❌ .arch-handoff.json 不存在。请先运行 guide-arch 完成 arch-done。" >&2; return 1; }

    local HOFFO_VERSION
    HOFFO_VERSION=$(python3 -c "import json; print(json.load(open('$PROJECT_ROOT/.rddf/state/.arch-handoff.json')).get('version', 0))" 2>/dev/null || echo "0")
    [ "$HOFFO_VERSION" = "2" ] \
        || { echo "❌ .arch-handoff.json version=$HOFFO_VERSION（需要 v2 schema）" >&2; return 1; }

    [ -d "$PROJECT_ROOT/docs/adr" ] \
        || { echo "❌ docs/adr/ 目录不存在。" >&2; return 1; }

    local ADR_COUNT
    ADR_COUNT=$(find "$PROJECT_ROOT/docs/adr" -maxdepth 1 -name 'ADR-*.md' -type f 2>/dev/null | wc -l)
    [ "$ADR_COUNT" -gt 0 ] \
        || { echo "❌ docs/adr/ 中无 ADR 文件。" >&2; return 1; }

    [ -f "$PROJECT_ROOT/.rddf/roadmap.md" ] \
        || { echo "❌ .rddf/roadmap.md 不存在。" >&2; return 1; }

    grep -q "^## Phase Skeleton" "$PROJECT_ROOT/.rddf/roadmap.md" \
        || { echo "❌ .rddf/roadmap.md 缺少 '## Phase Skeleton' 段。" >&2; return 1; }

    return 0
}


# --- Step 4: backup ---
backup_fragments() {
    local PROJECT_ROOT="$1"
    local BACKUP_DIR="$PROJECT_ROOT/.rddf/roadmap/.backup/$(date -u +%Y%m%dT%H%M%SZ)"
    mkdir -p "$BACKUP_DIR/phases" || return 1
    cp -p "$PROJECT_ROOT/.rddf/roadmap/phases/"*.md "$BACKUP_DIR/phases/" 2>/dev/null || true
    echo "$BACKUP_DIR"
}


# --- Step 5: write fragments ---
write_fragment() {
    local FRAGMENT_PATH="$1"
    local NEW_BODY="$2"

    # Extract frontmatter (between first --- pair)
    local FRONTMATTER
    FRONTMATTER=$(sed -n '/^---$/,/^---$/p' "$FRAGMENT_PATH")

    # Atomic write: tmp + rename
    local TMP
    TMP=$(mktemp)
    {
        printf '%s\n\n' "$FRONTMATTER"
        printf '%s\n' "$NEW_BODY"
    } > "$TMP"
    mv "$TMP" "$FRAGMENT_PATH"
}


# --- Step 6: validate ---
validate() {
    local PROJECT_ROOT="$1"

    # 6a. rdd-doctor roadmap-refs
    if [ -f "$PROJECT_ROOT/skills/rdd-doctor/scripts/doctor.sh" ]; then
        echo ""
        echo "▶ 跑 rdd-doctor --category roadmap-refs..."
        if bash "$PROJECT_ROOT/skills/rdd-doctor/scripts/doctor.sh" --category roadmap-refs --quiet 2>&1; then
            echo "✅ rdd-doctor roadmap-refs"
        else
            echo "❌ rdd-doctor roadmap-refs 失败 — 修复 fragment 后重跑。" >&2
            return 1
        fi
    else
        echo "⚠️ rdd-doctor 不存在；跳过 roadmap-refs 验证"
    fi

    # 6b. load_fragments 完整性
    echo ""
    echo "▶ 验证 fragment 可被 load_fragments 解析..."
    if (cd "$PROJECT_ROOT" && python3 -c "import sys; sys.path.insert(0, '.'); from _lib.roadmap_state import load_fragments; frags = load_fragments('.rddf/roadmap/'); print(f'✅ loaded {len(frags)} fragments')" 2>&1); then
        return 0
    else
        echo "❌ load_fragments 失败" >&2
        return 1
    fi
}


# --- Step 7: report ---
report() {
    local PROJECT_ROOT="$1"
    local BACKUP_DIR="${2:-}"

    echo ""
    echo "✅ Populated phase fragments"

    for phase in phase-1 phase-2 phase-3 phase-4; do
        local F="$PROJECT_ROOT/.rddf/roadmap/phases/$phase.md"
        if [ -f "$F" ]; then
            local LINES BYTES
            LINES=$(wc -l < "$F")
            BYTES=$(wc -c < "$F")
            printf "  %s: %s lines, %s bytes\n" "$phase" "$LINES" "$BYTES"
        fi
    done

    if [ -n "$BACKUP_DIR" ]; then
        echo ""
        echo "Backup: $BACKUP_DIR"
    fi

    echo ""
    echo "ℹ️ Working tree has changes — review with 'git diff .rddf/roadmap/' and commit when ready."
    echo "   Suggested commit: chore(roadmap): populate phase fragments from ADR + arch docs"
}


# --- Main entry ---
populate_main() {
    local TARGET_PHASE="all"
    local DRY_RUN="false"
    local NO_BACKUP="false"
    local SKIP_PROMPT="false"

    while [ $# -gt 0 ]; do
        case "$1" in
            --phase) TARGET_PHASE="$2"; shift 2 ;;
            --dry-run) DRY_RUN="true"; shift ;;
            --no-backup) NO_BACKUP="true"; shift ;;
            --yes) SKIP_PROMPT="true"; shift ;;
            --code-verify) CODE_VERIFY="$2"; shift 2 ;;
            --code-verify=*) CODE_VERIFY="${1#--code-verify=}"; shift ;;
            --no-code-verify) CODE_VERIFY="off"; shift ;;
            --help|-h)
                echo "Usage: populate.sh [--phase phase-N] [--dry-run] [--no-backup] [--yes] [--code-verify=off|on|strict]"
                echo ""
                echo "  --code-verify=MODE   Cross-check ADRs against code (off|on|strict). Default: off"
                echo "    off     No verification (v1.0 behavior)"
                echo "    on      Verify and write supplementary state; render new badges"
                echo "    strict  Like 'on' but exit 2 on any discrepancy"
                echo "  --no-code-verify    Shortcut for --code-verify=off"
                return 0
                ;;
            *) echo "Unknown flag: $1" >&2; return 1 ;;
        esac
    done

    CODE_VERIFY="${CODE_VERIFY:-off}"

    echo "=== populate-roadmap-from-arch ==="

    # Step 0
    preflight "$PROJECT_ROOT" || return 1

    # Step 1+2+3 (+1.5 if --code-verify): run Python
    echo ""
    echo "▶ Catalog + classify + generate (Step 1-3)..."

    local PYTHON_OUT
    PYTHON_OUT=$(cd "$PROJECT_ROOT" && CODE_VERIFY_MODE="$CODE_VERIFY" python3 -c "
import sys, json, os
sys.path.insert(0, '.')
sys.path.insert(0, '$SCRIPT_DIR')
from pathlib import Path
from populate_lib import (
    catalog_sources, classify_adrs_by_phase, generate_phase_body,
    verify_adr_by_code, save_supplementary,
)

project_root = Path('${PROJECT_ROOT}')
adrs, arch_docs, main_doc_phases = catalog_sources(project_root)
classified = classify_adrs_by_phase(adrs, main_doc_phases)

code_verify_mode = os.environ.get('CODE_VERIFY_MODE', 'off')
verifications = {}

if code_verify_mode in ('on', 'strict'):
    # Step 1.5: cross-check ADRs against actual code (mcp→grep fallback)
    inputs = []
    adr_text_map = {}
    for adr in adrs:
        try:
            adr_text = adr.path.read_text(encoding='utf-8', errors='replace')
        except OSError:
            adr_text = ''
        adr_text_map[adr.id] = adr_text
        inputs.append((adr, adr_text, project_root))

    from populate_lib import verify_all_adrs
    results = verify_all_adrs(inputs, max_workers=4)
    verifications = {r.adr_id: r for r in results}

    if '${DRY_RUN}' != 'true':
        save_supplementary(results, project_root)
        print(f'[code-verify] Wrote {len(results)} records (mode={code_verify_mode})', file=sys.stderr)

    if code_verify_mode == 'strict':
        discrepancies = [r for r in results if r.has_discrepancy]
        if discrepancies:
            print(f'[code-verify] {len(discrepancies)} discrepancies found:', file=sys.stderr)
            for d in discrepancies:
                print(f'  - {d.adr_id}: {d.verification_status}', file=sys.stderr)
            sys.exit(2)

# Get related archived changes from openspec/changes/archive/
archive_dir = project_root / 'openspec/changes/archive'
related_archived = []
if archive_dir.exists():
    for d in sorted(archive_dir.iterdir()):
        if d.is_dir():
            related_archived.append(d.name)

# Generate body for each phase
phase_bodies = {}
phases_in_order = [f'phase-{i}' for i in range(1, 5)]
for idx, phase_id in enumerate(phases_in_order):
    next_phase_id = phases_in_order[idx + 1] if idx + 1 < len(phases_in_order) else None
    phase_changes = [c for c in related_archived if phase_id in c.lower() or any(kw in c.lower() for kw in ['session', 'design', 'plan', 'hub', 'roadmap'])]
    body = generate_phase_body(
        phase_id=phase_id,
        classified_adrs=classified,
        arch_docs=arch_docs,
        main_doc_phases=main_doc_phases,
        project_root=project_root,
        related_archived_changes=phase_changes[:5],
        next_phase_id=next_phase_id,
        verifications=verifications if verifications else None,
    )
    phase_bodies[phase_id] = body

print(json.dumps(phase_bodies, ensure_ascii=False))
" 2>&1) || {
        rc=$?
        if [ $rc -eq 2 ]; then
            echo "❌ --code-verify=strict 发现 discrepancy,exit 2" >&2
            return 2
        fi
        echo "❌ Python 步骤失败" >&2
        echo "$PYTHON_OUT" >&2
        return 1
    }

    # Step 4: backup
    local BACKUP_DIR=""
    if [ "$NO_BACKUP" = "false" ] && [ "$DRY_RUN" = "false" ]; then
        BACKUP_DIR=$(backup_fragments "$PROJECT_ROOT") || { echo "❌ backup 失败" >&2; return 1; }
        echo "▶ Backup: $BACKUP_DIR"
    fi

    # Step 5: write
    if [ "$DRY_RUN" = "true" ]; then
        echo ""
        echo "▶ --dry-run: 跳过写入。生成内容预览（前 30 行每个 phase）:"
        for phase in phase-1 phase-2 phase-3 phase-4; do
            if [ "$TARGET_PHASE" != "all" ] && [ "$TARGET_PHASE" != "$phase" ]; then
                continue
            fi
            echo ""
            echo "===== $phase ====="
            echo "$PYTHON_OUT" | python3 -c "
import sys, json
data = json.loads(sys.stdin.read())
body = data.get('$phase', '')
for line in body.split('\n')[:30]:
    print(line)
" 2>/dev/null
        done
        return 0
    fi

    # Diff prompt
    if [ "$SKIP_PROMPT" = "false" ]; then
        echo ""
        echo "▶ Diff preview:"
        for phase in phase-1 phase-2 phase-3 phase-4; do
            if [ "$TARGET_PHASE" != "all" ] && [ "$TARGET_PHASE" != "$phase" ]; then
                continue
            fi
            local F="$PROJECT_ROOT/.rddf/roadmap/phases/$phase.md"
            local OLD_LINES
            OLD_LINES=$(wc -l < "$F")
            local NEW_BODY
            NEW_BODY=$(echo "$PYTHON_OUT" | python3 -c "
import sys, json
data = json.loads(sys.stdin.read())
print(data.get('$phase', ''))
" 2>/dev/null)
            local NEW_LINES
            NEW_LINES=$(echo "$NEW_BODY" | wc -l)
            printf "  %s: %s → %s lines\n" "$phase" "$OLD_LINES" "$NEW_LINES"
        done

        echo ""
        read -p "Continue? [Y/n/d/b/q] " -r REPLY
        case "$REPLY" in
            [Yy]|"") ;;
            [Dd]) echo "详细 diff 略（--yes 跳过 diff prompt 重跑）"; return 0 ;;
            [Bb]) echo "Backup: $BACKUP_DIR"; return 0 ;;
            [Qq]) echo "退出（保留 backup）"; return 0 ;;
            *) echo "取消"; return 1 ;;
        esac
    fi

    echo ""
    echo "▶ Writing fragments (atomic tmp + rename)..."
    for phase in phase-1 phase-2 phase-3 phase-4; do
        if [ "$TARGET_PHASE" != "all" ] && [ "$TARGET_PHASE" != "$phase" ]; then
            continue
        fi
        local F="$PROJECT_ROOT/.rddf/roadmap/phases/$phase.md"
        local NEW_BODY
        NEW_BODY=$(echo "$PYTHON_OUT" | python3 -c "
import sys, json
data = json.loads(sys.stdin.read())
print(data.get('$phase', ''), end='')
" 2>/dev/null)
        write_fragment "$F" "$NEW_BODY"
        echo "  ✅ $phase"
    done

    # Step 6
    if ! validate "$PROJECT_ROOT"; then
        echo "❌ 验证失败 — 恢复 backup"
        if [ -n "$BACKUP_DIR" ]; then
            cp -p "$BACKUP_DIR/phases/"*.md "$PROJECT_ROOT/.rddf/roadmap/phases/"
            echo "✅ 已恢复 backup"
        fi
        return 1
    fi

    # Step 7
    report "$PROJECT_ROOT" "$BACKUP_DIR"
}

# Sourceable guard (defined last so all functions are available when sourced or executed directly)
if [ "${BASH_SOURCE[0]:-}" = "${0}" ]; then
    populate_main "$@"
    exit $?
fi
