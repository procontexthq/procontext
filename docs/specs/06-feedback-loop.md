# ProContext: Feedback Loop Design

> **Document**: 06-feedback-loop.md
> **Status**: Draft v1
> **Last Updated**: 2026-03-15

---

## Table of Contents

- [1. Motivation](#1-motivation)
- [2. Prior Art: Context-Hub](#2-prior-art-context-hub)
  - [2.1 Annotations (Local Learning)](#21-annotations-local-learning)
  - [2.2 Feedback (Global Quality Signal)](#22-feedback-global-quality-signal)
  - [2.3 Key Design Choices](#23-key-design-choices)
- [3. ProContext Adaptation](#3-procontext-adaptation)
  - [3.1 What Maps Well](#31-what-maps-well)
  - [3.2 What Does Not Map](#32-what-does-not-map)
- [4. Annotations](#4-annotations)
  - [4.1 Storage](#41-storage)
  - [4.2 MCP Tool: annotate_page](#42-mcp-tool-annotate_page)
  - [4.3 Auto-Inclusion in Existing Tools](#43-auto-inclusion-in-existing-tools)
  - [4.4 AnnotationStore Protocol](#44-annotationstore-protocol)
- [5. Feedback](#5-feedback)
  - [5.1 Storage](#51-storage)
  - [5.2 MCP Tool: feedback_page](#52-mcp-tool-feedback_page)
  - [5.3 Integration with Existing Tools](#53-integration-with-existing-tools)
- [6. Infrastructure Changes](#6-infrastructure-changes)
  - [6.1 AppState](#61-appstate)
  - [6.2 Configuration](#62-configuration)
  - [6.3 Error Codes](#63-error-codes)
  - [6.4 Protocols](#64-protocols)
- [7. Implementation Sequence](#7-implementation-sequence)
- [8. Privacy](#8-privacy)
- [9. Design Decisions](#9-design-decisions)
- [10. Open Questions](#10-open-questions)

---

## 1. Motivation

ProContext gives agents accurate documentation, but agents have no way to persist discoveries about that documentation across sessions. If an agent discovers that a page's async example is missing an `await` keyword, or that webhook verification requires the raw request body, that knowledge is lost when the session ends. The next session with the same page starts from zero.

A feedback loop addresses this with two mechanisms:

1. **Annotations** — local notes that agents save for themselves, automatically surfaced on subsequent fetches.
2. **Feedback** — structured quality ratings on documentation pages, stored for future use.

The design is inspired by [context-hub](https://github.com/nichochar/context-hub), a Node.js documentation distribution system that implements both mechanisms. This document first describes how context-hub does it, then defines how ProContext adapts the concept.

---

## 2. Prior Art: Context-Hub

Context-hub (`chub`) is an open-source CLI and MCP server that distributes curated documentation and skills to AI agents. It implements a self-improving loop through two complementary features.

### 2.1 Annotations (Local Learning)

Annotations are per-machine notes that agents attach to documentation entries. They persist across sessions and are automatically included when the same entry is fetched again.

**Storage**: JSON files in `~/.chub/annotations/`, one file per entry ID. Entry ID slashes are converted to dashes for safe filenames (e.g., `stripe/api` becomes `stripe--api.json`).

**Format**:

```json
{
  "id": "stripe/api",
  "note": "Webhook verification requires raw body",
  "updatedAt": "2025-01-15T10:30:00Z"
}
```

**CRUD operations** via the `chub annotate` CLI command:

| Command | Effect |
|---------|--------|
| `chub annotate <id> <note>` | Save or replace annotation |
| `chub annotate <id>` | View existing annotation |
| `chub annotate <id> --clear` | Remove annotation |
| `chub annotate --list` | List all annotations |

**Auto-inclusion**: When `chub get <id>` is called and an annotation exists for that entry, the annotation is appended to the output:

```
[Doc content...]

---
[Agent note -- 2025-01-15T10:30:00Z]
Webhook verification requires raw body -- do not parse JSON before verifying
```

**MCP integration**: The `chub_annotate` tool is exposed via context-hub's MCP server, giving agents programmatic access to annotation CRUD.

### 2.2 Feedback (Global Quality Signal)

Feedback is a binary rating (up/down) with structured labels, sent to a remote API endpoint for aggregation by content authors.

**API call**:

```
POST https://api.aichub.org/v1/feedback
{
  "entry_id": "stripe/api",
  "rating": "up",
  "labels": ["accurate", "helpful"],
  "comment": "Clear examples",
  "agent": {"name": "claude-code", "model": "claude-sonnet-4"},
  "cli_version": "0.1.2"
}
```

**Labels** — a predefined taxonomy:

| Positive | Negative |
|----------|----------|
| `accurate` | `outdated` |
| `well-structured` | `inaccurate` |
| `helpful` | `incomplete` |
| `good-examples` | `wrong-examples` |
| | `wrong-version` |
| | `poorly-structured` |

**Client identity**: Each machine gets a stable anonymous ID — a SHA-256 hash of the platform's machine UUID. This correlates feedback from the same machine without collecting PII.

**Agent detection**: Context-hub auto-detects the calling agent from environment variables (e.g., `claude-code`, `cursor`, `codex`).

**CLI**: `chub feedback <id> <up|down> --label <label> [comment]`

**MCP**: `chub_feedback` tool exposed via MCP server.

### 2.3 Key Design Choices

| Choice | Rationale |
|--------|-----------|
| Annotations are local-only, not synced | Machine-specific; sync adds complexity without clear value |
| Feedback goes upstream to authors | Closes the loop — authors see what's working and what's not |
| Auto-inclusion on fetch | Zero-friction learning; agent doesn't need to remember to check annotations |
| Predefined label taxonomy | Structured feedback is easier to aggregate than freeform text |
| Anonymous machine-based identity | Privacy-preserving; stable enough for correlation |
| Both features are opt-out | On by default via config; disable with `feedback: false` or env var `CHUB_FEEDBACK=0` |

**Data flow**:

```
Agent fetches doc
  |
  +--> Discovers a gotcha
  |
  +--> Saves annotation locally    (for next session)
  |    |
  |    +--> Next session: annotation auto-included in fetch
  |
  +--> Sends feedback upstream     (for doc authors)
       |
       +--> Authors improve docs for everyone
```

---

## 3. ProContext Adaptation

### 3.1 What Maps Well

**Annotations** translate naturally. ProContext already caches pages in SQLite keyed by `sha256(url)`. Annotations can use the same key. The auto-inclusion concept is directly applicable — when `read_page`, `search_page`, or `read_outline` return results, any annotations for that URL are included.

**Feedback storage** works locally. ProContext's SQLite layer can store structured ratings alongside annotations.

**MCP tool exposure** fits ProContext's existing pattern — a tool handler function, Pydantic input/output models, and registration in `server.py`.

### 3.2 What Does Not Map

| Context-Hub | ProContext | Adaptation |
|-------------|-----------|------------|
| Keys by entry ID (`stripe/api`) | Keys by URL | Use `sha256(url)`, same as page cache |
| JSON file storage | SQLite database | Use existing async SQLite layer |
| Upstream feedback API | No backend server; "no telemetry" guarantee | Store feedback locally only |
| Machine-based client ID | Not needed without upstream | Skip entirely |
| Agent auto-detection from env | Not needed without upstream | Skip entirely |
| One annotation per entry (replace) | Multiple annotations per URL | Allow multiple, cap at 20 |

---

## 4. Annotations

### 4.1 Storage

A new `annotations` table in the existing SQLite database.

**Schema**:

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-increment annotation ID |
| `url_hash` | TEXT NOT NULL | `sha256(url)`, same key as page cache |
| `url` | TEXT NOT NULL | Original URL for human reference |
| `note` | TEXT NOT NULL | Freeform annotation text |
| `created_at` | TEXT NOT NULL | ISO 8601 UTC timestamp |
| `updated_at` | TEXT NOT NULL | ISO 8601 UTC timestamp |

**Index**: `idx_annotations_url_hash` on `url_hash`.

**Constraints**:

- No `FOREIGN KEY` to `page_cache` — annotations must survive cache expiration and cleanup.
- Maximum 20 annotations per URL (enforced at the application layer, not SQL).
- Maximum 2000 characters per note.

**Why SQLite, not JSON files**: ProContext already has a mature async SQLite layer (`Cache` class) with error handling patterns, atomic writes, and query capability. JSON files would introduce a second storage backend, require filesystem enumeration for listing, and lack atomicity.

### 4.2 MCP Tool: `annotate_page`

A single tool with an `action` parameter handles create, list, and remove. This keeps the tool count at 6 (4 existing + 2 new) rather than 8.

**Input**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `action` | string (enum) | Yes | — | `"add"`, `"list"`, or `"remove"` |
| `url` | string | Yes | — | URL of the documentation page (max 2048 chars) |
| `note` | string | When `action = "add"` | — | Annotation text (max 2000 chars) |
| `annotation_id` | integer | When `action = "remove"` | — | ID of the annotation to remove |

**Output for `action: "add"`**:

| Field | Type | Description |
|-------|------|-------------|
| `action` | string | `"add"` |
| `url` | string | Canonical URL |
| `annotation_id` | integer | ID of the created annotation |
| `note` | string | The saved annotation text |
| `total_annotations` | integer | Total annotations for this URL after adding |

**Output for `action: "list"`**:

| Field | Type | Description |
|-------|------|-------------|
| `action` | string | `"list"` |
| `url` | string | Canonical URL |
| `annotations` | array | List of `{id, note, created_at}` objects |
| `total_annotations` | integer | Count of annotations for this URL |

**Output for `action: "remove"`**:

| Field | Type | Description |
|-------|------|-------------|
| `action` | string | `"remove"` |
| `url` | string | Canonical URL |
| `annotation_id` | integer | ID of the removed annotation |
| `removed` | boolean | `true` if the annotation was found and removed |

**Error cases**:

| Condition | Error Code | Recoverable |
|-----------|------------|-------------|
| `action: "add"` without `note` | `INVALID_INPUT` | `false` |
| `action: "remove"` without `annotation_id` | `INVALID_INPUT` | `false` |
| Non-existent `annotation_id` | `INVALID_INPUT` | `false` |
| `note` exceeds 2000 characters | `INVALID_INPUT` | `false` |
| URL exceeds 2048 characters | `INVALID_INPUT` | `false` |
| URL already has 20 annotations | `ANNOTATION_LIMIT_REACHED` | `false` |
| Feature disabled via config | `FEATURE_DISABLED` | `false` |

### 4.3 Auto-Inclusion in Existing Tools

When `read_page`, `search_page`, or `read_outline` return results for a URL that has annotations, the annotations are included in the output via a new `annotations` field.

**New field on `ReadPageOutput`, `SearchPageOutput`, `ReadOutlineOutput`**:

| Field | Type | Description |
|-------|------|-------------|
| `annotations` | string or null | Formatted annotations block, or `null` if none exist |

**Format**:

```
[Annotations for this page]
- (2026-03-14) The async example is missing an await keyword. [#5]
- (2026-03-15) Webhook verification requires the raw request body. [#7]
```

The `[#5]` suffix is the annotation ID, allowing the agent to reference it for removal via `annotate_page`.

**Why a separate field**: Mixing annotations into the `content` field would corrupt line numbers that `offset`, outline entries, and `search_page` matches reference. A dedicated field preserves content integrity.

**Injection point**: Each tool handler (`read_page.py`, `search_page.py`, `read_outline.py`) calls the page service after `fetch_or_cached_page` returns. The annotation lookup helper can run on top of that result without being coupled to the fetch path itself.

**When disabled**: If `feedback.enabled` is `false`, annotation lookup is skipped and the field is `null`.

### 4.4 AnnotationStore Protocol

Following ProContext's existing protocol pattern (`CacheProtocol`, `FetcherProtocol`):

| Method | Signature | Description |
|--------|-----------|-------------|
| `add` | `(url, url_hash, note) -> int` | Create annotation, return its ID |
| `list_for_url` | `(url_hash) -> list[AnnotationEntry]` | Return all annotations for a URL |
| `remove` | `(annotation_id, url_hash) -> bool` | Delete annotation, return whether it existed |
| `get_formatted` | `(url_hash) -> str` | Return formatted annotation string (empty if none) |

The protocol enables test doubles without touching the database, consistent with how `CacheProtocol` and `FetcherProtocol` are used in tests.

---

## 5. Feedback

### 5.1 Storage

A new `feedback` table in the existing SQLite database.

**Schema**:

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-increment feedback ID |
| `url_hash` | TEXT NOT NULL | `sha256(url)` |
| `url` | TEXT NOT NULL | Original URL |
| `rating` | TEXT NOT NULL | `"up"` or `"down"` |
| `labels` | TEXT NOT NULL DEFAULT '' | Comma-separated labels |
| `comment` | TEXT NOT NULL DEFAULT '' | Optional freeform comment |
| `created_at` | TEXT NOT NULL | ISO 8601 UTC timestamp |

**Index**: `idx_feedback_url_hash` on `url_hash`.

### 5.2 MCP Tool: `feedback_page`

**Input**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | Yes | — | URL of the documentation page (max 2048 chars) |
| `rating` | string (enum) | Yes | — | `"up"` or `"down"` |
| `labels` | array of strings | No | `[]` | Structured quality labels |
| `comment` | string | No | `""` | Freeform comment (max 1000 chars) |

**Valid labels**:

| Positive | Negative |
|----------|----------|
| `accurate` | `outdated` |
| `well-written` | `inaccurate` |
| | `incomplete` |
| | `wrong-examples` |
| | `confusing` |

**Output**:

| Field | Type | Description |
|-------|------|-------------|
| `url` | string | Canonical URL |
| `rating` | string | The submitted rating |
| `labels` | array | The submitted labels |
| `feedback_id` | integer | ID of the created feedback entry |
| `page_feedback_summary` | object | `{"up": int, "down": int}` — total counts for this URL |

**Error cases**:

| Condition | Error Code | Recoverable |
|-----------|------------|-------------|
| Missing `url` or `rating` | `INVALID_INPUT` | `false` |
| Invalid label value | `INVALID_INPUT` | `false` |
| `comment` exceeds 1000 characters | `INVALID_INPUT` | `false` |
| Feature disabled via config | `FEATURE_DISABLED` | `false` |

### 5.3 Integration with Existing Tools

Feedback is **not** auto-included in tool output. Automatically appending "this page has 3 downvotes" would bias the agent before it reads the content. Feedback is a passive record — it is stored and available via `feedback_page`, but does not alter the read experience.

**Future possibility**: If a page has accumulated significant negative feedback (e.g., 3+ `down` ratings with `outdated` label), a subtle `quality_warning` field could be added to `read_page` output. This is deferred to a future iteration.

---

## 6. Infrastructure Changes

### 6.1 AppState

Two new optional fields on the `AppState` dataclass:

| Field | Type | Description |
|-------|------|-------------|
| `annotation_store` | `AnnotationStoreProtocol \| None` | Annotation storage |
| `feedback_store` | `FeedbackStoreProtocol \| None` | Feedback storage |

Both default to `None`. Created and injected during the FastMCP lifespan, same pattern as `cache` and `fetcher`.

### 6.2 Configuration

New `FeedbackSettings` section in `Settings`:

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `feedback.enabled` | bool | `true` | Master switch for annotations and feedback |
| `feedback.max_annotations_per_url` | int | `20` | Cap per URL |
| `feedback.max_note_length` | int | `2000` | Character limit for annotation notes |
| `feedback.max_comment_length` | int | `1000` | Character limit for feedback comments |

In `procontext.yaml`:

```yaml
feedback:
  enabled: true
  max_annotations_per_url: 20
  max_note_length: 2000
  max_comment_length: 1000
```

**When `feedback.enabled` is `false`**: The `annotate_page` and `feedback_page` tools remain registered (tool discovery always lists them) but return a `FEATURE_DISABLED` error when called. Annotation auto-inclusion in existing tools is also skipped. This avoids conditional tool registration complexity while giving operators a kill switch.

### 6.3 Error Codes

Two new codes added to `ErrorCode`:

| Code | Description |
|------|-------------|
| `FEATURE_DISABLED` | The feedback/annotation feature is disabled via configuration |
| `ANNOTATION_LIMIT_REACHED` | URL already has the maximum number of annotations |

### 6.4 Protocols

Two new protocols in `protocols.py`:

- `AnnotationStoreProtocol` — see [Section 4.4](#44-annotationstore-protocol)
- `FeedbackStoreProtocol` — methods: `add(url, url_hash, rating, labels, comment) -> int`, `get_summary(url_hash) -> dict`

---

## 7. Implementation Sequence

### Step 1: Storage Layer

- Add `FeedbackSettings` to config
- Add `AnnotationStoreProtocol` and `FeedbackStoreProtocol` to protocols
- Create `AnnotationEntry` and `FeedbackEntry` models
- Implement `AnnotationStore` (new file: `annotation_store.py`)
- Implement `FeedbackStore` (new file: `feedback_store.py`)
- Table creation in lifespan (alongside existing `Cache.init_db()`)
- Unit tests for both stores

### Step 2: Tool Handlers

- Create `tools/annotate_page.py` with `handle()` function
- Create `tools/feedback_page.py` with `handle()` function
- Add I/O Pydantic models to `models/tools.py`
- Add error codes to `errors.py`
- Register both tools in `mcp/server.py`
- Integration tests for both tools

### Step 3: Auto-Inclusion

- Add `annotations: str | None = None` field to `ReadPageOutput`, `SearchPageOutput`, `ReadOutlineOutput`
- Add annotation lookup call in `read_page.py`, `search_page.py`, `read_outline.py`
- Respect `feedback.enabled` setting
- Integration tests verifying auto-inclusion

### Step 4: AppState and Lifespan

- Add fields to `AppState`
- Create stores in lifespan, inject into state
- Update integration test fixtures

### Step 5: Documentation

- Update `01-functional-spec.md` (new tools section)
- Update `04-api-reference.md` (new tool schemas)
- Update `03-implementation-guide.md` (module acceptance criteria)
- Update `README.md`

---

## 8. Privacy

- **No PII collected.** Annotations and feedback contain only documentation URLs and user-authored text. No session IDs, user identifiers, or machine fingerprints.
- **All local.** Nothing leaves the machine. ProContext's security spec (Section 6) states "No telemetry or analytics." The feedback system maintains this guarantee.
- **Deletable.** Users can delete all feedback data by deleting the SQLite database, same as the existing cache.

---

## 9. Design Decisions

**D8: Annotations in SQLite, not JSON files.**
Context-hub uses JSON files. ProContext already has a mature async SQLite layer with error handling patterns. Using SQLite avoids a second storage backend, provides atomic writes, and enables efficient queries by URL hash. JSON files would require filesystem enumeration, lack atomicity, and introduce a new error surface.

**D9: Single `annotate_page` tool with action parameter, not three separate tools.**
A single tool with an `action` parameter (`add`/`list`/`remove`) keeps the tool count at 6 (from 4). Adding three tools (`add_annotation`, `list_annotations`, `remove_annotation`) would push to 8, conflicting with the "minimal footprint" design philosophy.

**D10: Auto-inclusion in a separate field, not mixed into content.**
Mixing annotations into `content` would corrupt line number references used by `offset`, outline entries, and `search_page` matches. A dedicated `annotations` field preserves content integrity while still surfacing discoveries automatically.

**D11: Feedback stored locally, not sent upstream.**
ProContext has no backend API. Sending feedback to a third-party service contradicts the "no telemetry" guarantee. Local storage provides value (quality tracking, agent awareness) without privacy compromise. Upstream feedback can be added later behind an opt-in flag.

**D12: `feedback.enabled` as a kill switch, not conditional tool registration.**
Conditionally registering tools based on config adds complexity to the lifespan and makes the tool surface area unpredictable. Always-registered tools with a `FEATURE_DISABLED` error are simpler, discoverable, and self-documenting.

**D13: Multiple annotations per URL, not single-replace.**
Context-hub stores one annotation per entry (overwrite semantics). ProContext allows multiple annotations per URL because a page may have several independent discoveries worth preserving. A cap of 20 prevents runaway accumulation.

---

## 10. Open Questions

1. **Annotation lifecycle vs. cache lifecycle.** If the user deletes the SQLite database to reset the cache, annotations are also lost. Should annotations live in a separate database file (e.g., `annotations.db`) to decouple their lifecycle from the cache?

2. **Section-level annotations.** The current design keys annotations to the full URL. Should there be an optional `line_number` or `section` field to associate annotations with specific parts of a page? This adds precision but complicates the data model and auto-inclusion logic.

3. **Feedback-informed quality warnings.** Should `read_page` show a subtle indicator when a page has accumulated significant negative feedback? This could help agents be cautious, but risks biasing them before reading the content.

4. **Tool count.** Going from 4 to 6 tools is a 50% increase. An alternative is a single `page_feedback` tool that combines annotation and feedback actions under one umbrella. Trade-off: fewer tools vs. a more complex action parameter space.

5. **Annotation staleness.** Should annotations older than a configurable threshold (e.g., 90 days) be auto-pruned or flagged as potentially stale? Documentation evolves, and old annotations may become misleading.
