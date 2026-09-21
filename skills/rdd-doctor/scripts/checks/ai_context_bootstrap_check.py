"""ai-context-bootstrap check — detect Layer 0 deployment status.

Checks whether the project has rdd-workflow Layer 0 protocol blocks deployed
in its AI configuration files (AGENTS.md, .cursorrules, CLAUDE.md, etc.).

This is a standalone check (no _lib dependency) — it calls the same
detection logic that `rddf setup ai-context` uses.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from doctor_render import Finding, Severity


# Sentinel markers — must match the SSOT template.
_SENTINEL_START = "<!-- RDD-WORKFLOW-CORE-USAGE-START -->"

# AI config file detection order (per ADR-0052).
_AI_CONFIG_FILES = [
    "AGENTS.md",
    ".cursorrules",
    "CLAUDE.md",
    ".clinerules",
    ".continue/rules/*.md",
    ".github/copilot-instructions.md",
]


def _detect_config_files(project_root: Path) -> list[Path]:
    """Return ordered list of existing AI config files."""
    found: list[Path] = []
    for pattern in _AI_CONFIG_FILES:
        full_pattern = project_root / pattern
        if "*" in str(full_pattern):
            matches = sorted(project_root.glob(pattern))
            found.extend(m for m in matches if m.is_file())
        else:
            if full_pattern.is_file():
                found.append(full_pattern)
    return found


def _has_sentinel(content: str) -> bool:
    return _SENTINEL_START in content


def run(project_root: Path | None = None) -> List[Finding]:
    """Run ai-context-bootstrap detection.

    Reports:
      - ✅ healthy: Layer 0 block found in at least one config file
      - ⚠️ warn: no config files found, or none has the block
      - 💡 info: block present but no Hub protocol
    """
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))

    findings: List[Finding] = []
    config_files = _detect_config_files(project_root)

    if not config_files:
        findings.append(Finding(
            severity=Severity.WARNING,
            category="ai-context-bootstrap",
            file="(repo-wide)",
            line=None,
            snippet="未找到 AI 配置文件（AGENTS.md 等）。Layer 0 未部署。",
            fix_hint="运行 `rddf setup ai-context` 部署 Layer 0 协议块。",
        ))
        return findings

    deployed_count = 0
    for cfg in config_files:
        content = cfg.read_text(encoding="utf-8", errors="replace")
        if _has_sentinel(content):
            deployed_count += 1

    if deployed_count == 0:
        files_list = ", ".join(str(c.relative_to(project_root)) for c in config_files)
        findings.append(Finding(
            severity=Severity.WARNING,
            category="ai-context-bootstrap",
            file="(repo-wide)",
            line=None,
            snippet=(
                f"找到 {len(config_files)} 个 AI 配置文件但均无 Layer 0 块: {files_list}"
            ),
            fix_hint="运行 `rddf setup ai-context` 部署 Layer 0 协议块。",
        ))
    elif deployed_count < len(config_files):
        findings.append(Finding(
            severity=Severity.INFO,
            category="ai-context-bootstrap",
            file="(repo-wide)",
            line=None,
            snippet=(
                f"Layer 0 已部署到 {deployed_count}/{len(config_files)} 个 AI 配置文件"
            ),
            fix_hint=(
                f"运行 `rddf setup ai-context` 部署到剩余文件。"
            ),
        ))
    else:
        findings.append(Finding(
            severity=Severity.INFO,
            category="ai-context-bootstrap",
            file="(repo-wide)",
            line=None,
            snippet="✅ Layer 0 已部署到所有检测到的 AI 配置文件",
            fix_hint="无需操作。运行 `rddf doctor --category ai-context-bootstrap` 再次检查。",
        ))

    return findings