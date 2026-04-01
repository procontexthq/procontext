"""Mixed-ecosystem lookup behavior for the simplified resolver."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from procontext.models.registry import PackageEntry, RegistryEntry
from procontext.registry import build_indexes
from procontext.resolver import _fuzzy_search, resolve_library

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
            id="priority-lib",
            name="Priority Name",
            description="Tests text-match precedence between name and alias.",
            packages=[],
            aliases=["priority name"],
            llms_txt_url="https://example.com/priority-lib/llms.txt",
        ),
        RegistryEntry(
            id="shared-pkg-lib",
            name="Shared Package Library",
            description="Resolves through package lookup.",
            packages=[
                PackageEntry(
                    ecosystem="pypi",
                    languages=["python"],
                    package_names=["shared"],
                    repo_url="https://github.com/example/shared-pkg-lib",
                ),
            ],
            aliases=[],
            llms_txt_url="https://example.com/shared-pkg-lib/llms.txt",
        ),
        RegistryEntry(
            id="shared",
            name="Shared",
            description="Resolves through exact text lookup.",
            packages=[],
            aliases=[],
            llms_txt_url="https://example.com/shared/llms.txt",
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
    def test_same_library_hit_by_package_and_text_returns_once_as_package_match(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("langchain", mixed_indexes)

        assert _library_ids(matches) == ["langchain"]
        assert matches[0].matched_via == "package_name"

    def test_exact_package_match_resolves_plain_package_name(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("langchain-openai", mixed_indexes)

        assert _library_ids(matches) == ["langchain"]
        assert matches[0].matched_via == "package_name"

    def test_exact_name_lookup_matches_display_name(self, mixed_indexes: RegistryIndexes) -> None:
        matches = resolve_library("  Babel   Core  ", mixed_indexes)

        assert _library_ids(matches) == ["babel-core"]
        assert matches[0].matched_via == "name"

    def test_exact_name_lookup_collapses_whitespace_without_removing_it(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("BabelCore", mixed_indexes, fuzzy_score_cutoff=100)

        assert matches == []

    def test_exact_library_id_lookup_uses_merged_text_index(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("react-lib", mixed_indexes)

        assert _library_ids(matches) == ["react-lib"]
        assert matches[0].matched_via == "library_id"

    def test_alias_lookup_uses_merged_text_index(self, mixed_indexes: RegistryIndexes) -> None:
        matches = resolve_library("lang-chain", mixed_indexes)

        assert _library_ids(matches) == ["langchain"]
        assert matches[0].matched_via == "alias"

    def test_exact_package_and_text_hits_for_different_libraries_both_return(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("shared", mixed_indexes)

        assert _library_ids(matches) == ["shared-pkg-lib", "shared"]
        assert matches[0].matched_via == "package_name"
        assert matches[1].matched_via == "library_id"

    def test_plain_cross_ecosystem_package_query_returns_all_exact_matches(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("openai", mixed_indexes)

        assert set(_library_ids(matches)) == {"openai-python", "openai-js"}
        assert {match.matched_via for match in matches} == {"package_name"}

    def test_exact_npm_scope_lookup_preserves_scope_prefix(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("@babel/core", mixed_indexes)

        assert _library_ids(matches) == ["babel-core"]
        assert matches[0].matched_via == "package_name"

    def test_modifier_syntax_does_not_resolve_as_plain_name(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        assert resolve_library("langchain[openai]>=0.3", mixed_indexes) == []
        assert resolve_library("@babel/core@^7.26.0", mixed_indexes) == []
        assert resolve_library("react@18", mixed_indexes) == []

    def test_source_spec_queries_return_no_matches(self, mixed_indexes: RegistryIndexes) -> None:
        assert resolve_library("https://github.com/openai/openai-python", mixed_indexes) == []
        assert resolve_library("github:openai/openai-python", mixed_indexes) == []
        assert (
            resolve_library("openai @ https://example.com/openai-1.0.0.tar.gz", mixed_indexes) == []
        )

    def test_no_pypi_separator_canonicalisation_is_applied(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("zope_interface", mixed_indexes, fuzzy_score_cutoff=100)

        assert matches == []

    def test_text_match_priority_prefers_name_over_alias(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("priority name", mixed_indexes)

        assert _library_ids(matches) == ["priority-lib"]
        assert matches[0].matched_via == "name"


class TestFuzzyFallback:
    def test_fuzzy_only_runs_after_exact_miss(self, mixed_indexes: RegistryIndexes) -> None:
        matches = resolve_library("langchian", mixed_indexes)

        assert matches[0].library_id == "langchain"
        assert matches[0].matched_via == "fuzzy"
        assert 0.0 < matches[0].relevance < 1.0

    def test_fuzzy_query_uses_same_space_normalisation_as_text_lookup(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        matches = resolve_library("  lang chian  ", mixed_indexes)

        assert matches[0].library_id == "langchain"
        assert matches[0].matched_via == "fuzzy"

    def test_fuzzy_limit_is_applied_after_library_deduplication(self) -> None:
        entries = [
            RegistryEntry(
                id=f"lib{i}",
                name=f"Library {i}",
                description="Synthetic fuzzy candidate.",
                packages=[],
                aliases=[],
                llms_txt_url=f"https://example.com/lib{i}/llms.txt",
            )
            for i in range(1, 7)
        ]
        by_id = {entry.id: entry for entry in entries}
        corpus = [
            ("langchain variant", "lib1"),
            ("langchain variat", "lib1"),
            ("langchain variants", "lib2"),
            ("langchain varint", "lib2"),
            ("langchain vart", "lib3"),
            ("langchain vrt", "lib4"),
            ("langchn vrt", "lib5"),
            ("langch vrt", "lib6"),
        ]

        matches = _fuzzy_search(
            "langchain variant",
            corpus,
            by_id,
            limit=5,
            score_cutoff=0,
        )

        assert len(matches) == 5
        assert len({match.library_id for match in matches}) == 5


class TestFuzzyEdgeCases:
    def test_empty_corpus_returns_empty(self) -> None:
        matches = _fuzzy_search("query", corpus=[], by_id={}, limit=5, score_cutoff=70)
        assert matches == []

    def test_limit_zero_returns_empty(self) -> None:
        corpus = [("langchain", "lib1")]
        by_id = {
            "lib1": RegistryEntry(
                id="lib1",
                name="lib1",
                description="d",
                packages=[],
                aliases=[],
                llms_txt_url="https://example.com/llms.txt",
            )
        }
        matches = _fuzzy_search("langchain", corpus, by_id, limit=0, score_cutoff=0)
        assert matches == []

    def test_fuzzy_query_normalizes_to_empty_returns_empty(
        self, mixed_indexes: RegistryIndexes
    ) -> None:
        """A query that normalizes to empty after fuzzy normalization returns no matches."""
        # A query that's valid (non-empty, not unsupported) but normalizes to empty
        # is unlikely in practice, but the branch guard on line 47 handles it.
        matches = resolve_library("   ", mixed_indexes)
        assert matches == []


def test_registry_entries_keep_original_package_names(
    mixed_entries: list[RegistryEntry], mixed_indexes: RegistryIndexes
) -> None:
    del mixed_indexes  # fixture forces index construction for this scenario

    assert mixed_entries[0].packages[0].package_names == ["langchain", "langchain-openai"]
