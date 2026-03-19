"""Tests for rejecting non-plain-name resolve_library queries."""

from __future__ import annotations

from procontext.normalization import is_unsupported_resolve_query


class TestSupportedPlainNames:
    def test_whitespace_only_query_is_not_marked_unsupported(self) -> None:
        assert is_unsupported_resolve_query("   ") is False

    def test_plain_package_name_is_supported(self) -> None:
        assert is_unsupported_resolve_query("langchain-openai") is False

    def test_plain_library_id_is_supported(self) -> None:
        assert is_unsupported_resolve_query("react-lib") is False

    def test_plain_display_name_is_supported(self) -> None:
        assert is_unsupported_resolve_query("  Babel   Core  ") is False

    def test_scoped_npm_package_name_is_supported(self) -> None:
        assert is_unsupported_resolve_query("@babel/core") is False


class TestUnsupportedPythonDependencySyntax:
    def test_python_extras_only_query_is_unsupported(self) -> None:
        assert is_unsupported_resolve_query("langchain[openai]") is True

    def test_python_version_specifier_is_unsupported(self) -> None:
        assert is_unsupported_resolve_query("langchain>=0.1") is True

    def test_python_version_and_extras_are_unsupported(self) -> None:
        assert is_unsupported_resolve_query("langchain[openai]>=0.1") is True

    def test_python_spaced_comparison_is_unsupported(self) -> None:
        assert is_unsupported_resolve_query("langchain > 0.1") is True

    def test_python_arbitrary_equality_is_unsupported(self) -> None:
        assert is_unsupported_resolve_query("langchain===0.1") is True


class TestUnsupportedNpmDependencySyntax:
    def test_unscoped_npm_version_query_is_unsupported(self) -> None:
        assert is_unsupported_resolve_query("react@18.3.1") is True

    def test_unscoped_npm_dist_tag_is_unsupported(self) -> None:
        assert is_unsupported_resolve_query("react@latest") is True

    def test_scoped_npm_version_query_is_unsupported(self) -> None:
        assert is_unsupported_resolve_query("@babel/core@^7.26.0") is True

    def test_scoped_npm_dist_tag_is_unsupported(self) -> None:
        assert is_unsupported_resolve_query("@babel/core@next") is True

    def test_unscoped_tarball_like_at_url_is_unsupported(self) -> None:
        assert is_unsupported_resolve_query("openai@https://example.com/openai.tgz") is True


class TestUnsupportedSourceSpecs:
    def test_python_direct_reference_is_unsupported(self) -> None:
        assert (
            is_unsupported_resolve_query("openai @ https://github.com/openai/openai-python") is True
        )

    def test_git_direct_reference_is_unsupported(self) -> None:
        assert (
            is_unsupported_resolve_query("openai @ git+https://github.com/openai/openai-python.git")
            is True
        )

    def test_bare_github_url_is_unsupported(self) -> None:
        assert is_unsupported_resolve_query("https://github.com/openai/openai-python") is True

    def test_github_shorthand_is_unsupported(self) -> None:
        assert is_unsupported_resolve_query("github:openai/openai-python") is True

    def test_ssh_source_url_is_unsupported(self) -> None:
        assert is_unsupported_resolve_query("ssh://github.com/openai/openai-python") is True
