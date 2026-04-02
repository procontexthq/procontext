# Library Resolution Strategy

**Status:** Decision Recorded (Implementation Pending)
**Last Updated:** 2026-03-22
**Relates to:** `resolve_library()` tool in MCP server

## Context

`resolve_library()` is the entry point for agents to find libraries. It uses a multi-phase matching strategy to locate libraries from a user's query.

Some legitimate libraries with descriptive names like "TwicPics by Frontify" are not matching user queries like "TwicPics", indicating gaps in the current resolution pipeline.

## Current Resolution Pipeline

```
resolve_library(query)
    ↓
1. Package matches (exact, normalized)
    ├─ Match query against by_package_exact index
    └─ E.g., "langchain" → finds ["langchain", "langchain-core"]
    ↓
2. Text matches (exact, normalized)
    ├─ Match query against by_text_exact index
    ├─ Covers: library_id, display name, aliases
    └─ E.g., "LangChain" (capitalized) → finds "langchain" via name index
    ↓
3. Return exact matches if found
    ↓
4. Fuzzy matches (Levenshtein distance, score ≥ 70)
    ├─ Uses rapidfuzz library
    ├─ Matches query against all terms in fuzzy_corpus
    ├─ Deduplicates by library_id (1 result per library)
    └─ E.g., "langchian" (typo) → matches "langchain" with high score
    ↓
5. Return fuzzy matches or empty list
```

## Case Study: TwicPics

**Query:** "TwicPics"
**Library:** "TwicPics by Frontify"
**Expected:** Match found
**Actual:** No match

### Why It Fails

**Phase 1-2 (Exact):** No match
- Query "twicpics" ≠ library_id "twicpics-by-frontify" (hypothetical)
- Query "twicpics" ≠ name "TwicPics by Frontify" (exact case/text mismatch)
- Query "twicpics" ≠ any alias (if not set)

**Phase 4 (Fuzzy):** Score too low
- Normalized query: `"twicpics"`
- Normalized name: `"twicpics by frontify"`
- Levenshtein distance: ~12 chars difference (" by frontify")
- Score calculation: ~60-65 / 100 (depends on algorithm)
- Cutoff: 70
- Result: Rejected ✗

### Root Cause

The library name includes a descriptive suffix (" by Frontify") that:
- Adds ~12 characters to the fuzzy comparison
- Reduces match score below the 70-point threshold
- Doesn't help users find the library

## Options Considered

### Option 1: Use Aliases (Registry Maintenance)

**Approach:** Add "TwicPics" as an alias in the registry

```json
{
  "id": "twicpics-by-frontify",
  "name": "TwicPics by Frontify",
  "aliases": ["twicpics", "twicpics-frontify"]
}
```

**Pros:**
- Simple to implement
- Zero code changes
- Explicit control over what matches what
- Already supported by phase 2 (exact text matches)

**Cons:**
- Manual maintenance burden
- Doesn't scale for "X by Y" pattern
- Requires anticipating user queries
- Other similar libraries have same problem

**Verdict:** Necessary but insufficient. Registry should have good aliases, but they shouldn't be required as a workaround.

### Option 2: Improve Fuzzy Matching

**Approach:** Strip descriptive suffixes (" by ", " from ", " for ", etc.) before fuzzy matching

```python
def normalize_fuzzy_term(raw: str) -> str:
    normalized = normalize_text_key(raw)
    normalized = re.sub(r'\s+(by|from|for)\s+.+$', '', normalized, flags=re.IGNORECASE)
    return normalized
```

**Pros:**
- Scales automatically to all "X by Y" patterns
- Handles other similar patterns (" - ", " for ")
- No manual registry maintenance
- Intelligent normalization

**Cons:**
- More complex logic
- Potential false positives if someone searches for the suffix
- Changes existing fuzzy behavior

**Verdict:** Good long-term solution, but adds complexity now.

### Option 3: Add Substring Matching as Last Resort

**Approach:** Add a final fallback phase that checks if query is a substring of library name/ID

```
Exact → Fuzzy → Substring (if nothing else matches)
```

Execution order:
1. Run exact matches (package, text)
2. If found: return
3. Run fuzzy matches
4. If found: return
5. **NEW:** Run substring matches
   - Check if query appears in name or ID
   - Low precision (many false positives)
   - Safe because it only runs when user got no results
