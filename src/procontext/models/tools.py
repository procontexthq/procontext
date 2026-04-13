from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator

from procontext.models.registry import LibraryMatch
from procontext.normalization import normalize_doc_url


def _validate_http_url(raw: str) -> str:
    """Validate a tool URL after applying conservative normalization."""
    url = normalize_doc_url(raw)
    if len(url) > 2048:
        raise ValueError("url must not exceed 2048 characters")
    if not url.startswith(("http://", "https://")):
        raise ValueError("url must use http or https scheme")
    return url


class ResolveLibraryInput(BaseModel):
    query: str
    language: str | None = None

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("query must be at least 3 characters")
        if len(v) > 500:
            raise ValueError("query must not exceed 500 characters")
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip().lower()
        if not v:
            return None
        if len(v) > 50:
            raise ValueError("language must not exceed 50 characters")
        return v


class ResolveHint(BaseModel):
    code: Literal["UNSUPPORTED_QUERY_SYNTAX", "FUZZY_FALLBACK_USED"]
    message: str


class ResolveLibraryOutput(BaseModel):
    matches: list[LibraryMatch]
    hint: ResolveHint | None = None


class ReadPageInput(BaseModel):
    url: str
    offset: int = 1
    limit: int = 500
    before: int = 0
    include_outline: bool = True

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _validate_http_url(v)

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

    @field_validator("before")
    @classmethod
    def validate_before(cls, v: int) -> int:
        if v < 0:
            raise ValueError("before must be >= 0")
        return v


class OutlineSummary(BaseModel):
    text: str
    total_entries: int


class ReadPageOutput(BaseModel):
    url: str
    content: str
    outline: OutlineSummary | None
    total_lines: int
    offset: int
    limit: int
    has_more: bool
    next_offset: int | None
    content_hash: str


class ReadOutlineInput(BaseModel):
    url: str
    offset: int = 1
    limit: int = 500
    before: int = 0

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _validate_http_url(v)

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

    @field_validator("before")
    @classmethod
    def validate_before(cls, v: int) -> int:
        if v < 0:
            raise ValueError("before must be >= 0")
        return v


class ReadOutlineOutput(BaseModel):
    url: str
    outline: str
    total_entries: int
    has_more: bool
    next_offset: int | None
    content_hash: str


class SearchPageInput(BaseModel):
    url: str
    query: str
    target: Literal["content", "outline"] = "content"
    mode: Literal["literal", "regex"] = "literal"
    case_mode: Literal["smart", "insensitive", "sensitive"] = "smart"
    whole_word: bool = False
    offset: int = 1
    max_results: int = 20

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _validate_http_url(v)

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("query must not be empty")
        if len(v) > 200:
            raise ValueError("query must not exceed 200 characters")
        return v

    @field_validator("offset")
    @classmethod
    def validate_offset(cls, v: int) -> int:
        if v < 1:
            raise ValueError("offset must be >= 1")
        return v

    @field_validator("max_results")
    @classmethod
    def validate_max_results(cls, v: int) -> int:
        if v < 1:
            raise ValueError("max_results must be >= 1")
        return v


class SearchPageOutput(BaseModel):
    url: str
    query: str
    matches: str
    outline: OutlineSummary
    total_lines: int
    has_more: bool
    next_offset: int | None
    content_hash: str
