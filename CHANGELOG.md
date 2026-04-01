# CHANGELOG


## v0.1.2 (2026-04-01)

### Bug Fixes

- Handle malformed outline lines gracefully instead of crashing
  ([`983ce0a`](https://github.com/procontexthq/procontext/commit/983ce0a91bf52c57a3385698e17f87814adc6bb1))

Replace .index() with .find() and skip lines without a colon separator, logging a warning for
  debuggability. Also remove a redundant assert that was inside an equivalent if-check.

- Prevent TOCTOU race in client ID creation
  ([`a307dc3`](https://github.com/procontexthq/procontext/commit/a307dc326c4d754190868106fb770df8c33c5611))

Use os.O_EXCL for exclusive file creation so concurrent callers cannot overwrite each other's client
  IDs. Falls back to reading the existing file if another process created it first.

- Replace assert guards with proper runtime checks in page service
  ([`c13c908`](https://github.com/procontexthq/procontext/commit/c13c908023f068790a6f5a98c2ab2f9dd4971e1a))

Assertions are skipped under python -O. Use explicit RuntimeError raises for cache and fetcher
  initialization checks so they work regardless of optimization flags.

- Validate numeric config bounds at settings load
  ([`605786a`](https://github.com/procontexthq/procontext/commit/605786a76e98f22b478a420336aa0a65d2606d4d))

- **ci**: Skip editable package in pip-audit
  ([`6ca9da2`](https://github.com/procontexthq/procontext/commit/6ca9da2661fc20c644b0668a505354f892d149eb))

pip-audit fails when procontext is not published to PyPI. The --skip-editable flag skips the local
  development install while still auditing all real dependencies.

- **ci**: Upgrade requests to 2.33.0 and ignore unfixed pygments CVE
  ([`461a249`](https://github.com/procontexthq/procontext/commit/461a2492e3c793508708d1a2d466a9427fe2964b))

- Upgrade requests 2.32.5 → 2.33.0 (fixes CVE-2026-25645) - Ignore CVE-2026-4539 for pygments 2.19.2
  (no fix available, dev-only)

- **deps**: Upgrade cryptography to 46.0.6 (CVE-2026-34073)
  ([`7267058`](https://github.com/procontexthq/procontext/commit/72670587895ab29cfbbd00f7fcd2dca9a46888b7))

- **deps**: Upgrade pygments to 2.20.0 (CVE-2026-4539)
  ([`3fb8f04`](https://github.com/procontexthq/procontext/commit/3fb8f04164a388354e9fd01607700c9bde11f2a5))

Removes the --ignore-vuln workaround from CI now that pygments 2.20.0 ships with the ReDoS fix.

- **security**: Use constant-time comparison for bearer token auth
  ([`14ad901`](https://github.com/procontexthq/procontext/commit/14ad901f09b5ed397136e6eba0be1ecc298d5840))

Replace string != with secrets.compare_digest() to prevent timing side-channel attacks on the bearer
  key in HTTP transport mode.

### Chores

- Fix lint in normalization tests and format search_page tests
  ([`feaa6fd`](https://github.com/procontexthq/procontext/commit/feaa6fda19128c6e1a57d77a7172fa1143c6c2dd))

### Continuous Integration

- Gate PyPI publish behind environment approval
  ([`32c062e`](https://github.com/procontexthq/procontext/commit/32c062e014df192c36acc4692a3493b4f118ce0a))

- Harden workflows for reproducibility and smoke coverage
  ([`3e64025`](https://github.com/procontexthq/procontext/commit/3e640255eda73f7ec5ad0e948d6a6c658e475703))

### Documentation

- Add branching guideline to git operations policy
  ([`e0e654e`](https://github.com/procontexthq/procontext/commit/e0e654e0c5e1c742ba8ce0194e335d2bf76efe49))

- Add PR-based merge policy to git operations guidelines
  ([`e68090c`](https://github.com/procontexthq/procontext/commit/e68090cfa5c3de65ded2cb76427e04cb7028d4fb))

Prevent direct local merges into main — all changes must go through a pull request to ensure CI runs
  and changes are reviewed.

- Align MCP specs with current tool contract
  ([`f7dc7bb`](https://github.com/procontexthq/procontext/commit/f7dc7bb045b403b3595af6cece2c586b69d24786))

- Clarify intentional HEAD probe in doctor check
  ([`cb45cf3`](https://github.com/procontexthq/procontext/commit/cb45cf3cb0b00e0c72878ac93eb54df5cd44f18f))

- Clarify testing guideline on unit vs integration test scope
  ([`694c5fb`](https://github.com/procontexthq/procontext/commit/694c5fb4da08d14ca62771a1eae29959ab669f54))

Rewrite guideline #19 to distinguish integration tests (test public API contracts) from unit tests
  (test internal functions with complex logic). Removes the blanket 'do not reach into private
  methods' statement that contradicted the actual test suite.

- Improve grammar and clarity in MCP tool descriptions
  ([`9c180b3`](https://github.com/procontexthq/procontext/commit/9c180b38807ed5624b5688b19c91a525d78346dc))

Fix grammar issues (semicolons, missing verbs), remove "useful for broad search" phrasing that
  steered agents toward full_docs_url, clarify ambiguous wording in search_page and read_outline
  descriptions.

- Refresh README with comparison table, logo, and section emojis
  ([`af5d7c0`](https://github.com/procontexthq/procontext/commit/af5d7c0b949838ebca92090cbbfc341b24ae3fff))

Rewrote the "Why ProContext" section as a side-by-side comparison table, added the project logo
  inline with the heading, and updated the intro copy and section headings for clarity.

- Rewrite README intro and rename setup guide to integration guide
  ([`4dd6743`](https://github.com/procontexthq/procontext/commit/4dd6743f51af422cddb47e3f73e79ef8af54351e))

Tightened the README intro, replaced the feature bullet list with a comparison table, and renamed
  docs/setup.md to docs/integration-guide.md to distinguish it from the installation guide.

- Rewrite tool descriptions for clarity and consistency
  ([`9014960`](https://github.com/procontexthq/procontext/commit/90149606a164fa913db54be9133ac982f49c3db7))

Rename "smart outline" to "compact outline" throughout, reorganize resolve_library input docs,
  simplify search_page and read_page descriptions, and tighten server.py Field descriptions.

- Tighten README intro and update badge colors
  ([`3ee4aa1`](https://github.com/procontexthq/procontext/commit/3ee4aa1e9d7dd083e599d9fbf0012e053b0d4cdd))

### Refactoring

- Move search imports to module level in search_page
  ([`ae0cd87`](https://github.com/procontexthq/procontext/commit/ae0cd87e6fa194289b31f00e1aaef0ccafcb2d83))

Move LineMatch and SearchResult imports from inside _search_outline_lines to the top of the file,
  per coding guideline #16.

- Simplify tool descriptions and drop output model Field descriptions
  ([`7816234`](https://github.com/procontexthq/procontext/commit/7816234058b0cf1e47aabf484c6246c66125b7f6))

- Streamline SERVER_INSTRUCTIONS and RESOLVE_LIBRARY_DESCRIPTION to cover libraries, frameworks,
  protocols, SDKs, and standards - Remove Field(description=...) from output models since MCP
  clients do not receive them; tool_docs.py is the single source of truth - Update wire contract
  test to match simplified server instructions

- Use precise type hint for cached_entry parameter
  ([`aced42f`](https://github.com/procontexthq/procontext/commit/aced42f3b8ce886248d7d19ee944f9dcd4536ffc))

Replace generic object type with PageCacheEntry | None on _maybe_spawn_refresh, reflecting the
  actual expected type.

### Testing

- Add fuzzy search edge case tests for resolver (83% → 85%)
  ([`b8c5a90`](https://github.com/procontexthq/procontext/commit/b8c5a903f5910ea04782980cea702af6db5fe1d2))

Cover empty corpus, zero limit, and whitespace-only query paths in the fuzzy search fallback.

- Add unit tests for normalization module (69% → 100%)
  ([`1b8bcd0`](https://github.com/procontexthq/procontext/commit/1b8bcd0c04f832743c87c20da1723b2332d1af20))

Cover URL normalization edge cases (IPv6, userinfo, invalid ports, default port removal), origin
  extraction validation, exact origin validation, and dependency modifier detection.

- Improve search_page coverage (79% → 92%)
  ([`caddaf9`](https://github.com/procontexthq/procontext/commit/caddaf91c31e7efc0b3c1fc57dafa4944f4b6e6d))

Add tests for large outline compaction paths: no-match compaction, compactable outline with note,
  dense match range, and outline search pagination with has_more lookahead.

- Keep refresh internals in unit coverage
  ([`9b91ceb`](https://github.com/procontexthq/procontext/commit/9b91cebbd6f453c4760ded799fa5d2900da7dc7a))


## v0.1.1 (2026-03-25)

### Bug Fixes

- Handle invalid URLs gracefully during domain extraction
  ([`86a0054`](https://github.com/procontexthq/procontext/commit/86a00541653d38f12e4f9f7dc1ec6ba132bb8239))

When extracting domains from documentation content, urlparse() can raise ValueError for malformed
  URLs (e.g., invalid IPv6 format). Wrap the URL parsing in a try-except block to skip invalid URLs
  instead of crashing.

This fixes an issue where processing large files like llms-full.txt could fail due to malformed URLs
  in the documentation content.

Add regression test to verify invalid URLs are skipped.

- Include exception details in JSON log output
  ([`828a724`](https://github.com/procontexthq/procontext/commit/828a724c9949bba76709ca8e0a0d35e14ee8a445))

- Include stale metadata in search responses
  ([`4771d52`](https://github.com/procontexthq/procontext/commit/4771d5219709d95e6573e6be2177046b1220f773))

- Log invalid URLs instead of silently swallowing exceptions
  ([`2eff51c`](https://github.com/procontexthq/procontext/commit/2eff51c162f536481fe78c10206e942c60dbc3c5))

When parsing URLs extracted from documentation content, gracefully handle ValueError from urlparse()
  by logging the malformed URL instead of silently continuing. This provides visibility into
  problematic content while preventing crashes when processing large files like llms-full.txt.

Logging includes the truncated URL and error message for debugging.

Also update expand_allowlist_from_content() to always extract and return discovered domains (for
  cache persistence) while only expanding the live allowlist when in "discovered" mode. This
  simplifies the logic compared to the previous optimization that skipped extraction entirely in
  "registry" mode.

Remove ALLOWLIST_ANALYSIS.md as the performance optimization it documented is no longer implemented.

- Move registry pre-flight to main() and clean up scheduler
  ([`e01ea44`](https://github.com/procontexthq/procontext/commit/e01ea44f405145cb94c42f10bed2f1c6d4a046b0))

- sys.exit(1) inside the async lifespan was wrapped in a BaseExceptionGroup by anyio, preventing a
  clean exit when the registry was missing. Moved the registry check and auto-setup to main() where
  sys.exit(1) is synchronous and reliable. - Replaced print() for the registry-not-found error with
  log.critical() now that structlog is configured before that code path runs. - Removed
  skip_initial_check parameter from run_registry_update_scheduler; both transports now use
  registry_check_is_due to decide whether to check or defer, keeping the scheduler self-contained. -
  Added regression test that verifies clean exit (code 1, no ExceptionGroup traceback) when registry
  is absent.

- Narrow exception catches to match failure surfaces (Rule 11)
  ([`5737e10`](https://github.com/procontexthq/procontext/commit/5737e10f6670640512e17b839d80b0847e605451))

- storage.py: catch (OSError, json.JSONDecodeError, ValueError, KeyError) in registry_check_is_due —
  pure local computation with enumerable failures - _shared.py: catch ProContextError in .md probe —
  the only exception fetcher.fetch() legitimately raises; bugs should not hide behind fallback -
  schedulers.py: wrap pre-loop registry_check_is_due in try/except to prevent unexpected exceptions
  from killing the long-running scheduler

- Narrow exception handling per coding guidelines (Rule 11)
  ([`1e8f665`](https://github.com/procontexthq/procontext/commit/1e8f66505b8bd4109df47b811a1d24d6ae7c7e4f))

- registry/storage.py: catch specific exceptions (OSError, JSONDecodeError, ValueError, KeyError)
  instead of bare Exception in registry_check_is_due - tools/_shared.py: keep broad catch in
  _fetch_with_md_probe (speculative probe must always fall back gracefully) but add exc_info=True
  for visibility and downgrade to log.debug

- Pre-release review — dead config, type gaps, security defaults, test coverage
  ([`e38121b`](https://github.com/procontexthq/procontext/commit/e38121b1a9da8c1327be3937cd28bd2cda98f0c6))

- Remove dead RegistrySettings.url field (never referenced; metadata_url drives the two-step
  registry fetch) - Use __version__ from importlib.metadata in fetcher User-Agent header;
  __init__.py now reads version from installed package metadata instead of hardcoding it, making
  pyproject.toml the single source of truth - Strengthen LibraryMatch.matched_via and
  _match_from_entry parameter to Literal["package_name","library_id","alias","fuzzy"] — pyright now
  enforces valid values at every call site - Drop stale security controls summary table from
  05-security-spec.md (all 9 implemented controls are already documented in threat sections); move
  SLSA attestation to ROADMAP.md as the one outstanding item - Change default HTTP server host from
  0.0.0.0 to 127.0.0.1 — safe by default; users opt into network-wide binding explicitly; update all
  spec and doc references to match - Add wire-level subprocess tests for get_library_docs (cache hit
  and LIBRARY_NOT_FOUND error envelope) — the only tool without coverage at the JSON-RPC boundary;
  add _seed_toc_cache helper alongside existing _seed_page_cache

- Preserve small search outline context
  ([`e64e522`](https://github.com/procontexthq/procontext/commit/e64e5220379f7f99d768fc12858ff0e72946c563))

- Reject unknown config fields and surface ValidationError cleanly
  ([`bb88802`](https://github.com/procontexthq/procontext/commit/bb88802065f5fe7f373e7db5496ecde8a0e0acc8))

Add extra="forbid" to all nested settings models so a YAML typo like db_paht is a hard
  ValidationError at startup rather than silent data loss. Catch ValidationError in main() and print
  a clean human-readable message instead of a raw traceback.

Add tests covering all config validation and startup error scenarios (wrong type, unknown nested
  field, missing db_path parent dirs auto-created, unwriteable db dir) for both stdio and HTTP
  transports.

- Remove docs_url from resolve_library response and fix server.py nits
  ([`7e73aa8`](https://github.com/procontexthq/procontext/commit/7e73aa8ed99e313e4ca4e05f7fe6bae32f936095))

docs_url (the human docs homepage) served no purpose in the tool response — it's not a valid input
  to any tool and risks confusing agents into bypassing the llms.txt pipeline. Also remove a stale
  Phase 2 comment and fix a typo in the setup error message.

- Return null outline in search outline mode, preserve outline on no matches
  ([`ea5f7ea`](https://github.com/procontexthq/procontext/commit/ea5f7eaf975884854248bb178635944667074570))

search_page outline field now returns null when target="outline" (matches already are outline
  entries) instead of an empty string. When content search finds no matches, the full outline is
  still returned for context instead of being empty.

- Revert to broad except in registry_check_is_due
  ([`2f158f4`](https://github.com/procontexthq/procontext/commit/2f158f49e493e6d801ee47a22dbd56f45eb8ddd2))

Same reasoning as _fetch_with_md_probe: this is a best-effort check where the safe fallback (return
  True = "check is due") is always correct. Crashing the scheduler over a state file parse error is
  worse than one extra metadata poll.

- Tighten markdown outline parsing
  ([`46bc065`](https://github.com/procontexthq/procontext/commit/46bc0651aa9790c1eccf038c31157bfc8d77eb96))

- Update registry metadata URL to procontexthq.github.io
  ([`0089f8e`](https://github.com/procontexthq/procontext/commit/0089f8eb48e17b8af3d56c0bba3d6dcccbbb8019))

Correct the default metadata_url in config.py, procontext.example.yaml, and the technical spec from
  procontext.github.io to procontexthq.github.io.

- Use exc_info=True for caught exceptions per coding guidelines
  ([`148d9f7`](https://github.com/procontexthq/procontext/commit/148d9f7a45c41d5aef26fca62bd5c3ca335d7b6b))

- registry/storage.py: log suppressed exception in registry_check_is_due instead of silently
  returning True - registry/update.py: replace error=str(exc) with exc_info=True in _safe_get so
  structlog captures the full traceback structurally - test_mcp_wire_contract.py: clarify expected
  OSError comment in cleanup

- **deps**: Pin pyjwt>=2.12.0 to resolve CVE-2026-32597
  ([`5296b47`](https://github.com/procontexthq/procontext/commit/5296b47014d4935e5d28546c3dc03ecacafa4ef3))

pyjwt 2.11.0 (transitive via mcp) was flagged by pip-audit. Adding a direct lower-bound constraint
  forces resolution to the patched version (2.12.1).

- **installer**: Harden platform install fallbacks
  ([`a4c6323`](https://github.com/procontexthq/procontext/commit/a4c632332b1ed277d78ef304655b18b4d7bf0dc6))

- **parser**: Support up to 3 spaces of indentation on headings
  ([`949efce`](https://github.com/procontexthq/procontext/commit/949efce05da95bf09535fd6f652d81e588279db3))

CommonMark allows 0–3 spaces of indentation before the # character. Update the heading regex from
  ^(#{1,4}) to ^ {0,3}(#{1,4}) so indented headings are detected correctly. 4-space indented lines
  (indented code blocks) are correctly excluded. Adds a dedicated test class covering 1-, 2-,
  3-space indentation and the 4-space exclusion.

- **read_page**: Append .md to path component, not raw URL string
  ([`d9ac1d2`](https://github.com/procontexthq/procontext/commit/d9ac1d24b635a5efaddb06cdb8eb44b8e540cb28))

URLs with fragments (e.g. /page#section) were incorrectly producing /page#section.md — .md ended up
  inside the fragment, so the server never saw it. Use urlunparse to insert .md into the path only,
  yielding /page.md#section. Fragments are stripped by httpx before sending, so the actual request
  goes to /page.md as intended.

- **read_page**: Fall back to original URL when .md probe fails
  ([`e1b3453`](https://github.com/procontexthq/procontext/commit/e1b3453ca37fb582f80e7f0b24932702736c2e5c))

- Try url+".md" on cache miss; catch any failure (404, timeout, network error) and fall back to the
  original URL silently - 200 HTML from the .md probe is accepted as-is — the original URL would
  return the same content on an SPA, so falling back adds no value - .md is never appended to
  redirect targets; redirects follow the server's Location header as-is - Fix fetcher to skip domain
  allowlist check on redirect hops so cross-domain redirects (e.g. docs.anthropic.com →
  platform.claude.com) are followed; private IP check still runs on every hop - Remove _is_html()
  helper — no longer needed under the fallback model

- **read_page**: Skip .md probe for URLs with query parameters
  ([`18f0ce0`](https://github.com/procontexthq/procontext/commit/18f0ce0f315d1e4568a9558640234ddf180e6edf))

URLs with query strings are served by dynamic servers that don't serve raw markdown at .md paths —
  the probe would always 404. Skip it and fetch the original URL directly.

Rename _has_file_extension to _should_probe_md to make the intent explicit. The function now
  consolidates all skip conditions: real alphabetic extension, trailing slash / empty segment, and
  query string.

- **read_page**: Skip .md probe only for alphabetic file extensions
  ([`b5493c4`](https://github.com/procontexthq/procontext/commit/b5493c4994abdc2f0cbc1bfec4c30c65fdc26cc3))

Replace the endswith('.md') check with _has_file_extension(), which uses os.path.splitext and checks
  ext[1:].isalpha(). This ensures version segments like v1.2 are not mistaken for file extensions —
  those URLs are still probed with .md. Any URL with a real alphabetic extension (.md, .txt, .html,
  etc.) skips probing as before.

- **transport**: Accept IPv6 loopback origins in security middleware
  ([`7b0b270`](https://github.com/procontexthq/procontext/commit/7b0b270d4f1e57ad869b1722becac3997d60ac76))

Replace the localhost-only regex with _is_loopback_origin() using
  ipaddress.ip_address().is_loopback, so [::1] is correctly accepted alongside localhost and
  127.0.0.1. Add edge-case tests for non-http schemes, query/fragment in origins, and missing
  hostnames.

### Chores

- Add changelog-release skill and update CLAUDE.md
  ([`fec1fdf`](https://github.com/procontexthq/procontext/commit/fec1fdf091259f67f48d8a8da56a0ff0ecf58bc5))

- Apply ruff formatting to integration and registry test files
  ([`99244f3`](https://github.com/procontexthq/procontext/commit/99244f31ac1a70d4a09cfb293a97d14dbab9632c))

- Remove orphaned data/ package directory
  ([`f6ba67f`](https://github.com/procontexthq/procontext/commit/f6ba67fab23880caac3bcaef759b2fe6211675f3))

The bundled known-libraries.json snapshot and its accompanying __init__.py were only needed by
  load_bundled_registry(), which was removed when the registry overhaul replaced the bundled
  fallback with an explicit setup command. Nothing in the codebase references procontext.data
  anymore.

- Update changelog, CLAUDE.md checks policy, and changelog-release skill
  ([`3a4347b`](https://github.com/procontexthq/procontext/commit/3a4347b992f5df61aa545ae9705951d0f26d811e))

- Populate [Unreleased] with Added/Changed entries for the registry overhaul (setup command,
  auto-setup fallback, new config options, bundled snapshot removal) - Add pre-push checks
  requirement to CLAUDE.md (ruff, pyright, pytest) - Add user-facing definition to changelog-release
  skill to prevent internal refactors from appearing in the changelog

- **installer**: Consolidate root install workflow
  ([`ec75a6a`](https://github.com/procontexthq/procontext/commit/ec75a6afd1ddc847d5f01c0a02ef0094270e820b))

- **license**: Switch from GPL-3.0 to MIT
  ([`19e85fc`](https://github.com/procontexthq/procontext/commit/19e85fceec04916cc798fcb7f8d3554d98458e7e))

MIT removes enterprise adoption friction (many orgs have blanket GPL policies), aligns with the MCP
  ecosystem (Context7 Apache-2.0, context-hub MIT), and simplifies the open-core model. The actual
  competitive moat is the registry, pre-warmed indexes, and enterprise features — not the copyleft
  license.

- **release**: Bump version to 0.1.1
  ([`58ec16e`](https://github.com/procontexthq/procontext/commit/58ec16e34e355aa4d46cb416594116ecfa1fa653))

### Continuous Integration

- Add release pipeline with python-semantic-release and PyPI publish
  ([`8313a9c`](https://github.com/procontexthq/procontext/commit/8313a9c6cd43dcf77adc424504883b94d9611af0))

Adds a manual-trigger workflow that: - Uses python-semantic-release to determine the version bump
  from conventional commits since the last tag, update pyproject.toml, and push the vX.Y.Z tag back
  to the repo. - Builds the package with uv build. - Publishes to PyPI via OIDC trusted publishing
  (no token secrets needed, configure the Trusted Publisher on pypi.org before first use).

Also tags the current commit as v0.1.0 so semantic-release has a known baseline to scan from.

- Add SLSA provenance attestation to release workflow
  ([`4129be6`](https://github.com/procontexthq/procontext/commit/4129be6dc19dd421d1d4a177328d0503453600f8))

Adds the actions/attest-build-provenance step so each PyPI release ships a cryptographic attestation
  linking the published artifact to the exact source commit. Adds the required attestations: write
  permission to the workflow.

- Enable branch coverage and raise threshold to 90%
  ([`98ed8e9`](https://github.com/procontexthq/procontext/commit/98ed8e9fc7135187b6c46c4815d43672424140d8))

- Add branch = true to [tool.coverage.run] in pyproject.toml - Add anyio to explicit runtime
  dependencies (was implicit transitive dep) - Raise --cov-fail-under from 80 to 90 in ci.yml -
  Update testing section in implementation guide: anyio preference, branch coverage metric, and sync
  ci.yml example to match actual workflow

### Documentation

- Add comprehensive allowlist expansion robustness and performance analysis
  ([`3fada93`](https://github.com/procontexthq/procontext/commit/3fada9342cb740ee70d9b30171ef70df418a4ff9))

- Add comprehensive URL extraction strategy documentation
  ([`8e9f68f`](https://github.com/procontexthq/procontext/commit/8e9f68fe81e82823965dc5e70c63c13c17fdba67))

Document the design decisions behind the simple regex-based URL extraction approach used for SSRF
  domain discovery. Explain why we chose a permissive regex with error handling over strict RFC 3986
  parsing.

Add detailed inline comments to fetcher.py explaining: - Why ] is excluded (markdown link handling)
  - Known limitations (IPv6 URLs, single quotes) - Trade-offs (simplicity vs completeness) - Edge
  cases and how they're handled

Create docs/decisions/url-extraction-strategy.md covering: - Context and problem statement - Design
  decision and rationale - Extraction flow and limitations - Evaluation matrix of edge cases -
  Future improvement considerations - Q&A for common questions

This captures important context that would otherwise be lost, helping future contributors understand
  the intentional trade-offs.

- Add failing-tests-are-signals rule and AGENTS.md
  ([`1d33ec4`](https://github.com/procontexthq/procontext/commit/1d33ec4387a4014d89aaba620f66f2138dc8ba6f))

CLAUDE.md: when tests fail after a code change, investigate the root cause and explain it before
  modifying the test.

AGENTS.md: point other AI agents at the project instructions.

- Add feedback loop design document
  ([`3d974e7`](https://github.com/procontexthq/procontext/commit/3d974e7cb31df99d61014511b79304ef3c764f08))

Outlines how context-hub implements annotations and feedback, and how ProContext should adapt the
  pattern — SQLite-backed annotations, annotate_page/feedback_page MCP tools, and privacy-first
  local storage.

- Add logging section to CLAUDE.md coding conventions
  ([`7b7cf53`](https://github.com/procontexthq/procontext/commit/7b7cf53a77a5b9adea3a05aa452a089a86a6ea70))

- Add setup guide with per-tool MCP configurations
  ([`140bf3d`](https://github.com/procontexthq/procontext/commit/140bf3dd45f82be742378f724cadffb9eeb18cef))

New docs/setup.md covers installation and MCP server setup for Claude Code, Claude Desktop, Cursor,
  Windsurf, VS Code, Codex CLI, and Amazon Q CLI — both stdio and HTTP transports. README rewritten
  with benefit-first feature descriptions and links to the setup guide.

- Add website link, commercial plans note, and README polish
  ([`9d61a88`](https://github.com/procontexthq/procontext/commit/9d61a8825dc5f01f181197baf329e04ba155ee1a))

- Add procontext.dev badge, inline link, and footer link - Add hosted/enterprise early access note
  to License section - Clarify GPL permits use by individuals, teams, and organizations

- Align specs with implementation
  ([`15d6b48`](https://github.com/procontexthq/procontext/commit/15d6b4849308cd7f328a8991098217da0cd5a7fa))

- Align specs, example config, and CLAUDE.md with current codebase
  ([`0915a57`](https://github.com/procontexthq/procontext/commit/0915a573a0aa73ac68a14c52aeb7058dd66eff6b))

Remove dead registry.url field from all spec examples and procontext.example.yaml. Clarify db_path
  is independently configurable from data_dir. Fix registry update scheduling descriptions to match
  actual stdio vs HTTP behaviour. Add testing requirements and async testing guidelines to
  CLAUDE.md.

- Align stale refresh specs
  ([`6f16d2e`](https://github.com/procontexthq/procontext/commit/6f16d2e4a306463686ab8203f1177ae6d2b5c3a8))

- Clean up CLAUDE.md — reword motivation, remove redundant conventions
  ([`15050b1`](https://github.com/procontexthq/procontext/commit/15050b17e92f808279ea2fa0345b0a120a4e281a))

- Reword Project Motivation to remove author name and fix awkward phrasing - Remove duplicate
  TYPE_CHECKING/annotations bullets (already in coding-guidelines Rule 16) - Remove redundant
  Testing practices bullet (covered by Testing Requirements and Git Operations Policy) - Remove
  generic "Type hints required" bullet (standard Python practice)

- Clean up README and add Docker to roadmap candidates
  ([`8b8df5d`](https://github.com/procontexthq/procontext/commit/8b8df5dc88bbb2f2654f4d5d14fa80c765081de9))

README is rewritten to remove all phase-based framing and development status language — it now reads
  as a finished product doc. ROADMAP.md adds Docker image as a future candidate for HTTP transport
  deployments.

- Overhaul README and add registry contribution redirect
  ([`5d4bf1c`](https://github.com/procontexthq/procontext/commit/5d4bf1c4ada7436e4789f455ef1a9bb9920a825a))

- Add TOC and reference-style badge links to README - Shorten integrations section; collapse
  identical stdio configs into one - Add claude mcp add commands for stdio and HTTP - Remove
  platform path table (implementation detail) - Add Registry section directing users to
  procontexthq/procontexthq.github.io - Update CONTRIBUTING.md: remove registry additions from
  fast-track line, add dedicated section redirecting registry PRs to the registry repo

- Refine maintainability guidance
  ([`27e42cb`](https://github.com/procontexthq/procontext/commit/27e42cb60536139e238664b2c4fb59ca1d8aa11d))

- Reframe coding guidelines for a tool, not a library
  ([`a2eade0`](https://github.com/procontexthq/procontext/commit/a2eade0b45a198fca542c8584b80332667b64b91))

- Rename document title from 'for Public Libraries' to 'Coding Guidelines' - Rule 8: replace
  'library code' with 'core modules'; add explicit carve-out for top-level handlers (MCP tools,
  schedulers) - Rule 12: extend with 'never suppress silently' — pass/comment-only except blocks are
  forbidden even when no recovery is possible - Rule 3: replace 'exported symbol' / '@Beta' with
  ProContext-specific surface (MCP tool names, config schema fields, CLI commands) - Rule 6: reframe
  'escape hatches for consumers' as 'extension and override points for operators'; add
  ProContext-specific examples - Rule 10: 'library boundary' / 'consumer' → 'module boundary' /
  'callers' - Rule 21 + section header: 'Library Adoptability' → 'Maintainability'; reframe
  dependency cost in terms of a tool (attack surface, CVEs, install size) - CLAUDE.md: remove
  'public library development' framing; update key areas summary to say 'maintainability' instead of
  'library adoptability'

- Remove code blocks from registry updates section of technical spec
  ([`bb3b40b`](https://github.com/procontexthq/procontext/commit/bb3b40b8a945ce4c7a015a90a5c77d5dab98ca53))

Section 9 code blocks duplicated the source and added maintenance burden. Replaced with prose
  descriptions referencing the actual implementation files.

- Remove phase framing from user-facing and contributor docs
  ([`6de5cb3`](https://github.com/procontexthq/procontext/commit/6de5cb375d008ce3c9398139127f7fb33f20059b))

ROADMAP.md is rewritten to describe what ships in v0.1.0 and what's planned next, without exposing
  the internal phase breakdown. CONTRIBUTING.md and CLAUDE.md drop the two remaining phase
  references.

- Restructure coding guidelines — move imports rule, add focused-functions rule
  ([`d1c9357`](https://github.com/procontexthq/procontext/commit/d1c9357b11617e3c7288b29632f4aa9c26df87d6))

- Move Rule 7 (imports) from API Design into a new Code Conventions section where it belongs
  alongside Rule 17 (keep functions small and focused) - Add Rule 17: functions should do one thing;
  extract when you reach for # Step N - Fix duplicate Testing Strategy heading left from original
  file - Renumber all downstream rules consistently (18–23)

- Rewrite SERVER_INSTRUCTIONS for clarity and suggestive tone
  ([`68fac81`](https://github.com/procontexthq/procontext/commit/68fac81da90528424e1aeda9dcef53512c69ca2e))

Reorganize from a forced numbered workflow into capability-based sections (Getting Started, Reading,
  Searching, Outlines, Caching). Promote full_docs_url and readme_url, document search_page
  target="outline", and remove hardcoded default values that could go stale.

- Rewrite tool descriptions for clarity and accuracy
  ([`8890e42`](https://github.com/procontexthq/procontext/commit/8890e42bae279ffd40f2dc2fc3b946f35d98db5d))

Fix grammar issues, remove jargon, and improve accuracy of all four tool descriptions. Add
  cross-tool URL guidance to SERVER_INSTRUCTIONS. Update search_page to describe three-stage outline
  compaction behavior.

- Sync all specs with current codebase (24-item audit)
  ([`5aef5b4`](https://github.com/procontexthq/procontext/commit/5aef5b43b3b7c3885fa930a06a45a3b490bfff8c))

Full doc-vs-code consistency audit, 24 discrepancies resolved:

Stale narrative (bundled snapshot removed): - Remove bundled-snapshot fallback from 01-func §5.1/§6,
  02-tech §9/log events, 03-impl §1.1/§3.1/Phase1/Phase5, 04-api §8, 05-sec §3.3 - Replace with
  auto-setup + exit-on-failure behaviour throughout

Configuration gaps (new fields undocumented): - Add ResolverSettings (fuzzy_score_cutoff,
  fuzzy_max_results) to 02-tech §10 - Add FetcherSettings.request_timeout_seconds to 02-tech §10 +
  YAML example - Add RegistrySettings.poll_interval_hours to 02-tech §10 + YAML example - Add
  Settings.data_dir to Python class pseudocode in 02-tech §10 - Add resolver section to YAML config
  block in 02-tech §10

registry-state.json schema: - Add last_checked_at field across 01-func §6, 02-tech §9.1, 05-sec §6 -
  Document that last_checked_at gates the stdio startup polling check

RegistryIndexes / resolution algorithm: - Add by_alias dict to 01-func §6, 02-tech §4.1
  RegistryIndexes class - Fix build_indexes pseudocode to populate by_alias - Fix resolution step 3:
  O(1) by_alias.get() not linear fuzzy_corpus scan

Other code-vs-doc fixes: - §5.3 redirect: use urljoin+location header, not response.next_request.url
  - §6.2 stale-while-revalidate: asyncio.create_task moved to tool handler not Cache - CacheProtocol
  signatures: add headings + discovered_domains params (03-impl §3.2) - AppState pseudocode: add
  registry_path, registry_state_path; correct optionality - session/libraries resource: mark as
  planned/not-implemented in 04-api §5 - X-ProContext-Version header: remove undocumented claim from
  04-api §8 - --config CLI flag: remove from 04-api §7; document auto-discovery instead - uvx
  examples: clarify not-yet-on-PyPI in 01-func §5.1, 04-api §7 - schedulers.py: add to source layout
  and module responsibilities in 03-impl §1.1 - Dev deps: update [project.optional-dependencies] to
  [dependency-groups]; add pytest-cov, pip-audit, python-semantic-release to 03-impl §2 - Dep count:
  9 to 10 in 05-sec §3.6

README + CHANGELOG: - README: add procontext setup step to Quick Start and Installation - CHANGELOG
  [Unreleased]: document last_checked_at field and stdio polling gate

- Sync specs and code with CLI refactor and stale cache semantics
  ([`278124b`](https://github.com/procontexthq/procontext/commit/278124b2f6ed828828126a1346accc8af6e46a7f))

- 03-implementation-guide: add cli/ package to file tree, remove ghost data/ directory, fix entry
  point to cli.main:main, update entrypoint layer table, move registry_paths() annotation to
  config.py, add anyio to dependency list and license table (10→11 deps) - 02-technical-spec: add
  section 8A covering CLI dispatcher, doctor command checks, --fix behavior, and auto-derived schema
  validation - 01-functional-spec: fix query length caps (500 for resolve_library, 200 for
  search_page) - 04-api-reference: add stale field descriptions to read_page and read_outline output
  schemas - 05-security-spec: fix dependency count 10→11 - models/tools.py, mcp/server.py: update
  stale field descriptions from "background refresh in progress" to "re-fetch failed, content stale"

- Update changelog and roadmap for v0.1.1
  ([`616e536`](https://github.com/procontexthq/procontext/commit/616e536370091f2b07286460318d3fab58817f1f))

Changelog and roadmap now reflect the full v0.1.1 feature set: before parameter, include_outline
  toggle, outline search target, full_docs_url, per-package metadata, language hint, server
  instructions, registry sidecar, and formalized registry state. Server instructions expanded with
  usage trigger guidance.

- Update changelog with unreleased changes since v0.1.0
  ([`128039f`](https://github.com/procontexthq/procontext/commit/128039f98ad3e2447a0054c87d6f45dc985a42e3))

- Update changelog, roadmap, and contributing
  ([`db23f06`](https://github.com/procontexthq/procontext/commit/db23f06c2949e083bf93628cc57baf342a24d757))

CHANGELOG: add unreleased entries for docs_url removal, registry URL fix, clean registry startup
  exit, cache/BOM parser fixes, and indented heading support.

ROADMAP: rewrite with themed sections, rationale per item, PyPI release candidate, and a "How we
  decide" section replacing the thin one-liner.

CONTRIBUTING: add GitHub Discussions link to Questions section.

- Update read_page spec to reflect .md probe fallback behaviour
  ([`2b4dfd3`](https://github.com/procontexthq/procontext/commit/2b4dfd3f7eea0deba4f9305fc309a7ef69dd74c1))

Specs previously described fail-fast on 404 with no fallback. Updated 01-functional-spec.md and
  04-api-reference.md to document the current behaviour: try .md, fall back on any failure, HTML 200
  accepted as-is, .md never appended to redirect targets.

- Update README, ROADMAP, CHANGELOG and specs for tool redesign
  ([`103f29d`](https://github.com/procontexthq/procontext/commit/103f29d2704b5e0e014dde419df5492de553300e))

Sync all documentation with the completed tool redesign: rename llms_txt_url → index_url in
  LibraryMatch references across specs, rewrite README workflow for resolve_library → read_page →
  search_page, and update CHANGELOG [Unreleased] section.

- Update roadmap — remove implemented SLSA item, add read_page limit research
  ([`593a283`](https://github.com/procontexthq/procontext/commit/593a283cecdf79c1ed05c2ee3239893cf42a2164))

- Update specs and CLI docs for additional-info sidecar
  ([`f46fd94`](https://github.com/procontexthq/procontext/commit/f46fd947d099221f2c2c3450e1babcdb2b59e79c))

Document the registry additional-info sidecar feature across all spec documents and the doctor CLI
  reference.

- Update specs and guidelines to reflect recent changes
  ([`b626008`](https://github.com/procontexthq/procontext/commit/b6260083f065d4b1feca4da2a0386a412905a3a6))

- CLAUDE.md: update logging_config.py and mcp/lifespan.py file references - coding-guidelines.md:
  add Rule 24 (keep files small and focused) - 01-functional-spec.md: split connect/read timeout
  description - 02-technical-spec.md: Heading Parser → Outline Parser, split timeouts in
  FetcherSettings and build_http_client snippet, update server.py references to mcp/ package, fix
  get_library_docs → get_library_index - 03-implementation-guide.md: update file tree to show mcp/
  package, update all phase build tables and module responsibility table, update entry point snippet

- Update technical spec and fix coding guidelines heading
  ([`874b047`](https://github.com/procontexthq/procontext/commit/874b047692d9fbdceaabf404a4cd914031e94ba3))

- Rewrite Section 9 of the technical spec to reflect the new registry initialisation flow:
  procontext setup command, auto-setup fallback, last_checked_at interval guard, split httpx
  timeouts, and skip_initial_check behaviour for both transports - Add data_dir to the config
  reference table (Section 10) - Fix Section 22 heading level in coding-guidelines.md

- **readme**: Clarify install platform sections
  ([`20b5fbf`](https://github.com/procontexthq/procontext/commit/20b5fbfd4722668643480c97e9b0717ebf004942))

- **server**: Trim resolve_library tool docstring
  ([`891c06c`](https://github.com/procontexthq/procontext/commit/891c06c8d7fa3d5de8002f65762261d27612ca69))

- **specs**: Redesign tool surface — remove get_library_index, add search_page
  ([`f137452`](https://github.com/procontexthq/procontext/commit/f1374529f09b5503cb7cdc0dce3542467634bf04))

Comprehensive spec update across all 5 documents for the tool redesign:

- Remove `get_library_index` tool; absorb its responsibilities into `resolve_library` (returns
  llms_txt_url, docs_url, readme_url) and `read_page` (handles all URL types including llms.txt with
  pagination) - Add `search_page` tool with literal/regex search, smart case, word boundary
  matching, and paginated results - Replace `allowlist_depth: 0|1|2` with `allowlist_expansion:
  "registry"|"discovered"` enum - Merge toc_cache into single page_cache table - Add `readme_url` to
  registry entries and resolve_library output - Remove stale error codes (LIBRARY_NOT_FOUND,
  LLMS_TXT_NOT_FOUND, LLMS_TXT_FETCH_FAILED) - Restructure implementation phases into module
  acceptance criteria - Align security testing sections to module-based structure

### Features

- Add anonymous client identity
  ([`94bd557`](https://github.com/procontexthq/procontext/commit/94bd5572a507a3ac3876af0833265f03fc906d31))

Lazy UUID4 generator persisted to data_dir/client_id. No hardware fingerprinting or PII — just a
  stable random ID created on first access for future use in feedback and telemetry features.

- Add before parameter, outline search target, and extract tool docs
  ([`4a8cecb`](https://github.com/procontexthq/procontext/commit/4a8cecbea5f0edb053f2c75e0510413976806f6d))

Add backward context support (before parameter) to read_page and read_outline. Switch read_outline
  from entry-index pagination to page-line windowing so all three page tools share the same
  coordinate system. Add target="outline" mode to search_page for searching stored outline entries
  without scanning full page content. Extract tool descriptions from server.py into
  mcp/tool_docs.py.

- Add configurable character limit to outline compaction
  ([`fccb018`](https://github.com/procontexthq/procontext/commit/fccb0180ec8c1fdbd5e4b364e5cc091b6c0f099a))

Implement character-based constraints alongside existing entry count limits for outline compaction
  in read_page and search_page tools.

Changes: - Add OutlineSettings with max_entries (default 50) and max_chars (default 4000) - Both
  constraints are active: compaction continues until both satisfied - Update compact_outline() to
  check character count at each reduction stage - Pass settings to tools via AppState - Update all
  affected documentation specs - Add 6 new tests for character limit functionality

Configuration: - Via YAML: outline.max_chars, outline.max_entries - Via env vars:
  PROCONTEXT__OUTLINE__MAX_CHARS, PROCONTEXT__OUTLINE__MAX_ENTRIES - Defaults balance token
  efficiency with structural conciseness

This prevents token bloat in agent contexts while maintaining readable outlines.

- Add full_docs_url field for comprehensive documentation search
  ([`5a27c92`](https://github.com/procontexthq/procontext/commit/5a27c92bd7fbf2e557bc0d7d2f576fa3bde283d0))

Add support for complete merged documentation (llms-full.txt) alongside the documentation index
  (llms.txt). This enables agents to search and read entire library documentation at once instead of
  navigating page by page.

Changes: - Add llms_full_txt_url to RegistryEntry (internal model) - Add full_docs_url to
  LibraryMatch (API response) - Update resolver to map llms_full_txt_url -> full_docs_url - Update
  resolve_library tool docstring to document new field - Update resolve_library handler docstring
  with return details - Update SERVER_INSTRUCTIONS with full_docs_url guidance

The full_docs_url field is optional (nullable) for libraries that don't have merged documentation
  yet. When available, agents can pass it to read_page or search_page to work with complete
  documentation.

Also creates docs/decisions/library-resolution-strategy.md documenting the fuzzy matching
  limitations and planned substring matching fallback for cases like "TwicPics" not matching
  "TwicPics by Frontify".

All 573 tests pass. This change is backward compatible - existing code continues to work, new field
  is optional.

- Add include_outline parameter to read_page
  ([`1697c3f`](https://github.com/procontexthq/procontext/commit/1697c3ff1566e49f6f58921eaf64893c31fad586))

Allow agents to skip outline computation on subsequent pagination calls by setting
  include_outline=false, saving tokens when the outline is already known from the first read_page
  call.

- Add outline compaction, read_outline tool, and remove view parameter
  ([`6421ad0`](https://github.com/procontexthq/procontext/commit/6421ad02e9be3f6cac08dae774a249436d008d62))

Redesign outline handling for token-efficient responses:

- Add outline.py module with structured parsing, empty fence stripping, progressive compaction
  (H6→H5→fences→H4→H3, target ≤50 entries), match-range trimming, and compaction notes - Add
  read_outline tool for paginated full-outline browsing - Remove view parameter from read_page —
  always return content + compacted outline - Integrate compaction into read_page and search_page -
  Change outline wire format from "N: content" to "N:content" - Update specs, README, and tests

- Add registry additional-info sidecar with MD probe gating
  ([`6cdca14`](https://github.com/procontexthq/procontext/commit/6cdca1451ee9e334b451deaae8af1fef759ebf9a))

Introduce a best-effort additional-info.json sidecar downloaded alongside the registry. It carries
  useful_md_probe_base_urls, which gates .md probing to only URLs whose origin matches an entry in
  the list. This prevents unnecessary .md probe requests for sites that don't serve Markdown
  variants.

Key changes: - RegistryState and RegistryAdditionalInfo Pydantic models with strict SHA-256 checksum
  validation - Best-effort sidecar download during setup and background updates (failure does not
  block registry operations) - 3-state advertised_additional_info return (tuple | "not_advertised" |
  "incomplete") to eliminate duplicated partial-metadata detection - normalize_exact_doc_origin for
  strict origin-only URL validation - Doctor check for additional-info health with --fix support -
  Comprehensive test coverage for all new registry/update.py branches

- Add search_page tool for grep-like documentation search
  ([`b4009d2`](https://github.com/procontexthq/procontext/commit/b4009d2bea310df98e043a36de1d08a709ad244e))

New tool that searches within a documentation page for lines matching a query. Supports literal and
  regex modes, smart case sensitivity (ripgrep style), word boundary matching, and
  offset/max_results pagination.

- search.py: pure functions build_matcher() and search_lines() - tools/search_page.py: handler using
  shared fetch_or_cached_page flow - models/tools.py: SearchPageInput, LineMatchOutput,
  SearchPageOutput - mcp/server.py: register search_page with full parameter annotations - 33 new
  tests (19 unit + 7 integration + 7 input validation)

- Add stdout guard and lint rule to protect stdio MCP transport
  ([`48aaf0a`](https://github.com/procontexthq/procontext/commit/48aaf0aa1e092e1a2d932497a37636f454055330))

In stdio mode, stdout is the MCP JSON-RPC stream. Three layers now prevent accidental writes from
  corrupting the protocol:

- Runtime guard: _StdoutGuard replaces sys.stdout in stdio mode after MCP captures the buffer. Any
  write raises RuntimeError immediately. - Lint rule: ruff T201 catches print() statements at commit
  time. - Integration tests: every tool handler is exercised with stdout captured — any output fails
  the test.

Also configures structlog to stderr in test conftest to match production behavior.

- Add view parameter to read_page and MCP schema descriptions
  ([`969ef6c`](https://github.com/procontexthq/procontext/commit/969ef6c4c3ae9ff8e16d2f9037751ac5f1521411))

read_page: - view="headings" returns heading map and total_lines only, no content — lets agents scan
  page structure cheaply before committing to a read - view="full" (default) unchanged: heading map
  + content window

Schema improvements: - Annotated[T, Field(description=...)] on all tool input parameters;
  descriptions now appear in inputSchema so agents know what each field does - Tools return typed
  Pydantic models; FastMCP auto-generates outputSchema from the return type annotation — all three
  tools now advertise their output structure in tools/list

Error handling: - ProContextError propagates naturally to FastMCP instead of being manually
  serialised to CallToolResult; error text includes the code, message, and suggestion so agents
  still have all the context they need - Remove _serialise_tool_error and ProContextError.to_dict()

- Enhance server instructions with comprehensive workflow guidance
  ([`529b91d`](https://github.com/procontexthq/procontext/commit/529b91d0fcce3f862e205c1c4165b5d9eb2f786c))

Add detailed SERVER_INSTRUCTIONS to provide agents with clear workflow guidance for using ProContext
  tools. Instructions now include: - Typical workflow (5-step process from resolve_library to
  navigation) - Key details on input requirements and caching behavior - Pro tips for effective use
  of tools

Update test to verify instructions are present in initialize response and contain all key workflow
  elements (resolve_library, read_page, search_page, read_outline, Typical Workflow, compacted
  outline, pagination, caching).

Also updates API reference documentation to describe the instructions field in the initialize
  response.

- Improve doctor cache repair workflow
  ([`295210f`](https://github.com/procontexthq/procontext/commit/295210f78a79720447cb4637727da746b3e63888))

- Refine read page and resolver contracts
  ([`c51c9ee`](https://github.com/procontexthq/procontext/commit/c51c9ee0ac5d5406ce1edaed4742fa90920a1f6d))

- Rename get_library_docs to get_library_index, improve MCP API surface
  ([`ee85a7f`](https://github.com/procontexthq/procontext/commit/ee85a7f79a3fdeb8f925b4ac75f6b090d39eafbe))

- Rename tool from `get_library_docs` to `get_library_index` — the name better reflects that it
  returns an index of pages, not the docs themselves - Add `index_url` to `get_library_index` output
  so agents can resolve relative URLs found in the content - Add Field descriptions to all tool
  input/output models so agents receive useful context in inputSchema and outputSchema - Rewrite
  tool docstrings for clarity and correct grammar throughout - Lower `read_page` default limit from
  2000 to 500 lines - Fix Pylance error in tests: narrow `cache` type via `isinstance(cache, Cache)`
  - Update all spec docs, README, ROADMAP, and CHANGELOG to match

- Stale-while-revalidate, content hash, and field reorder
  ([`c899a45`](https://github.com/procontexthq/procontext/commit/c899a45bc72de690f920cb1da93b0d99d7cd963d))

Restore background refresh for stale cache entries instead of blocking on a synchronous re-fetch.
  Add a truncated SHA-256 content_hash (12 hex chars) to read_page, read_outline, and search_page
  responses so agents can detect when page content changes between paginated calls.

Guards against redundant work: in-memory _refreshing set prevents duplicate concurrent tasks;
  last_checked_at column enforces a 15-minute cooldown before retrying a URL.

Output model fields reordered for logical agent consumption — primary content first, then
  pagination, hash, and cache metadata last.

- Suggest doctor for recoverable startup issues
  ([`ef5586e`](https://github.com/procontexthq/procontext/commit/ef5586e1a195ea74aa706e07c30ea6d4eb0d755b))

- **config**: Promote fetch timeout, fuzzy params, and poll interval to config
  ([`bcf8aea`](https://github.com/procontexthq/procontext/commit/bcf8aea0acb99a4b9d7874dd67a2f35fab7c42d2))

Moves four hardcoded values into Settings so operators can tune them without code changes. Adds
  ResolverSettings (fuzzy_score_cutoff, fuzzy_max_results), request_timeout_seconds to
  FetcherSettings, and poll_interval_hours to RegistrySettings. All defaults are unchanged so
  existing deployments are unaffected.

- **fetcher**: Split connect and read timeouts
  ([`714a1f7`](https://github.com/procontexthq/procontext/commit/714a1f73812a0562bbc111b02007480ba2f2ee88))

- **parser**: Emit fence lines and support blockquote + H5-H6 headings
  ([`bb78db4`](https://github.com/procontexthq/procontext/commit/bb78db4280c5fa165adc65d578919c23b37066b5))

The heading parser now uses a stateless single-pass algorithm: - Fence opener/closer lines (``` /
  ~~~, up to 3 spaces indentation) are included in the structural map so agents can distinguish code
  block content from document-level headings - H5–H6 headings are now captured (previously capped at
  H4) - Blockquote headings (> ## Section) are matched via the optional (?:>\s*)? prefix on the
  heading regex - 4-space indented lines (CommonMark indented code blocks) are correctly excluded by
  the ^{0,3} indentation constraint on _FENCE_RE

The old stateful code-block-tracking approach is replaced by two simple regexes applied in a single
  pass with no mutable state.

- **read_outline**: Increase default limit to 1000 and remove upper bound
  ([`708e422`](https://github.com/procontexthq/procontext/commit/708e4229c57c9e39941e306a13d79b70e4c5b118))

The read_outline tool's limit parameter now defaults to 1000 (was 200) with no upper cap (was 500).
  Update code, tests, and all spec documents to reflect the new constraint.

Also add description field to resolve_library tool docstring.

- **read_page**: Add has_more and next_offset pagination fields
  ([`2273c91`](https://github.com/procontexthq/procontext/commit/2273c912275c78f7987305897aa5308a486aaa42))

Agents shouldn't have to compute whether more content exists — an explicit signal is more reliable
  and consistent with search_page.

- **read_page**: Probe .md URL variant on cache miss
  ([`57d1744`](https://github.com/procontexthq/procontext/commit/57d1744149106a7198f0071e9e024ed693947285))

- **registry**: Remove bundled snapshot, add setup command, and guard stdio checks
  ([`0780f43`](https://github.com/procontexthq/procontext/commit/0780f4396231cd32169a1a678eb6f87a68244a5e))

Removes the bundled registry snapshot entirely. The server now requires an explicit initialisation
  step and falls back gracefully when none exists.

Registry initialisation: - Add `procontext setup` CLI command that downloads and persists the
  registry - Auto-setup fallback in lifespan: if no local registry is found on startup, attempt a
  one-time fetch before failing with an actionable error message - `load_registry()` returns None
  instead of bundled data when no local pair exists; callers handle the None case explicitly

Scheduler improvements: - Extract scheduler coroutines into procontext.schedulers module - Extract
  HTTP transport and MCPSecurityMiddleware into procontext.transport - Add registry_check_is_due()
  guard: stdio sessions skip the metadata fetch if poll_interval_hours have not elapsed since
  last_checked_at - _write_last_checked_at() updates registry-state.json after every successful
  check (whether or not a new version was downloaded) - save_registry_to_disk() now also writes
  last_checked_at alongside updated_at - skip_initial_check now respected in HTTP mode (sleeps full
  poll interval before first check when auto-setup just ran)

Server / config: - Settings gains data_dir field (PROCONTEXT__DATA_DIR) for testability -
  _setup_logging() called once in main() before branching; removed from lifespan() to avoid
  redundant reconfiguration - _run_setup() receives Settings from main() instead of constructing its
  own - Redundant except clause removed from _attempt_registry_setup()

Tests: - Delete test_first_run_fetch.py (behaviour no longer exists) - Update test_registry.py:
  load_registry returns None on mismatch; add TestRegistryCheckIsDue suite and last_checked_at
  assertion on save - Update test_scheduler.py: add due/not-due guard tests; patch
  registry_check_is_due in stdio path tests - integration/conftest.py: seed registry files in
  DATA_DIR; set last_checked_at to now so background checks do not fire during tests

- **resolve_library**: Add description field to library matches
  ([`f7fc184`](https://github.com/procontexthq/procontext/commit/f7fc184adf323a6a4879ebabf4f4bdc64e213580))

Add `description` to `RegistryEntry` (default "") and `LibraryMatch` so agents can see what a
  library does when choosing between matches. Updated across all spec documents, README, resolver,
  and test fixtures.

### Performance Improvements

- Skip domain extraction in registry mode (50-120ms saved per fetch)
  ([`21221ac`](https://github.com/procontexthq/procontext/commit/21221ac28a4b4d515372f6ccebb71da2ab8175c1))

When allowlist_expansion='registry' (the default and recommended mode), skip the expensive
  regex-based domain extraction entirely. In this mode, the allowlist is purely registry-based and
  extracted domains are never used.

Benefits: - Eliminates 50-120ms overhead per large file (e.g., llms-full.txt) - Reduces CPU cost for
  default configuration by 100% - Negligible impact on "discovered" mode (still extracts when
  needed)

Impact on cache: - In registry mode, discovered_domains is now empty (not extracted) - In discovered
  mode, behavior unchanged (extracts and expands) - The cache accepts empty discovered_domains by
  default

Testing: - Updated test to reflect new behavior (extraction skipped in registry mode) - All 573
  tests pass

### Refactoring

- Change search_page matches to line_number:content string format
  ([`870a0ac`](https://github.com/procontexthq/procontext/commit/870a0ac80b68f2c3ff8ee4314109ef6691d76df5))

Replace structured list[LineMatchOutput] with a plain string using the same "N:content" format as
  outline, saving tokens and maintaining consistency across all tool responses.

- Remove LineMatchOutput model - Change SearchPageOutput.matches to str - Format matches as
  "\n"-joined "line_number:content" entries - Fix stale docs: view references in 04-api-reference,
  missing read_outline in TOCs, resource subsection numbering, README tool count and search example

- Extract page service layer
  ([`67c5247`](https://github.com/procontexthq/procontext/commit/67c5247421cb350bf07b6c866c8616e26faa3e62))

- Migrate schedulers to anyio.sleep and clean up async test markers
  ([`ff12f4c`](https://github.com/procontexthq/procontext/commit/ff12f4c3e39638349f2c68f5d9f1ca670f55e322))

- Replace asyncio.sleep with anyio.sleep in schedulers.py so the scheduler stays transport-agnostic
  and testable with anyio backends - Update test_scheduler.py to patch anyio.sleep instead of
  asyncio.sleep - Remove redundant @pytest.mark.asyncio decorators from test_http_transport.py (13
  occurrences) and test_registry.py (9 occurrences); asyncio_mode=auto in pyproject.toml makes these
  no-ops - Remove now-unused pytest import from test_registry.py

- Move RegistryIndexes to models.registry and extract allowlist helper
  ([`ba13f9e`](https://github.com/procontexthq/procontext/commit/ba13f9e1bf5f3c4b8fde9f8cbd8f744e8dafc630))

- Define RegistryIndexes as a dataclass in models/registry.py (was inline in registry.py); export it
  from models/__init__.py - Update all importers (state.py, resolver.py, tests/conftest.py,
  tests/unit/test_resolver.py) to import from the new location - Extract repeated
  allowlist-expansion pattern into expand_allowlist_from_content() in fetcher.py; remove four
  duplicated blocks from tools/get_library_docs.py and tools/read_page.py

- Redesign registry package model for multi-language support
  ([`bcf14a5`](https://github.com/procontexthq/procontext/commit/bcf14a5c33cd7f0f4ec15258e3c375fa234b56f8))

Replace RegistryPackages ({pypi: [], npm: []}) with a list of PackageEntry objects, each carrying
  ecosystem, languages, package_names, readme_url, and repo_url. This allows multi-language SDKs
  (e.g., OpenAI Python + JS) to share a single library ID with per-language metadata.

Drop library-level docs_url, readme_url, repo_url, and languages from RegistryEntry and
  LibraryMatch. Add optional language parameter to resolve_library that sorts matching-language
  packages to the top without filtering results.

- Remove docs_url from resolve_library response
  ([`67bb958`](https://github.com/procontexthq/procontext/commit/67bb958beacd3419b44ab061073ad1fa0ff33e53))

The docs_url field is not actionable for agents — they navigate via index_url (llms.txt) and
  readme_url. Removing it simplifies the response surface. docs_url remains in RegistryEntry for
  SSRF allowlist building.

- Remove get_library_index tool, enrich resolve_library output
  ([`38b66b6`](https://github.com/procontexthq/procontext/commit/38b66b686642f0d0ac98ab44027a4d157d266ddb))

Drop the get_library_index tool entirely — its functionality is absorbed by resolve_library (which
  now exposes llms_txt_url, docs_url, readme_url on each match) combined with read_page.

- Delete tools/get_library_docs.py and its models, error codes, tests - Add llms_txt_url, docs_url,
  readme_url to LibraryMatch; readme_url to RegistryEntry - Simplify CacheProtocol: remove
  get_toc/set_toc, parameterless load_discovered_domains - Remove TocCacheEntry model (toc_cache
  table kept — no migration needed) - Update server docstrings to reference the new two-tool
  workflow

- Remove httpx from registry public API (Rule 10)
  ([`58bf05e`](https://github.com/procontexthq/procontext/commit/58bf05e9d06aad809959c7fcaf179fc34fe23f57))

- check_for_registry_update: drop unused timeout parameters, defaults live in update.py where they
  belong - fetch_registry_for_setup: accept Settings instead of httpx.AsyncClient, build and manage
  the HTTP client internally - cmd_setup.py: attempt_registry_setup becomes a one-liner delegate

Callers no longer need to import httpx to use the registry facade.

- Rename headings to outline throughout
  ([`6447051`](https://github.com/procontexthq/procontext/commit/6447051e4b06e166ef2bff016f842c307eb682bf))

Renames the `headings` field/column/function to `outline` across the cache layer, data models,
  parser, and read_page handler to better reflect that the structural map includes fence markers in
  addition to headings.

- `parse_headings()` → `parse_outline()` in parser.py - `PageCacheEntry.headings` → `.outline` in
  models/cache.py - SQLite column `headings` → `outline` in cache.py - `Cache.set_page()` /
  `get_page()` parameter updated - `read_page` handler and CacheProtocol updated accordingly

- Split cache cleanup into startup check and HTTP scheduler
  ([`75d4f9f`](https://github.com/procontexthq/procontext/commit/75d4f9f75e76d7f520e9250227a6327b3529b372))

Mirror the registry scheduler refactor: run_cache_cleanup_scheduler now handles HTTP mode only
  (infinite loop), and run_cache_startup_cleanup handles stdio mode (single pass). Server.py
  dispatches accordingly.

- Split doctor registry and tool tests
  ([`508e282`](https://github.com/procontexthq/procontext/commit/508e282d752ef2040a7f34ec81673aa0dcfca649))

- Split http transport and require explicit setup
  ([`9db27c3`](https://github.com/procontexthq/procontext/commit/9db27c3d6801a666ea767ba262cb505a7bb316d2))

- Split scheduler into startup check and HTTP polling loop
  ([`51e150c`](https://github.com/procontexthq/procontext/commit/51e150ca099ee688d2f0590554a4dfd47dc64692))

run_registry_update_scheduler mixed two fundamentally different behaviors behind one name — a
  one-shot startup check for stdio and an infinite polling loop for HTTP. Split into:

- run_registry_startup_check() stdio: checks once if due, returns - run_registry_update_scheduler()
  HTTP: polls indefinitely

server.py dispatches the correct function based on transport. Spec updated to match.

- Split server.py into mcp/ package and logging_config.py
  ([`b29f7c8`](https://github.com/procontexthq/procontext/commit/b29f7c8bf0f144815eccf1e677c39e60581314fb))

server.py (422 lines) is split into focused modules: - mcp/server.py — FastMCP instance and tool
  registrations - mcp/lifespan.py — asynccontextmanager, resource lifecycle, registry_paths() -
  mcp/startup.py — main(), CLI entry point, registry bootstrap - logging_config.py — structlog
  processor chain configuration

Entry point updated: procontext.server:main → procontext.mcp.startup:main Coverage omit list updated
  to reflect new paths. All subprocess-based tests updated to use procontext.mcp.startup.

- Tighten doctor and registry boundaries
  ([`0140db4`](https://github.com/procontexthq/procontext/commit/0140db484278bd7c85c218edb206ae664b605db3))

- **cache**: Remove vestigial toc_cache table
  ([`15c5334`](https://github.com/procontexthq/procontext/commit/15c533491e2c92406f960c54a634ae4fcaf68593))

The toc_cache table was a leftover from the old get_library_index tool design. All content is now
  stored in the unified page_cache table per the spec. Also documents the server_metadata table in
  the tech spec schema section.

- **cache**: Replace background stale refresh with sync re-fetch
  ([`712ec61`](https://github.com/procontexthq/procontext/commit/712ec6172ada1abae7bcb98e35caf7c81a577afc))

Expired cache entries now trigger a synchronous re-fetch instead of a fire-and-forget background
  task. On success, fresh content is returned. On failure, stale content is served as fallback.

This eliminates a pagination consistency bug where a background refresh could update the cache
  between paginated read_page calls, causing line numbers from the first response to point to wrong
  locations in the second response.

- **cli**: Extract CLI into dedicated package with production-grade doctor command
  ([`55819d5`](https://github.com/procontexthq/procontext/commit/55819d502edce81a7f55f1296978bcca5f97321c))

- Create cli/ package with argparse dispatcher (main.py) and per-command modules (cmd_serve,
  cmd_setup, cmd_doctor) - Move registry_paths() from mcp/lifespan.py to config.py to eliminate
  CLI→MCP coupling - Reduce mcp/startup.py to a backward-compatible shim - Overhaul doctor command
  with deep health validation: - Data directory: existence and permissions - Registry: file
  presence, parseability, checksum integrity - Cache DB: SQLite integrity, WAL mode, auto-derived
  schema validation - Network: registry endpoint reachability - Add --fix flag for auto-repair
  (mkdir, registry download, DB recreate) - Auto-derived schema validation compares against
  in-memory Cache.init_db() so doctor stays in sync with code automatically

- **config**: Replace allowlist_depth with allowlist_expansion enum
  ([`fbd1707`](https://github.com/procontexthq/procontext/commit/fbd17079b74dc10656215bce240ed12084abbf5c))

Replace the three-level integer `allowlist_depth: 0|1|2` with a two-value string enum
  `allowlist_expansion: "registry"|"discovered"`.

- "registry" (default): allowlist fixed at startup from registry domains - "discovered": expand
  allowlist from URLs found in any fetched content

Simplifies the allowlist logic — the old depth-based thresholds per tool (depth_threshold=1 for
  llms.txt, depth_threshold=2 for pages) are replaced by a single boolean check in
  expand_allowlist_from_content.

- **models**: Rename LibraryMatch.llms_txt_url to index_url
  ([`102d368`](https://github.com/procontexthq/procontext/commit/102d368fd7edde92ba8b9826067cc4d32340cc28))

More generic name that doesn't leak the underlying file format into the public API surface.

- **registry**: Move registry_loaded log to server lifespan
  ([`f923394`](https://github.com/procontexthq/procontext/commit/f9233943a4b8c6138eb07ca54f25af33710bbbe7))

load_registry() is a pure validation function called by doctor, cmd_serve, and the server lifespan.
  The info log only belongs in the lifespan — doctor and cmd_serve have their own output and don't
  need operational logs mixed in.

- **registry**: Replace wall-clock timeouts with split httpx timeouts
  ([`ce793fc`](https://github.com/procontexthq/procontext/commit/ce793fcaad391d05bce1ecfd754c1cbca5b8225d))

All registry HTTP fetches now use connect=5s (fail fast if unreachable) and read=300s (patient once
  transfer starts), via a single _REGISTRY_TIMEOUT constant in registry.py. Removes the
  asyncio.wait_for wrapper and the FIRST_RUN_FETCH_TIMEOUT_SECONDS constant from server.py.

- **tests**: Split test_registry.py by module boundary (Rule 24)
  ([`7f5cf7e`](https://github.com/procontexthq/procontext/commit/7f5cf7eda31c9d08e51f17629dad1d6efbcf56c4))

Extract check_for_registry_update and fetch_registry_for_setup tests into test_registry_update.py.
  Both files now well under the 500-line ceiling (316 and 389 lines respectively, down from 668).

- **tools**: Extract shared fetch helper from read_page
  ([`806a182`](https://github.com/procontexthq/procontext/commit/806a1829736bf41bc5d1c818f8d59214f7f2bd12))

Move cache-check → .md probe → fetch → outline parse → allowlist expansion → cache-write →
  stale-refresh into tools/_shared.py. read_page.py becomes a thin wrapper: validate input, call
  fetch_or_cached_page, apply line windowing.

This prepares for search_page which will reuse the same fetch flow.

### Testing

- Cover HTTP startup dispatch
  ([`b1f869f`](https://github.com/procontexthq/procontext/commit/b1f869fa77cec943f267562e1bb0c734ac09625a))

- Fill coverage gaps and raise threshold to 90%
  ([`a6453e7`](https://github.com/procontexthq/procontext/commit/a6453e71259dc5640cd8e27590b17705b624afb3))

Add targeted tests for previously uncovered paths: - cache.py: TestCleanupIfDue (startup run,
  skip-if-recent, interval elapsed, DB error fall-through) - schedulers.py:
  TestCacheCleanupScheduler (stdio/HTTP paths, sleep interval) and TestJitteredDelay - registry.py:
  load_registry edge cases (None paths, missing files, bad version/checksum/JSON),
  TestWriteLastCheckedAt, up-to-date path with last_checked_at refresh, 4xx semantic failure -
  fetcher.py: TestExpandAllowlistFromContent (depth met/unmet, already-in-allowlist no-op)

Also omit server.py and protocols.py from coverage (untestable by design) and raise the coverage
  fail-under threshold from 80% to 90% — current total is 93.7%.

- **read_page**: Comprehensive edge case coverage for .md probe helpers
  ([`8b988fe`](https://github.com/procontexthq/procontext/commit/8b988fe209aef43e8711ed7b2c636602d75bf41c))

Fix _has_file_extension to return True (skip probe) for trailing-slash URLs and bare domain roots —
  appending .md to an empty last segment produces a malformed path like /docs/.md.

Add tests/unit/test_read_page_helpers.py covering _has_file_extension and _with_md_extension in full
  isolation: standard extensions, uppercase, compound (.tar.gz), numeric/version segments, mixed
  alpha+digit, trailing slash, domain root, query strings, fragments, and hidden dot-prefix files.

Add integration tests for: query string probe path correctness, 500 and timeout on probe both
  triggering fallback, trailing slash skipping probe, and both probe and fallback failing
  propagating the error.


## v0.1.0 (2026-02-28)

### Bug Fixes

- Phase 3 review — SSRF before cache, spec alignment, test cleanup
  ([`222b88e`](https://github.com/procontexthq/procontext/commit/222b88e4270f65405fada2334ce305310dcd6911))

Add SSRF allowlist check before cache lookup in read_page handler so pages from domains removed from
  the registry are not served from cache. Align spec documents with implementation: remove stale
  anchor generation references, fix read_page signature in tech spec, correct cache-hit flow
  diagram. Consolidate read_page integration tests into test_tools.py. Replace RuntimeError guards
  with assert statements.

Changes: - src/procontext/tools/read_page.py: SSRF check before cache, assert guards -
  docs/specs/02-technical-spec.md: fix read_page signature, request flow, remove anchor references -
  docs/specs/03-implementation-guide.md: remove Heading model and anchor references from source
  layout and test list - tests/integration/test_tools.py: merge read_page tests, add _db comments -
  tests/integration/test_read_page.py: deleted (merged into test_tools.py)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

- Prevent race condition in wire contract integration test
  ([`c9ae8f8`](https://github.com/procontexthq/procontext/commit/c9ae8f85403dd96880375faf4effc98e367ae011))

The MCP stdio transport uses zero-capacity anyio memory streams, so the receive loop dispatches
  async tool handlers (e.g. aiosqlite lookups) via start_soon() and immediately reads the remaining
  stdin messages. Closing stdin tears down the write stream before those handlers finish, silently
  dropping in-flight responses.

On Python 3.12/Linux the event loop scheduling makes this race reliably reproducible; it was
  invisible on Python 3.13/macOS where the cache lookup completed within the narrower window.

Fix: read stdout line-by-line until all expected request IDs are answered before sending
  shutdown/exit and closing stdin. This keeps the write stream open until async handlers complete.

### Chores

- Rename display name from Pro-Context to ProContext
  ([`4687290`](https://github.com/procontexthq/procontext/commit/4687290ac9c51da0ad163caffdc8523500f21a3a))

Replaces all occurrences of "Pro-Context" (capitalised, hyphenated) with "ProContext" across docs,
  specs, config, and source. Technical identifiers are unchanged — pro-context (CLI/PyPI/config
  filename) and pro_context (Python module) follow their respective naming conventions.

Co-Authored-By: Claude Sonnet 4-6 <noreply@anthropic.com>

- Rename filenames, paths, and identifiers to procontext
  ([`c9ea5df`](https://github.com/procontexthq/procontext/commit/c9ea5df01b04bae23059fc742190992c2aed1659))

- Rename pro-context.example.yaml → procontext.example.yaml - Config filename convention:
  pro-context.yaml → procontext.yaml - Data directory: ~/.local/share/pro-context/ →
  ~/.local/share/procontext/ - Config directory: ~/.config/pro-context/ → ~/.config/procontext/ -
  Env var prefix: PRO_CONTEXT__ → PROCONTEXT__ - MCP server name: FastMCP("pro-context") →
  FastMCP("procontext") - MCP resource URI: pro-context://session/libraries →
  procontext://session/libraries - MCP client config key: "pro-context" → "procontext"

CLI command (pro-context), PyPI package name, and Python module (pro_context) are unchanged — these
  follow their respective naming conventions.

Co-Authored-By: Claude Sonnet 4-6 <noreply@anthropic.com>

- Rename Python module to procontext, migrate dev deps to dependency-groups
  ([`3c0a937`](https://github.com/procontexthq/procontext/commit/3c0a937f374f89c11feca948413efbe8ff1e4985))

- Rename src/pro_context/ → src/procontext/ (Python module now matches package name) - Update all
  imports from pro_context.* to procontext.* - pyproject.toml: rename package, entry point, and
  hatch build path - pyproject.toml: migrate dev deps from [project.optional-dependencies] to
  [dependency-groups] so uv sync --dev installs them correctly - Update all CLI references (uv run
  procontext, uvx procontext) - Update all env var prefixes to PROCONTEXT__ - Update config paths to
  ~/.config/procontext/ and ~/.local/share/procontext/ - Rename pro-context.example.yaml →
  procontext.example.yaml - Update MCP server name and resource URI to procontext:// - Update
  README: Phase 1 marked complete, Phase 2 is current - Fix pitch deck HTML: Pro-Context →
  ProContext, update GitHub URLs

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Documentation

- Add circuit breaker for consecutive transient registry update failures
  ([`1a85d93`](https://github.com/procontexthq/procontext/commit/1a85d9390cef82d4d40bb67b538059d9bd755104))

After 8 consecutive transient failures, fast retries are suspended and checks return to 24-hour
  cadence until the next successful check.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

- Add CONTRIBUTING.md, fix uv sync command
  ([`547c854`](https://github.com/procontexthq/procontext/commit/547c85458610622c98cc4ebf8032b442a43c4304))

Adds contributor guide covering setup, development workflow, branch naming, commit conventions,
  coding conventions, and project structure.

Also fixes `uv sync --extra dev` → `uv sync --dev` in CONTRIBUTING.md and CLAUDE.md (same typo in
  both).

Co-Authored-By: Claude Sonnet 4-6 <noreply@anthropic.com>

- Add security spec, add bearer key auth for HTTP mode
  ([`c7dcc0d`](https://github.com/procontexthq/procontext/commit/c7dcc0d51cedec40ac4c2d0a10f6c47f0dba120c))

- Create 05-security-spec.md: threat model (6 threats), trust boundaries, security controls summary,
  data handling, dependency vulnerability management, phase-gated security testing - Add optional
  bearer key authentication for HTTP transport across all specs (01 functional, 02 technical, 03
  implementation, 04 API reference) - Fix missing code fence closure in 04-api-reference.md - Update
  CLAUDE.md active specifications list

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

- Align HTTP auth model and spec consistency
  ([`c71f342`](https://github.com/procontexthq/procontext/commit/c71f3422d9edfb2e85be139ff52f8b689e9562a1))

- Clarify registry loading and update semantics
  ([`5f4f90d`](https://github.com/procontexthq/procontext/commit/5f4f90d3443fb870b19a6880c741fdd494ddff25))

- Document platformdirs convention in CLAUDE.md and README.md
  ([`4ecb224`](https://github.com/procontexthq/procontext/commit/4ecb2242be43ae0d4d0068fb19212ca2d00c8876))

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

- Propagate circuit breaker detail to tech spec and implementation guide
  ([`2588917`](https://github.com/procontexthq/procontext/commit/2588917bdd7e26474ed9e1ba82fbea876e7cd09c))

Add MAX_TRANSIENT_BACKOFF_ATTEMPTS=8 to 02-technical-spec scheduling policy and illustrative code,
  and to 03-implementation-guide Phase 5 test expectations. Consistent with 01-functional-spec
  update.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

- Refine commit granularity policy in CLAUDE.md
  ([`5a3d12d`](https://github.com/procontexthq/procontext/commit/5a3d12d19114b936e985f665b531d4e42301c734))

- Update README and strengthen large-document parser test
  ([`ef4ccc4`](https://github.com/procontexthq/procontext/commit/ef4ccc4a712691b3a61d2e9918a8807dfc6d3c5d))

- Rewrite README: fix future-tense language, split Features into implemented (Phases 0–3) vs coming
  soon (Phases 4–5), add SSRF Protection feature, update Installation with dev setup instructions
  and Claude Desktop config, move Platform Support above Installation, update MCP badge to spec
  version 2025-11-25 - Strengthen test_large_document: rename to test_large_document_over_1mb, use
  120-char body lines so content actually exceeds 1MB, assert the size invariant explicitly

- Update specs and status for Phase 2 completion and read_page redesign
  ([`7261612`](https://github.com/procontexthq/procontext/commit/726161263e9791e857beb460f1c93dae1a42bc84))

- Update README and CLAUDE.md to reflect Phase 2 complete, Phase 3 next - Align 01-functional-spec
  read_page section with new plain-text headings, offset/limit windowing design from
  04-api-reference - Update 02-technical-spec: remove old Heading class, update ReadPageInput/
  ReadPageOutput models, add headings column to page_cache schema, rewrite parser section for
  plain-text output - Update 03-implementation-guide Phase 3 file table and test expectations -
  Remove vestigial stale column from cache schema (staleness is computed dynamically at read time
  from expires_at) - Add note in 04-api-reference clarifying MCP handshake is SDK-provided

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

### Features

- Add CI pipeline
  ([`5456638`](https://github.com/procontexthq/procontext/commit/5456638778222b4eb9d348a954129ada8d32e6df))

- Add .github/workflows/ci.yml: lint (ruff), format check, type check (pyright), pytest with 80%
  coverage gate, and pip-audit dependency audit - Add pip-audit to dev dependencies in
  pyproject.toml - Fix formatting in two test files caught by ruff format --check

- Add LLMS_TXT_NOT_FOUND error code and first-run blocking registry fetch
  ([`812b387`](https://github.com/procontexthq/procontext/commit/812b38741d537e5bd01c0066bfaecfba34c494f5))

Split LLMS_TXT_FETCH_FAILED into two codes: LLMS_TXT_NOT_FOUND (404, non-recoverable) and
  LLMS_TXT_FETCH_FAILED (transient, recoverable), mirroring the PAGE_NOT_FOUND / PAGE_FETCH_FAILED
  pattern.

Add first-run blocking registry fetch with 5s timeout so agents get fresh data on first launch
  instead of stale bundled snapshot. On failure, fall back to bundled with a prominent warning
  listing actionable next steps (check internet, restart later, download manually).

Also: decouple registry paths from cache.db_path, downgrade missing local registry log from warning
  to debug, and add fast-fail env var to wire contract tests.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

- Align registry scheduler, config defaults, and specs
  ([`b5a760d`](https://github.com/procontexthq/procontext/commit/b5a760df57e033ee3ded13a5b0b2ca78dd685519))

- Cache cleanup scheduler and CHANGELOG
  ([`9d4a077`](https://github.com/procontexthq/procontext/commit/9d4a07706c0138ed911381e53de527b745bcb05a))

- Add server_metadata table to SQLite schema for tracking cleanup state - Add
  Cache.cleanup_if_due(interval_hours) — checks last_cleanup_at before running, updates timestamp on
  completion; skips silently if not due - Add cleanup_if_due to CacheProtocol - Add
  _run_cache_cleanup_scheduler in server.py — runs cleanup_if_due at startup for both transports
  (avoids redundant runs on frequent restarts), then loops on the configured interval in HTTP
  long-running mode - Wire cleanup task into lifespan alongside registry update task - Add
  CHANGELOG.md with initial v0.1.0 entry (Phases 0–4)

- Implement Phase 3 — read_page tool and heading parser
  ([`07c6782`](https://github.com/procontexthq/procontext/commit/07c6782a3024980c63c6b98de4b94d23cb8337a8))

Add the read_page MCP tool with a code-block-aware heading parser, page caching with
  stale-while-revalidate, and line-number windowing. All three MCP tools (resolve_library,
  get_library_docs, read_page) are now implemented. 153 tests pass, pyright clean.

New files: - src/procontext/parser.py — single-pass H1–H4 heading extractor -
  src/procontext/tools/read_page.py — tool handler with cache + fetch - tests/unit/test_parser.py —
  28 parser unit tests - tests/integration/test_read_page.py — 13 integration tests

Modified: - src/procontext/server.py — register read_page tool - CLAUDE.md, README.md — update Phase
  3 status to complete

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Implement Phase 4 — Streamable HTTP transport
  ([`c470e58`](https://github.com/procontexthq/procontext/commit/c470e581fdb0c9a3e64e656f2cc465ed56fb26be))

- Add MCPSecurityMiddleware as pure ASGI middleware (bearer auth, origin validation, protocol
  version check); pure ASGI avoids BaseHTTPMiddleware response buffering which would break SSE
  streaming - Add run_http_server() wiring mcp.streamable_http_app() through the security middleware
  and launching uvicorn - Add auth_enabled/auth_key fields to ServerSettings; auto-generated keys
  are not persisted — regenerated on every restart by design - Fix background refresh null-check in
  read_page.py to log a warning instead of using assert (stripped in optimised Python) - Add same
  warning log to get_library_docs.py for consistency - Add 22 security middleware tests covering
  auth, origin, and protocol version validation - Update 02-technical-spec.md: fix get_asgi_app() →
  streamable_http_app(), document pure ASGI middleware rationale and allowlist atomicity - Update
  CLAUDE.md and README.md to reflect Phase 4 completion

- Implement registry update scheduler and persistence
  ([`69cec34`](https://github.com/procontexthq/procontext/commit/69cec341c40ba55e0afb48bcc6eefda73570c372))

- Phase 0 foundation — server skeleton, models, config, errors
  ([`02db703`](https://github.com/procontexthq/procontext/commit/02db703b9f5937a8843aa9874832de484bf84e38))

- FastMCP server with lifespan, structlog logging (stderr), stdio transport - Pydantic models:
  registry (RegistryEntry, LibraryMatch), cache (TocCacheEntry, PageCacheEntry), tool I/O (all 3
  tools) - Settings via pydantic-settings: nested YAML config + env var overrides - ErrorCode
  (StrEnum) + ProContextError with code, message, suggestion, recoverable - AppState dataclass with
  progressive field population across phases - CacheProtocol + FetcherProtocol (typing.Protocol) for
  swappable backends - RegistryIndexes stub for Phase 1 - py.typed PEP 561 marker - pyproject.toml
  with hatchling build, ruff (TCH + Pydantic config), pyright standard mode -
  pro-context.example.yaml with all config fields documented - uv.lock for reproducible dev
  environments - Fix uv sync command: --dev → --extra dev in CLAUDE.md

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

- Phase 1 complete — registry, resolver, resolve-library tool, tests
  ([`a801b4b`](https://github.com/procontexthq/procontext/commit/a801b4bb566020fda8009a3819a06566980a9712))

Registry & Resolution: - load_registry() loads bundled known-libraries.json via importlib.resources
  with local path fallback for Phase 5 update mechanism - build_indexes() single-pass builds four
  indexes: by_package, by_id, by_alias (new — fixes matched_via correctness), fuzzy_corpus -
  resolve_library() 5-step algorithm: exact package → exact ID → alias → fuzzy (rapidfuzz, 70%
  cutoff) → empty list - normalise_query() strips pip extras, version specifiers, lowercases, trims

Tool handler (tools/resolve_library.py): - Input validation via ResolveLibraryInput, raises
  ProContextError on failure - Removed startup race guard — FastMCP lifespan guarantees indexes
  populated - AppState.indexes typed as non-optional RegistryIndexes (was RegistryIndexes | None)

Fixes applied during review: - Add by_alias index so Step 3 always returns matched_via="alias" (not
  a false positive from scanning fuzzy_corpus which contains all term types) - Fix
  logging.getLevelName() deprecation → getLevelNamesMapping()[level] - Wire format field names
  snake_case throughout specs and API reference (library_id, docs_url, matched_via, cached_at,
  resolved_at, etc.)

Tests (31 passing): - tests/unit/test_resolver.py — 24 tests covering all 5 resolution steps,
  normalise_query edge cases, match structure - tests/integration/test_tools.py — 7 tests covering
  full handler pipeline: valid query, output shape, no match, invalid input, pip specifier stripping

Co-Authored-By: Claude Sonnet 4-6 <noreply@anthropic.com>

- Phase 2 complete — fetcher, cache, and get_library_docs tool
  ([`25ffe72`](https://github.com/procontexthq/procontext/commit/25ffe729530a6f70a8b3e8ae415431ae8d17d8c1))

Implements the full Phase 2 feature set: - SQLite cache (aiosqlite) with stale-while-revalidate and
  7-day cleanup - httpx fetcher with SSRF protection (domain allowlist, private IP blocking, per-hop
  redirect validation, max 3 hops) - get_library_docs tool handler with cache-first lookup and
  background refresh - CacheProtocol and FetcherProtocol for testability - Comprehensive unit tests
  (cache, fetcher) and integration tests (tool handlers)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

- **cache**: Persist discovered_domains for cross-restart allowlist continuity
  ([`e5b55b7`](https://github.com/procontexthq/procontext/commit/e5b55b79a60ff37d90ad6b218d18150ae5de11cd))

Adds a discovered_domains column to toc_cache and page_cache. Base domains extracted from fetched
  content are always written to SQLite regardless of allowlist_depth config. At startup the server
  reads them back and merges into the initial allowlist so cached pages from a previous session
  remain reachable after a restart without re-fetching.

- **fetcher**: Configurable SSRF controls and runtime allowlist expansion
  ([`874eab3`](https://github.com/procontexthq/procontext/commit/874eab3187cd8f6a0c28779099b8cd6d92231ee9))

Add FetcherSettings with four new config knobs: - ssrf_private_ip_check: toggle private IP blocking
  (default on) - ssrf_domain_check: toggle domain allowlist enforcement (default on) -
  allowlist_depth: 0=registry only, 1=+llms.txt links, 2=+page links - extra_allowed_domains: manual
  trusted domains, ships with github.com and githubusercontent.com as defaults

At depth 1, get_library_docs expands state.allowlist with base domains extracted from fetched
  llms.txt content. At depth 2, read_page does the same for every fetched page. Expansion is
  monotonic and resets on registry updates.

Also fixes a silent early-return in both background refresh functions — now logs a warning when
  fetcher or cache is unexpectedly None, and replaces the assert in read_page.handle with a proper
  RuntimeError.

Spec and example config updated to document all new options.

### Refactoring

- Too_many_redirects error code, import fixes, coding guidelines rewrite
  ([`9e958d1`](https://github.com/procontexthq/procontext/commit/9e958d1fef43fead53de114b15dd8d08686a9d37))

- Add TOO_MANY_REDIRECTS error code; replace generic PAGE_FETCH_FAILED for redirect-limit breaches
  in fetcher.py - Add top-level except Exception logging guard in all three tool handlers
  (resolve_library, get_library_docs, read_page) so unexpected errors reach stderr before
  propagating - Move in-function imports to module level in cache.py and resolver.py (guideline #7);
  remove now-unused TYPE_CHECKING import from cache.py - Rewrite coding-guidelines.md in imperative
  tone; add rules 7 (no imports inside functions), 11 (catch specific exceptions), 12
  (exc_info=True), 18 (regression test per bug fix); renumber all rules 1–22 sequentially

### Testing

- Centralise subprocess test env in conftest fixture
  ([`d6b3236`](https://github.com/procontexthq/procontext/commit/d6b323617641664b0f1ec38f6cca1403f603861a))

Add subprocess_env fixture to tests/integration/conftest.py that builds the baseline env dict for
  all subprocess-based MCP tests: forces stdio transport, isolates the cache db under tmp_path, and
  redirects the registry metadata URL to an unlistened port so the first-run fetch fails fast.

Both test_mcp_wire_contract.py and test_mcp_error_envelope.py now use the fixture instead of
  duplicating os.environ.copy() + manual overrides. This also fixes a latent bug where a local
  procontext.yaml setting transport=http caused all subprocess tests to silently produce no output.