6. If found: return
7. Return empty list

**Example:**
- Query: "TwicPics"
- Phase 1-2: No exact matches
- Phase 4: No fuzzy matches (score 60/100 < 70)
- Phase 5: Substring search finds "TwicPics" in "TwicPics by Frontify" ✓

**Pros:**
- Simple fallback mechanism
- Safe (only runs on "no results" case)
- Catches many edge cases
- Minimal performance impact

**Cons:**
- Less sophisticated than fuzzy
- Could match "py" to many libraries (but only if fuzzy fails)
- Doesn't solve "Frontify TwicPics" (different order)

**Verdict:** Good pragmatic solution for edge cases.

## Decision

**Recommended Approach: Option 1 + Option 3**

1. **Immediate:** Ensure registry has good aliases for known problematic cases
   - "TwicPics" as alias for "TwicPics by Frontify"
   - Similar aliases for other "X by Y" libraries

2. **Future:** Implement substring matching as last fallback phase
   - Add after fuzzy, before returning empty list
   - Document the matching pipeline clearly
   - Monitor which queries hit substring phase to identify patterns

3. **Long-term:** Consider Option 2 if "X by Y" pattern becomes widespread
   - Profile impact of fuzzy suffix stripping
   - Test on real queries

## Resolution Pipeline (Future)

```
resolve_library(query)
    ↓
1. Package matches (exact)
    ↓
2. Text matches (exact)
    ├─ Return if found
    ↓
3. Fuzzy matches (score ≥ 70)
    ├─ Return if found
    ↓
4. **Substring matches (NEW)**
    ├─ Check if query is substring of name or ID
    ├─ Relevance: 0.5 (low, but better than nothing)
    ├─ Return if found
    ↓
5. Return empty list
```

## Implementation Notes

### When to Implement Substring Phase

Implement when:
- Registry is complete (no quick aliases to add)
- Multiple "X by Y" cases exist
- User feedback indicates this is a common issue

### Substring Matching Details

Should match:
- Case-insensitive: "twicpics" in "TwicPics by Frontify" ✓
- Partial: "langchain" in "langchain-core" ✓
- Word boundaries: "chain" in "langchain" ✓ (or ✗ depending on design)

Should return:
- Library match with low relevance score (0.5 or lower)
- Match type: "substring" (new variant)
- Sorted by relevance descending

### Testing Strategy

Before implementing:
1. Collect failing queries from logs
2. Determine patterns (% are "X by Y", % are typos, etc.)
3. Verify substring matching would help
4. Test for false positives with common terms

## Registry Maintenance Best Practices

To minimize resolution failures:

1. **Naming conventions:** Avoid complex naming patterns in base name
   - Prefer: separate components as aliases
   - "TwicPics" as ID, "TwicPics by Frontify" as display name ✗
   - Better: "twicpics" as ID, "TwicPics by Frontify" as name, "twicpics" as alias

2. **Aliases:** Provide multiple variants
   - Common abbreviations: "TC" for "TwicPics"
   - Without descriptors: "TwicPics" as alias (even if in display name)
   - Alternative names: "Twic" if users call it that

3. **IDs:** Keep minimal and searchable
   - Use kebab-case for hyphenation
   - Avoid "by X" in ID
   - Example: "twicpics-by-frontify" (acceptable, contains core name)

## Questions & Answers

**Q: Why not just improve fuzzy to 100%?**
A: Fuzzy matching is fundamentally a heuristic. Perfect matching requires either exact aliases or understanding user intent, which requires context.

**Q: Couldn't substring match too much?**
A: Only a problem if fuzzy fails. Users getting substring results are happy to have any result. If fuzzy gets better, we'd return those first.

**Q: What if user searches "Frontify"?**
A: Would not match with substring (Frontify only appears after "by"). Would need alias or proper fuzzy. Acceptable trade-off.

**Q: Should substring phase use regex word boundaries?**
A: Depends on use case. For first implementation: simple substring (no boundaries). Refine based on logs.

## References

- `src/procontext/tools/resolve_library/resolver.py` - Resolution logic
- `src/procontext/normalization.py` - Query normalization
- `src/procontext/models/registry.py` - Registry data structure
- RFC: `resolve_library` in MCP server instructions
