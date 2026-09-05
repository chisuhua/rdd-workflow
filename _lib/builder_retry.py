"""Verifier verdict → Phase routing + retry counter (per spec §3.4, Oracle C1).

Preserves ADR-0034 §7 5-value exit semantics (0/1/2/3/4).
"""


def route_verifier_verdict(verifier_exit_code: int, verifier_kind=None) -> dict:
    if verifier_exit_code == 0:
        return {"next_phase": "phase-3-archive", "should_back_route": False, "halted": False,
                "verifier_kind": verifier_kind or "pass"}
    if verifier_exit_code == 1:
        return {"next_phase": "phase-2", "should_back_route": True, "halted": False,
                "verifier_kind": verifier_kind or "implementation_gap"}
    if verifier_exit_code == 2:
        return {"next_phase": "phase-1", "should_back_route": True, "halted": False,
                "verifier_kind": verifier_kind or "ac_fail"}
    if verifier_exit_code in (3, 4):
        kind = verifier_kind or ("needs_human" if verifier_exit_code == 3 else "halted_max_loops")
        return {"next_phase": "halt", "should_back_route": False, "halted": True, "verifier_kind": kind}
    return {"next_phase": "halt", "should_back_route": False, "halted": True,
            "verifier_kind": verifier_kind or f"unknown_exit_{verifier_exit_code}"}


def should_halt_for_retry_exceeded(retry_count: int, max_retries: int) -> bool:
    return retry_count >= max_retries


def should_increment_retry(should_back_route: bool) -> bool:
    return should_back_route