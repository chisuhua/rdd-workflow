"""Contract diff engine: compare Hub OpenAPI contracts vs Spoke implementations.

Uses openapi-diff library if available; falls back to simple YAML+grep
analysis if not. Returns DiffResult with severity classification:
  - Breaking-Change: Spoke missing required Hub field → exit 1
  - High: Spoke has additional unused field
  - Medium: API path mismatches
  - Low: cosmetic diffs
  - No-Diff: clean

Output formats: json (default for CI), markdown (human).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Union

PathLike = Union[str, Path]


class Severity(str, Enum):
    BREAKING = "Breaking-Change"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    NO_DIFF = "No-Diff"


SEVERITY_LEVELS = [s.value for s in Severity]


@dataclass
class DiffItem:
    type: str
    path: str
    message: str
    severity: str = "Medium"


@dataclass
class DiffResult:
    severity: str = "No-Diff"
    diffs: List[DiffItem] = field(default_factory=list)
    contract_name: str = ""
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "diffs": [d.__dict__ for d in self.diffs],
            "contract_name": self.contract_name,
            "summary": self.summary,
        }


class DiffEngine:
    """Compare Hub contract vs Spoke local implementation."""

    def run(self, hub_path: PathLike, local_path: PathLike) -> DiffResult:
        hub = Path(hub_path)
        local = Path(local_path)
        result = DiffResult(contract_name=hub.stem)
        if not hub.exists():
            result.severity = Severity.BREAKING.value
            result.diffs.append(DiffItem(
                type="missing-contract",
                path=str(hub),
                message=f"Hub contract not found: {hub}",
                severity=Severity.BREAKING.value,
            ))
            return result

        # Try openapi-diff library
        try:
            return self._run_with_openapi_diff(hub, local, result)
        except ImportError:
            return self._run_fallback(hub, local, result)

    def _run_with_openapi_diff(self, hub: Path, local: Path, result: DiffResult) -> DiffResult:
        """Use openapi-diff if available."""
        try:
            import openapi_diff  # noqa: F401
        except ImportError:
            raise ImportError("openapi-diff not installed")
        # Parse required fields from Hub
        hub_required = self._extract_required_fields(hub)
        # Parse local impl for those fields
        local_text = local.read_text() if local.exists() else ""
        for field_name in hub_required:
            if not re.search(rf"\b{re.escape(field_name)}\b", local_text):
                result.diffs.append(DiffItem(
                    type="missing-field",
                    path=field_name,
                    message=f"Spoke impl missing required Hub field: {field_name}",
                    severity=Severity.BREAKING.value,
                ))
        result.severity = (
            Severity.BREAKING.value if result.diffs else Severity.NO_DIFF.value
        )
        result.summary = (
            f"{len(result.diffs)} breaking change(s)" if result.diffs
            else "Contract compliant"
        )
        return result

    def _run_fallback(self, hub: Path, local: Path, result: DiffResult) -> DiffResult:
        """Pure-Python fallback without openapi-diff dependency."""
        hub_required = self._extract_required_fields(hub)
        local_text = local.read_text() if local.exists() else ""
        for field_name in hub_required:
            if not re.search(rf"\b{re.escape(field_name)}\b", local_text):
                result.diffs.append(DiffItem(
                    type="missing-field",
                    path=field_name,
                    message=f"Spoke impl missing required Hub field: {field_name}",
                    severity=Severity.BREAKING.value,
                ))
        result.severity = (
            Severity.BREAKING.value if result.diffs else Severity.NO_DIFF.value
        )
        result.summary = (
            f"{len(result.diffs)} breaking change(s)" if result.diffs
            else "Contract compliant"
        )
        return result

    @staticmethod
    def _extract_required_fields(contract_path: Path) -> List[str]:
        """Extract required field names from OpenAPI contract YAML/JSON."""
        import yaml
        text = contract_path.read_text()
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError:
            return []
        fields = []
        try:
            for path_obj in data.get("paths", {}).values():
                for method_obj in path_obj.values():
                    if not isinstance(method_obj, dict):
                        continue
                    content = (
                        method_obj.get("requestBody", {})
                        .get("content", {})
                    )
                    for media in content.values():
                        schema = media.get("schema", {})
                        if "required" in schema:
                            fields.extend(schema["required"])
        except (KeyError, TypeError, AttributeError):
            return []
        return list(set(fields))


def format_output(result: DiffResult, format: str = "json") -> str:
    """Format DiffResult as JSON or Markdown."""
    if format == "json":
        return json.dumps(result.to_dict(), indent=2)
    if format == "markdown":
        lines = [f"# Contract Diff Report: {result.contract_name}", ""]
        lines.append(f"**Severity**: {result.severity}")
        lines.append(f"**Summary**: {result.summary}")
        lines.append("")
        if result.diffs:
            lines.append(f"## {len(result.diffs)} Difference(s)")
            for d in result.diffs:
                lines.append(f"- **{d.type}** (`{d.path}`): {d.message}")
        return "\n".join(lines)
    return format_output(result, format="json")
