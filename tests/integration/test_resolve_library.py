"""Integration tests for the resolve_library tool handler."""

from __future__ import annotations

import aiosqlite
import httpx
import pytest

from procontext.cache import Cache
from procontext.config import Settings
from procontext.errors import ErrorCode, ProContextError
from procontext.fetch.security import build_allowlist
from procontext.fetch.service import Fetcher
from procontext.models.registry import PackageEntry, RegistryEntry
from procontext.registry import build_indexes
from procontext.state import AppState
from procontext.tools.resolve_library import handle


class TestResolveLibraryHandler:
    """Full handler pipeline tests for resolve_library."""

    async def test_valid_query_returns_match(self, app_state: AppState) -> None:
        # "langchain" is both a package name and a library ID — Step 1 wins
        result = await handle("langchain", app_state)
        assert len(result["matches"]) == 1
        assert result["hint"] is None
        match = result["matches"][0]
        assert match["library_id"] == "langchain"
        assert match["matched_via"] == "package_name"
        assert match["relevance"] == 1.0

    async def test_output_contains_all_required_fields(self, app_state: AppState) -> None:
        result = await handle("pydantic", app_state)
        assert set(result.keys()) == {"matches", "hint"}
        match = result["matches"][0]
        assert set(match.keys()) == {
            "library_id",
            "name",
            "description",
            "index_url",
            "full_docs_url",
            "packages",
            "matched_via",
            "relevance",
        }

    async def test_no_match_returns_empty_list(self, app_state: AppState) -> None:
        result = await handle("xyzzy-nonexistent", app_state)
        assert result["matches"] == []
        assert result["hint"] is None

    async def test_empty_query_raises_invalid_input(self, app_state: AppState) -> None:
        with pytest.raises(ProContextError) as exc_info:
            await handle("", app_state)
        assert exc_info.value.code == ErrorCode.INVALID_INPUT
        assert exc_info.value.recoverable is False

    async def test_query_over_limit_raises_invalid_input(self, app_state: AppState) -> None:
        with pytest.raises(ProContextError) as exc_info:
            await handle("a" * 501, app_state)
        assert exc_info.value.code == ErrorCode.INVALID_INPUT
        assert exc_info.value.recoverable is False

    async def test_package_name_resolves_to_library(self, app_state: AppState) -> None:
        result = await handle("langchain-openai", app_state)
        assert result["matches"][0]["library_id"] == "langchain"
        assert result["matches"][0]["matched_via"] == "package_name"

    async def test_dependency_specifier_returns_unsupported_query_syntax_hint(
        self, app_state: AppState
    ) -> None:
        result = await handle("langchain[openai]>=0.3", app_state)
        assert result["matches"] == []
        assert result["hint"] == {
            "code": "UNSUPPORTED_QUERY_SYNTAX",
            "message": (
                "Provide only the published package name, library ID, display name, "
                "or alias without version specifiers, extras, tags, or source URLs."
            ),
        }

    async def test_packages_in_response(self, app_state: AppState) -> None:
        result = await handle("langchain", app_state)
        packages = result["matches"][0]["packages"]
        assert len(packages) == 1
        pkg = packages[0]
        assert pkg["ecosystem"] == "pypi"
        assert "python" in pkg["languages"]
        assert "langchain" in pkg["package_names"]


@pytest.fixture()
async def mixed_state() -> AppState:
    """AppState with mixed-ecosystem packages for resolver edge cases."""
    entries = [
        RegistryEntry(
            id="langchain",
            name="LangChain",
            description="Framework for building LLM-powered applications.",
            packages=[
                PackageEntry(
                    ecosystem="pypi",
                    languages=["python"],
                    package_names=["langchain", "langchain-openai"],
                ),
            ],
            aliases=["lang-chain"],
            llms_txt_url="https://python.langchain.com/llms.txt",
        ),
        RegistryEntry(
            id="babel-core",
            name="Babel Core",
            description="JavaScript compiler core package.",
            packages=[
                PackageEntry(
                    ecosystem="npm",
                    languages=["javascript", "typescript"],
                    package_names=["@babel/core"],
                ),
            ],
            llms_txt_url="https://babeljs.io/llms.txt",
        ),
        RegistryEntry(
            id="openai-python",
            name="OpenAI Python",
            description="Official OpenAI SDK for Python.",
            packages=[
                PackageEntry(
                    ecosystem="pypi",
                    languages=["python"],
                    package_names=["openai"],
                ),
            ],
            llms_txt_url="https://openai.github.io/openai-python/llms.txt",
        ),
        RegistryEntry(
            id="openai-js",
            name="OpenAI JavaScript",
            description="Official OpenAI SDK for JavaScript and TypeScript.",
            packages=[
                PackageEntry(
                    ecosystem="npm",
                    languages=["javascript", "typescript"],
                    package_names=["openai"],
                ),
            ],
            llms_txt_url="https://openai.github.io/openai-node/llms.txt",
        ),
    ]
    indexes = build_indexes(entries)
    async with aiosqlite.connect(":memory:") as db:
        cache = Cache(db)
        await cache.init_db()
        async with httpx.AsyncClient() as client:
            fetcher = Fetcher(client)
            allowlist = build_allowlist(entries)
            state = AppState(
                settings=Settings(),
                indexes=indexes,
                registry_version="test",
                http_client=client,
                cache=cache,
                fetcher=fetcher,
                allowlist=allowlist,
            )
            yield state


