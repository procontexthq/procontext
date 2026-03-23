"""Unit tests for procontext.resolver."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from procontext.models.tools import (
    ReadOutlineInput,
    ReadPageInput,
    ResolveLibraryInput,
    SearchPageInput,
)
from procontext.resolver import resolve_library

if TYPE_CHECKING:
    from procontext.models.registry import RegistryIndexes


# ---------------------------------------------------------------------------
# resolve_library
# ---------------------------------------------------------------------------


class TestResolveLibraryStep1PackageName:
    """Step 1: Exact package name match."""

    def test_exact_pypi_package(self, indexes: RegistryIndexes) -> None:
        matches = resolve_library("langchain-openai", indexes)
        assert len(matches) == 1
        assert matches[0].library_id == "langchain"
        assert matches[0].matched_via == "package_name"
        assert matches[0].relevance == 1.0

    def test_monorepo_package(self, indexes: RegistryIndexes) -> None:
        """Monorepo sub-package resolves to the parent library."""
        matches = resolve_library("langchain-core", indexes)
        assert len(matches) == 1
        assert matches[0].library_id == "langchain"
        assert matches[0].matched_via == "package_name"

    def test_case_insensitive(self, indexes: RegistryIndexes) -> None:
        """Package lookup remains case-insensitive."""
        matches = resolve_library("Pydantic-Settings", indexes)
        assert len(matches) == 1
        assert matches[0].library_id == "pydantic"

    def test_dependency_syntax_is_not_rewritten_for_package_lookup(
        self, indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("langchain[openai]>=0.3", indexes)
        assert matches == []


class TestResolveLibraryStep2LibraryId:
    """Step 2: Exact library ID match."""

    def test_exact_id(self, indexes: RegistryIndexes) -> None:
        matches = resolve_library("pydantic", indexes)
        # "pydantic" is both a library ID and a package name.
        # Step 1 (package match) fires first, which is fine — it still resolves.
        assert len(matches) == 1
        assert matches[0].library_id == "pydantic"
        assert matches[0].relevance == 1.0

    def test_id_not_in_packages(self, indexes: RegistryIndexes) -> None:
        """When a library ID doesn't collide with any package name, step 2 fires.

        In our sample data, 'langchain' IS also a package name so step 1 fires.
        This test documents the behaviour — both paths produce the same result.
        """
        matches = resolve_library("langchain", indexes)
        assert len(matches) == 1
        assert matches[0].library_id == "langchain"
        assert matches[0].matched_via == "package_name"
        assert matches[0].relevance == 1.0


class TestResolveLibraryStep3Alias:
    """Step 3: Alias match."""

    def test_alias(self, indexes: RegistryIndexes) -> None:
        matches = resolve_library("lang-chain", indexes)
        assert len(matches) == 1
        assert matches[0].library_id == "langchain"
        assert matches[0].matched_via == "alias"
        assert matches[0].relevance == 1.0

    def test_alias_case_insensitive(self, indexes: RegistryIndexes) -> None:
        matches = resolve_library("Lang-Chain", indexes)
        assert len(matches) == 1
        assert matches[0].library_id == "langchain"


class TestResolveLibraryStep4Fuzzy:
    """Step 4: Fuzzy match."""

    def test_fuzzy_typo(self, indexes: RegistryIndexes) -> None:
        matches = resolve_library("langchan", indexes)
        assert len(matches) >= 1
        assert matches[0].library_id == "langchain"
        assert matches[0].matched_via == "fuzzy"
        assert 0.0 < matches[0].relevance < 1.0

    def test_fuzzy_results_sorted_descending(self, indexes: RegistryIndexes) -> None:
        """Multiple fuzzy results are sorted by relevance descending."""
        matches = resolve_library("langchan", indexes)
        for i in range(len(matches) - 1):
            assert matches[i].relevance >= matches[i + 1].relevance


class TestResolveLibraryStep5NoMatch:
    """Step 5: No match."""

    def test_no_match(self, indexes: RegistryIndexes) -> None:
        matches = resolve_library("xyzzy-nonexistent", indexes)
        assert matches == []

    def test_empty_query(self, indexes: RegistryIndexes) -> None:
        matches = resolve_library("   ", indexes)
        assert matches == []


# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Input model boundary conditions
# ---------------------------------------------------------------------------


class TestResolveLibraryInputBoundary:
    def test_query_at_500_chars_accepted(self) -> None:
        validated = ResolveLibraryInput(query="a" * 500)
        assert len(validated.query) == 500

    def test_query_at_501_chars_raises(self) -> None:
        with pytest.raises(ValueError, match="500"):
            ResolveLibraryInput(query="a" * 501)

    def test_whitespace_only_query_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            ResolveLibraryInput(query="   ")


class TestReadPageInputBoundary:
    def test_offset_at_1_accepted(self) -> None:
        validated = ReadPageInput(url="https://example.com/page", offset=1, limit=10)
        assert validated.offset == 1

    def test_offset_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="offset"):
            ReadPageInput(url="https://example.com/page", offset=0, limit=10)

    def test_limit_at_1_accepted(self) -> None:
        validated = ReadPageInput(url="https://example.com/page", offset=1, limit=1)
        assert validated.limit == 1

    def test_limit_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="limit"):
            ReadPageInput(url="https://example.com/page", offset=1, limit=0)

    def test_before_at_0_accepted(self) -> None:
        validated = ReadPageInput(url="https://example.com/page", offset=1, limit=10, before=0)
        assert validated.before == 0

    def test_before_positive_accepted(self) -> None:
        validated = ReadPageInput(url="https://example.com/page", offset=5, limit=10, before=3)
        assert validated.before == 3

    def test_before_negative_rejected(self) -> None:
        with pytest.raises(ValueError, match="before"):
            ReadPageInput(url="https://example.com/page", offset=1, limit=10, before=-1)

    def test_url_exceeding_2048_chars_rejected(self) -> None:
        long_url = "https://example.com/" + "a" * 2030
        assert len(long_url) > 2048
        with pytest.raises(ValueError, match="2048"):
            ReadPageInput(url=long_url)

    def test_url_at_exactly_2048_chars_accepted(self) -> None:
        url = "https://example.com/" + "a" * (2048 - len("https://example.com/"))
        assert len(url) == 2048
        validated = ReadPageInput(url=url)
        assert len(validated.url) == 2048

    def test_non_http_url_rejected(self) -> None:
        with pytest.raises(ValueError, match="http"):
            ReadPageInput(url="ftp://example.com/page")

    def test_url_normalizes_scheme_host_and_default_https_port(self) -> None:
        validated = ReadPageInput(url="  HTTPS://Example.COM:443/Docs/Page  ")

        assert validated.url == "https://example.com/Docs/Page"

    def test_url_preserves_path_query_fragment_and_trailing_slash(self) -> None:
        validated = ReadPageInput(url="https://Example.com/Docs/Page/?a=1#Section")

        assert validated.url == "https://example.com/Docs/Page/?a=1#Section"


class TestSearchPageInputBoundary:
    def test_valid_input(self) -> None:
        validated = SearchPageInput(url="https://example.com/page", query="test")
        assert validated.query == "test"
        assert validated.target == "content"
        assert validated.mode == "literal"
        assert validated.case_mode == "smart"
        assert validated.whole_word is False
        assert validated.offset == 1
        assert validated.max_results == 20

    def test_outline_target_accepted(self) -> None:
        validated = SearchPageInput(
            url="https://example.com/page",
            query="test",
            target="outline",
        )
        assert validated.target == "outline"

    def test_empty_query_rejected(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            SearchPageInput(url="https://example.com/page", query="   ")

    def test_query_over_200_chars_rejected(self) -> None:
        with pytest.raises(ValueError, match="200"):
            SearchPageInput(url="https://example.com/page", query="a" * 201)

    def test_query_at_200_chars_accepted(self) -> None:
        validated = SearchPageInput(url="https://example.com/page", query="a" * 200)
        assert len(validated.query) == 200

    def test_offset_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="offset"):
            SearchPageInput(url="https://example.com/page", query="test", offset=0)

    def test_max_results_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="max_results"):
            SearchPageInput(url="https://example.com/page", query="test", max_results=0)

    def test_non_http_url_rejected(self) -> None:
        with pytest.raises(ValueError, match="http"):
            SearchPageInput(url="ftp://example.com/page", query="test")

    def test_url_normalizes_default_http_port(self) -> None:
        validated = SearchPageInput(url="HTTP://Example.com:80/page", query="test")

        assert validated.url == "http://example.com/page"

    def test_invalid_target_rejected(self) -> None:
        with pytest.raises(ValueError, match="target"):
            SearchPageInput(url="https://example.com/page", query="test", target="bad")


class TestReadOutlineInputBoundary:
    def test_offset_at_1_accepted(self) -> None:
        validated = ReadOutlineInput(url="https://example.com/page", offset=1, limit=10)
        assert validated.offset == 1

    def test_offset_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="offset"):
            ReadOutlineInput(url="https://example.com/page", offset=0, limit=10)

    def test_limit_at_1_accepted(self) -> None:
        validated = ReadOutlineInput(url="https://example.com/page", offset=1, limit=1)
        assert validated.limit == 1

    def test_limit_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="limit"):
            ReadOutlineInput(url="https://example.com/page", offset=1, limit=0)

    def test_before_at_0_accepted(self) -> None:
        validated = ReadOutlineInput(url="https://example.com/page", offset=1, limit=10, before=0)
        assert validated.before == 0

    def test_before_positive_accepted(self) -> None:
        validated = ReadOutlineInput(url="https://example.com/page", offset=5, limit=10, before=3)
        assert validated.before == 3

    def test_before_negative_rejected(self) -> None:
        with pytest.raises(ValueError, match="before"):
            ReadOutlineInput(url="https://example.com/page", offset=1, limit=10, before=-1)


class TestMatchStructure:
    """Verify the shape of returned LibraryMatch objects."""

    def test_match_fields(self, indexes: RegistryIndexes) -> None:
        matches = resolve_library("langchain-openai", indexes)
        match = matches[0]
        assert match.library_id == "langchain"
        assert match.name == "LangChain"
        assert match.description == "Framework for building LLM-powered applications."
        assert match.index_url == "https://python.langchain.com/llms.txt"
        assert len(match.packages) == 1
        assert match.packages[0].ecosystem == "pypi"
        assert "python" in match.packages[0].languages
        assert match.matched_via == "package_name"
        assert match.relevance == 1.0
