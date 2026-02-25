"""Configuration loading.

Settings are loaded in priority order (highest first):
  1. Environment variables  (PROCONTEXT__SERVER__TRANSPORT=http)
  2. procontext.yaml        (searched in cwd, then ~/.config/procontext/)
  3. Hardcoded defaults

The config file is optional — all fields have sensible defaults.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


def _find_config_file() -> str | None:
    """Return the path of the first procontext.yaml found, or None."""
    candidates = [
        Path("procontext.yaml"),
        Path.home() / ".config" / "procontext" / "procontext.yaml",
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return None


class ServerSettings(BaseModel):
    transport: Literal["stdio", "http"] = "stdio"
    host: str = "0.0.0.0"
    port: int = 8080


class RegistrySettings(BaseModel):
    url: str = "https://pro-context.github.io/known-libraries.json"
    metadata_url: str = "https://pro-context.github.io/registry_metadata.json"


class CacheSettings(BaseModel):
    ttl_hours: int = 24
    db_path: str = "~/.local/share/procontext/cache.db"
    cleanup_interval_hours: int = 6


class LoggingSettings(BaseModel):
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

    server: ServerSettings = ServerSettings()
    registry: RegistrySettings = RegistrySettings()
    cache: CacheSettings = CacheSettings()
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
