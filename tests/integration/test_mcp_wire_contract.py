"""Wire-level integration tests for MCP transport contract."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
from contextlib import closing
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def _run_mcp_exchange(env: dict[str, str], messages: list[dict]) -> list[dict]:

    proc = subprocess.Popen(
        [sys.executable, "-m", "procontext.mcp.startup"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    assert proc.stdin is not None
    assert proc.stdout is not None
    assert proc.stderr is not None

    for message in messages:
        proc.stdin.write(json.dumps(message) + "\n")
    proc.stdin.flush()

    # Read responses line-by-line until every request ID has been answered.
    #
    # The MCP stdio transport uses zero-capacity anyio streams, so the receive
    # loop dispatches async tool handlers (e.g. aiosqlite lookups) via
    # anyio.start_soon() and immediately continues reading the remaining stdin
    # messages.  If we close stdin before those handlers finish, the receive
    # loop exits and tears down the write stream, silently dropping in-flight
    # responses.  Reading first keeps stdin open until the handlers complete.
    expected_ids = frozenset(msg["id"] for msg in messages if "id" in msg)
    responses: list[dict] = []
    seen_ids: set = set()
    while seen_ids < expected_ids:
        line = proc.stdout.readline()
        if not line:  # server exited before answering all requests
            break
        stripped = line.strip()
        if stripped:
            resp = json.loads(stripped)
            responses.append(resp)
            rid = resp.get("id")
            if rid is not None:
                seen_ids.add(rid)

    # Ask the server to shut down gracefully now that we have all responses.
    try:
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 9999, "method": "shutdown"}) + "\n")
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "exit"}) + "\n")
    except OSError:
        pass  # server already exited; write to closed pipe is expected
    proc.stdin.close()

    proc.stderr.read()  # drain for reliable process shutdown
    proc.wait(timeout=10)
    proc.stdout.close()
    proc.stderr.close()

    return responses


def _seed_page_cache(
    tmp_path: Path,
    *,
    url: str,
    content: str,
    outline: str,
) -> None:
    db_path = tmp_path / "cache.db"
    url_hash = hashlib.sha256(url.encode()).hexdigest()
    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=24)

    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS page_cache (
                url_hash           TEXT PRIMARY KEY,
                url                TEXT NOT NULL UNIQUE,
                content            TEXT NOT NULL,
                outline            TEXT NOT NULL DEFAULT '',
                discovered_domains TEXT NOT NULL DEFAULT '',
                fetched_at         TEXT NOT NULL,
                expires_at         TEXT NOT NULL,
                last_checked_at    TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO page_cache
            (url_hash, url, content, outline, fetched_at, expires_at, last_checked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                url_hash,
                url,
                content,
                outline,
                now.isoformat(),
                expires_at.isoformat(),
                now.isoformat(),
            ),
        )
        conn.commit()


def test_initialize_and_tools_list_contract(subprocess_env: dict[str, str]) -> None:
    responses = _run_mcp_exchange(
        subprocess_env,
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "0"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ],
    )

    init_response = next(response for response in responses if response.get("id") == 1)
    init_result = init_response["result"]
    assert init_result["protocolVersion"] in {"2025-11-25", "2025-03-26"}
    assert init_result["serverInfo"]["name"] == "procontext"
    assert "tools" in init_result["capabilities"]
    assert "instructions" in init_result
    instructions = init_result["instructions"]
    # Verify key workflow elements are documented
    assert "resolve_library" in instructions
    assert "index_url" in instructions
    assert "full_docs_url" in instructions

    tools_response = next(response for response in responses if response.get("id") == 2)
    tools = tools_response["result"]["tools"]
    tools_by_name = {tool["name"]: tool for tool in tools}

    assert "resolve_library" in tools_by_name
    assert "read_page" in tools_by_name
    assert "get_library_index" not in tools_by_name

    resolve_schema = tools_by_name["resolve_library"]["inputSchema"]
    assert resolve_schema["type"] == "object"
    assert "query" in resolve_schema["required"]

    read_page_schema = tools_by_name["read_page"]["inputSchema"]
    assert read_page_schema["type"] == "object"
    assert "url" in read_page_schema["required"]
    assert read_page_schema["properties"]["offset"]["type"] == "integer"
    assert read_page_schema["properties"]["limit"]["type"] == "integer"
    assert read_page_schema["properties"]["before"]["type"] == "integer"
    assert read_page_schema["properties"]["include_outline"]["type"] == "boolean"

    read_outline_schema = tools_by_name["read_outline"]["inputSchema"]
    assert read_outline_schema["type"] == "object"
    assert read_outline_schema["properties"]["offset"]["type"] == "integer"
    assert read_outline_schema["properties"]["limit"]["type"] == "integer"
    assert read_outline_schema["properties"]["before"]["type"] == "integer"

    search_page_schema = tools_by_name["search_page"]["inputSchema"]
    assert search_page_schema["type"] == "object"
    assert search_page_schema["properties"]["target"]["enum"] == ["content", "outline"]

    # Each tool must advertise its outputSchema.
    for tool_name in ("resolve_library", "read_page"):
        tool = tools_by_name[tool_name]
        assert "outputSchema" in tool, f"{tool_name} missing outputSchema"
        assert tool["outputSchema"]["type"] == "object"

    resolve_output_schema = tools_by_name["resolve_library"]["outputSchema"]
    assert "matches" in resolve_output_schema["properties"]
    assert "hint" in resolve_output_schema["properties"]
    resolve_hint_schema = resolve_output_schema["$defs"]["ResolveHint"]
    assert resolve_hint_schema["properties"]["code"]["enum"] == [
        "UNSUPPORTED_QUERY_SYNTAX",
        "FUZZY_FALLBACK_USED",
    ]
    assert "outline" in tools_by_name["read_page"]["outputSchema"]["properties"]
    assert tools_by_name["read_page"]["outputSchema"]["properties"]["outline"]["anyOf"] == [
        {"type": "string"},
        {"type": "null"},
    ]


def test_resolve_library_wire_success(subprocess_env: dict[str, str]) -> None:
    responses = _run_mcp_exchange(
        subprocess_env,
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "0"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "resolve_library",
                    "arguments": {"query": "langchain-openai"},
                },
            },
        ],
    )

    tool_response = next(response for response in responses if response.get("id") == 2)
    assert tool_response["result"]["isError"] is False

    payload = json.loads(tool_response["result"]["content"][0]["text"])
    assert "matches" in payload
    assert payload["matches"][0]["library_id"] == "langchain"


def test_resolve_library_wire_unsupported_input_hint(subprocess_env: dict[str, str]) -> None:
    responses = _run_mcp_exchange(
        subprocess_env,
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "0"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "resolve_library",
                    "arguments": {"query": "langchain[openai]>=0.3"},
                },
            },
        ],
    )

    tool_response = next(response for response in responses if response.get("id") == 2)
    assert tool_response["result"]["isError"] is False

    payload = json.loads(tool_response["result"]["content"][0]["text"])
    assert payload["matches"] == []
    assert payload["hint"] == {
        "code": "UNSUPPORTED_QUERY_SYNTAX",
        "message": (
            "Provide only the published package name, library ID, display name, "
            "or alias without version specifiers, extras, tags, or source URLs."
        ),
    }


def test_read_page_wire_success_from_cache(tmp_path: Path, subprocess_env: dict[str, str]) -> None:
    url = "https://python.langchain.com/docs/concepts/cached.md"
    content = "# Title\n\n## Section\nLine A\nLine B"
    outline = "1:# Title\n3:## Section"
    _seed_page_cache(tmp_path, url=url, content=content, outline=outline)

    responses = _run_mcp_exchange(
        subprocess_env,
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "0"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "read_page",
                    "arguments": {"url": url, "offset": 3, "limit": 2, "before": 2},
                },
            },
        ],
    )

    tool_response = next(response for response in responses if response.get("id") == 2)
    assert tool_response["result"]["isError"] is False

    payload = json.loads(tool_response["result"]["content"][0]["text"])
    assert payload["url"] == url
    assert payload["offset"] == 1
    assert payload["limit"] == 2
    assert payload["outline"] == outline
    assert payload["total_lines"] == 5
    assert payload["content"] == "# Title\n\n## Section\nLine A"


def test_read_page_wire_include_outline_false_returns_null(
    tmp_path: Path, subprocess_env: dict[str, str]
) -> None:
    url = "https://python.langchain.com/docs/concepts/cached.md"
    content = "# Title\n\n## Section\nLine A\nLine B"
    outline = "1:# Title\n3:## Section"
    _seed_page_cache(tmp_path, url=url, content=content, outline=outline)

    responses = _run_mcp_exchange(
        subprocess_env,
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "0"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "read_page",
                    "arguments": {
                        "url": url,
                        "offset": 1,
                        "limit": 2,
                        "include_outline": False,
                    },
                },
            },
        ],
    )

    tool_response = next(response for response in responses if response.get("id") == 2)
    assert tool_response["result"]["isError"] is False

    payload = json.loads(tool_response["result"]["content"][0]["text"])
    assert payload["outline"] is None


def test_read_page_wire_error_envelope(subprocess_env: dict[str, str]) -> None:
    responses = _run_mcp_exchange(
        subprocess_env,
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "0"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "read_page",
                    "arguments": {"url": "https://evil.example.com/docs.md"},
                },
            },
        ],
    )

    tool_response = next(response for response in responses if response.get("id") == 2)
    assert tool_response["result"]["isError"] is True

    text = tool_response["result"]["content"][0]["text"]
    assert "URL_NOT_ALLOWED" in text


def test_server_exits_cleanly_when_registry_missing(tmp_path: Path) -> None:
    """Server must exit with code 1 and a clean error message when the registry is
    absent. Before the fix, sys.exit(1) inside the async lifespan was wrapped in
    a BaseExceptionGroup by anyio, causing an ugly crash traceback instead of a
    clean exit."""
    import os

    env = os.environ.copy()
    env["PROCONTEXT__SERVER__TRANSPORT"] = "stdio"
    env["PROCONTEXT__DATA_DIR"] = str(tmp_path)
    env["PROCONTEXT__CACHE__DB_PATH"] = str(tmp_path / "cache.db")

    proc = subprocess.run(
        [sys.executable, "-m", "procontext.mcp.startup"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )

    assert proc.returncode == 1
    assert "procontext setup" in proc.stderr
    assert "procontext doctor --fix" in proc.stderr
    # Must NOT crash with an exception group traceback.
    assert "ExceptionGroup" not in proc.stderr
    assert "BaseExceptionGroup" not in proc.stderr
