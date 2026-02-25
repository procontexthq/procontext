from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, field_validator

from procontext.models.registry import LibraryMatch


class ResolveLibraryInput(BaseModel):
    query: str

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("query must not be empty")
        if len(v) > 500:
            raise ValueError("query must not exceed 500 characters")
        return v


class ResolveLibraryOutput(BaseModel):
    matches: list[LibraryMatch]


class GetLibraryDocsInput(BaseModel):
    library_id: str

    @field_validator("library_id")
    @classmethod
    def validate_library_id(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-z0-9][a-z0-9_-]*$", v):
            raise ValueError(f"Invalid library ID: {v!r}")
        return v


class GetLibraryDocsOutput(BaseModel):
    library_id: str
    name: str
    content: str  # Raw llms.txt markdown
    cached: bool
    cached_at: datetime | None
    stale: bool = False


class Heading(BaseModel):
    title: str
    level: int  # 1–4
    anchor: str  # Slugified, deduplicated (useful for constructing deep links)
    line: int  # 1-based line number where the heading appears in the page


class ReadPageInput(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 2048:
            raise ValueError("url must not exceed 2048 characters")
        if not v.startswith(("http://", "https://")):
            raise ValueError("url must use http or https scheme")
        return v


class ReadPageOutput(BaseModel):
    url: str
    headings: list[Heading]
    content: str  # Full page markdown
    cached: bool
    cached_at: datetime | None
    stale: bool = False
