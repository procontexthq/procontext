"""Shared fixtures and helpers for tool integration tests."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from procontext.cache import Cache

if TYPE_CHECKING:
    from procontext.state import AppState


SAMPLE_PAGE = """\
# Streaming

## Overview

LangChain supports streaming.

## Streaming with Chat Models

Details here.

### Using .stream()

The `.stream()` method returns an iterator.

### Using .astream()

The `.astream()` method is async.

## Streaming with Chains

Chain streaming details."""

SAMPLE_URL = "https://python.langchain.com/docs/concepts/streaming.md"

SETEXT_PAGE = """\
Main Title
==========

Section Title
-------------

Body content for the setext section.

## Tail

Tail details."""

SETEXT_URL = "https://python.langchain.com/docs/concepts/setext.md"


def build_large_setext_page(extra_sections: int = 60) -> str:
    """Build a page whose full outline exceeds 50 entries."""
    lines = [
        "# Top",
        "",
        "Match Section",
        "-------------",
        "",
        "needle before details",
        "",
    ]
    for index in range(extra_sections):
        lines.append(f"### Detail {index}")
        lines.append(f"Detail body {index} with needle {index}.")
        lines.append("")
    return "\n".join(lines)


def build_compactable_page_no_match() -> str:
    """Build a page whose outline exceeds max_entries but can be compacted.

    Creates 20 H2 sections each with 2 H6 subheadings = 60 entries total.
    Compaction removes H6 first, leaving 20 entries (under the 50 limit).
    """
    lines = ["# Top", ""]
    for index in range(20):
        lines.append(f"## Section {index}")
        lines.append(f"###### Leaf A{index}")
        lines.append(f"###### Leaf B{index}")
        lines.append(f"Body {index}.")
        lines.append("")
    return "\n".join(lines)


def build_large_page_no_match(sections: int = 60) -> str:
    """Build a page with a large outline but no content matching 'xyzzy'."""
    lines = ["# Top", ""]
    for index in range(sections):
        lines.append(f"## Section {index}")
        lines.append(f"Body content for section {index}.")
        lines.append("")
    return "\n".join(lines)


def build_dense_match_page(sections: int = 80) -> str:
    """Build a page where many outline entries fall within the match range."""
    lines = ["# Top", "", "needle_start", ""]
    for index in range(sections):
        lines.append(f"### Detail {index}")
        lines.append(f"Content {index}.")
        lines.append("")
    lines.append("needle_end")
    return "\n".join(lines)


async def expire_cached_page(
    app_state: AppState,
    *,
    url: str = SAMPLE_URL,
    last_checked_at: str | None = None,
) -> None:
    """Mark a cached page stale, optionally preserving last_checked_at."""
    stale_time = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    assert isinstance(app_state.cache, Cache)
    await app_state.cache._db.execute(  # pyright: ignore[reportPrivateUsage]
        "UPDATE page_cache SET expires_at = ?, last_checked_at = ? WHERE url = ?",
        (stale_time, last_checked_at, url),
    )
    await app_state.cache._db.commit()  # pyright: ignore[reportPrivateUsage]


def hashed_url(url: str = SAMPLE_URL) -> str:
    """Return the internal URL hash used for background refresh tracking."""
    return hashlib.sha256(url.encode()).hexdigest()


async def update_cached_page_content(
    app_state: AppState,
    content: str,
    *,
    url: str = SAMPLE_URL,
) -> None:
    """Overwrite cached content for a page."""
    assert isinstance(app_state.cache, Cache)
    await app_state.cache._db.execute(  # pyright: ignore[reportPrivateUsage]
        "UPDATE page_cache SET content = ? WHERE url = ?",
        (content, url),
    )
    await app_state.cache._db.commit()  # pyright: ignore[reportPrivateUsage]
