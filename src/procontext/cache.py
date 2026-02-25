"""SQLite documentation cache with stale-while-revalidate.

All cache operations catch ``aiosqlite.Error`` internally and degrade
gracefully: read failures return ``None`` (treated as cache miss by callers),
write failures are logged and ignored (fetched content is still returned).
Infrastructure errors never cross the Cache class boundary.

Note on coding guideline #7 ("Libraries Must Never Swallow Errors"): That
guideline targets public API surfaces where swallowing errors steals the
decision from the consumer. Cache is an internal infrastructure component —
the design decision (per 02-technical-spec §6.3) is that cache failures must
never prevent the agent from receiving a response. Errors are still logged
with ``exc_info=True`` so they remain observable via stderr.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import aiosqlite
import structlog

if TYPE_CHECKING:
    from procontext.models.cache import PageCacheEntry, TocCacheEntry

log = structlog.get_logger()

_CREATE_TOC_TABLE = """
CREATE TABLE IF NOT EXISTS toc_cache (
    library_id   TEXT PRIMARY KEY,
    llms_txt_url TEXT NOT NULL,
    content      TEXT NOT NULL,
    fetched_at   TEXT NOT NULL,
    expires_at   TEXT NOT NULL
)
"""

_CREATE_PAGE_TABLE = """
CREATE TABLE IF NOT EXISTS page_cache (
    url_hash    TEXT PRIMARY KEY,
    url         TEXT NOT NULL UNIQUE,
    content     TEXT NOT NULL,
    headings    TEXT NOT NULL DEFAULT '',
    fetched_at  TEXT NOT NULL,
    expires_at  TEXT NOT NULL
)
"""

_CREATE_TOC_INDEX = "CREATE INDEX IF NOT EXISTS idx_toc_expires ON toc_cache(expires_at)"
_CREATE_PAGE_INDEX = "CREATE INDEX IF NOT EXISTS idx_page_expires ON page_cache(expires_at)"


class Cache:
    """SQLite-backed documentation cache implementing CacheProtocol."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def init_db(self) -> None:
        """Create tables and set WAL mode. Called once at startup."""
        await self._db.execute("PRAGMA journal_mode = WAL")
        await self._db.execute("PRAGMA foreign_keys = ON")
        await self._db.execute(_CREATE_TOC_TABLE)
        await self._db.execute(_CREATE_PAGE_TABLE)
        await self._db.execute(_CREATE_TOC_INDEX)
        await self._db.execute(_CREATE_PAGE_INDEX)
        await self._db.commit()

    # ------------------------------------------------------------------
    # ToC cache
    # ------------------------------------------------------------------

    async def get_toc(self, library_id: str) -> TocCacheEntry | None:
        """Read a ToC entry. Returns ``None`` on cache miss or read failure."""
        try:
            cursor = await self._db.execute(
                "SELECT library_id, llms_txt_url, content, fetched_at, expires_at "
                "FROM toc_cache WHERE library_id = ?",
                (library_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None

            from procontext.models.cache import TocCacheEntry

            fetched_at = datetime.fromisoformat(row[3])
            expires_at = datetime.fromisoformat(row[4])
            stale = datetime.now(UTC) > expires_at

            return TocCacheEntry(
                library_id=row[0],
                llms_txt_url=row[1],
                content=row[2],
                fetched_at=fetched_at,
                expires_at=expires_at,
                stale=stale,
            )
        except aiosqlite.Error:
            log.warning("cache_read_error", key=f"toc:{library_id}", exc_info=True)
            return None

    async def set_toc(
        self,
        library_id: str,
        llms_txt_url: str,
        content: str,
        ttl_hours: int,
    ) -> None:
        """Write a ToC entry. Non-fatal on failure."""
        try:
            now = datetime.now(UTC)
            expires_at = now + timedelta(hours=ttl_hours)
            await self._db.execute(
                "INSERT OR REPLACE INTO toc_cache "
                "(library_id, llms_txt_url, content, fetched_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (library_id, llms_txt_url, content, now.isoformat(), expires_at.isoformat()),
            )
            await self._db.commit()
        except aiosqlite.Error:
            log.warning("cache_write_error", key=f"toc:{library_id}", exc_info=True)

    # ------------------------------------------------------------------
    # Page cache
    # ------------------------------------------------------------------

    async def get_page(self, url_hash: str) -> PageCacheEntry | None:
        """Read a page entry. Returns ``None`` on cache miss or read failure."""
        try:
            cursor = await self._db.execute(
                "SELECT url_hash, url, content, headings, fetched_at, expires_at "
                "FROM page_cache WHERE url_hash = ?",
                (url_hash,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None

            from procontext.models.cache import PageCacheEntry

            fetched_at = datetime.fromisoformat(row[4])
            expires_at = datetime.fromisoformat(row[5])
            stale = datetime.now(UTC) > expires_at

            return PageCacheEntry(
                url_hash=row[0],
                url=row[1],
                content=row[2],
                headings=row[3],
                fetched_at=fetched_at,
                expires_at=expires_at,
                stale=stale,
            )
        except aiosqlite.Error:
            log.warning("cache_read_error", key=f"page:{url_hash}", exc_info=True)
            return None

    async def set_page(
        self,
        url: str,
        url_hash: str,
        content: str,
        headings: str,
        ttl_hours: int,
    ) -> None:
        """Write a page entry. Non-fatal on failure."""
        try:
            now = datetime.now(UTC)
            expires_at = now + timedelta(hours=ttl_hours)
            await self._db.execute(
                "INSERT OR REPLACE INTO page_cache "
                "(url_hash, url, content, headings, fetched_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (url_hash, url, content, headings, now.isoformat(), expires_at.isoformat()),
            )
            await self._db.commit()
        except aiosqlite.Error:
            log.warning("cache_write_error", key=f"page:{url_hash}", exc_info=True)

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    async def cleanup_expired(self) -> None:
        """Delete entries expired more than 7 days ago. Non-fatal on failure."""
        try:
            cutoff = (datetime.now(UTC) - timedelta(days=7)).isoformat()

            cursor = await self._db.execute("DELETE FROM toc_cache WHERE expires_at < ?", (cutoff,))
            toc_deleted = cursor.rowcount

            cursor = await self._db.execute(
                "DELETE FROM page_cache WHERE expires_at < ?", (cutoff,)
            )
            page_deleted = cursor.rowcount

            await self._db.commit()
            log.info(
                "cache_cleanup_complete",
                toc_deleted=toc_deleted,
                page_deleted=page_deleted,
            )
        except aiosqlite.Error:
            log.warning("cache_cleanup_error", exc_info=True)
