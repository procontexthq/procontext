"""Shared test fixtures for the procontext test suite."""

from __future__ import annotations

import sys

import pytest
import structlog

from procontext.models.registry import PackageEntry, RegistryEntry, RegistryIndexes
from procontext.registry import build_indexes

# Configure structlog to write to stderr, matching production behavior.
# Without this, structlog defaults to stdout which would corrupt the MCP
# JSON-RPC stream in stdio mode.
structlog.configure(
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
)


@pytest.fixture()
def sample_entries() -> list[RegistryEntry]:
    """Minimal registry entries for testing resolution logic."""
    return [
        RegistryEntry(
            id="langchain",
            name="LangChain",
            description="Framework for building LLM-powered applications.",
            packages=[
                PackageEntry(
                    ecosystem="pypi",
                    languages=["python"],
                    package_names=["langchain", "langchain-openai", "langchain-core"],
                    repo_url="https://github.com/langchain-ai/langchain",
                ),
            ],
            aliases=["lang-chain"],
            llms_txt_url="https://python.langchain.com/llms.txt",
        ),
        RegistryEntry(
            id="pydantic",
            name="Pydantic",
            description="Data validation using Python type annotations.",
            packages=[
                PackageEntry(
                    ecosystem="pypi",
                    languages=["python"],
                    package_names=["pydantic", "pydantic-settings"],
                    repo_url="https://github.com/pydantic/pydantic",
                ),
            ],
            aliases=[],
            llms_txt_url="https://docs.pydantic.dev/llms.txt",
        ),
    ]


@pytest.fixture()
def indexes(sample_entries: list[RegistryEntry]) -> RegistryIndexes:
    """Pre-built indexes from sample_entries."""
    return build_indexes(sample_entries)
