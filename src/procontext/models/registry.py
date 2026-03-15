from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field, field_validator


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

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9][a-z0-9_-]*$", v):
            raise ValueError(f"Invalid library ID: {v!r}")
        return v


class LibraryMatch(BaseModel):
    """Single result returned by resolve_library."""

    library_id: str = Field(description="Unique library identifier.")
    name: str = Field(description="Human-readable library name.")
    description: str = Field(description="Short description of what the library does.")
    index_url: str = Field(description="URL of the library's documentation index (llms.txt).")
    packages: list[PackageEntry] = Field(
        description="Package groups by ecosystem with language, README, and repo metadata."
    )
    matched_via: Literal["package_name", "library_id", "alias", "fuzzy"] = Field(
        description="Match method: package_name, library_id, alias, or fuzzy text match."
    )
    relevance: float = Field(description="Match confidence 0.0 (low) to 1.0 (high).")


@dataclass
class RegistryIndexes:
    """In-memory indexes built from known-libraries.json at startup.

    Four dicts rebuilt in a single pass (<100ms for 1,000 entries).
    """

    # package name (lowercase) → library ID  e.g. "langchain-openai" → "langchain"
    by_package: dict[str, str] = field(default_factory=dict)

    # library ID → full registry entry
    by_id: dict[str, RegistryEntry] = field(default_factory=dict)

    # alias (lowercase) → library ID  e.g. "lang-chain" → "langchain"
    by_alias: dict[str, str] = field(default_factory=dict)

    # flat list of (term, library_id) pairs for fuzzy matching
    # populated from all IDs + package names + aliases (lowercased)
    fuzzy_corpus: list[tuple[str, str]] = field(default_factory=list)
