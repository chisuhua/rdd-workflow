#!/usr/bin/env bash
# DEPRECATED (v2.1, removal in v2.2.0): moved to skills/guide-design/scripts/approve_proposal.sh
echo "⚠️ DEPRECATED: guide-arch Phase 5.5 已迁移到 guide-design (v2.1);请使用 skill_use(\"guide-design\")" >&2
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../../guide-design/scripts/approve_proposal.sh" "$@"