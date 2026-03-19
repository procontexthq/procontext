"""Target behavior for safe dependency-syntax stripping.

These tests describe a narrow, syntax-aware pre-lookup cleanup step:

- strip Python version/range suffixes
- strip npm trailing ``@version`` suffixes
- do not rewrite bare scoped npm package names
- do not rewrite Python direct references
- do not guess package names from bare repository URLs
"""

from __future__ import annotations

import procontext.resolver as resolver


def _strip_safe_query(raw: str) -> str:
    return resolver.strip_safe_query(raw)


class TestStripSafeQueryPython:
    def test_whitespace_only_query_becomes_empty(self) -> None:
        assert _strip_safe_query("   ") == ""

    def test_trims_whitespace(self) -> None:
        assert _strip_safe_query("  langchain>=0.1  ") == "langchain"

    def test_strips_python_greater_equal_version(self) -> None:
        assert _strip_safe_query("langchain>=0.1") == "langchain"

    def test_strips_python_exact_version(self) -> None:
        assert _strip_safe_query("openai==1.2.3") == "openai"

    def test_strips_python_compatible_release(self) -> None:
        assert _strip_safe_query("httpx~=0.28") == "httpx"

    def test_strips_python_spaced_comparison(self) -> None:
        assert _strip_safe_query("langchain > 0.1") == "langchain"

    def test_strips_python_extras_without_version(self) -> None:
        assert _strip_safe_query("langchain[openai]") == "langchain"

    def test_strips_python_version_and_extras(self) -> None:
        assert _strip_safe_query("langchain[openai]>=0.1") == "langchain"

    def test_keeps_python_direct_reference_to_https_url_unchanged(self) -> None:
        raw = "openai @ https://github.com/openai/openai-python"
        assert _strip_safe_query(raw) == raw

    def test_keeps_python_direct_reference_to_git_url_unchanged(self) -> None:
        raw = "openai @ git+https://github.com/openai/openai-python.git"
        assert _strip_safe_query(raw) == raw


class TestStripSafeQueryNpm:
    def test_strips_unscoped_npm_exact_version(self) -> None:
        assert _strip_safe_query("react@18.3.1") == "react"

    def test_strips_unscoped_npm_caret_range(self) -> None:
        assert _strip_safe_query("react@^18.3.1") == "react"

    def test_strips_scoped_npm_exact_version(self) -> None:
        assert _strip_safe_query("@babel/core@7.26.0") == "@babel/core"

    def test_strips_scoped_npm_caret_range(self) -> None:
        assert _strip_safe_query("@babel/core@^7.26.0") == "@babel/core"

    def test_does_not_strip_bare_scoped_package_name(self) -> None:
        assert _strip_safe_query("@babel/core") == "@babel/core"

    def test_does_not_strip_unscoped_npm_dist_tag(self) -> None:
        assert _strip_safe_query("react@latest") == "react@latest"

    def test_does_not_strip_scoped_npm_dist_tag(self) -> None:
        assert _strip_safe_query("@babel/core@next") == "@babel/core@next"


class TestStripSafeQueryUnsafeCases:
    def test_keeps_bare_github_url_unchanged(self) -> None:
        raw = "https://github.com/openai/openai-python"
        assert _strip_safe_query(raw) == raw

    def test_keeps_github_shorthand_unchanged(self) -> None:
        raw = "github:openai/openai-python"
        assert _strip_safe_query(raw) == raw

    def test_keeps_plain_package_name_unchanged(self) -> None:
        assert _strip_safe_query("langchain-openai") == "langchain-openai"
