"""commit-gate 声明的**生成规则**与**非平凡判据**（单一真源）。

`ADR-commit-verification-gate` 的 D3 明文决策：仓库未声明 `<workRoot>/.rddf/commit-gate.json`
⇒ 三判据**不设门禁**（不是 bug）⇒ 使用方仓「想启用门禁也没有入口」。

本模块回答两个问题，**生成器 / doctor / `--help` 文案共用**（禁第二份实现）：

1. **能从仓内既有入口推导出什么 `verify_commands`**（`derive_verify_commands`）——**不猜**：
   只认固定候选表里的**已存在**文件（+ 必要的内容条件，如 `package.json` 的 `scripts.test`）；
2. **什么算「空壳声明」**（`is_shell_declaration`）——**枚举**，不是「之类」。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

#: 声明文件（与 `ADR-commit-verification-gate` D3 的路径逐字一致）。
DECLARATION_REL = ".rddf/commit-gate.json"

#: **空壳命令枚举**（恰好 1 条且归一后 ∈ 此集合 ⇒ 空壳）。
#: ⚠ 生成器、doctor、`--help` 文案**同源** import 这一份（AC6：禁「之类」的模糊表述）。
SHELL_COMMANDS: tuple[str, ...] = ("true", "echo", ":", "exit 0")

#: 推导候选表（**顺序即优先级**；只取第一个命中者 —— 声明越短越不易腐坏）。
#:
#: ⚠ **脚本类入口故意缺席**（`test.sh` / `package.json::scripts.test` / `Makefile::test:`）：
#: 裸调用是否真的执行验证**不可静态判定**（实测：本仓裸 `./test.sh` rc=0 / 40 行 help / 0 用例；
#: `"test": "echo ok"`、`test:\n\t@echo no tests` 同理）⇒ 只能来自**显式来源**
#: （既有合法声明），否则生成器拒绝（rc=3）。
#:
#: 工具链类保留推导，但要求仓内**确有测试件**（零测试件时 go/cargo 的 rc=0、pytest 的 rc=5
#: 都等于「验证没有意义」）。
CANDIDATES: tuple[dict, ...] = (
    {"requires": "pyproject.toml", "argv": ["python3", "-m", "pytest"], "tool": "pytest"},
    {"requires": "pytest.ini", "argv": ["python3", "-m", "pytest"], "tool": "pytest"},
    {"requires": "setup.cfg", "argv": ["python3", "-m", "pytest"], "tool": "pytest"},
    {"requires": "go.mod", "argv": ["go", "test", "./..."], "tool": "go"},
    {"requires": "Cargo.toml", "argv": ["cargo", "test"], "tool": "cargo"},
)

#: **脚本类入口**的探测证据（用于把「仓里有脚本入口」与「什么都没有」区分开：
#: 前者 ⇒ 需要显式 argv（生成器 rc=3），后者 ⇒ 找不到入口（rc=1））。
SCRIPT_ENTRY_EVIDENCE: tuple[dict, ...] = (
    {"requires": "test.sh", "hint": "./test.sh"},
    {"requires": "package.json", "requires_test_script": True, "hint": "npm test"},
    {"requires": "Makefile", "requires_make_test_target": True, "hint": "make test"},
)

#: 各工具链的**测试件形态**（枚举，禁「之类」）。cargo 额外要求文件内含 `#[test]`。
TEST_FILE_GLOBS: dict[str, tuple[str, ...]] = {
    "pytest": ("**/test_*.py", "**/*_test.py"),
    "go": ("**/*_test.go",),
    "cargo": ("tests/**/*.rs", "src/**/*.rs"),
}


def _normalize(argv: list[str]) -> str:
    """归一：拼接 + 空白折叠（`["exit", "0"]` 与 `": "` 之类都可比）。"""
    return " ".join(" ".join(argv).split())


def is_shell_declaration(verify_commands: list[list[str]] | None) -> bool:
    """是否为**空壳声明**（恰好 1 条命令，且该命令 ∈ `SHELL_COMMANDS`）。"""
    if not verify_commands or not isinstance(verify_commands, list):
        return False
    if len(verify_commands) != 1:
        return False
    first = verify_commands[0]
    if not isinstance(first, list) or not first:
        return False
    return _normalize(first) in SHELL_COMMANDS


def _package_has_test_script(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return False
    scripts = data.get("scripts") if isinstance(data, dict) else None
    return isinstance(scripts, dict) and isinstance(scripts.get("test"), str) and bool(scripts["test"].strip())


def _makefile_has_test_target(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return re.search(r"^test\s*:", text, re.MULTILINE) is not None


def detect_unresolved_entries(project_root: str | Path) -> list[str]:
    """仓内**存在、但无法自动推导**的入口（可读提示）；空列表 ⇒ 什么入口都没探到。

    两类都算「需要显式 argv」：
    - 脚本类入口（`test.sh` / `npm test` / `make test`）—— 裸调用是否执行验证不可判定；
    - 工具链类入口（pytest / go / cargo）—— 证据文件在，但仓内**没有测试件**（零测试时 rc=0/5）。
    """
    root = Path(project_root)
    found: list[str] = []
    for entry in SCRIPT_ENTRY_EVIDENCE:
        evidence = root / entry["requires"]
        if not evidence.is_file():
            continue
        if entry.get("requires_test_script") and not _package_has_test_script(evidence):
            continue
        if entry.get("requires_make_test_target") and not _makefile_has_test_target(evidence):
            continue
        found.append(entry["hint"])
    for candidate in CANDIDATES:
        if not (root / candidate["requires"]).is_file():
            continue
        tool = candidate.get("tool")
        if tool and not _has_test_files(root, tool):
            found.append(f"{' '.join(candidate['argv'])}（未找到 {tool} 测试件）")
    return found


def _has_test_files(root: Path, tool: str) -> bool:
    """仓内是否存在该工具链的测试件（静态判定；读不了 ⇒ 视为不存在，不抛栈）。"""
    for pattern in TEST_FILE_GLOBS.get(tool, ()):
        for path in root.glob(pattern):
            if tool != "cargo":
                return True
            try:
                if "#[test]" in path.read_text(encoding="utf-8"):
                    return True
            except (OSError, UnicodeDecodeError):
                continue
    return False


def derive_verify_commands(project_root: str | Path) -> list[list[str]] | None:
    """从仓内**既有**入口推导 `verify_commands`；一个都不命中 ⇒ `None`（**不猜**）。"""
    root = Path(project_root)
    for candidate in CANDIDATES:
        evidence = root / candidate["requires"]
        if not evidence.is_file():
            continue
        tool = candidate.get("tool")
        if tool and not _has_test_files(root, tool):
            continue
        return [list(candidate["argv"])]
    return None


def declaration_path(project_root: str | Path) -> Path:
    return Path(project_root) / DECLARATION_REL


def read_declaration(project_root: str | Path) -> dict | None:
    """读声明；不存在 / 解析失败 ⇒ `None`。"""
    path = declaration_path(project_root)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None


def render_declaration(verify_commands: list[list[str]]) -> str:
    """声明文件的**字节确定**形态（无时间戳 ⇒ 便于断言与 diff）。"""
    return json.dumps({"verify_commands": verify_commands}, ensure_ascii=False, indent=2) + "\n"


def manual_template() -> str:
    """找不到入口时给作者的最小手工模板（含 D3 的 git-tracked 提醒）。"""
    return (
        "手工模板（`.rddf/commit-gate.json`）：\n"
        '{\n  "verify_commands": [\n    ["./your-verify-script.sh"]\n  ]\n}\n'
        "⚠ 声明必须 **git-tracked**（否则 worktree 内无门禁，ADR-commit-verification-gate D3）。\n"
    )


def shell_commands_display() -> str:
    """`--help` / doctor 文案用的枚举展示（**从常量渲染** ⇒ 改常量即改文案）。"""
    return " / ".join(SHELL_COMMANDS)


__all__ = [
    "CANDIDATES",
    "TEST_FILE_GLOBS",
    "SCRIPT_ENTRY_EVIDENCE",
    "detect_unresolved_entries",
    "DECLARATION_REL",
    "SHELL_COMMANDS",
    "declaration_path",
    "derive_verify_commands",
    "is_shell_declaration",
    "manual_template",
    "read_declaration",
    "render_declaration",
    "shell_commands_display",
]
