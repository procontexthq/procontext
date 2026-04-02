"""Unit tests for platform-aware configuration defaults."""

from __future__ import annotations

import platformdirs
import pytest
from pydantic import BaseModel, ValidationError

from procontext.config import (
    _DEFAULT_DATA_DIR,
    _DEFAULT_DB_PATH,
    CacheSettings,
    FetcherSettings,
    OutlineSettings,
    RegistrySettings,
    ResolverSettings,
    ServerSettings,
    Settings,
)


class TestPlatformDefaults:
    """Verify config defaults use platformdirs instead of hardcoded Unix paths."""

    def test_default_data_dir_matches_platformdirs(self) -> None:
        expected = platformdirs.user_data_dir("procontext")
        assert expected == _DEFAULT_DATA_DIR

    def test_default_db_path_under_data_dir(self) -> None:
        assert _DEFAULT_DB_PATH.startswith(_DEFAULT_DATA_DIR)
        assert _DEFAULT_DB_PATH.endswith("cache.db")

    def test_cache_settings_uses_platform_default(self) -> None:
        settings = CacheSettings()
        assert settings.db_path == _DEFAULT_DB_PATH
        # Ensure it's not the old hardcoded Unix path
        assert settings.db_path != "~/.local/share/procontext/cache.db"

    def test_data_dir_override_does_not_change_default_db_path(self) -> None:
        settings = Settings(data_dir="/tmp/custom-procontext-data")
        assert settings.data_dir == "/tmp/custom-procontext-data"
        assert settings.cache.db_path == _DEFAULT_DB_PATH


class TestConfigValidation:
    """Verify config validation behaviour for invalid and boundary values."""

    def test_wrong_type_raises_validation_error(self) -> None:
        """A non-integer port raises ValidationError immediately."""
        with pytest.raises(ValidationError):
            # type: ignore comment is intentional — we are deliberately passing
            # a wrong type to verify that Pydantic catches and rejects it.
            Settings(server={"port": "not-a-number"})  # type: ignore[arg-type]

    def test_unknown_top_level_field_raises_validation_error(self) -> None:
        """pydantic-settings already raises for unknown top-level fields.

        A YAML typo at the top level (e.g. 'cach:' instead of 'cache:') is caught.
        """
        with pytest.raises(ValidationError):
            Settings(completely_unknown_field="oops")  # type: ignore[call-arg]

    def test_unknown_nested_field_raises_validation_error(self) -> None:
        """Unknown nested model fields raise ValidationError (extra='forbid').

        A typo like 'db_paht' instead of 'db_path' is caught immediately rather
        than silently falling back to the platform default.
        """
        with pytest.raises(ValidationError):
            CacheSettings(db_paht="/intended/path/cache.db")  # type: ignore[call-arg]

    @pytest.mark.parametrize(
        ("model", "field", "value"),
        [
            (ServerSettings, "port", 0),
            (ServerSettings, "port", 65536),
            (RegistrySettings, "poll_interval_hours", 0),
            (RegistrySettings, "poll_interval_hours", -1),
            (CacheSettings, "ttl_hours", 0),
            (CacheSettings, "ttl_hours", -1),
            (CacheSettings, "cleanup_interval_hours", 0),
            (CacheSettings, "cleanup_interval_hours", -1),
            (FetcherSettings, "connect_timeout_seconds", 0),
            (FetcherSettings, "connect_timeout_seconds", -0.5),
            (FetcherSettings, "request_timeout_seconds", 0),
            (FetcherSettings, "request_timeout_seconds", -1),
            (ResolverSettings, "fuzzy_score_cutoff", -1),
            (ResolverSettings, "fuzzy_score_cutoff", 101),
            (ResolverSettings, "fuzzy_max_results", 0),
            (OutlineSettings, "max_entries", 0),
            (OutlineSettings, "read_page_max_chars", 0),
            (OutlineSettings, "search_page_max_chars", 0),
        ],
    )
    def test_invalid_numeric_bounds_raise_validation_error(
        self, model: type[BaseModel], field: str, value: int | float
    ) -> None:
        with pytest.raises(ValidationError):
            model(**{field: value})  # type: ignore[misc]

    def test_valid_numeric_lower_bounds_are_accepted(self) -> None:
        server = ServerSettings(port=1)
        registry = RegistrySettings(poll_interval_hours=1)
        cache = CacheSettings(ttl_hours=1, cleanup_interval_hours=1)
        fetcher = FetcherSettings(connect_timeout_seconds=0.1, request_timeout_seconds=0.1)
        resolver = ResolverSettings(fuzzy_score_cutoff=0, fuzzy_max_results=1)
        outline = OutlineSettings(max_entries=1, read_page_max_chars=1, search_page_max_chars=1)

        assert server.port == 1
        assert registry.poll_interval_hours == 1
        assert cache.ttl_hours == 1
        assert cache.cleanup_interval_hours == 1
        assert fetcher.connect_timeout_seconds == 0.1
        assert fetcher.request_timeout_seconds == 0.1
        assert resolver.fuzzy_score_cutoff == 0
        assert resolver.fuzzy_max_results == 1
        assert outline.max_entries == 1
        assert outline.read_page_max_chars == 1
        assert outline.search_page_max_chars == 1

    def test_legacy_outline_max_chars_alias_sets_both_limits(self) -> None:
        outline = OutlineSettings(max_entries=1, max_chars=1234)  # type: ignore[call-arg]

        assert outline.max_entries == 1
        assert outline.read_page_max_chars == 1234
        assert outline.search_page_max_chars == 1234

    def test_empty_auth_key_with_auth_enabled(self) -> None:
        """auth_key='' with auth_enabled=True is accepted by pydantic.

        The security implication: the middleware will only admit a request whose
        Authorization header is exactly 'Bearer ' (empty token). Document this
        so it is a conscious choice, not an oversight.
        """
        settings = ServerSettings(auth_enabled=True, auth_key="")
        assert settings.auth_enabled is True
        assert settings.auth_key == ""
