#!/bin/bash
# adr_gate.sh - ADR 架构影响力判定
#
# Classifies a topic as ARCHITECTURE, GOVERNANCE, or IMPLEMENTATION
# using keyword heuristics. Honors SKIP_ADR_GATE=yes to bypass.
#
# CHANGED 2026-10-28: keyword classification demoted from hard gate to advisory.
#   Rationale: the heuristic matches only a few words in the *title*, so genuine
#   architecture decisions are misclassified as IMPLEMENTATION. Measured on the
#   2026-10-27 ADR batch: 8/8 real architecture ADRs (skid buffer, data
#   forwarding, canonical home, backend retirement, parity gate, open-core port,
#   coherence-domain ownership, platform charter) were classified IMPLEMENTATION.
#   A hard gate on that signal blocks exactly the decisions worth recording.
#
#   Env:
#     SKIP_ADR_GATE=yes        bypass classification entirely (prints ARCHITECTURE)
#     ADR_GATE_MODE=advisory  default — print classification + advisory note to stderr
#     ADR_GATE_MODE=block     suppress the advisory (caller may hard-block)
#     ADR_GATE_CLASS=<CLASS>  explicit override (ARCHITECTURE|GOVERNANCE|IMPLEMENTATION)
#
# stdout : the class token (ARCHITECTURE | GOVERNANCE | IMPLEMENTATION)
# stderr : advisory note (advisory mode only)

TOPIC="${1:-}"
SKIP_ADR_GATE="${SKIP_ADR_GATE:-no}"
ADR_GATE_MODE="${ADR_GATE_MODE:-advisory}"
ADR_GATE_CLASS="${ADR_GATE_CLASS:-}"

if [ "$SKIP_ADR_GATE" = "yes" ]; then
  echo "ARCHITECTURE"
  exit 0
fi

# Explicit override wins over the heuristic.
if [ -n "$ADR_GATE_CLASS" ]; then
  echo "$ADR_GATE_CLASS"
  exit 0
fi

if [ -z "$TOPIC" ]; then
  echo "USAGE: adr_gate.sh <topic>"
  exit 1
fi

CLASS=$(ADR_TOPIC="$TOPIC" python3 -c '
import os
topic = os.environ.get("ADR_TOPIC", "")
arch_keywords = ["module", "boundary", "interface", "contract", "layer", "abstraction"]
gov_keywords = ["version", "release", "ci", "cd", "test framework", "process"]
topic_lower = topic.lower()
if any(k in topic_lower for k in arch_keywords):
    print("ARCHITECTURE")
elif any(k in topic_lower for k in gov_keywords):
    print("GOVERNANCE")
else:
    print("IMPLEMENTATION")
')

echo "$CLASS"

# Advisory note (stderr) — the caller decides, not the heuristic.
if [ "$ADR_GATE_MODE" = "advisory" ]; then
  case "$CLASS" in
    IMPLEMENTATION)
      echo "⚠️  [advisory] 关键词判定为实现类，但这只匹配标题里的少数词。" >&2
      echo "   微架构 / 契约 / 所有权类议题常被误判（实测 8/8 近期真实架构 ADR 被判 IMPLEMENTATION）。" >&2
      echo "   若你确认它是架构决策，仍可创建 ADR；否则改用替代路径。" >&2
      ;;
    GOVERNANCE)
      echo "⚠️  [advisory] 关键词判定为治理/流程类；若它其实承载了架构取舍，仍可按 ADR 记录。" >&2
      ;;
  esac
fi
