"""Protocols for fetched-content processors."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .payload import FetchedContent


class HtmlProcessor(Protocol):
    """Interface for HTML processors in the fetch pipeline."""

    name: str

    def applies_to(self, payload: FetchedContent) -> bool: ...

    async def transform(self, payload: FetchedContent) -> FetchedContent: ...
