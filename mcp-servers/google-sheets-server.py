#!/usr/bin/env python3
"""
Google Sheets MCP Server — Hermes Agent integration (standalone, no deps needed).

Implements the MCP stdio protocol (JSON-RPC over stdin/stdout) directly
without requiring the 'mcp' Python package. Only needs google-auth and
google-api-python-client.

Usage: python google-sheets-server.py

Auth: Set GOOGLE_SHEETS_CREDENTIALS env var (service account JSON)
"""

import json
import os
import sys
import traceback
from typing import Any

# Try to import Google deps - give a helpful error if missing
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError as e:
    print(json.dumps({
        "jsonrpc": "2.0", "id": None,
        "error": {"code": -32000, "message": f"Missing dependency: {e}. Install: pip install google-auth google-api-python-client"}
    }), flush=True)
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive.readonly"]


def get_creds():
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS", "")
    if creds_json:
        info = json.loads(creds_json)
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)

    creds_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if creds_file and os.path.exists(creds_file):
        return service_account.Credentials.from_service_account_file(creds_file, scopes=SCOPES)

    raise ValueError(
        "No Google credentials found. Set GOOGLE_SHEETS_CREDENTIALS (JSON service account) "
        "or GOOGLE_APPLICATION_CREDENTIALS (file path)."
    )


def sheets_service():
    return build("sheets", "v4", credentials=get_creds())


def drive_service():
    return build("drive", "v3", credentials=get_creds())


TOOLS = [
    {
        "name": "sheets_list",
        "description": "List Google Sheets accessible by the service account",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "sheets_read",
        "description": "Read data from a Google Sheet range",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {"type": "string", "description": "Google Sheet ID from URL"},
                "range": {"type": "string", "description": "A1 notation (e.g. Sheet1!A1:D10)", "default": "Sheet1!A1:Z1000"},
            },
            "required": ["spreadsheet_id"],
        },
    },
    {
        "name": "sheets_write",
        "description": "Write data to a Google Sheet range",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {"type": "string"},
                "range": {"type": "string", "description": "A1 notation"},
                "values": {"type": "array", "items": {"type": "array"}, "description": "2D array of values"},
            },
            "required": ["spreadsheet_id", "range", "values"],
        },
    },
    {
        "name": "sheets_append",
        "description": "Append a row to a Google Sheet",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {"type": "string"},
                "range": {"type": "string", "description": "A1 notation", "default": "Sheet1!A:D"},
                "values": {"type": "array", "description": "Array of values for one row"},
            },
            "required": ["spreadsheet_id", "values"],
        },
    },
    {
        "name": "sheets_create",
        "description": "Create a new Google Sheet",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Sheet title", "default": "New Sheet"},
            },
        },
    },
]


def handle_tool(name: str, args: dict) -> dict:
    try:
        sheets = sheets_service()

        if name == "sheets_list":
            drive = drive_service()
            results = drive.files().list(
                q="mimeType='application/vnd.google-apps.spreadsheet'",
                pageSize=20,
                fields="files(id, name, modifiedTime)",
            ).execute()
            return {"result": results.get("files", [])}

        elif name == "sheets_read":
            sid = args["spreadsheet_id"]
            r = args.get("range", "Sheet1!A1:Z1000")
            result = sheets.spreadsheets().values().get(spreadsheetId=sid, range=r).execute()
            return {"result": {"rows": len(result.get("values", [])), "data": result.get("values", [])}}

        elif name == "sheets_write":
            sid = args["spreadsheet_id"]
            r = args["range"]
            vals = args["values"]
            body = {"values": vals}
            result = sheets.spreadsheets().values().update(
                spreadsheetId=sid, range=r,
                valueInputOption="USER_ENTERED", body=body,
            ).execute()
            return {"result": {"updated_cells": result.get("updatedCells", 0)}}

        elif name == "sheets_append":
            sid = args["spreadsheet_id"]
            r = args.get("range", "Sheet1!A:D")
            vals = args["values"]
            body = {"values": [vals]}
            result = sheets.spreadsheets().values().append(
                spreadsheetId=sid, range=r,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS", body=body,
            ).execute()
            return {"result": {"updated_cells": result.get("updates", {}).get("updatedCells", 0)}}

        elif name == "sheets_create":
            title = args.get("title", "New Sheet")
            spreadsheet = sheets.spreadsheets().create(
                body={"properties": {"title": title}}
            ).execute()
            return {"result": {
                "spreadsheet_id": spreadsheet["spreadsheetId"],
                "url": spreadsheet["spreadsheetUrl"],
                "title": spreadsheet["properties"]["title"],
            }}

        else:
            return {"error": {"code": -32601, "message": f"Unknown tool: {name}"}}

    except Exception as e:
        return {"error": {"code": -32000, "message": str(e), "data": traceback.format_exc()}}


def send(msg: dict):
    line = json.dumps(msg)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def main():
    # Send initialize response after receiving initialize request
    # MCP protocol: client sends initialize, server responds
    # Then client sends tools/list, server responds with tools
    # Then client sends tools/call with tool name and args

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            continue

        method = msg.get("method", "")
        msg_id = msg.get("id")

        if method == "initialize":
            send({
                "jsonrpc": "2.0", "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "google-sheets", "version": "1.0.0"},
                }
            })
            # Also send initialized notification per protocol
            send({"jsonrpc": "2.0", "method": "notifications/initialized"})

        elif method == "ping":
            send({"jsonrpc": "2.0", "id": msg_id, "result": {}})

        elif method == "tools/list":
            send({
                "jsonrpc": "2.0", "id": msg_id,
                "result": {"tools": TOOLS}
            })

        elif method == "tools/call":
            name = msg.get("params", {}).get("name", "")
            args = msg.get("params", {}).get("arguments", {})
            result = handle_tool(name, args)
            if "error" in result:
                send({"jsonrpc": "2.0", "id": msg_id, "error": result["error"]})
            else:
                send({
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result["result"], indent=2)}]
                    }
                })

        else:
            send({"jsonrpc": "2.0", "id": msg_id, "error": {
                "code": -32601, "message": f"Method not found: {method}"
            }})


if __name__ == "__main__":
    main()
