"""Mock LLM responses for AC verifier tests.

Activated when AC_LLM_MOCK=yes. Provides 5 canned scenarios:
- mock_pass_all
- mock_fail_one
- mock_partial
- mock_invalid_json
- mock_omitted_ac
"""
from __future__ import annotations

import json
import os


def mock_invoke(system: str, user: str) -> str:
    """Return canned response for current mock scenario."""
    scenario = os.environ.get("AC_LLM_MOCK_SCENARIO", "mock_pass_all")

    if scenario == "mock_pass_all":
        import re
        ac_ids = re.findall(r"(AC-\d+):", user)
        verdicts = [
            {"ac_id": ac, "description": f"AC {ac}", "status": "pass",
             "confidence": 0.95, "evidence": [], "reasoning": "mock pass"}
            for ac in ac_ids
        ]
        return json.dumps(verdicts)

    if scenario == "mock_fail_one":
        import re
        ac_ids = re.findall(r"(AC-\d+):", user)
        verdicts = []
        for i, ac in enumerate(ac_ids):
            status = "fail" if i == 1 else "pass"
            verdicts.append({
                "ac_id": ac, "description": f"AC {ac}", "status": status,
                "confidence": 0.85, "evidence": [], "reasoning": f"mock {status}"
            })
        return json.dumps(verdicts)

    if scenario == "mock_partial":
        import re
        ac_ids = re.findall(r"(AC-\d+):", user)
        verdicts = [
            {"ac_id": ac, "description": f"AC {ac}", "status": "partial",
             "confidence": 0.6, "evidence": [], "reasoning": "mock partial"}
            for ac in ac_ids
        ]
        return json.dumps(verdicts)

    if scenario == "mock_invalid_json":
        return "This is not valid JSON. Sorry."

    if scenario == "mock_omitted_ac":
        import re
        ac_ids = re.findall(r"(AC-\d+):", user)
        # Omit the last AC
        verdicts = [
            {"ac_id": ac, "description": f"AC {ac}", "status": "pass",
             "confidence": 0.9, "evidence": [], "reasoning": "mock"}
            for ac in ac_ids[:-1]
        ]
        return json.dumps(verdicts)

    raise ValueError(f"Unknown mock scenario: {scenario}")