"""Desired mixed-ecosystem lookup behavior for the resolver.

These tests describe the target lookup flow before the implementation is
changed:

1. Safe version stripping first
2. Exact package lookup
3. Exact name / ID / alias lookup
4. Ecosystem-aware PyPI canonical fallback
5. Fuzzy search last
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from procontext.models.registry import PackageEntry, RegistryEntry
from procontext.registry import build_indexes
from procontext.resolver import resolve_library

if TYPE_CHECKING:
    from procontext.models.registry import LibraryMatch, RegistryIndexes


def _library_ids(matches: list[LibraryMatch]) -> list[str]:
    return [match.library_id for match in matches]


@pytest.fixture()
def mixed_entries() -> list[RegistryEntry]:
    return [
        RegistryEntry(
            id="langchain",
            name="LangChain",
            description="Framework for building LLM-powered applications.",
            packages=[
                PackageEntry(
                    ecosystem="pypi",
                    languages=["python"],
                    package_names=["langchain", "langchain-openai"],
                    repo_url="https://github.com/langchain-ai/langchain",
                ),
            ],
            aliases=["lang-chain"],
            llms_txt_url="https://python.langchain.com/llms.txt",
        ),
        RegistryEntry(
            id="zope-lib",
            name="Zope Interface",
            description="Python interface definitions.",
            packages=[
                PackageEntry(
                    ecosystem="pypi",
                    languages=["python"],
                    package_names=["zope.interface"],
                    repo_url="https://github.com/zopefoundation/zope.interface",
                ),
            ],
            aliases=[],
            llms_txt_url="https://zopeinterface.readthedocs.io/llms.txt",
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
                    repo_url="https://github.com/babel/babel",
                ),
            ],
            aliases=[],
            llms_txt_url="https://babeljs.io/llms.txt",
        ),
        RegistryEntry(
            id="react-lib",
            name="React",
            description="UI library for building component-based applications.",
            packages=[
                PackageEntry(
                    ecosystem="npm",
                    languages=["javascript", "typescript"],
                    package_names=["react"],
                    repo_url="https://github.com/facebook/react",
                ),
            ],
            aliases=[],
            llms_txt_url="https://react.dev/llms.txt",
        ),
        RegistryEntry(
            id="my-pkg-js",
            name="My Package JS",
            description="npm package whose punctuation should stay exact.",
            packages=[
                PackageEntry(
                    ecosystem="npm",
                    languages=["javascript"],
                    package_names=["my_pkg"],
                    repo_url="https://github.com/example/my-pkg-js",
                ),
            ],
            aliases=[],
            llms_txt_url="https://example.com/my-pkg-js/llms.txt",
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
                    repo_url="https://github.com/openai/openai-python",
                ),
            ],
            aliases=[],
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
                    repo_url="https://github.com/openai/openai-node",
                ),
            ],
            aliases=[],
            llms_txt_url="https://openai.github.io/openai-node/llms.txt",
        ),
    ]


@pytest.fixture()
def mixed_indexes(mixed_entries: list[RegistryEntry]) -> RegistryIndexes:
    return build_indexes(mixed_entries)


class TestBuildIndexes:
    def test_builds_exact_package_index_for_pypi_and_npm(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        by_package_exact = mixed_indexes.by_package_exact

        assert by_package_exact["langchain-openai"] == ["langchain"]
        assert by_package_exact["@babel/core"] == ["babel-core"]

    def test_builds_pypi_canonical_index_for_separator_variants(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        by_package_pypi_canonical = mixed_indexes.by_package_pypi_canonical

        assert by_package_pypi_canonical["zope-interface"] == ["zope-lib"]
        assert "my-pkg" not in by_package_pypi_canonical

    def test_builds_merged_text_index_for_names_and_ids(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        by_text_exact = mixed_indexes.by_text_exact

        assert "babel core" in by_text_exact
        assert "babel-core" in by_text_exact
        assert "react-lib" in by_text_exact

    def test_keeps_cross_ecosystem_package_collisions(self, mixed_indexes: RegistryIndexes) -> None:
        by_package_exact = mixed_indexes.by_package_exact

        assert set(by_package_exact["openai"]) == {"openai-python", "openai-js"}


class TestResolveLibraryLookupFlow:
    def test_exact_package_match_wins_over_text_index_when_same_key_exists(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("langchain", mixed_indexes)

        assert _library_ids(matches) == ["langchain"]
        assert matches[0].matched_via == "package_name"

    def test_exact_package_match_wins_for_clean_pypi_package(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("langchain-openai", mixed_indexes)

        assert _library_ids(matches) == ["langchain"]
        assert matches[0].matched_via == "package_name"

    def test_exact_name_lookup_matches_display_name(self, mixed_indexes: RegistryIndexes) -> None:
        matches = resolve_library("  Babel   Core  ", mixed_indexes)

        assert _library_ids(matches) == ["babel-core"]
        assert matches[0].matched_via == "name"

    def test_exact_library_id_lookup_uses_merged_text_index(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("react-lib", mixed_indexes)

        assert _library_ids(matches) == ["react-lib"]
        assert matches[0].matched_via == "library_id"

    def test_alias_lookup_still_works_after_text_index_merge(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("lang-chain", mixed_indexes)

        assert _library_ids(matches) == ["langchain"]
        assert matches[0].matched_via == "alias"

    def test_python_requirement_syntax_resolves_to_base_package(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("langchain[openai]>=0.3", mixed_indexes)

        assert _library_ids(matches) == ["langchain"]
        assert matches[0].matched_via == "package_name"

    def test_python_direct_reference_is_not_treated_as_safe_exact_package_input(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library(
            "openai @ https://example.com/openai-1.0.0.tar.gz",
            mixed_indexes,
            fuzzy_score_cutoff=100,
        )

        assert matches == []

    def test_bare_github_url_returns_no_matches(self, mixed_indexes: RegistryIndexes) -> None:
        matches = resolve_library(
            "https://github.com/openai/openai-python",
            mixed_indexes,
            fuzzy_score_cutoff=100,
        )

        assert matches == []

    def test_github_shorthand_returns_no_matches(self, mixed_indexes: RegistryIndexes) -> None:
        matches = resolve_library("github:openai/openai-python", mixed_indexes)

        assert matches == []

    def test_pypi_pep503_fallback_matches_separator_variants(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("zope_interface", mixed_indexes)

        assert _library_ids(matches) == ["zope-lib"]
        assert matches[0].matched_via == "package_name"

    def test_exact_npm_scope_lookup_preserves_scope_prefix(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("@babel/core", mixed_indexes)

        assert _library_ids(matches) == ["babel-core"]
        assert matches[0].matched_via == "package_name"

    def test_npm_version_lookup_extracts_scoped_package_name(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("@babel/core@^7.26.0", mixed_indexes)

        assert _library_ids(matches) == ["babel-core"]
        assert matches[0].matched_via == "package_name"

    def test_npm_version_lookup_extracts_unscoped_package_name(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("react@18", mixed_indexes)

        assert _library_ids(matches) == ["react-lib"]
        assert matches[0].matched_via == "package_name"

    def test_pypi_canonical_fallback_is_not_applied_to_npm_packages(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("my-pkg", mixed_indexes, fuzzy_score_cutoff=100)

        assert matches == []

    def test_plain_cross_ecosystem_package_query_returns_all_exact_matches(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("openai", mixed_indexes)

        assert set(_library_ids(matches)) == {"openai-python", "openai-js"}
        assert {match.matched_via for match in matches} == {"package_name"}


class TestFuzzyFallback:
    def test_fuzzy_only_runs_after_exact_and_ecosystem_aware_paths(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("langchian", mixed_indexes)

        assert matches[0].library_id == "langchain"
        assert matches[0].matched_via == "fuzzy"
        assert 0.0 < matches[0].relevance < 1.0

    def test_fuzzy_query_uses_same_space_normalisation_as_corpus(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("  lang chian  ", mixed_indexes)

        assert matches[0].library_id == "langchain"
        assert matches[0].matched_via == "fuzzy"


def test_registry_entries_keep_original_package_names(
    mixed_entries: list[RegistryEntry], mixed_indexes: RegistryIndexes
) -> None:
    del mixed_indexes  # fixture forces index construction for this scenario

    assert mixed_entries[1].packages[0].package_names == ["zope.interface"]
