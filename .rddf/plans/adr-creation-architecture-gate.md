# adr-creation-architecture-gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task.

**Goal:** ADR 创建前增加架构影响力判定，防止非架构决策成为 ADR

**Architecture:** 在 guide-arch Phase 2 选项 1 前插入 Oracle 判定步骤

**Tech Stack:** Bash, Python, Oracle API

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/guide-arch/scripts/adr_gate.sh` | Oracle 判定脚本 |
| `skills/guide-arch/SKILL.md` | 集成判定步骤 |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_adr_gate.bats` | 测试判定分类 |

---

### Task 1: 创建 adr_gate.sh 脚本

**Files:**
- Create: `skills/guide-arch/scripts/adr_gate.sh`
- Test: `tests/integration/test_adr_gate.bats`

- [ ] **Step 1: Write the failing test**

```bash
@test "adr_gate: classifies ARCHITECTURE decision" {
  run bash skills/guide-arch/scripts/adr_gate.sh "Define module boundary"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "ARCHITECTURE" ]]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_adr_gate.bats`
Expected: FAIL - script not found

- [ ] **Step 3: Write minimal implementation**

```bash
#!/bin/bash
# adr_gate.sh - ADR 架构影响力判定

TOPIC="$1"
SKIP_ADR_GATE="${SKIP_ADR_GATE:-no}"

[ "$SKIP_ADR_GATE" = "yes" ] && { echo "ARCHITECTURE"; exit 0; }

# Call Oracle for classification (simplified)
if command -v python3 &>/dev/null; then
  python3 -c "
topic = '''$TOPIC'''
# Simple heuristic: check for architecture keywords
arch_keywords = ['module', 'boundary', 'interface', 'contract', 'layer', 'abstraction']
gov_keywords = ['version', 'release', 'ci', 'cd', 'test framework', 'process']

topic_lower = topic.lower()
if any(k in topic_lower for k in arch_keywords):
    print('ARCHITECTURE')
elif any(k in topic_lower for k in gov_keywords):
    print('GOVERNANCE')
else:
    print('IMPLEMENTATION')
"
else
  echo "ARCHITECTURE"  # fallback
fi
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_adr_gate.bats`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/guide-arch/scripts/adr_gate.sh tests/integration/test_adr_gate.bats
git commit -m "feat: add ADR architecture gate script"
```
