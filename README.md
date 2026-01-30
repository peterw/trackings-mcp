# Trackings MCP Server

MCP server for Claude Desktop integration with trackings.ai.

## Installation

```bash
uvx --from git+https://github.com/peterw/trackings-mcp trackings-mcp
```

## Configuration

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "trackings": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/peterw/trackings-mcp", "trackings-mcp"],
      "env": {
        "TRACKINGS_API_KEY": "your-api-key",
        "TRACKINGS_API_URL": "https://your-convex-deployment.convex.site"
      }
    }
  }
}
```

## Available Tools

- `list_projects` - List all projects
- `list_scans` - List scans for a project
- `list_scan_runs` - List scan runs for a project or scan
- `get_scan_run` - Get details for a scan run
- `get_scan_results` - Get consolidated keyword results for a run
- `get_credits` - Get current credit balance
- `create_scan` - Create a scan configuration
- `trigger_scan_run` - Trigger a scan run
