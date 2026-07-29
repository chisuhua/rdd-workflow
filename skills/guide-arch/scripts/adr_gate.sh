#!/bin/bash
# adr_gate.sh - ADR 架构影响力判定
# Classifies a topic as ARCHITECTURE, GOVERNANCE, or IMPLEMENTATION
# using keyword heuristics. Honors SKIP_ADR_GATE=yes to bypass.

TOPIC="${1:-}"
SKIP_ADR_GATE="${SKIP_ADR_GATE:-no}"

if [ "$SKIP_ADR_GATE" = "yes" ]; then
  echo "ARCHITECTURE"
  exit 0
fi

if [ -z "$TOPIC" ]; then
  echo "USAGE: adr_gate.sh <topic>"
  exit 1
fi

ADR_TOPIC="$TOPIC" python3 -c '
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
'
