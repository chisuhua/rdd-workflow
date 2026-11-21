"""Cat — `v4-residue`: 契约面上残留的 v3 skill 名（`guide-*`）。

v3 → v4 重命名（ADR-0043 / ADR-0044）覆盖了主路径，但契约面容易滞留旧名：
路由 enum、面向用户的字符串、SKILL.md 的 `name:`。本检查只扫**契约面**，
不扫注释与历史文档 —— 那些是考古信息，全仓 grep 会把真问题淹掉。

规则（per fix-v4-residue-contract design.md Decision 4）：

- **R1** 路由型 enum 必须能表达 v4 路由（含 `rdd-builder`）。缺 → CRITICAL。
  注意语义：问的是「**还能不能表达 v4 路由**」，不是「有没有旧值」。
  旧值（`guide-ship` / `guide-plan`）是**历史兼容输入**，删了会让存量
  `.rddf/state/verifier/*.json` 加载失败（`loop_state.py` save 时强制校验 enum）。
- **R2** 活代码的**字符串字面量**里出现 `skill_use("guide-*")` / `--phase guide-*`
  / `for guide-*` → WARNING。用 `ast` 只取字面量，**注释与 docstring 豁免**。
- **R3** `skills/*/SKILL.md` frontmatter 的 `name:` 为 `guide-*` → CRITICAL
  （该 skill 不存在）。
- **R4** `openspec/specs/*/spec.md` 的 **normative 段**里出现已退役 stage 名
  → WARNING（判据与口径见 `spec_residue_scan` 模块的 docstring）。**开关控制**：
  `.rddf/project.yaml` 的 `doctor.v4_residue.scan_specs`（默认 `false`）——
  scan 面首版只报 WARNING，且 `v4-residue` 属 advisory gate ⇒ 不拖红 CI。
  `files_scanned == 0` 时**不得**报「无残留」，改报 INFO「checked 0」——
  干净 clone 上 `openspec/` 不存在，静默通过就是假通过。
"""
from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path
from typing import List

from doctor_render import Finding, Severity

from spec_residue_scan import scan_specs


CATEGORY = "v4-residue"

# R1: 路由型 enum 的落点 + 「能表达 v4 路由」的判据。
_ROUTE_ENUMS = (
    ("_lib/schemas/verifier_loop_schema.json", "route"),
    ("_lib/schemas/iteration_schema.json", "route"),
)
_REQUIRED_V4_ROUTES = frozenset({"rdd-builder"})

# 显式豁免清单（不得靠「扫不到」蒙混）：这些字段的历史值属合法兼容输入。
_ALLOWLIST = {
    "feedback_entry_schema.json": ("source",),      # 历史 feedback 回放需要
    "sessions_schema.json": ("phase",),             # 历史 session 的合法 phase
}

# R2: 只扫活代码。
_SCAN_ROOTS = ("_lib", "skills")
_SCAN_SUFFIXES = (".py", ".sh")
_SKIP_DIR_PARTS = frozenset({"__pycache__", "node_modules", ".git"})
_R2_PATTERN = re.compile(
    r'skill_use\(\s*["\']guide-'      # skill_use("guide-…")
    r'|--phase\s+guide-'             # --phase guide-…
    r'|\bfor guide-'                  # for guide-…
    r'|\brun guide-'                  # "run guide-plan first"
    r'|\bor guide-'                   # "Run rdd-arch or guide-plan to start."
)

# R3
_SKILL_DIR = "skills"
_FRONTMATTER_NAME = re.compile(r"^name:\s*(.+?)\s*$", re.MULTILINE)


def _iter_source_files(root: Path):
    for top in _SCAN_ROOTS:
        base = root / top
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in _SCAN_SUFFIXES:
                continue
            if _SKIP_DIR_PARTS & set(path.parts):
                continue
            yield path


def _docstring_node_ids(tree: ast.AST) -> set[int]:
    """id() of Constant nodes that are docstrings (to exempt them from R2)."""
    ids: set[int] = set()
    holders = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    for node in ast.walk(tree):
        if not isinstance(node, holders):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if (isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)):
            ids.add(id(first.value))
    return ids


def _find_property_enums(node, field: str, path=()):
    """Yield ``(path, enum)`` for every ``properties.<field>.enum`` in a schema.

    The same logical field lives at different nesting depths across schemas
    (``verifier_loop_schema.json`` keeps ``route`` at the top level, while
    ``iteration_schema.json`` nests it inside ``properties.changes.items``...),
    so the lookup must be recursive rather than a single key hop.
    """
    if isinstance(node, dict):
        props = node.get("properties")
        if isinstance(props, dict):
            spec = props.get(field)
            if isinstance(spec, dict) and isinstance(spec.get("enum"), list):
                yield path, spec["enum"]
        for key, value in node.items():
            yield from _find_property_enums(value, field, path + (key,))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _find_property_enums(value, field, path + (index,))


