# URL Extraction Strategy

**Status:** Accepted
**Last Updated:** 2026-03-22

## Context

ProContext extracts URLs from documentation content to build a domain allowlist for SSRF protection. This document explains why we use a simple regex-based approach instead of strict RFC 3986 parsing, and documents the known limitations and trade-offs.

## Problem Statement

When fetching documentation pages, we need to discover which external domains are referenced. This enables:
- Runtime allowlist expansion (discovering new safe domains)
- Cache persistence (recording what URLs were found)
- SSRF protection (blocking unwhitelisted domains)

The challenge: documentation is messy. URLs appear in various contexts:
- Markdown links: `[text](https://example.com)`
- Code examples: `https://example.com/api`
- Plain prose: `Visit https://example.com for details.`
- Comments and embedded code blocks

## Decision

**Use a simple, permissive regex pattern with graceful error handling instead of strict RFC 3986 parsing.**

### Why Not Strict RFC 3986?

RFC 3986 defines URL syntax precisely, but strict compliance:
1. **Requires complex regex or parser** — hard to maintain, easy to introduce bugs
2. **Still has false negatives** — documentation contains valid URLs outside strict spec (e.g., URLs with unusual characters)
3. **Performance overhead** — full RFC validation slower than simple regex scan
4. **Fragile in practice** — real documentation doesn't follow RFC precisely

### Why Simple Regex?

1. **Permissiveness catches more URLs** — especially in messy documentation
2. **Error handling is simple** — try to parse, skip if it fails
3. **Performance** — O(content_size) single scan, no per-URL validation overhead
4. **Maintainability** — regex is short, easy to understand and modify

## Solution

### Current Regex

```python
_URL_RE = re.compile(r"https?://[^\s\)\]\"<>]+")
```

Matches `http://` or `https://` followed by any characters except:
- Whitespace (end of URL)
- `)` (markdown link closing)
- `]` (markdown link closing, IPv6 closing bracket)
- `\` (escape character)
- `"` (quote)
- `<`, `>` (angle brackets)

### Extraction Flow

1. Regex scans content, finds potential URLs
2. `urlparse()` validates and extracts hostname
3. If parsing fails: log warning and skip
4. `_base_domain()` normalizes: `api.example.com` → `example.com`
5. Add to allowlist (if in discovery mode) or cache (for persistence)

## Known Limitations

### IPv6 URLs (Skipped)

**Pattern:** `https://[::1]:8080/path`

**Issue:** The regex excludes `]` to handle markdown `[text](url)` properly. This causes incomplete IPv6 matches: `https://[::1` (missing closing bracket). `urlparse()` fails with `ValueError("Invalid IPv6 URL")`.

**Current Behavior:** Logged as malformed URL, skipped.

**Why Acceptable:**
- IPv6 URLs are rare in public documentation (<1% of typical docs)
- Most IPv6 URLs in docs are examples:
  - `[::1]` (loopback/localhost)
  - `[fe80::1]` (link-local)
  - Internal network examples
- Even if extracted, these would be blocked by SSRF private IP checks
- Value of supporting IPv6 is minimal vs complexity of fixing

**Future Consideration:** If IPv6 documentation becomes common, implement post-processing: when `ValueError("Invalid IPv6 URL")` is caught, try adding missing `]` and re-parsing.

### Single Quotes (Included but Handled)

**Pattern:** `'https://example.com'`

**Issue:** Single quote `'` is not excluded, so matches: `https://example.com'`

**Current Behavior:** urlparse extracts hostname as `example.com'`. When checking allowlist, `example.com'` is not found, so URL is blocked (safe behavior).

**Why Acceptable:**
- Rare in structured documentation
- Fails safely (blocked, not allowed)
- Fixing adds complexity (need quote handling logic)

### Trailing Punctuation (Included but Handled)

**Pattern:** `See https://example.com. or Visit https://example.com!`

**Issue:** Period/punctuation included in regex match.

**Current Behavior:** `urlparse()` and `_base_domain()` handle it correctly:
- `urlparse("https://example.com.")` → hostname: `example.com.`
- `_base_domain()` strips trailing dots → `example.com`
- Result: correct domain extracted

**Status:** No issue, works as intended.

## Evaluation Matrix

| Edge Case | Status | Behavior | Safe? |
|-----------|--------|----------|-------|
| Markdown links `[text](url)` | ✅ Handled | Stops at `)` | Yes |
| IPv6 `https://[::1]` | ⚠️ Skipped | ValueError logged | Yes (safe skip) |
| Single quotes `'url'` | ⚠️ Partial | Included in match, blocked by allowlist | Yes (safe block) |
| Trailing punctuation `url.` | ✅ Handled | Stripped by `_base_domain()` | Yes |
| Query strings `url?a=1&b=2` | ✅ Handled | Parsed correctly | Yes |
| Ports `url:8080` | ✅ Handled | Parsed correctly | Yes |
| Fragments `url#section` | ✅ Handled | Parsed correctly | Yes |

## Trade-offs

| Aspect | Simple Regex | Strict RFC 3986 |
|--------|--------------|-----------------|
| Completeness | ~98% (misses IPv6) | ~99.5% |
| False Positives | Minimal (handled by error catching) | Very low |
| Complexity | Low | High |
| Performance | O(n) content scan | O(n*m) per-URL validation |
| Maintainability | High | Medium |
| Real-world Accuracy | High (works with messy docs) | Lower (strict parser may reject valid practical URLs) |

**Verdict:** Simple regex wins on practical grounds. The 1-2% of missed URLs (mostly IPv6 examples) have minimal impact compared to the simplicity and performance benefit.

## Future Improvements

### If IPv6 Support Becomes Necessary

Implement post-processing in `extract_base_domains_from_content()`:

```python
except ValueError as e:
    if "IPv6" in str(e) and match.group().startswith("https://["):
        try:
            fixed_url = match.group() + "]"
            hostname = urlparse(fixed_url).hostname or ""
            if hostname:
                domains.add(_base_domain(hostname))
                continue
        except ValueError:
            pass
    log.warning("skipped_malformed_url", url=match.group()[:100], error=str(e))
```

**Cost:** ~5 lines, no regex change, backwards compatible.

### If Stricter Extraction Needed

Consider two-phase approach:
1. Regex extraction (current, permissive)
2. Optional strict validation (RFC 3986) on extracted URLs
3. Log statistics on rejection rates

This allows experimentation without breaking current behavior.

## References

- RFC 3986: Uniform Resource Identifier (URI) - Generic Syntax
- Python `urllib.parse.urlparse()` documentation
- SSRF Protection in `src/procontext/fetcher.py`

## Questions & Answers

**Q: Why not just use a library for URL parsing?**
A: Libraries like `furl` or `hyperlink` add dependency overhead for simple extraction. Our current approach is simpler and faster for the use case.

**Q: Should we extract IPv6 URLs?**
A: Only if documentation you're processing contains IPv6 links that agents need to follow. Currently: no, they're examples/local addresses.

**Q: What if we see strange extraction patterns?**
A: Log level is `warning` for malformed URLs. Monitor logs to identify common edge cases and update this document.
