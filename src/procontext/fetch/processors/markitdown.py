"""MarkItDown-backed HTML processor."""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

from anyio import to_thread
from markitdown import MarkItDown
from markitdown._stream_info import StreamInfo

if TYPE_CHECKING:
    from procontext.fetch.models import FetchedContent


class MarkItDownHtmlProcessor:
    """Convert fetched HTML into Markdown using MarkItDown."""

    name = "markitdown"

    def __init__(self) -> None:
        self._converter = MarkItDown(enable_plugins=False)

    def applies_to(self, payload: FetchedContent) -> bool:
        return payload.is_html()

    async def transform(self, payload: FetchedContent) -> FetchedContent:
        def _convert() -> str:
            result = self._converter.convert(
                BytesIO(payload.body),
                stream_info=StreamInfo(
                    mimetype=payload.content_type,
                    charset=payload.charset,
                    url=payload.final_url,
                ),
            )
            return result.text_content

        return payload.with_text_content(await to_thread.run_sync(_convert))
