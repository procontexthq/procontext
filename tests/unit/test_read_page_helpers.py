"""Unit tests for read_page private helper functions.

Tests _has_file_extension and _with_md_extension in isolation — no network,
no cache, no AppState. Covers the full space of URL shapes these helpers
will encounter in the wild.
"""

from __future__ import annotations

from procontext.tools.read_page import _has_file_extension, _with_md_extension

# ---------------------------------------------------------------------------
# _has_file_extension
# ---------------------------------------------------------------------------


class TestHasFileExtension:
    # --- standard extensions (should skip probe) ---

    def test_md_extension(self) -> None:
        assert _has_file_extension("https://example.com/docs/page.md") is True

    def test_txt_extension(self) -> None:
        assert _has_file_extension("https://example.com/llms.txt") is True

    def test_html_extension(self) -> None:
        assert _has_file_extension("https://example.com/docs/index.html") is True

    def test_css_extension(self) -> None:
        assert _has_file_extension("https://example.com/style.css") is True

    def test_json_extension(self) -> None:
        assert _has_file_extension("https://example.com/openapi.json") is True

    def test_rst_extension(self) -> None:
        assert _has_file_extension("https://example.com/README.rst") is True

    def test_uppercase_extension(self) -> None:
        # .MD, .HTML — isalpha is case-aware but uppercase letters are alpha
        assert _has_file_extension("https://example.com/CHANGELOG.MD") is True
        assert _has_file_extension("https://example.com/index.HTML") is True

    def test_compound_extension_tar_gz(self) -> None:
        # splitext gives the last extension only (.gz); gz is alphabetic
        assert _has_file_extension("https://example.com/archive.tar.gz") is True

    # --- no extension (should probe) ---

    def test_no_extension(self) -> None:
        assert _has_file_extension("https://example.com/docs/streaming") is False

    def test_no_extension_deep_path(self) -> None:
        assert _has_file_extension("https://example.com/a/b/c/d") is False

    def test_no_extension_single_segment(self) -> None:
        assert _has_file_extension("https://example.com/about") is False

    # --- version / numeric patterns (should probe) ---

    def test_version_segment_major_minor(self) -> None:
        # v1.2 — the suffix .2 is numeric, not a real extension
        assert _has_file_extension("https://example.com/docs/v1.2") is False

    def test_version_segment_patch(self) -> None:
        # v1.2.3 — splitext gives .3 (numeric)
        assert _has_file_extension("https://example.com/docs/v1.2.3") is False

    def test_bare_version(self) -> None:
        # 1.0 — same logic
        assert _has_file_extension("https://example.com/docs/1.0") is False

    def test_year_month(self) -> None:
        # 2024.01 — numeric suffix
        assert _has_file_extension("https://example.com/releases/2024.01") is False

    # --- mixed alpha+digit extensions (should probe) ---

    def test_mixed_alphanumeric_extension(self) -> None:
        # .v2rc — has a digit, not all alphabetic
        assert _has_file_extension("https://example.com/page.v2rc") is False

    def test_h5_extension(self) -> None:
        # .h5 (HDF5) — has digit, treated as not a real doc extension
        assert _has_file_extension("https://example.com/data.h5") is False

    # --- trailing slash / empty segment (should skip probe) ---

    def test_trailing_slash(self) -> None:
        # Last segment is empty — appending .md would produce /docs/page/.md
        assert _has_file_extension("https://example.com/docs/page/") is True

    def test_trailing_slash_root(self) -> None:
        assert _has_file_extension("https://example.com/") is True

    def test_domain_only_no_path(self) -> None:
        # No path at all — path is "" → empty last segment
        assert _has_file_extension("https://example.com") is True

    # --- query strings and fragments (urlparse strips these — should not affect result) ---

    def test_no_extension_with_query(self) -> None:
        assert _has_file_extension("https://example.com/docs/page?v=1") is False

    def test_md_extension_with_query(self) -> None:
        assert _has_file_extension("https://example.com/docs/page.md?v=1") is True

    def test_no_extension_with_fragment(self) -> None:
        assert _has_file_extension("https://example.com/docs/page#section") is False

    def test_md_extension_with_fragment(self) -> None:
        assert _has_file_extension("https://example.com/docs/page.md#section") is True

    def test_no_extension_with_query_and_fragment(self) -> None:
        assert _has_file_extension("https://example.com/docs/page?v=1#section") is False

    # --- hidden files (dot-prefixed, no extension by splitext convention) ---

    def test_hidden_file_dot_prefix(self) -> None:
        # splitext('.hidden') = ('.hidden', '') — treated as extensionless
        assert _has_file_extension("https://example.com/docs/.hidden") is False


# ---------------------------------------------------------------------------
# _with_md_extension
# ---------------------------------------------------------------------------


class TestWithMdExtension:
    def test_plain_path(self) -> None:
        result = _with_md_extension("https://example.com/docs/page")
        assert result == "https://example.com/docs/page.md"

    def test_deep_path(self) -> None:
        result = _with_md_extension("https://example.com/a/b/c/page")
        assert result == "https://example.com/a/b/c/page.md"

    def test_fragment_goes_after_md(self) -> None:
        # .md must be in the path, not inside the fragment
        result = _with_md_extension("https://example.com/docs/page#section")
        assert result == "https://example.com/docs/page.md#section"

    def test_fragment_complex(self) -> None:
        result = _with_md_extension("https://example.com/docs/page#heading-1-2")
        assert result == "https://example.com/docs/page.md#heading-1-2"

    def test_query_string(self) -> None:
        # .md must be in the path, not inside the query string
        result = _with_md_extension("https://example.com/docs/page?v=latest")
        assert result == "https://example.com/docs/page.md?v=latest"

    def test_query_with_multiple_params(self) -> None:
        result = _with_md_extension("https://example.com/docs/page?a=1&b=2")
        assert result == "https://example.com/docs/page.md?a=1&b=2"

    def test_query_and_fragment(self) -> None:
        # Both must be preserved, .md in path only
        result = _with_md_extension("https://example.com/docs/page?v=1#section")
        assert result == "https://example.com/docs/page.md?v=1#section"

    def test_preserves_scheme_and_host(self) -> None:
        result = _with_md_extension("https://docs.python.org/3/library/asyncio")
        assert result.startswith("https://docs.python.org")
        assert result.endswith(".md")

    def test_port_preserved(self) -> None:
        result = _with_md_extension("https://example.com:8080/docs/page")
        assert result == "https://example.com:8080/docs/page.md"

    def test_version_in_path(self) -> None:
        result = _with_md_extension("https://example.com/docs/v1.2")
        assert result == "https://example.com/docs/v1.2.md"
