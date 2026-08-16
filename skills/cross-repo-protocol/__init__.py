"""Cross-repo protocol package: MCP client + trace logger."""
from skills.cross_repo_protocol.mcp_client import MCPClient, MCPConfigurationError
from skills.cross_repo_protocol.trace import MCPTraceLogger

__all__ = ["MCPClient", "MCPConfigurationError", "MCPTraceLogger"]
