"""Page outline parser for documentation pages.

Single-pass algorithm that extracts H1-H6 headings, conservative setext
headings, and fenced code block boundaries from Markdown content. Outputs a
plain-text outline with 1-based line numbers for agent navigation via the
``read_page`` tool.

Emitted lines:
- Heading lines (H1-H6), including ATX headings inside fenced code blocks and
  blockquote-prefixed ATX headings (``> ## Section``).
- Plain setext headings outside fenced code blocks, normalized to synthetic
  ATX lines (``# Title`` / ``## Section``) anchored to the title line number.
- Fence opener and closer lines (`` ``` `` / ``~~~``), so the agent can tell
  which headings belong to code block content vs. structural page sections.
"""

from __future__ import annotations

import re

# Matches fence openers/closers: at most 3 spaces of indentation, then 3+
# backticks or tildes. Checked against the original (unstripped) line so that
# 4-space indented lines (indented code blocks) are correctly ignored.
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")

# Matches ATX headings H1–H6 once leading structural indentation has already
# been handled. The optional ``(?:>\s*)?`` prefix handles blockquote headings
# (``> ## Section``). A heading marker may be followed by spaces, tabs, or
# end-of-line (empty heading).
_HEADING_RE = re.compile(r"(?:>\s*)?(#{1,6})(?:[ \t]+|$)")

# Matches conservative setext underlines: at most 3 spaces of indentation, then
# one or more "=" or "-" characters, optionally followed by whitespace.
_SETEXT_RE = re.compile(r"^ {0,3}(=+|-+)\s*$")

_FRONT_MATTER_OPEN_RE = re.compile(r"^---\s*$")
_FRONT_MATTER_CLOSE_RE = re.compile(r"^(---|\.\.\.)\s*$")


def parse_outline(content: str) -> str:
    """Extract a plain-text structural map from Markdown content.

    Returns one line per heading or fence marker in the format
    ``"<lineno>:<original line>"``, joined by newlines.
    Returns an empty string if no headings or fences are found.

    Fence opener and closer lines are included so the agent can determine
    whether a heading-like line belongs to code content or the document
    structure proper.
    """
    # Strip UTF-8 BOM if present — some servers prepend \ufeff to responses,
    # which would prevent the heading regex from matching line 1.
    content = content.removeprefix("\ufeff")

    raw_lines = content.splitlines()
    lines: list[str] = []

    front_matter_end = _front_matter_end(raw_lines)
    in_fence = False
    fence_char = ""
    fence_len = 0
    index = 0

    while index < len(raw_lines):
        if front_matter_end is not None and index <= front_matter_end:
            index += 1
            continue

        line = raw_lines[index]
        lineno = index + 1
        fence_match = _FENCE_RE.match(line)

        if not in_fence and fence_match is not None:
            lines.append(f"{lineno}:{line}")
            marker = fence_match.group(1)
            char = marker[0]
            length = len(marker)
            in_fence = True
            fence_char = char
            fence_len = length

            index += 1
            continue

        if in_fence and _is_matching_fence_closer(
            line,
            fence_char=fence_char,
            fence_len=fence_len,
        ):
            lines.append(f"{lineno}:{line}")
            in_fence = False
            fence_char = ""
            fence_len = 0

            index += 1
            continue

        if _match_heading(line, in_fence=in_fence) is not None:
            lines.append(f"{lineno}:{line}")
            index += 1
            continue

        setext_text = None
        if not in_fence and index + 1 < len(raw_lines):
            setext_text = _normalized_setext_heading(line, raw_lines[index + 1])

        if setext_text is not None:
            lines.append(f"{lineno}:{setext_text}")
            index += 2
            continue

        index += 1

    return "\n".join(lines)


def _front_matter_end(lines: list[str]) -> int | None:
    """Return the closing line index for top-of-file YAML front matter."""
    if not lines or _FRONT_MATTER_OPEN_RE.fullmatch(lines[0]) is None:
        return None

    for index, line in enumerate(lines[1:], start=1):
        if _FRONT_MATTER_CLOSE_RE.fullmatch(line) is not None:
            return index

    return None


def _normalized_setext_heading(title_line: str, underline_line: str) -> str | None:
    """Normalize a supported setext heading pair to synthetic ATX text."""
    underline_match = _SETEXT_RE.fullmatch(underline_line)
    if underline_match is None:
        return None

    title = title_line.strip()
    if not title:
        return None
    if title.startswith(">"):
        return None
    if _FENCE_RE.match(title_line) is not None:
        return None
    if _HEADING_RE.match(title) is not None:
        return None
    if _SETEXT_RE.fullmatch(title_line) is not None:
        return None
    if len(title_line) - len(title_line.lstrip(" ")) > 3:
        return None

    marker = "#" if underline_match.group(1)[0] == "=" else "##"
    return f"{marker} {title}"


def _match_heading(line: str, *, in_fence: bool) -> re.Match[str] | None:
    """Match an ATX heading using fence-aware indentation rules."""
    if in_fence:
        return _HEADING_RE.match(line.strip())

    leading_spaces = len(line) - len(line.lstrip(" "))
    if leading_spaces > 3:
        return None

    return _HEADING_RE.match(line[leading_spaces:])


def _is_matching_fence_closer(line: str, *, fence_char: str, fence_len: int) -> bool:
    """Return True when *line* is a valid closer for the active fence.

    CommonMark requires the closer to use the same fence character, be at
    least as long as the opener, and contain only trailing spaces/tabs.
    """
    if not line:
        return False

    stripped = line.lstrip(" ")
    indent = len(line) - len(stripped)
    if indent > 3:
        return False

    marker_len = len(stripped) - len(stripped.lstrip(fence_char))
    if marker_len < fence_len:
        return False

    return stripped[marker_len:].strip(" \t") == ""
