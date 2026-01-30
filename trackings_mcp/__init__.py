#!/usr/bin/env python3
"""
Trackings MCP Server - Read-only API access for AI agents

Supports both stdio (Claude Desktop) and HTTP/SSE (Claude.ai web) transports.
- stdio: Uses TRACKINGS_API_KEY env var
- HTTP/SSE: Uses OAuth Bearer token from request
"""
import os
import json
import asyncio
from contextvars import ContextVar
import httpx
from mcp.server import Server
from mcp.types import Tool, TextContent

API_BASE = os.getenv("TRACKINGS_API_URL", "")
API_KEY = os.getenv("TRACKINGS_API_KEY", "")  # For stdio mode
PORT = int(os.getenv("PORT", "8000"))

# Context var to store OAuth token for HTTP mode
current_token: ContextVar[str] = ContextVar("current_token", default="")

server = Server("trackings")


def build_headers() -> dict:
    token = current_token.get()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {"Authorization": f"Api-Key {API_KEY}"}


def api_get(endpoint: str, params: dict = None) -> dict:
    """Make authenticated GET request to Trackings API"""
    if not API_BASE:
        raise ValueError("TRACKINGS_API_URL is not set")
    headers = build_headers()
    resp = httpx.get(f"{API_BASE}{endpoint}", headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def api_post(endpoint: str, payload: dict, idempotency_key: str | None = None) -> dict:
    """Make authenticated POST request to Trackings API"""
    if not API_BASE:
        raise ValueError("TRACKINGS_API_URL is not set")
    headers = build_headers()
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    resp = httpx.post(f"{API_BASE}{endpoint}", headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="list_projects",
            description="List all projects in Trackings",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="list_scans",
            description="List scans for a project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"}
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="list_scan_runs",
            description="List scan runs by project or scan",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "project_scan_id": {"type": "string", "description": "Project scan ID"}
                }
            }
        ),
        Tool(
            name="get_scan_run",
            description="Get details for a scan run",
            inputSchema={
                "type": "object",
                "properties": {"run_id": {"type": "string", "description": "Scan run ID"}},
                "required": ["run_id"]
            }
        ),
        Tool(
            name="get_scan_results",
            description="Get consolidated keyword results for a scan run",
            inputSchema={
                "type": "object",
                "properties": {"scan_run_id": {"type": "string", "description": "Scan run ID"}},
                "required": ["scan_run_id"]
            }
        ),
        Tool(
            name="get_credits",
            description="Get current credit balance and subscription info",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="create_scan",
            description="Create a scan configuration",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "keywords": {"type": "array", "items": {"type": "string"}},
                    "type": {"type": "string", "enum": ["one-time", "recurring"]},
                    "scan_type": {"type": "string", "enum": ["broad_mention", "exact_url"]},
                    "recurring_interval": {"type": "string", "enum": ["daily", "weekly", "monthly"]},
                    "test_mode": {"type": "boolean"},
                    "idempotency_key": {"type": "string"}
                },
                "required": ["project_id", "keywords", "type"]
            }
        ),
        Tool(
            name="trigger_scan_run",
            description="Trigger a scan run for an existing scan configuration",
            inputSchema={
                "type": "object",
                "properties": {
                    "scan_id": {"type": "string", "description": "Scan ID"},
                    "idempotency_key": {"type": "string"}
                },
                "required": ["scan_id"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        if name == "list_projects":
            data = api_get("/mcp/projects")
            return [TextContent(type="text", text=json.dumps(data, indent=2))]

        if name == "list_scans":
            data = api_get("/mcp/scans", params={"projectId": arguments["project_id"]})
            return [TextContent(type="text", text=json.dumps(data, indent=2))]

        if name == "list_scan_runs":
            params = {}
            if arguments.get("project_id"):
                params["projectId"] = arguments["project_id"]
            if arguments.get("project_scan_id"):
                params["projectScanId"] = arguments["project_scan_id"]
            data = api_get("/mcp/scan-runs", params=params)
            return [TextContent(type="text", text=json.dumps(data, indent=2))]

        if name == "get_scan_run":
            data = api_get("/mcp/scan-run", params={"runId": arguments["run_id"]})
            return [TextContent(type="text", text=json.dumps(data, indent=2))]

        if name == "get_scan_results":
            data = api_get("/mcp/scan-results", params={"scanRunId": arguments["scan_run_id"]})
            return [TextContent(type="text", text=json.dumps(data, indent=2))]

        if name == "get_credits":
            data = api_get("/mcp/credits")
            return [TextContent(type="text", text=json.dumps(data, indent=2))]

        if name == "create_scan":
            payload = {
                "projectId": arguments["project_id"],
                "keywords": arguments["keywords"],
                "type": arguments["type"],
                "scanType": arguments.get("scan_type"),
                "recurringInterval": arguments.get("recurring_interval"),
                "testMode": arguments.get("test_mode"),
            }
            data = api_post("/mcp/scans", payload, arguments.get("idempotency_key"))
            return [TextContent(type="text", text=json.dumps(data, indent=2))]

        if name == "trigger_scan_run":
            payload = {"scanId": arguments["scan_id"]}
            data = api_post("/mcp/scan-runs", payload, arguments.get("idempotency_key"))
            return [TextContent(type="text", text=json.dumps(data, indent=2))]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except httpx.HTTPStatusError as e:
        return [TextContent(type="text", text=f"API Error {e.response.status_code}: {e.response.text}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def run_stdio():
    """Run server with stdio transport (for Claude Desktop)"""
    from mcp.server.stdio import stdio_server
    from mcp.server.models import InitializationOptions
    from mcp.server import NotificationOptions

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="trackings",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def run_http():
    """Run server with HTTP/SSE transport (for Claude.ai web)"""
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.responses import JSONResponse
    import uvicorn

    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:]
            current_token.set(token)

        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(
                streams[0], streams[1], server.create_initialization_options()
            )

    async def handle_messages(request):
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:]
            current_token.set(token)
        await sse.handle_post_message(request.scope, request.receive, request._send)

    async def health(request):
        return JSONResponse({"status": "ok"})

    app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/messages/", endpoint=handle_messages, methods=["POST"]),
            Route("/health", endpoint=health),
        ]
    )

    uvicorn.run(app, host="0.0.0.0", port=PORT)


def main():
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--http":
        run_http()
    else:
        asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
