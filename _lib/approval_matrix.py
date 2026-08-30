"""Multi-stakeholder approval gate (per phase-4-general-20260829063814).

Per ADR-0031: 1 owner + 1+ hub_approver + 0+ hub_observer all required.
"""
REQUIRED_ROLES = ("owner", "hub_approver", "hub_observer")
_APPROVED = "approved"


def evaluate_approval(entries):
    """Return (approved, missing_roles).

    approved is True iff every role in REQUIRED_ROLES has >= 1 approved entry.
    missing_roles lists the roles that have no approved entry.
    """
    approved_roles = {e["role"] for e in entries if e.get("status") == _APPROVED}
    missing = [r for r in REQUIRED_ROLES if r not in approved_roles]
    return (not missing, missing)