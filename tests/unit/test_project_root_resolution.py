"""canonical resolver 的契约（per _resolve_project_root_contract.yaml）。"""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_resolver_prefers_env_override():
    from skills._lib._python_resolve_project_root import resolve_project_root

    os.environ["RDDF_PROJECT_ROOT"] = str(REPO_ROOT)
    try:
        assert resolve_project_root() == str(REPO_ROOT)
    finally:
        os.environ.pop("RDDF_PROJECT_ROOT", None)


def test_shim_identity_merge():
    import skills._lib._python_resolve_project_root as shim
    import _lib._python_resolve_project_root as real

    assert shim is real


def test_anchor_is_independent_of_cwd(tmp_path, monkeypatch):
    """锚点必须压过 CWD：否则从任意目录调用会把状态写进调用目录。"""
    from skills._lib._python_resolve_project_root import resolve_project_root

    monkeypatch.delenv("RDDF_PROJECT_ROOT", raising=False)

    # 基准：cwd = 仓库根时的 canonical 结果。linked worktree 下 resolver 按
    # ADR-0033 返回**主仓根**而非 worktree 目录，故此处不写死 REPO_ROOT。
    monkeypatch.chdir(REPO_ROOT)
    expected = resolve_project_root()

    monkeypatch.chdir(tmp_path)          # 非 git 目录
    assert resolve_project_root() == str(tmp_path)
    assert resolve_project_root(start_dir=str(REPO_ROOT)) == expected
