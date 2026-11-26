"""openspec CLI 版本探测（纯 stdlib · **语义化**比较）。

为什么需要（2026-11-27）：openspec 的「MODIFIED 块必须含既有 Scenario」检查
**1.7.0 才引入**（1.4.1 的 `specs-apply.js` 全文无此检查）⇒ 生成侧必须知道项目实际用的
openspec 版本，才能决定「复用原生检查」还是「自实现等价检查」。

⚠ **必须语义化比较**：`1.14.3 > 1.7.0` 成立，但**字符串比较会判反**（"1.14.3" < "1.7.0"）
⇒ 任何字符串比较都是 bug（AC13 的变异腿专门盯这一条）。
"""
from __future__ import annotations

import os
import re
import subprocess

#: 版本号抽取（`1.14.3` / `v1.7.0` / `1.7` 皆可）。
_VERSION_RE = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")


def parse_version(text: str) -> tuple[int, int, int]:
    """从任意文本里抽出版本三元组；抽不到 ⇒ ValueError（**不猜**）。

    >>> parse_version("openspec 1.14.3")
    (1, 14, 3)
    """
    m = _VERSION_RE.search(text or "")
    if not m:
        raise ValueError(f"无法解析 openspec 版本：{text!r}")
    major, minor, patch = m.group(1), m.group(2), m.group(3)
    return (int(major), int(minor), int(patch) if patch else 0)


def current_version(cli: str = "openspec") -> tuple[int, int, int] | None:
    """取本机 openspec CLI 版本；**探测失败 ⇒ None（不崩、不猜）**。

    ⚠ `RDDF_OPENSPEC_VERSION` 环境变量优先（测试与离线环境用 ⇒ **确定性**，不 spawn 子进程）。
    ⚠ CLI 缺失 / 输出不可解析 ⇒ None：调用方按「**无原生检查**」保守处理
    （本仓的本地预检永远执行 ⇒ 不会因为探测失败而失去守卫）。
    """
    override = os.environ.get("RDDF_OPENSPEC_VERSION")
    if override:
        try:
            return parse_version(override)
        except ValueError:
            return None
    try:
        proc = subprocess.run(
            [cli, "--version"], capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    try:
        return parse_version((proc.stdout or "") + (proc.stderr or ""))
    except ValueError:
        return None


def at_least(
    minimum: tuple[int, int, int], actual: tuple[int, int, int] | None = None
) -> bool:
    """**语义化**比较：`actual >= minimum`。

    >>> at_least((1, 7, 0), (1, 14, 3))
    True
    >>> at_least((1, 7, 0), (1, 4, 1))
    False

    ⚠ **探测不到版本 ⇒ False**（保守：按「无原生检查」处理 ⇒ 本地预检照常执行）。
    """
    if actual is None:
        actual = current_version()
    if actual is None:
        return False
    return actual >= minimum


def native_scenario_conservation_available(
    actual: tuple[int, int, int] | None = None,
) -> bool:
    """openspec 是否自带「MODIFIED 必须含既有 Scenario」检查（**1.7.0 起**）。"""
    return at_least((1, 7, 0), actual)