def _check_route_enums(root: Path) -> List[Finding]:
    findings: List[Finding] = []
    for rel, field in _ROUTE_ENUMS:
        schema_path = root / rel
        if not schema_path.is_file():
            continue
        if field in _ALLOWLIST.get(schema_path.name, ()):
            continue
        try:
            data = json.loads(schema_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            continue  # 非法 JSON 由 state 类检查负责，这里不重复报
        for path, enum in _find_property_enums(data, field):
            if _REQUIRED_V4_ROUTES & set(v for v in enum if isinstance(v, str)):
                continue
            where = "/".join(str(p) for p in path) or "<root>"
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category=CATEGORY,
                file=rel,
                line=None,
                snippet=(f"R1 properties.{field}.enum 无法表达任何 v4 路由"
                         f"（缺 {sorted(_REQUIRED_V4_ROUTES)}）；位置 {where}；现存值 {enum}"),
                fix_hint="为 enum 补 rdd-builder（保留 guide-ship/guide-plan 以兼容存量 state）",
            ))
    return findings


def _check_string_literals(root: Path) -> List[Finding]:
    findings: List[Finding] = []
    for path in _iter_source_files(root):
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if path.suffix == ".sh":
            # shell 没有 AST：只取非注释行，避免把注释里的历史引用算进来。
            for lineno, line in enumerate(source.splitlines(), 1):
                code = line.split("#", 1)[0] if line.lstrip().startswith("#") else line
                if line.lstrip().startswith("#"):
                    continue
                if _R2_PATTERN.search(code):
                    findings.append(_r2_finding(root, path, lineno, code.strip()))
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        docstrings = _docstring_node_ids(tree)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Constant)
                    and isinstance(node.value, str)
                    and id(node) not in docstrings):
                continue
            if not _R2_PATTERN.search(node.value):
                continue
            findings.append(
                _r2_finding(root, path, getattr(node, "lineno", None), node.value.strip()))
    return findings


def _r2_finding(root: Path, path: Path, lineno, text: str) -> Finding:
    try:
        shown = str(path.relative_to(root))
    except ValueError:
        shown = str(path)
    return Finding(
        severity=Severity.WARNING,
        category=CATEGORY,
        file=shown,
        line=lineno,
        snippet=f"R2 面向用户的字符串指向已删除的 v3 skill：{text[:120]}",
        fix_hint="改为 v4 名称（rdd-arch / rdd-planner / rdd-builder）",
    )


def _check_skill_frontmatter(root: Path) -> List[Finding]:
    findings: List[Finding] = []
    skills_dir = root / _SKILL_DIR
    if not skills_dir.is_dir():
        return findings
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        try:
            text = skill_md.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if not text.startswith("---"):
            continue
        end = text.find("\n---", 3)
        frontmatter = text[3:end] if end != -1 else text[3:]
        match = _FRONTMATTER_NAME.search(frontmatter)
        if not match:
            continue
        name = match.group(1).strip().strip("'\"")
        if not name.startswith("guide-"):
            continue
        findings.append(Finding(
            severity=Severity.CRITICAL,
            category=CATEGORY,
            file=str(skill_md.relative_to(root)),
            line=None,
            snippet=f"R3 SKILL.md frontmatter name: {name}（该 skill 不存在）",
            fix_hint="改为 v4 名称，或删除这个残留 skill 目录",
        ))
    return findings


_SPEC_SCAN_SWITCH = ("doctor", "v4_residue", "scan_specs")
#: Where the machine census lives — the fix hint points humans at the backlog list.
_CENSUS_HINT = ".rddf/reviews/spec-residue-census-*-full.md"


def _spec_scan_enabled(project_root: Path) -> bool:
    """Read ``doctor.v4_residue.scan_specs`` from project.yaml (default False)."""
    yaml_file = project_root / ".rddf" / "project.yaml"
    if not yaml_file.is_file():
        return False
    try:
        import yaml

        cfg = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or {}
    except Exception:
        return False
    node = cfg
    for key in _SPEC_SCAN_SWITCH:
        node = node.get(key) if isinstance(node, dict) else None
        if node is None:
            return False
    return node is True or str(node).lower() == "true"


