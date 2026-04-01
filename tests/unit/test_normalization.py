"""Tests for normalization helpers: URL normalization, origin extraction, dependency detection."""

from __future__ import annotations

import pytest

from procontext.normalization import (
    has_dependency_modifier_syntax,
    normalize_doc_origin,
    normalize_doc_url,
    normalize_exact_doc_origin,
)


class TestNormalizeDocUrl:
    """Tests for normalize_doc_url covering scheme, host, port, and edge cases."""

    def test_lowercases_scheme_and_host(self) -> None:
        assert normalize_doc_url("HTTPS://DOCS.EXAMPLE.COM/page") == "https://docs.example.com/page"

    def test_preserves_path_and_trailing_slash(self) -> None:
        assert normalize_doc_url("https://docs.example.com/page/") == (
            "https://docs.example.com/page/"
        )

    def test_strips_whitespace(self) -> None:
        assert normalize_doc_url("  https://example.com/page  ") == "https://example.com/page"

    def test_removes_default_http_port(self) -> None:
        assert normalize_doc_url("http://example.com:80/page") == "http://example.com/page"

    def test_removes_default_https_port(self) -> None:
        assert normalize_doc_url("https://example.com:443/page") == "https://example.com/page"

    def test_preserves_non_default_port(self) -> None:
        assert normalize_doc_url("https://example.com:8080/page") == (
            "https://example.com:8080/page"
        )

    def test_no_hostname_returns_scheme_lowered(self) -> None:
        result = normalize_doc_url("file:///local/path")
        assert result.startswith("file:")

    def test_ipv6_host_bracketed(self) -> None:
        assert normalize_doc_url("http://[::1]:8080/page") == "http://[::1]:8080/page"

    def test_userinfo_preserved(self) -> None:
        result = normalize_doc_url("https://user@example.com/page")
        assert "user@" in result

    def test_userinfo_with_password_preserved(self) -> None:
        result = normalize_doc_url("https://user:pass@example.com/page")
        assert "user:pass@" in result

    def test_invalid_port_returns_scheme_lowered(self) -> None:
        # urlsplit raises ValueError for certain malformed ports
        result = normalize_doc_url("http://example.com:not_a_port/page")
        assert result.startswith("http:")

    def test_preserves_query_and_fragment(self) -> None:
        url = "https://example.com/page?q=1#section"
        assert normalize_doc_url(url) == url


class TestNormalizeDocOrigin:
    """Tests for normalize_doc_origin — scheme://host[:port] extraction."""

    def test_extracts_origin_from_full_url(self) -> None:
        assert normalize_doc_origin("https://docs.example.com/page?q=1") == (
            "https://docs.example.com"
        )

    def test_rejects_non_http_scheme(self) -> None:
        with pytest.raises(ValueError, match="scheme must be http or https"):
            normalize_doc_origin("ftp://example.com/file")

    def test_rejects_missing_hostname(self) -> None:
        with pytest.raises(ValueError, match="must include a hostname"):
            normalize_doc_origin("https:///path")


class TestNormalizeExactDocOrigin:
    """Tests for normalize_exact_doc_origin — strict base URL validation."""

    def test_valid_origin(self) -> None:
        assert normalize_exact_doc_origin("https://example.com") == "https://example.com"

    def test_valid_origin_with_trailing_slash(self) -> None:
        assert normalize_exact_doc_origin("https://example.com/") == "https://example.com"

    def test_rejects_non_http_scheme(self) -> None:
        with pytest.raises(ValueError, match="scheme must be http or https"):
            normalize_exact_doc_origin("ftp://example.com")

    def test_rejects_missing_hostname(self) -> None:
        with pytest.raises(ValueError, match="must include a hostname"):
            normalize_exact_doc_origin("https:///")

    def test_rejects_userinfo(self) -> None:
        with pytest.raises(ValueError, match="must not include userinfo"):
            normalize_exact_doc_origin("https://user@example.com")

    def test_rejects_query(self) -> None:
        with pytest.raises(ValueError, match="must not include query or fragment"):
            normalize_exact_doc_origin("https://example.com?q=1")

    def test_rejects_fragment(self) -> None:
        with pytest.raises(ValueError, match="must not include query or fragment"):
            normalize_exact_doc_origin("https://example.com#section")

    def test_rejects_path(self) -> None:
        with pytest.raises(ValueError, match="must not include a path"):
            normalize_exact_doc_origin("https://example.com/docs")


class TestHasDependencyModifierSyntax:
    """Tests for has_dependency_modifier_syntax — source spec short-circuit."""

    def test_source_spec_is_not_dependency_modifier(self) -> None:
        # Source specs like git+ URLs are handled by is_source_spec_query,
        # not as dependency modifiers.
        assert has_dependency_modifier_syntax("git+https://github.com/org/repo") is False

    def test_empty_string(self) -> None:
        assert has_dependency_modifier_syntax("") is False

    def test_plain_name(self) -> None:
        assert has_dependency_modifier_syntax("langchain") is False

    def test_python_extras(self) -> None:
        assert has_dependency_modifier_syntax("langchain[openai]") is True

    def test_npm_version(self) -> None:
        assert has_dependency_modifier_syntax("react@18.3.1") is True
