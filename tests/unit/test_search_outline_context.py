"""Unit tests for search-page outline rollup and stage-aware selection."""

from __future__ import annotations

from procontext.outline import OutlineEntry, apply_outline_reduction_stage, parse_outline_entries
from procontext.parser import parse_outline
from procontext.tools.search_page.outline_context import (
    build_ancestor_rollup,
    build_match_range_with_rollup,
    merge_outline_entries,
    select_search_outline_entries,
)


def _entries(raw_outline: str) -> list[OutlineEntry]:
    return parse_outline_entries(raw_outline)


class TestBuildAncestorRollup:
    def test_returns_h2_h3_h4_chain(self) -> None:
        entries = _entries("1:# Top\n5:## Auth\n10:### OAuth\n15:#### PKCE")

        result = build_ancestor_rollup(entries, 20)

        assert [entry.text for entry in result] == ["## Auth", "### OAuth", "#### PKCE"]

    def test_falls_back_to_h1_when_no_h2_exists(self) -> None:
        entries = _entries("1:# Top\n10:### Local\n15:#### Leaf")

        result = build_ancestor_rollup(entries, 20)

        assert [entry.text for entry in result] == ["# Top", "### Local", "#### Leaf"]

    def test_returns_available_local_chain_when_h1_and_h2_missing(self) -> None:
        entries = _entries("10:### Local\n15:#### Leaf")

        result = build_ancestor_rollup(entries, 20)

        assert [entry.text for entry in result] == ["### Local", "#### Leaf"]

    def test_same_depth_sibling_replaces_previous_heading(self) -> None:
        entries = _entries("1:# Top\n5:## Old\n10:### Old Child\n15:## New\n20:### New Child")

        result = build_ancestor_rollup(entries, 25)

        assert [entry.text for entry in result] == ["## New", "### New Child"]

    def test_shallower_heading_drops_deeper_ancestors(self) -> None:
        entries = _entries("1:# Top\n5:## A\n10:### Child A\n15:## B\n20:#### Deep B")

        result = build_ancestor_rollup(entries, 25)

        assert [entry.text for entry in result] == ["## B", "#### Deep B"]

    def test_no_preceding_headings_returns_empty(self) -> None:
        entries = _entries("10:## Section\n20:### Match")

        assert build_ancestor_rollup(entries, 10) == []

    def test_setext_headings_participate_like_atx(self) -> None:
        entries = parse_outline_entries(parse_outline("Top\n===\n\nSection\n-------\n\n### Deep"))

        result = build_ancestor_rollup(entries, 8)

        assert [entry.text for entry in result] == ["## Section", "### Deep"]

    def test_h6_removed_stage_does_not_reintroduce_h6(self) -> None:
        entries = _entries("1:# Top\n5:## Section\n10:###### Leaf")
        staged = apply_outline_reduction_stage(entries, "drop_h6")

        result = build_ancestor_rollup(staged, 20)

        assert [entry.text for entry in result] == ["## Section"]
        assert all(entry.depth != 6 for entry in result)

    def test_h5_removed_stage_does_not_reintroduce_h5(self) -> None:
        entries = _entries("1:# Top\n5:## Section\n10:##### Leaf")
        staged = apply_outline_reduction_stage(entries, "drop_h5")

        result = build_ancestor_rollup(staged, 20)

        assert [entry.text for entry in result] == ["## Section"]
        assert all(entry.depth != 5 for entry in result)

    def test_h4_removed_stage_falls_back_to_h3(self) -> None:
        entries = _entries("1:# Top\n5:## Section\n10:### Child\n15:#### Leaf")
        staged = apply_outline_reduction_stage(entries, "drop_h4")

        result = build_ancestor_rollup(staged, 20)

        assert [entry.text for entry in result] == ["## Section", "### Child"]

    def test_h3_removed_stage_falls_back_to_h2(self) -> None:
        entries = _entries("1:# Top\n5:## Section\n10:### Child")
        staged = apply_outline_reduction_stage(entries, "drop_h3")

        result = build_ancestor_rollup(staged, 20)

        assert [entry.text for entry in result] == ["## Section"]


class TestBuildMatchRangeWithRollup:
    def test_match_on_heading_line_does_not_duplicate_heading(self) -> None:
        entries = _entries("1:# Top\n5:## Section\n10:### Match")

        result = build_match_range_with_rollup(entries, 10, 10)

        assert [entry.line_number for entry in result] == [5, 10]
        assert [entry.text for entry in result] == ["## Section", "### Match"]

    def test_empty_trimmed_range_returns_ancestor_chain_only(self) -> None:
        entries = _entries("1:# Top\n3:## Match Section")

        result = build_match_range_with_rollup(entries, 4, 4)

        assert [entry.text for entry in result] == ["## Match Section"]

    def test_merge_preserves_order_and_deduplicates_by_line_number(self) -> None:
        ancestors = _entries("5:## Section\n10:### Child")
        trimmed = _entries("10:### Child\n15:#### Match")

        result = merge_outline_entries(ancestors, trimmed)

        assert [entry.line_number for entry in result] == [5, 10, 15]


class TestSelectSearchOutlineEntries:
    def test_small_outline_returns_full_entries_without_compaction(self) -> None:
        entries = _entries("1:# Top\n5:## Section\n10:### Match")

        result = select_search_outline_entries(
            entries,
            first_line=10,
            last_line=10,
            max_entries=50,
            max_chars=1000,
        )

        assert result is not None
        assert result.compacted is False
        assert result.entries == entries

    def test_no_match_uses_normal_compaction(self) -> None:
        entries = _entries("\n".join([f"10{i}:## Section {i}" for i in range(1, 56)]))

        result = select_search_outline_entries(
            entries,
            first_line=None,
            last_line=None,
            max_entries=50,
            max_chars=1000,
        )

        assert result is None

    def test_stage_aware_selection_drops_h6_when_needed(self) -> None:
        h2 = ["1:# Top", "5:## Target"]
        h6 = [f"{10 + i * 5}:###### Leaf {i} {'x' * 60}" for i in range(20)]
        entries = _entries("\n".join(h2 + h6))

        result = select_search_outline_entries(
            entries,
            first_line=11,
            last_line=105,
            max_entries=50,
            max_chars=1000,
        )

        assert result is not None
        assert result.compacted is True
        assert [entry.text for entry in result.entries] == ["## Target"]
        assert all(entry.depth != 6 for entry in result.entries)