def _check_specs(root: Path) -> List[Finding]:
    """R4 — retired stage names inside adopted capability specs."""
    if not _spec_scan_enabled(root):
        return []

    result = scan_specs(root)
    findings: List[Finding] = []
    inline_lines = {f"{f}:{ln}" for f, ln in result.ignored_inline}

    if not result.checked_anything:
        findings.append(Finding(
            severity=Severity.INFO,
            category=CATEGORY,
            file="openspec/specs",
            line=None,
            snippet=("R4 checked 0 —— 未扫描任何 spec 文件（openspec/specs/ 不存在或为空）；"
                     "这不等于 clean"),
            fix_hint=("在本仓 `.rddf/project.yaml` 里开启 doctor.v4_residue.scan_specs "
                      "只对存在 openspec/specs/ 的项目有意义"),
        ))
        return findings

    blocks = result.blocks()
    findings.append(Finding(
        severity=Severity.INFO,
        category=CATEGORY,
        file="openspec/specs",
        line=None,
        snippet=(f"R4 checked {result.files_scanned} spec file(s); "
                 f"{len(blocks)} block(s) with retired-stage residue"),
        fix_hint=f"逐份处置清单见 {_CENSUS_HINT}",
    ))

    grouped: dict = {}
    for hit in result.hits:
        if hit.category:
            continue                      # explicitly exempted
        grouped.setdefault((hit.file, hit.block_line), []).append(hit)

    for (rel, block_line), hits in sorted(grouped.items()):
        tokens = sorted({h.matched_token for h in hits})
        weak = any(h.weak_wording for h in hits)
        title = hits[0].requirement_title or "(no requirement)"
        note = "；措辞把旧名说成现存物" if weak else ""
        inline = [h.line for h in hits if f"{rel}:{h.line}" in inline_lines]
        if inline:
            note += f"；L{inline[0]} 的 allow 标注与命中同行 ⇒ 已忽略（标注须独占一行并紧跟命中行）"
        findings.append(Finding(
            severity=Severity.WARNING,
            category=CATEGORY,
            file=rel,
            line=block_line,
            snippet=(f"R4 [req:{title}] {len(hits)} 处已退役 stage 名："
                     f"{', '.join(tokens)}{note}"),
            fix_hint=("改指现存落点，或加 `<!-- v4-residue:allow=<enum|proposal-name|"
                      "guard|history|rename-history> -->`（独占一行、紧跟命中行）；"
                      "代码块内的命中则把标注放在**围栏结束行之后**、code 限 enum/guard"),
        ))

    for rel, line, code in result.invalid_annotations:
        findings.append(Finding(
            severity=Severity.WARNING,
            category=CATEGORY,
            file=rel,
            line=line,
            snippet=(f"R4 invalid allow code `{code}` —— 合法取值仅 "
                     "enum / proposal-name / guard / history / rename-history；"
                     "该标注**不生效**"),
            fix_hint="改成五类之一，或删除该标注（拼错不得静默豁免）",
        ))

    for rel, line, code in result.fence_rejected:
        findings.append(Finding(
            severity=Severity.WARNING,
            category=CATEGORY,
            file=rel,
            line=line,
            snippet=(f"R4 fence-position allow code `{code}` 不生效 —— "
                     "紧跟围栏结束行的标注仅允许 enum / guard；该标注**不生效**"),
            fix_hint=("改成 enum（该值仍在某个 schema 的 enum 里）或 guard（反漂移断言/夹具）；"
                      "历史叙述不该出现在代码块里 ⇒ 若真是历史，改用文本处置"),
        ))

    for rel, line in result.in_fence_annotations:
        findings.append(Finding(
            severity=Severity.WARNING,
            category=CATEGORY,
            file=rel,
            line=line,
            snippet=("R4 allow 标注落在**围栏内** ⇒ 不生效（标注是元数据，不能藏在示例里）"),
            fix_hint="把标注移到围栏**结束行之后**（code 限 enum/guard），或删掉它",
        ))

    for stale in result.stale_allows:
        findings.append(Finding(
            severity=Severity.WARNING,
            category=CATEGORY,
            file=stale.file,
            line=stale.line,
            snippet=(f"R4 stale allow —— `{stale.code}` 标注的前一行已无退役 stage 名；"
                     "豁免已过期，请删除该标注"),
            fix_hint="删除过期标注，或确认上一行的命中是否被改指后漏删标注",
        ))

    return findings


def run(project_root: Path | None = None) -> List[Finding]:
    """Run the v4-residue contract check against project_root."""
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
    root = Path(project_root)
    findings: List[Finding] = []
    findings.extend(_check_route_enums(root))
    findings.extend(_check_string_literals(root))
    findings.extend(_check_skill_frontmatter(root))
    findings.extend(_check_specs(root))
    return findings
