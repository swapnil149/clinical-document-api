"""Minimal MCP server (stdio) exposing the existing document tools.

Run with: python -m app.mcp_server

stdout is reserved for MCP protocol frames, so anything the shared tool
functions print() is redirected to stderr while they run.
"""
import contextlib
import logging
import sys

from dotenv import load_dotenv

# Load .env before app.database reads DATABASE_URL.
load_dotenv()

from mcp.server.mcpserver import MCPServer  # noqa: E402

from app.tools import get_document as _get_document  # noqa: E402
from app.tools import search_documents as _search_documents  # noqa: E402

logging.basicConfig(stream=sys.stderr)

mcp = MCPServer("clinical-document-api")


@mcp.tool()
def get_document(document_id: int) -> str:
    """Retrieve a clinical document from the database using its document ID."""
    with contextlib.redirect_stdout(sys.stderr):
        return _get_document(document_id)


@mcp.tool()
def search_documents(question: str) -> str:
    """Search clinical documents for information relevant to a question."""
    with contextlib.redirect_stdout(sys.stderr):
        return _search_documents(question)


if __name__ == "__main__":
    mcp.run(transport="stdio")
