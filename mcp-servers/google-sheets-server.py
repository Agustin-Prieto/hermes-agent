#!/usr/bin/env python3
"""
Google Sheets MCP Server — Hermes Agent integration.

Allows Hermes to read, write, and append to Google Sheets via the
Google Sheets API. Uses service account authentication.

Install deps:
  pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client mcp

Usage:
  python google-sheets-server.py
  # Then add as MCP in Hermes: command: "python", args: ["/app/mcp-servers/google-sheets-server.py"]
"""

import json
import os
import sys
import traceback
from typing import Any

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from mcp.server import Server, NotificationOptions
    from mcp.server.models import InitializationOptions
    import mcp.server.stdio
    import mcp.types as types
except ImportError as e:
    print(f"Missing dependency: {e}", file=sys.stderr)
    print("Install with: pip install google-auth google-auth-oauthlib google-api-python-client mcp", file=sys.stderr)
    sys.exit(1)

# ── Auth ──────────────────────────────────────────────────────────────────────
# Credentials come from env var GOOGLE_SHEETS_CREDENTIALS (JSON string) or
# from GOOGLE_APPLICATION_CREDENTIALS (file path).
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_creds():
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS", "")
    if creds_json:
        info = json.loads(creds_json)
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)

    creds_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if creds_file and os.path.exists(creds_file):
        return service_account.Credentials.from_service_account_file(creds_file, scopes=SCOPES)

    raise ValueError(
        "No Google credentials found. Set GOOGLE_SHEETS_CREDENTIALS (JSON) "
        "or GOOGLE_APPLICATION_CREDENTIALS (file path)."
    )


def get_service():
    return build("sheets", "v4", credentials=get_creds())


# ── Tools ─────────────────────────────────────────────────────────────────────

async def handle_tool(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent]:
    if arguments is None:
        raise ValueError("Missing arguments")

    try:
        service = get_service()

        if name == "sheets_list":
            """List all spreadsheets the service account has access to."""
            # Note: The Drive API is needed to list files, Sheets API only reads
            # spreadsheets you know the ID of. We use Drive API.
            from googleapiclient.discovery import build as drive_build
            drive = drive_build("drive", "v3", credentials=get_creds())
            results = drive.files().list(
                q="mimeType='application/vnd.google-apps.spreadsheet'",
                pageSize=20,
                fields="files(id, name, modifiedTime)",
            ).execute()
            files = results.get("files", [])
            return [types.TextContent(
                type="text",
                text=json.dumps(files, indent=2)
            )]

        elif name == "sheets_read":
            """Read data from a Google Sheet.
            
            Arguments:
              spreadsheet_id: The ID from the sheet URL
              range: A1 notation range (e.g. 'Sheet1!A1:D10')
            """
            spreadsheet_id = arguments.get("spreadsheet_id")
            range_ = arguments.get("range", "Sheet1!A1:Z1000")
            if not spreadsheet_id:
                raise ValueError("spreadsheet_id is required")

            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_,
            ).execute()
            values = result.get("values", [])
            return [types.TextContent(
                type="text",
                text=json.dumps({"rows": len(values), "data": values}, indent=2)
            )]

        elif name == "sheets_write":
            """Write data to a Google Sheet.
            
            Arguments:
              spreadsheet_id: The ID from the sheet URL
              range: A1 notation range (e.g. 'Sheet1!A1:D10')
              values: 2D array of values (e.g. [["Name", "Email"], ["John", "john@x.com"]])
            """
            spreadsheet_id = arguments["spreadsheet_id"]
            range_ = arguments["range"]
            values = arguments["values"]
            if not isinstance(values, list) or not all(isinstance(r, list) for r in values):
                raise ValueError("values must be a 2D array (list of lists)")

            body = {"values": values}
            result = service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_,
                valueInputOption="USER_ENTERED",
                body=body,
            ).execute()
            return [types.TextContent(
                type="text",
                text=json.dumps({"updated_cells": result.get("updatedCells", 0)}, indent=2)
            )]

        elif name == "sheets_append":
            """Append a row to a Google Sheet.
            
            Arguments:
              spreadsheet_id: The ID from the sheet URL
              range: A1 notation range (e.g. 'Sheet1!A:D')
              values: Array of values for one row (e.g. ["John", "john@x.com"])
            """
            spreadsheet_id = arguments["spreadsheet_id"]
            range_ = arguments.get("range", "Sheet1!A:D")
            values = arguments["values"]
            if not isinstance(values, list):
                raise ValueError("values must be an array")

            body = {"values": [values]}
            result = service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body,
            ).execute()
            return [types.TextContent(
                type="text",
                text=json.dumps({"updated_cells": result.get("updates", {}).get("updatedCells", 0)}, indent=2)
            )]

        elif name == "sheets_create":
            """Create a new Google Sheet.
            
            Arguments:
              title: The title of the new sheet
            """
            title = arguments.get("title", "New Sheet")
            spreadsheet = service.spreadsheets().create(
                body={"properties": {"title": title}}
            ).execute()
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "spreadsheet_id": spreadsheet["spreadsheetId"],
                    "url": spreadsheet["spreadsheetUrl"],
                    "title": spreadsheet["properties"]["title"],
                }, indent=2)
            )]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        return [types.TextContent(
            type="text",
            text=json.dumps({"error": str(e), "traceback": traceback.format_exc()}, indent=2)
        )]


# ── Server ────────────────────────────────────────────────────────────────────
async def main():
    server = Server("google-sheets")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="sheets_list",
                description="List Google Sheets accessible by the service account",
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="sheets_read",
                description="Read data from a Google Sheet range",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_id": {"type": "string", "description": "Google Sheet ID from URL"},
                        "range": {"type": "string", "description": "A1 notation (e.g. Sheet1!A1:D10)", "default": "Sheet1!A1:Z1000"},
                    },
                    "required": ["spreadsheet_id"],
                },
            ),
            types.Tool(
                name="sheets_write",
                description="Write data to a Google Sheet range",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_id": {"type": "string", "description": "Google Sheet ID from URL"},
                        "range": {"type": "string", "description": "A1 notation"},
                        "values": {"type": "array", "items": {"type": "array"}, "description": "2D array of values"},
                    },
                    "required": ["spreadsheet_id", "range", "values"],
                },
            ),
            types.Tool(
                name="sheets_append",
                description="Append a row to a Google Sheet",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_id": {"type": "string", "description": "Google Sheet ID from URL"},
                        "range": {"type": "string", "description": "A1 notation range", "default": "Sheet1!A:D"},
                        "values": {"type": "array", "description": "Array of values for one row"},
                    },
                    "required": ["spreadsheet_id", "values"],
                },
            ),
            types.Tool(
                name="sheets_create",
                description="Create a new Google Sheet",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Sheet title"},
                    },
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent]:
        return await handle_tool(name, arguments)

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="google-sheets",
                server_version="1.0.0",
            ),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
