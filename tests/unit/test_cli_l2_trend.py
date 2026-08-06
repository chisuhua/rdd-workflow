from skills._lib.cli import list_commands, route


def test_l2_trend_registered():
    assert "l2-trend" in list_commands()


def test_l2_trend_no_iteration_json(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    code = route("l2-trend", [])
    out = capsys.readouterr().out
    assert code == 0
    assert "no l2 trend data" in out.lower() or "iteration.json not found" in out.lower()


def test_l2_trend_prints_sorted_table(tmp_path, monkeypatch, capsys):
    from skills._lib.iteration.store import save

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    iter_data = {
        "version": 5,
        "updated_at": "2026-08-06T00:00:00+00:00",
        "current_phase": "ship",
        "changes": [
            {
                "name": "c2",
                "status": "archived",
                "added_at": "2026-08-06T00:00:00+00:00",
                "archived_at": "2026-08-06T02:00:00+00:00",
                "l2_violation_count_after": 5,
            },
            {
                "name": "c1",
                "status": "archived",
                "added_at": "2026-08-06T00:00:00+00:00",
                "archived_at": "2026-08-06T01:00:00+00:00",
                "l2_violation_count_after": 8,
            },
        ],
    }
    save(str(tmp_path), iter_data)
    code = route("l2-trend", [])
    out = capsys.readouterr().out
    assert code == 0
    assert "c1" in out and "c2" in out
    assert out.index("c1") < out.index("c2")
