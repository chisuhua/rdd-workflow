"""Multi-stakeholder approval gate (per phase-4-general-20260829063814)."""
from _lib.approval_matrix import evaluate_approval, REQUIRED_ROLES


def test_all_three_roles_present_approved():
    entries = [
        {"role": "owner", "approver": "alice", "status": "approved"},
        {"role": "hub_approver", "approver": "bob", "status": "approved"},
        {"role": "hub_observer", "approver": "carol", "status": "approved"},
    ]
    approved, missing = evaluate_approval(entries)
    assert approved is True
    assert missing == []


def test_owner_missing_blocks_archive():
    entries = [
        {"role": "hub_approver", "approver": "bob", "status": "approved"},
        {"role": "hub_observer", "approver": "carol", "status": "approved"},
    ]
    approved, missing = evaluate_approval(entries)
    assert approved is False
    assert "owner" in missing


def test_one_hub_pending_blocks_archive():
    entries = [
        {"role": "owner", "approver": "alice", "status": "approved"},
        {"role": "hub_approver", "approver": "bob", "status": "pending"},
        {"role": "hub_observer", "approver": "carol", "status": "approved"},
    ]
    approved, missing = evaluate_approval(entries)
    assert approved is False


def test_required_roles_constant():
    assert REQUIRED_ROLES == ("owner", "hub_approver", "hub_observer")