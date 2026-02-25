"""Wire-level integration tests for MCP error envelope behavior."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def test_procontext_error_serializes_to_structured_tool_error(tmp_path: Path) -> None:
    """ProContextError should be returned as structured JSON in tool result text."""
    env = os.environ.copy()
    env["PROCONTEXT__CACHE__DB_PATH"] = str(tmp_path / "cache.db")

    proc = subprocess.Popen(
        [sys.executable, "-m", "procontext.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    assert proc.stdin is not None
    assert proc.stdout is not None
    assert proc.stderr is not None

    messages = [
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
                "arguments": {"query": ""},
            },
        },
    ]

    for message in messages:
        proc.stdin.write(json.dumps(message) + "\n")
    proc.stdin.close()

    stdout_lines = [line for line in proc.stdout.read().splitlines() if line.strip()]
    proc.stderr.read()  # Drain for clean process shutdown on all platforms
    proc.wait(timeout=10)

    responses = [json.loads(line) for line in stdout_lines]
    tool_response = next(response for response in responses if response.get("id") == 2)

    assert tool_response["result"]["isError"] is True

    text_payload = tool_response["result"]["content"][0]["text"]
    assert "Error executing tool" not in text_payload

    parsed = json.loads(text_payload)
    assert parsed["error"]["code"] == "INVALID_INPUT"
    assert parsed["error"]["recoverable"] is False
    assert "query must not be empty" in parsed["error"]["message"]
