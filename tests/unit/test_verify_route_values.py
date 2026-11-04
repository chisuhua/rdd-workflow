"""失败路由必须指向 v4 真实阶段（guide-* 已随 Wave 3 删除）。"""
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ROUTE_LOOP = REPO_ROOT / "skills/rdd-verifier/scripts/route_loop.sh"

V4_ROUTES = {"archive-ready", "rdd-builder", "halted", "pending-agent"}


def _run_route_loop(tmp_path, label):
    return subprocess.run(
        ["bash", str(ROUTE_LOOP), "demo-change", label],
        capture_output=True, text=True, cwd=str(tmp_path), check=False,
        # route_loop.sh:19 用 `git rev-parse --show-toplevel || pwd` 解析根 ——
        # 必须显式注入，否则 tmp_path 落在别的 git 仓库里时会写错地方
        env={**os.environ, "PROJECT_ROOT": str(tmp_path)},
    )


def test_route_loop_writes_v4_routes_for_gap(tmp_path):
    out = _run_route_loop(tmp_path, "implementation_gap")
    assert out.returncode == 0, out.stderr
    assert "guide-" not in out.stdout
    assert "rdd-builder" in out.stdout


def test_route_loop_writes_v4_routes_for_drift(tmp_path):
    """drift 也回 rdd-builder（P1 语义写在打印行里，不新增 state 取值）。"""
    out = _run_route_loop(tmp_path, "proposal_drift")
    assert out.returncode == 0, out.stderr
    assert "guide-" not in out.stdout
    assert "rdd-builder" in out.stdout
    assert "P1" in out.stdout


def test_classify_route_returns_v4_names():
    """两种分类都回 rdd-builder（P1/P2 差异由 classification + 打印行承载）。

    与 skills/rdd-verifier/SKILL.md:126,128 的状态机一致：
    implementation_gap → rdd-builder P2；proposal_drift → rdd-builder P1。
    """
    from skills._lib.cli.rdd_verify_cmd import _classify_route

    gap = [{"ac_id": "AC-1", "status": "fail", "reasoning": "code missing"}]
    drift = [{"ac_id": "AC-1", "status": "fail",
              "reasoning": "proposal says X but code does Y"}]
    assert _classify_route(["AC-1"], gap) == "rdd-builder"
    assert _classify_route(["AC-1"], drift) == "rdd-builder"


def test_schema_enums_keep_legacy_and_add_v4():
    """存量 state 仍带旧 route → enum 只能增，不能减。"""
    for rel in ("_lib/schemas/iteration_schema.json",
                "_lib/schemas/verifier_loop_schema.json"):
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "rdd-builder" in text, rel
        assert "guide-ship" in text, f"{rel} 不得删除历史值（存量 state 仍需可加载）"