class TestResolveLibraryMixedHandler:
    async def test_exact_name_match_returns_name_match_type(self, mixed_state: AppState) -> None:
        result = await handle("  Babel   Core  ", mixed_state)

        assert result["matches"][0]["library_id"] == "babel-core"
        assert result["matches"][0]["matched_via"] == "name"
        assert result["hint"] is None

    async def test_scoped_npm_package_with_version_returns_hint(
        self, mixed_state: AppState
    ) -> None:
        result = await handle("@babel/core@^7.26.0", mixed_state)

        assert result["matches"] == []
        assert result["hint"] == {
            "code": "UNSUPPORTED_QUERY_SYNTAX",
            "message": (
                "Provide only the published package name, library ID, display name, "
                "or alias without version specifiers, extras, tags, or source URLs."
            ),
        }

    async def test_npm_dist_tag_returns_unsupported_query_syntax_hint(
        self, mixed_state: AppState
    ) -> None:
        result = await handle("@babel/core@latest", mixed_state)

        assert result["matches"] == []
        assert result["hint"] == {
            "code": "UNSUPPORTED_QUERY_SYNTAX",
            "message": (
                "Provide only the published package name, library ID, display name, "
                "or alias without version specifiers, extras, tags, or source URLs."
            ),
        }

    async def test_shared_exact_package_identifier_returns_multiple_matches(
        self, mixed_state: AppState
    ) -> None:
        result = await handle("openai", mixed_state)

        assert {match["library_id"] for match in result["matches"]} == {
            "openai-python",
            "openai-js",
        }
        assert {match["matched_via"] for match in result["matches"]} == {"package_name"}
        assert result["hint"] is None

    async def test_github_like_query_returns_unsupported_query_syntax_hint(
        self, mixed_state: AppState
    ) -> None:
        result = await handle("https://github.com/openai/openai-python", mixed_state)

        assert result["matches"] == []
        assert result["hint"] == {
            "code": "UNSUPPORTED_QUERY_SYNTAX",
            "message": (
                "Provide only the published package name, library ID, display name, "
                "or alias without version specifiers, extras, tags, or source URLs."
            ),
        }

    async def test_fuzzy_match_returns_fallback_hint(self, mixed_state: AppState) -> None:
        result = await handle("langchian", mixed_state)

        assert result["matches"][0]["library_id"] == "langchain"
        assert result["matches"][0]["matched_via"] == "fuzzy"
        assert result["hint"] == {
            "code": "FUZZY_FALLBACK_USED",
            "message": "No exact match was found. Verify the fuzzy match before continuing.",
        }

    async def test_language_sort_reorders_multiple_matches_without_filtering(
        self, mixed_state: AppState
    ) -> None:
        result = await handle("openai", mixed_state, language="python")

        assert [match["library_id"] for match in result["matches"]] == [
            "openai-python",
            "openai-js",
        ]
        assert {match["library_id"] for match in result["matches"]} == {
            "openai-python",
            "openai-js",
        }
        assert all(match["packages"] for match in result["matches"])


@pytest.fixture()
async def multilang_state() -> AppState:
    """AppState with a multi-language library for language sorting tests."""
    entries = [
        RegistryEntry(
            id="openai",
            name="OpenAI",
            description="OpenAI API client.",
            packages=[
                PackageEntry(
                    ecosystem="npm",
                    languages=["javascript", "typescript"],
                    package_names=["openai"],
                ),
                PackageEntry(
                    ecosystem="pypi",
                    languages=["python"],
                    package_names=["openai"],
                ),
            ],
            llms_txt_url="https://platform.openai.com/llms.txt",
        ),
        RegistryEntry(
            id="numpy",
            name="NumPy",
            description="Numerical computing library.",
            packages=[
                PackageEntry(
                    ecosystem="pypi",
                    languages=["python"],
                    package_names=["numpy"],
                ),
            ],
            llms_txt_url="https://numpy.org/llms.txt",
        ),
    ]
    indexes = build_indexes(entries)
    async with aiosqlite.connect(":memory:") as db:
        cache = Cache(db)
        await cache.init_db()
        async with httpx.AsyncClient() as client:
            fetcher = Fetcher(client)
            allowlist = build_allowlist(entries)
            state = AppState(
                settings=Settings(),
                indexes=indexes,
                registry_version="test",
                http_client=client,
                cache=cache,
                fetcher=fetcher,
                allowlist=allowlist,
            )
            yield state


class TestLanguageSorting:
    """Tests for the optional language sorting parameter."""

    async def test_language_sorts_packages_within_match(self, multilang_state: AppState) -> None:
        result = await handle("openai", multilang_state, language="python")
        packages = result["matches"][0]["packages"]
        # Python package entry should sort to front
        assert packages[0]["languages"] == ["python"]
        assert packages[1]["languages"] == ["javascript", "typescript"]

    async def test_language_none_preserves_original_order(self, multilang_state: AppState) -> None:
        result = await handle("openai", multilang_state)
        packages = result["matches"][0]["packages"]
        # Original order: npm first, then pypi (as defined in fixture)
        assert packages[0]["ecosystem"] == "npm"
        assert packages[1]["ecosystem"] == "pypi"

    async def test_language_no_match_returns_all_unchanged(self, multilang_state: AppState) -> None:
        result = await handle("openai", multilang_state, language="rust")
        packages = result["matches"][0]["packages"]
        # No rust packages — order unchanged, nothing omitted
        assert len(packages) == 2

    async def test_language_empty_string_treated_as_none(self, multilang_state: AppState) -> None:
        result = await handle("openai", multilang_state, language="  ")
        packages = result["matches"][0]["packages"]
        # Whitespace-only → None, original order preserved
        assert packages[0]["ecosystem"] == "npm"
