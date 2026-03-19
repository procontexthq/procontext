"""Unit tests for the default CLI server command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from procontext.cli import cmd_serve
from procontext.config import Settings


def test_run_server_dispatches_http_transport() -> None:
    settings = Settings(server={"transport": "http"})
    fake_mcp = MagicMock()

    with (
        patch(
            "procontext.cli.cmd_serve.load_registry",
            return_value=([], "test-version"),
        ),
        patch("procontext.cli.cmd_serve.mcp", fake_mcp),
        patch("procontext.cli.cmd_serve._run_http_transport") as mock_run_http_transport,
    ):
        cmd_serve.run_server(settings)

    mock_run_http_transport.assert_called_once_with(fake_mcp, settings)
    fake_mcp.run.assert_not_called()


def test_run_server_dispatches_stdio_transport() -> None:
    settings = Settings(server={"transport": "stdio"})
    fake_mcp = MagicMock()

    with (
        patch(
            "procontext.cli.cmd_serve.load_registry",
            return_value=([], "test-version"),
        ),
        patch("procontext.cli.cmd_serve.mcp", fake_mcp),
        patch("procontext.cli.cmd_serve._run_http_transport") as mock_run_http_transport,
    ):
        cmd_serve.run_server(settings)

    mock_run_http_transport.assert_not_called()
    fake_mcp.run.assert_called_once_with()


def test_run_server_exits_when_registry_missing() -> None:
    settings = Settings(server={"transport": "stdio"})
    fake_mcp = MagicMock()

    with (
        patch("procontext.cli.cmd_serve.load_registry", return_value=None),
        patch("procontext.cli.cmd_serve.mcp", fake_mcp),
        patch("procontext.cli.cmd_serve._run_http_transport") as mock_run_http_transport,
        pytest.raises(SystemExit) as exc_info,
    ):
        cmd_serve.run_server(settings)

    assert exc_info.value.code == 1
    mock_run_http_transport.assert_not_called()
    fake_mcp.run.assert_not_called()
