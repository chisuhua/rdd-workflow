from skills._lib.iteration.render import print_view


def test_render_archived_change_with_l2_count(capsys, tmp_path):
    """Archived change with recorded L2 count should display it."""
    iter_data = {
        "version": 5,
        "updated_at": "2026-08-06T00:00:00+00:00",
        "current_phase": "ship",
        "changes": [
            {
                "name": "remove-sim-include",
                "status": "archived",
                "added_at": "2026-08-06T00:00:00+00:00",
                "archived_at": "2026-08-06T00:00:00+00:00",
                "l2_violation_count_after": 3,
                "l2_violation_kind": "sim_include_drv",
            }
        ],
    }
    from skills._lib.iteration.store import save

    save(str(tmp_path), iter_data)
    print_view(str(tmp_path))
    out = capsys.readouterr().out
    assert "L2: 3" in out
    assert "sim_include_drv" in out


def test_render_archived_change_without_l2_count(capsys, tmp_path):
    """Archived change without L2 count should display 'L2: not recorded'."""
    iter_data = {
        "version": 5,
        "updated_at": "2026-08-06T00:00:00+00:00",
        "current_phase": "ship",
        "changes": [
            {
                "name": "old-change",
                "status": "archived",
                "added_at": "2026-08-06T00:00:00+00:00",
                "archived_at": "2026-08-06T00:00:00+00:00",
                "l2_violation_count_after": None,
                "l2_violation_kind": None,
            }
        ],
    }
    from skills._lib.iteration.store import save

    save(str(tmp_path), iter_data)
    print_view(str(tmp_path))
    out = capsys.readouterr().out
    assert "L2: not recorded" in out
