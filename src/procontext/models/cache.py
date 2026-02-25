from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TocCacheEntry(BaseModel):
    """Cached llms.txt content for a library."""

    library_id: str
    llms_txt_url: str
    content: str  # Raw llms.txt markdown
    fetched_at: datetime
    expires_at: datetime
    stale: bool = False


class PageCacheEntry(BaseModel):
    """Cached content for a single documentation page."""

    url: str
    url_hash: str  # SHA-256 of url (primary key)
    content: str  # Full page markdown
    fetched_at: datetime
    expires_at: datetime
    stale: bool = False
