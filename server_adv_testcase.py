"""
POC Testcase Generator - MCP Server
Jalankan: python server.py
"""

import json
import asyncio
from pathlib import Path
from typing import Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types as mcp_types

from parser import read_poc_document
from generator import generate_testcases_with_format
from templates import Testcase

app = Server("poc-testcase-generator")


# ─── Tools ────────────────────────────────────────────────────────────────────

@app.list_tools()
async def list_tools() -> list[mcp_types.Tool]:
    return [
        mcp_types.Tool(
            name="read_poc_document",
            description="Membaca dan mem-parse file POC (markdown/txt) menjadi struktur section.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path ke file POC (misal: ./docs/poc-api-gateway.md)",
                    }
                },
                "required": ["file_path"],
            },
        ),
        mcp_types.Tool(
            name="generate_testcases",
            description=(
                "Generate test cases dari dokumen POC. "
                "Menghasilkan test case berbasis rule-engine (functional, boundary, "
                "exception, integration)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path ke file POC.",
                    },
                    "max_per_section": {
                        "type": "integer",
                        "default": 3,
                        "description": "Maksimal test case per section (default 3).",
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["json", "markdown", "table"],
                        "default": "markdown",
                        "description": "Format output.",
                    },
                },
                "required": ["file_path"],
            },
        ),
        mcp_types.Tool(
            name="list_poc_documents",
            description="List semua file POC yang tersedia di directory tertentu.",
            inputSchema={
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "default": "./docs",
                        "description": "Directory yang akan di-scan.",
                    }
                },
            },
        ),
    ]


# ─── Handlers ─────────────────────────────────────────────────────────────────

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[mcp_types.TextContent]:
    if name == "read_poc_document":
        return await _handle_read(arguments)
    elif name == "generate_testcases":
        return await _handle_generate(arguments)
    elif name == "list_poc_documents":
        return await _handle_list(arguments)
    else:
        return [mcp_types.TextContent(type="text", text=f"Unknown tool: {name}")]


async def _handle_read(args: dict) -> list[mcp_types.TextContent]:
    path = args["file_path"]
    try:
        doc = read_poc_document(path)
    except FileNotFoundError as e:
        return [mcp_types.TextContent(type="text", text=f"ERROR: {e}")]

    summary = {
        "title": doc.title,
        "total_sections": sum(1 for _ in doc.sections),
        "sections": [s.heading for s in doc.sections],
    }
    return [mcp_types.TextContent(
        type="text",
        text=json.dumps(summary, indent=2, ensure_ascii=False),
    )]


async def _handle_generate(args: dict) -> list[mcp_types.TextContent]:
    path = args["file_path"]
    max_per = int(args.get("max_per_section", 3))
    fmt = args.get("output_format", "markdown")

    try:
        doc = read_poc_document(path)
    except FileNotFoundError as e:
        return [mcp_types.TextContent(type="text", text=f"ERROR: {e}")]

    testcases = generate_testcases_with_format(doc, max_per_section=max_per, fmt=fmt)

    return [mcp_types.TextContent(type="text", text=testcases)]


async def _handle_list(args: dict) -> list[mcp_types.TextContent]:
    directory = args.get("directory", "./docs")
    path = Path(directory)

    if not path.exists() or not path.is_dir():
        return [mcp_types.TextContent(
            type="text",
            text=f"ERROR: Directory tidak ditemukan: {directory}",
        )]

    files = sorted(
        str(p)
        for p in path.iterdir()
        if p.is_file() and p.suffix.lower() in {".md", ".txt"}
    )
    result = {"directory": str(path), "files": files}
    return [mcp_types.TextContent(
        type="text",
        text=json.dumps(result, indent=2, ensure_ascii=False),
    )]


# ─── Entrypoint ───────────────────────────────────────────────────────────────

async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())