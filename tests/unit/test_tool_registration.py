"""Verify that all ProContext tools are registered with the expected names and parameters."""

from __future__ import annotations

from procontext.mcp.server import mcp

EXPECTED_TOOLS = {
    "resolve_library": {"language", "query"},
    "search_page": {
        "case_mode",
        "max_results",
        "mode",
        "offset",
        "query",
        "target",
        "url",
        "whole_word",
    },
    "read_outline": {"before", "limit", "offset", "url"},
    "read_page": {"before", "include_outline", "limit", "offset", "url"},
}


def test_all_tools_registered() -> None:
    tools = mcp._tool_manager._tools  # pyright: ignore[reportPrivateUsage]
    assert set(tools.keys()) == set(EXPECTED_TOOLS.keys())


def test_tool_parameters() -> None:
    tools = mcp._tool_manager._tools  # pyright: ignore[reportPrivateUsage]
    for name, expected_params in EXPECTED_TOOLS.items():
        tool = tools[name]
        params = tool.parameters
        props = params.get("properties", {}) if isinstance(params, dict) else {}
        actual_params = set(props.keys())
        assert actual_params == expected_params, (
            f"Tool '{name}' has params {actual_params}, expected {expected_params}"
        )


def test_tool_descriptions_are_nonempty() -> None:
    tools = mcp._tool_manager._tools  # pyright: ignore[reportPrivateUsage]
    for name, tool in tools.items():
        assert tool.description, f"Tool '{name}' has an empty description"
