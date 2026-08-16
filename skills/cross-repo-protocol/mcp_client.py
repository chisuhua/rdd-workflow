"""MCP Client: 4 Hub tools via MCP protocol with REST fallback.

Tools:
  - hub_read_issue(issue_number) -> dict
  - hub_create_issue(title, body, ...) -> dict
  - hub_update_status(issue_number, status, comment?) -> dict
  - hub_sync_contract(contract_id, state) -> dict

Transports:
  - stdio (default): spawn MCP Server as subprocess
  - http: use MCP_SERVER_URL (Streamable HTTP)

Fallback: REST GitHub API when MCP Server unreachable.
Trace: all calls logged to .rddf/state/.mcp-trace.jsonl.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from skills.cross_repo_protocol.trace import MCPTraceLogger


class MCPConfigurationError(Exception):
    """Raised when MCP client is misconfigured (e.g., missing GITHUB_TOKEN)."""


class MCPClient:
    """MCP client with REST fallback and trace logging."""

    DEFAULT_TIMEOUT = 5

    def __init__(
        self,
        transport: Optional[str] = None,
        server_path: Optional[str] = None,
        token: Optional[str] = None,
    ):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        if not self.token:
            raise MCPConfigurationError("GITHUB_TOKEN environment variable required")
        self.transport = transport or os.environ.get("MCP_TRANSPORT", "stdio")
        self.server_path = server_path or os.environ.get("MCP_SERVER_PATH")
        self.server_url = os.environ.get("MCP_SERVER_URL")
        self.trace_logger = MCPTraceLogger(
            os.environ.get("MCP_TRACE_FILE", ".rddf/state/.mcp-trace.jsonl")
        )

    def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Call MCP tool with trace logging. Falls back to REST on error."""
        start = time.time()
        trace_entry = {"tool_name": tool_name, "args": self._safe_args(args)}
        try:
            result = self._call_mcp_server(tool_name, args)
            trace_entry["result_status"] = "success"
            trace_entry["duration_ms"] = MCPTraceLogger.compute_duration_ms(start, time.time())
            self.trace_logger.append(trace_entry)
            return self._normalize_issue(result) if tool_name == "hub_read_issue" else result
        except (ConnectionRefusedError, OSError, subprocess.TimeoutExpired) as e:
            trace_entry["result_status"] = "error"
            trace_entry["error"] = str(e)
            trace_entry["fallback_attempted"] = True
            trace_entry["duration_ms"] = MCPTraceLogger.compute_duration_ms(start, time.time())
            self.trace_logger.append(trace_entry)
            if not os.environ.get("MCPSuppressFallbackWarning"):
                print(f"⚠️ MCP Server unreachable, using REST fallback: {e}", file=sys.stderr)
            return self._fallback_to_rest(tool_name, args)

    def _call_mcp_server(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke MCP tool via SDK. Stub for now; production would use mcp package."""
        raise ConnectionRefusedError("MCP Server not implemented in stub")

    def _fallback_to_rest(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback to GitHub REST API when MCP Server unreachable."""
        try:
            import requests
        except ImportError:
            raise MCPConfigurationError("requests library required for REST fallback")
        headers = {"Authorization": f"Bearer {self.token}"}
        if tool_name == "hub_read_issue":
            issue_num = args["issue_number"]
            owner = args.get("owner", "my-org")
            repo = args.get("repo", "rdd-hub")
            r = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_num}",
                headers=headers, timeout=self.DEFAULT_TIMEOUT,
            )
            r.raise_for_status()
            data = r.json()
            return self._normalize_issue(data)
        if tool_name == "hub_create_issue":
            owner = args.get("owner", "my-org")
            repo = args.get("repo", "rdd-hub")
            payload = {"title": args["title"], "body": args.get("body", "")}
            if "stakeholders" in args:
                payload["body"] += f"\n**Stakeholders**: {','.join(args['stakeholders'])}"
            r = requests.post(
                f"https://api.github.com/repos/{owner}/{repo}/issues",
                headers=headers, json=payload, timeout=self.DEFAULT_TIMEOUT,
            )
            r.raise_for_status()
            data = r.json()
            return {
                "number": data["number"],
                "title": data["title"],
                "body": data["body"],
                "state": data["state"],
                "created_at": data["created_at"],
                "url": data["html_url"],
            }
        raise NotImplementedError(f"No REST fallback for tool: {tool_name}")

    def _normalize_issue(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "number": raw["number"],
            "title": raw["title"],
            "body": raw.get("body", ""),
            "state": raw["state"],
            "status": "open" if raw["state"] == "open" else "closed",
            "stakeholders": raw.get("stakeholders", []),
            "contract_impact": raw.get("contract_impact", ""),
            "labels": [l["name"] for l in raw.get("labels", [])],
        }

    def _safe_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return MCPTraceLogger.redact(args)

    def hub_read_issue(self, issue_number: int) -> Dict[str, Any]:
        return self.call_tool("hub_read_issue", {"issue_number": issue_number})

    def hub_create_issue(
        self, title: str, body: str = "", stakeholders: Optional[list] = None,
        contract_impact: str = "Medium",
    ) -> Dict[str, Any]:
        if not title:
            raise ValueError("title is required")
        args = {"title": title, "body": body, "contract_impact": contract_impact}
        if stakeholders:
            args["stakeholders"] = stakeholders
        return self.call_tool("hub_create_issue", args)

    def hub_update_status(
        self, issue_number: int, status: str, comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        args = {"issue_number": issue_number, "status": status}
        if comment:
            args["comment"] = comment
        return self.call_tool("hub_update_status", args)

    def hub_sync_contract(self, contract_id: str, state: str) -> Dict[str, Any]:
        return self.call_tool("hub_sync_contract", {
            "contract_id": contract_id, "state": state,
        })
