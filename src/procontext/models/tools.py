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


class ReadPageInput(BaseModel):
    url: str
    offset: int = 1
    limit: int = 2000

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 2048:
            raise ValueError("url must not exceed 2048 characters")
        if not v.startswith(("http://", "https://")):
            raise ValueError("url must use http or https scheme")
        return v

    @field_validator("offset")
    @classmethod
    def validate_offset(cls, v: int) -> int:
        if v < 1:
            raise ValueError("offset must be >= 1")
        return v

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1:
            raise ValueError("limit must be >= 1")
        return v


class ReadPageOutput(BaseModel):
    url: str
    headings: str  # Plain-text heading map: "<line>: <heading>\n..."
    total_lines: int
    offset: int
    limit: int
    content: str  # Page markdown for the requested window
    cached: bool
    cached_at: datetime | None
    stale: bool = False
