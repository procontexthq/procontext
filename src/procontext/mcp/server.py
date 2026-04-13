"""MCP server instance and tool registration.

Creates the FastMCP instance and delegates tool registration to each
tool package's ``register()`` function.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from procontext import __version__
from procontext.mcp.lifespan import lifespan
from procontext.mcp.prompt import SERVER_INSTRUCTIONS
from procontext.tools import read_outline, read_page, resolve_library, search_page

mcp = FastMCP("procontext", instructions=SERVER_INSTRUCTIONS, lifespan=lifespan)
# FastMCP doesn't expose a version kwarg — set it on the underlying Server
# so the MCP initialize handshake reports our version, not the SDK's.
mcp._mcp_server.version = __version__  # pyright: ignore[reportPrivateUsage]

resolve_library.register(mcp)
search_page.register(mcp)
read_outline.register(mcp)
read_page.register(mcp)
