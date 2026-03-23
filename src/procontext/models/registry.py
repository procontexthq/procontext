from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from procontext.normalization import normalize_exact_doc_origin

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class PackageEntry(BaseModel):
    """Package group within a registry entry, scoped by ecosystem."""

    ecosystem: Literal["pypi", "npm", "conda", "jsr"] = Field(
        description="Package registry ecosystem."
    )
    languages: list[str] = Field(
        default=[],
        description="Programming languages, e.g. ['python'] or ['javascript', 'typescript'].",
    )
    package_names: list[str] = Field(description="Package names in this ecosystem.")
    readme_url: str | None = Field(
        default=None, description="URL to the README for this package group."
    )
    repo_url: str | None = Field(
        default=None, description="URL to the source repository for this package group."
    )


class RegistryEntry(BaseModel):
    """Single entry in known-libraries.json."""

    id: str
    name: str
    description: str = ""
    packages: list[PackageEntry] = []
    aliases: list[str] = []
    llms_txt_url: str
    llms_full_txt_url: str | None = None

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9][a-z0-9_-]*$", v):
            raise ValueError(f"Invalid library ID: {v!r}")
        return v


class RegistryState(BaseModel):
    """Persisted metadata stored in registry-state.json."""

    version: str
    checksum: str
    updated_at: str | None = None
    last_checked_at: str | None = None
    additional_info_download_url: str | None = None
    additional_info_checksum: str | None = None

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        if not isinstance(value, str) or not value:
            raise ValueError("'version' must be a non-empty string")
        return value

    @field_validator("checksum")
    @classmethod
    def validate_checksum(cls, value: str) -> str:
        if not _SHA256_RE.match(value):
            raise ValueError("checksum must be in 'sha256:<hex>' format")
        return value

    @field_validator("additional_info_checksum")
    @classmethod
    def validate_additional_info_checksum(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _SHA256_RE.match(value):
            raise ValueError("checksum must be in 'sha256:<hex>' format")
        return value

    @field_validator("additional_info_download_url")
    @classmethod
    def validate_additional_info_download_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise ValueError("'additional_info_download_url' must be a non-empty string")
        return value.strip()


class RegistryAdditionalInfo(BaseModel):
    """Optional registry sidecar metadata stored in additional-info.json."""

    useful_md_probe_base_urls: list[str] = Field(
        default=[],
        description="Exact normalized base URLs where .md probing is allowed.",
    )

    @field_validator("useful_md_probe_base_urls")
    @classmethod
    def validate_base_urls(cls, value: list[str]) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("'useful_md_probe_base_urls' must be an array of strings")
        normalized: list[str] = []
        seen: set[str] = set()
        for raw_url in value:
            if not isinstance(raw_url, str):
                raise ValueError("All useful_md_probe_base_urls entries must be strings")
            base_url = normalize_exact_doc_origin(raw_url)
            if base_url not in seen:
                seen.add(base_url)
                normalized.append(base_url)
        return normalized


class LibraryMatch(BaseModel):
    """Single result returned by resolve_library."""

    library_id: str = Field(description="Unique library identifier.")
    name: str = Field(description="Human-readable library name.")
    description: str = Field(description="Short description of what the library does.")
    index_url: str = Field(description="URL of the library's documentation index (llms.txt).")
    full_docs_url: str | None = Field(
        default=None,
        description="URL of the library's complete merged documentation (llms-full.txt).",
    )
    packages: list[PackageEntry] = Field(
        description="Package groups by ecosystem with language, README, and repo metadata."
    )
    matched_via: Literal["package_name", "library_id", "name", "alias", "fuzzy"] = Field(
        description="Match method: package_name, library_id, name, alias, or fuzzy text match."
    )
    relevance: float = Field(description="Match confidence 0.0 (low) to 1.0 (high).")


TextMatchType = Literal["library_id", "name", "alias"]


@dataclass(frozen=True)
class ExactTextHit:
    """Exact text lookup hit for a library ID, display name, or alias."""

    library_id: str
    match_type: TextMatchType


@dataclass
class RegistryIndexes:
    """In-memory indexes built from known-libraries.json at startup.

    Exact indexes are rebuilt in a single pass (<100ms for 1,000 entries).
    """

    # package name (lowercase, as published) → library IDs
    by_package_exact: dict[str, list[str]] = field(default_factory=dict)

    # library ID → full registry entry
    by_id: dict[str, RegistryEntry] = field(default_factory=dict)

    # normalized text → exact hits from library IDs, display names, and aliases
    by_text_exact: dict[str, list[ExactTextHit]] = field(default_factory=dict)

    # flat list of (term, library_id) pairs for fuzzy matching
    # populated from package names, IDs, names, and aliases
    fuzzy_corpus: list[tuple[str, str]] = field(default_factory=list)
