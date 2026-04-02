"""Configuration loading.

Settings are loaded in priority order (highest first):
  1. Environment variables  (PROCONTEXT__SERVER__TRANSPORT=http)
  2. procontext.yaml        (searched in cwd, then platform config dir)
  3. Hardcoded defaults

The config file is optional — all fields have sensible defaults.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import platformdirs
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from procontext.content_processing import is_supported_html_processor

_DEFAULT_DATA_DIR = platformdirs.user_data_dir("procontext")
# Cache path default is intentionally independent from data_dir overrides.
_DEFAULT_DB_PATH = str(Path(platformdirs.user_data_dir("procontext")) / "cache.db")


def _find_config_file() -> str | None:
    """Return the path of the first procontext.yaml found, or None."""
    candidates = [
        Path("procontext.yaml"),
        Path(platformdirs.user_config_dir("procontext")) / "procontext.yaml",
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return None


class ServerSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transport: Literal["stdio", "http"] = "stdio"
    host: str = "127.0.0.1"
    port: int = Field(default=8080, ge=1, le=65535)
    auth_enabled: bool = False
    auth_key: str = ""


class RegistrySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metadata_url: str = "https://procontexthq.github.io/registry_metadata.json"
    poll_interval_hours: int = Field(default=24, gt=0)


class CacheSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ttl_hours: int = Field(default=24, gt=0)
    db_path: str = _DEFAULT_DB_PATH
    cleanup_interval_hours: int = Field(default=6, gt=0)


class FetcherSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ssrf_private_ip_check: bool = True
    ssrf_domain_check: bool = True
    allowlist_expansion: Literal["registry", "discovered"] = "registry"
    extra_allowed_domains: list[str] = ["github.com", "githubusercontent.com"]
    html_processors: list[str] = Field(default_factory=lambda: ["markitdown"])
    connect_timeout_seconds: float = Field(default=5.0, gt=0)
    request_timeout_seconds: float = Field(default=30.0, gt=0)

    @field_validator("html_processors")
    @classmethod
    def validate_html_processors(cls, value: list[str]) -> list[str]:
        validated: list[str] = []
        for name in value:
            if not isinstance(name, str) or not name.strip():
                raise ValueError("All html_processors entries must be non-empty strings")
            normalized = name.strip().lower()
            if not is_supported_html_processor(normalized):
                raise ValueError(f"Unsupported HTML processor: {normalized}")
            validated.append(normalized)
        return validated


class ResolverSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fuzzy_score_cutoff: int = Field(default=70, ge=0, le=100)
    fuzzy_max_results: int = Field(default=5, gt=0)


class OutlineSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_entries: int = Field(default=50, gt=0)
    read_page_max_chars: int = Field(default=4000, gt=0)
    search_page_max_chars: int = Field(default=1000, gt=0)

    @model_validator(mode="before")
    @classmethod
    def apply_legacy_max_chars_alias(cls, data: Any) -> Any:
        """Map legacy ``max_chars`` to both per-tool limits for compatibility."""
        if not isinstance(data, dict) or "max_chars" not in data:
            return data

        normalized = dict(data)
        legacy_value = normalized.pop("max_chars")
        normalized.setdefault("read_page_max_chars", legacy_value)
        normalized.setdefault("search_page_max_chars", legacy_value)
        return normalized


class LoggingSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    format: Literal["json", "text"] = "json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Double-underscore separates nesting: PROCONTEXT__SERVER__PORT=9090
        env_prefix="PROCONTEXT__",
        env_nested_delimiter="__",
        yaml_file=_find_config_file(),
        yaml_file_encoding="utf-8",
    )

    data_dir: str = _DEFAULT_DATA_DIR
    server: ServerSettings = ServerSettings()
    registry: RegistrySettings = RegistrySettings()
    cache: CacheSettings = CacheSettings()
    fetcher: FetcherSettings = FetcherSettings()
    resolver: ResolverSettings = ResolverSettings()
    outline: OutlineSettings = OutlineSettings()
    logging: LoggingSettings = LoggingSettings()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
        **kwargs: Any,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,  # Constructor args (highest priority)
            env_settings,  # Environment variables
            YamlConfigSettingsSource(settings_cls),  # YAML file
            # dotenv and file secrets intentionally excluded
        )


def registry_paths(settings: Settings) -> tuple[Path, Path]:
    """Return (registry_json_path, state_json_path) for the current runtime."""
    registry_dir = Path(settings.data_dir) / "registry"
    return (
        registry_dir / "known-libraries.json",
        registry_dir / "registry-state.json",
    )


def registry_additional_info_path(settings: Settings) -> Path:
    """Return the local additional-info.json path for the current runtime."""
    return Path(settings.data_dir) / "registry" / "additional-info.json"
