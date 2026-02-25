from __future__ import annotations

import re

from pydantic import BaseModel, field_validator


class RegistryPackages(BaseModel):
    pypi: list[str] = []
    npm: list[str] = []


class RegistryEntry(BaseModel):
    """Single entry in known-libraries.json."""

    id: str
    name: str
    docs_url: str | None = None
    repo_url: str | None = None
    languages: list[str] = []
    packages: RegistryPackages = RegistryPackages()
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

    library_id: str
    name: str
    languages: list[str]
    docs_url: str | None
    matched_via: str  # "package_name" | "library_id" | "alias" | "fuzzy"
    relevance: float  # 0.0–1.0
