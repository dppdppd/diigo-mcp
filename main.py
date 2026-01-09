#!/usr/bin/env python3
"""
Diigo MCP Server
Model Context Protocol server for Diigo bookmarking service
"""

import asyncio
import json
import logging
import sys
from typing import Dict, Any
from config import Config
import tools

# Configure logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


class DiigoMCPServer:
    """JSON-RPC MCP Server for Diigo API"""

    def __init__(self):
        self.version = "0.1.0"
        self.tools_list = [
            {
                "name": "diigo_list_bookmarks",
                "description": "List bookmarks with optional filters (tags, user, sort order). Omit count to auto-paginate all.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user": {
                            "type": "string",
                            "description": "Username (defaults to configured user)",
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number to fetch (omit for all with auto-pagination)",
                        },
                        "start": {
                            "type": "integer",
                            "default": 0,
                            "description": "Start offset",
                        },
                        "sort": {
                            "type": "integer",
                            "enum": [0, 1, 2, 3],
                            "default": 1,
                            "description": "0=created, 1=updated, 2=popularity, 3=hot",
                        },
                        "tags": {
                            "type": "string",
                            "description": "Comma-separated tags to filter",
                        },
                        "filter": {
                            "type": "string",
                            "enum": ["all", "public"],
                            "default": "all",
                            "description": "Filter by visibility",
                        },
                        "list_name": {
                            "type": "string",
                            "description": "Filter by list name",
                        },
                    },
                },
            },
            {
                "name": "diigo_search_bookmarks",
                "description": "Search bookmarks by title/description query. Uses client-side filtering.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (matches title/description)",
                        },
                        "tags": {
                            "type": "string",
                            "description": "Comma-separated tags to filter",
                        },
                        "filter": {
                            "type": "string",
                            "enum": ["all", "public"],
                            "default": "all",
                        },
                        "user": {
                            "type": "string",
                            "description": "Username (defaults to configured user)",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "diigo_get_bookmark",
                "description": "Get a single bookmark by URL with full details including annotations",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Bookmark URL to find",
                        },
                        "user": {
                            "type": "string",
                            "description": "Username (defaults to configured user)",
                        },
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "diigo_create_bookmark",
                "description": "Create a new bookmark",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Bookmark URL"},
                        "title": {"type": "string", "description": "Bookmark title"},
                        "desc": {
                            "type": "string",
                            "default": "",
                            "description": "Description",
                        },
                        "tags": {
                            "type": "string",
                            "default": "",
                            "description": "Comma-separated tags",
                        },
                        "shared": {
                            "type": "boolean",
                            "default": False,
                            "description": "Public (true) or private (false)",
                        },
                        "read_later": {
                            "type": "boolean",
                            "default": False,
                            "description": "Mark as unread",
                        },
                    },
                    "required": ["url", "title"],
                },
            },
            {
                "name": "diigo_update_bookmark",
                "description": "Update an existing bookmark. Uses merge to preserve unmodified fields.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Bookmark URL (identifier)",
                        },
                        "title": {"type": "string", "description": "New title"},
                        "desc": {"type": "string", "description": "New description"},
                        "tags": {
                            "type": "string",
                            "description": "New tags (comma-separated)",
                        },
                        "shared": {
                            "type": "boolean",
                            "description": "New sharing status",
                        },
                        "read_later": {
                            "type": "boolean",
                            "description": "New read_later status",
                        },
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "diigo_delete_bookmark",
                "description": "Delete a bookmark by URL",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Bookmark URL"},
                        "title": {
                            "type": "string",
                            "description": "Bookmark title (auto-fetched if not provided)",
                        },
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "diigo_get_recent_bookmarks",
                "description": "Get recently updated bookmarks",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "count": {
                            "type": "integer",
                            "default": 50,
                            "description": "Number to fetch",
                        },
                        "user": {
                            "type": "string",
                            "description": "Username (defaults to configured user)",
                        },
                    },
                },
            },
            {
                "name": "diigo_get_annotations",
                "description": "Get annotations (highlights and comments) for a specific bookmark",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Bookmark URL"},
                        "user": {
                            "type": "string",
                            "description": "Username (defaults to configured user)",
                        },
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "diigo_bulk_create_bookmarks",
                "description": "Create multiple bookmarks with rate limiting",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bookmarks": {
                            "type": "array",
                            "description": "Array of bookmark objects",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "url": {"type": "string"},
                                    "title": {"type": "string"},
                                    "desc": {"type": "string"},
                                    "tags": {"type": "string"},
                                    "shared": {"type": "boolean"},
                                    "read_later": {"type": "boolean"},
                                },
                                "required": ["url", "title"],
                            },
                        },
                        "delay": {
                            "type": "number",
                            "default": 0.5,
                            "description": "Delay between requests in seconds",
                        },
                    },
                    "required": ["bookmarks"],
                },
            },
        ]

    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming JSON-RPC message"""
        method = message.get("method")
        msg_id = message.get("id")
        params = message.get("params", {})

        try:
            if method == "initialize":
                return await self.handle_initialize(msg_id, params)
            elif method == "tools/list":
                return await self.handle_list_tools(msg_id)
            elif method == "tools/call":
                return await self.handle_call_tool(msg_id, params)
            else:
                return self.error_response(
                    msg_id, -32601, f"Method not found: {method}"
                )

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            return self.error_response(msg_id, -32603, f"Internal error: {str(e)}")

    async def handle_initialize(
        self, msg_id: int, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle initialize request"""
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "diigo-mcp-server", "version": self.version},
            },
        }

    async def handle_list_tools(self, msg_id: int) -> Dict[str, Any]:
        """Handle tools/list request"""
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": self.tools_list}}

    async def handle_call_tool(
        self, msg_id: int, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle tools/call request"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        logger.info(f"Calling tool: {tool_name} with args: {arguments}")

        try:
            # Route to appropriate tool function
            if tool_name == "diigo_list_bookmarks":
                result = await tools.list_bookmarks_tool(**arguments)
            elif tool_name == "diigo_search_bookmarks":
                result = await tools.search_bookmarks_tool(**arguments)
            elif tool_name == "diigo_get_bookmark":
                result = await tools.get_bookmark_tool(**arguments)
            elif tool_name == "diigo_create_bookmark":
                result = await tools.create_bookmark_tool(**arguments)
            elif tool_name == "diigo_update_bookmark":
                result = await tools.update_bookmark_tool(**arguments)
            elif tool_name == "diigo_delete_bookmark":
                result = await tools.delete_bookmark_tool(**arguments)
            elif tool_name == "diigo_get_recent_bookmarks":
                result = await tools.get_recent_bookmarks_tool(**arguments)
            elif tool_name == "diigo_get_annotations":
                result = await tools.get_annotations_tool(**arguments)
            elif tool_name == "diigo_bulk_create_bookmarks":
                result = await tools.bulk_create_bookmarks_tool(**arguments)
            else:
                return self.error_response(msg_id, -32602, f"Unknown tool: {tool_name}")

            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"content": [{"type": "text", "text": result}]},
            }

        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}", exc_info=True)
            return self.error_response(msg_id, -32603, f"Tool error: {str(e)}")

    def error_response(self, msg_id: int, code: int, message: str) -> Dict[str, Any]:
        """Create JSON-RPC error response"""
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": code, "message": message},
        }

    async def run(self):
        """Run the MCP server (stdio transport)"""
        logger.info("Diigo MCP Server starting...")

        # Validate configuration
        try:
            Config.validate()
            logger.info("Configuration validated successfully")
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)

        # Read from stdin, write to stdout
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )

                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                # Parse JSON-RPC message
                message = json.loads(line)

                # Handle message
                response = await self.handle_message(message)

                # Write response to stdout
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                continue
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                continue


async def main():
    """Main entry point"""
    server = DiigoMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
