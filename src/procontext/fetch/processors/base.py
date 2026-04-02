"""Protocols for fetch-time HTML processors."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from procontext.fetch.models import FetchedContent


class HtmlProcessor(Protocol):
    """Interface for HTML processors in the fetch pipeline."""

    name: str

    def applies_to(self, payload: FetchedContent) -> bool: ...

    async def transform(self, payload: FetchedContent) -> FetchedContent: ...
