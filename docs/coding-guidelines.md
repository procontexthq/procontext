# Coding Guidelines for Public Libraries

These guidelines are specifically curated for building high-quality public/open-source libraries.

---

## API Design

### 1. Design for the Pit of Success

Structure your API so correct usage is the path of least resistance and incorrect usage requires deliberate extra effort. Make dangerous operations verbose and explicit (`React.dangerouslySetInnerHTML` is the canonical example).

### 2. Hyrum's Law — Every Observable Behavior Becomes a Contract

> "With a sufficient number of users of an API, it does not matter what you promise in the contract: all observable behaviors of your system will be depended on by somebody." — Hyrum Wright

This means error message wording, collection iteration order, response timing, and even incidental behaviors all become de facto contracts over time. Implications:

- Document observable behaviors explicitly, including those you consider incidental
- Use randomization or chaos-testing in CI to prevent consumers depending on undocumented ordering
- Treat any bug fix that changes observable behavior as a potential breaking change

### 3. Minimize Public Surface Area

Every exported symbol is a commitment. Removing or changing it later is a breaking change that forces every downstream consumer to update. Default to the most restrictive access modifier. Only expose what has a documented, intentional use case. Use `@Beta` or equivalent annotations to reserve the right to change APIs before fully committing.

### 4. Consistent Abstractions — No Leaks by Omission

If some methods require a `tenant_id` parameter while others don't, you're leaking internal architecture inconsistencies. Consumers are forced to understand your internal design to use your API correctly. Either all logically related methods carry the parameter or none do.

### 5. Progressive Disclosure of Complexity

The 80% case should be a one-liner. The 20% advanced case should be accessible but not required reading. Layer your API:

- `fetch(url)` — zero config default
- `fetch(url, { timeout: 5000, retries: 3 })` — intermediate
- `new HttpClient(config).request(spec)` — full control

### 6. Design Intentional Escape Hatches

All non-trivial abstractions leak eventually (Joel Spolsky's Law of Leaky Abstractions). Provide documented, intentional escape hatches that let consumers drop to a lower level without abandoning your library. The hatch should be: easy to use when needed, well-integrated (easy to return to the higher abstraction), and documented with clear caveats.

---

## Error Handling

### 7. Libraries Must Never Swallow Errors

An application can log-and-continue. A library must not. Catching an error silently steals the decision from the consumer — they cannot retry, fall back, alert, or audit what they cannot see. The specific anti-pattern AI generates:

```python
try:
    ...
except Exception as e:
    logger.error(e)  # silently swallowed — DO NOT do this in library code
```

Propagate errors with enough context for the consumer to make an informed decision, or convert infrastructure errors into domain errors that expose your abstraction boundary.

### 8. Typed, Domain-Specific Error Types

Consumers need to distinguish between "network unavailable," "malformed input," and "invalid API key" without parsing strings. Use a typed error hierarchy:

- A sealed/discriminated union (TypeScript)
- Custom exception subclasses with structured fields (Python/Java)
- `Result[T, LibraryError]` where idiomatic

Each error type should carry: classification, human-readable message, and structured data the consumer needs to act on (which field failed validation, what the rate limit reset time is).

### 9. Wrap Infrastructure Errors at the Boundary

If your library uses a database, HTTP client, or file system internally, raw infrastructure exceptions must not cross your library boundary. A consumer should never need to import `httpx` or `sqlite3` to handle your library's errors. Catch infrastructure exceptions at the boundary, wrap them in your domain error types with the original as the cause.

---

## Versioning and Breaking Changes

### 10. Non-Obvious Breaking Changes AI Consistently Misses But You Must Not Miss

Not all breaking changes involve removing a method. These are routinely overlooked:

- Dropping runtime/Python version/OS compatibility (code may not change at all)
- Changing error types — consumers who `except SpecificError` silently stop catching
- Changing default parameter values — behavior changes, signature doesn't
- Narrowing accepted input types
- Changing iteration order of returned collections (see Hyrum's Law)
- Persisted data format changes — these outlive code versions

### 11. Deprecation Cycle Before Removal

The correct lifecycle:

1. Introduce the replacement in a minor release
2. Deprecate the old API in the same or following minor release (warning level)
3. Escalate to error-level deprecation in a subsequent minor release
4. Remove in the next major version

The deprecation warning must include: when deprecated, why, and exactly what to use instead. Google's policy: 12 months minimum before removal. **Do not removes APIs immediately in the same commit as the replacement — never do this.**

### 12. Machine-Readable Changelogs with Breaking Change Markers

Follow [Keep a Changelog](https://keepachangelog.com) format:

- ISO 8601 dates
- `Added / Changed / Deprecated / Removed / Fixed / Security` categories
- Breaking changes prefixed with `BREAKING` in a visible callout

Automate via Conventional Commits + semantic-release to eliminate friction. The changelog is the artifact consumers rely on before upgrading — it is not optional.

---

## Testing Strategy

### 13. Test the Public API Contract, Not the Implementation

Tests should be written from the perspective of a consumer: import the public API and assert on observable behavior, not internal state or private methods. Tests that reach into private methods break on refactoring even when behavior is unchanged.

**Target**: A complete internal rewrite should not break any test. If it does, the tests are testing the implementation, not the contract.

Do not generate tests that mirror the source file structure and test private helpers directly. Resist this pattern.

### 14. Test Deprecated APIs Until They Are Removed

Deprecated code is still public API. Consumers depending on it need it to remain stable through the deprecation cycle. Maintain tests for deprecated code and suppress deprecation warnings explicitly in those test files so future contributors know the suppression is intentional.

---

## Supply Chain Security

### 15. Publish Provenance Attestations

GitHub Actions supports signed SLSA provenance attestations — a cryptographic record proving which source commit produced which artifact, via which build pipeline. This costs one extra CI step:

```yaml
- uses: actions/attest-build-provenance@v1
  with:
    subject-path: dist/
```

Enterprise consumers increasingly require provenance for security-sensitive libraries. The absence of it is becoming an adoption barrier.

### 16. Audit Every Import

A 2025 study of 576,000 AI-generated code samples found ~20% recommended packages that do not exist in any public registry. Attackers register these hallucinated package names ("slopsquatting") with malicious code. Verify every package name against the actual registry before adding it as a dependency.

---

## Library Adoptability

### 17. Zero Dependencies is a Feature

When a library has zero (or minimal) runtime dependencies:

- No transitive CVEs land on consumers' SBOMs
- No version conflicts with other libraries in the consumer's project
- Bundle size is fully knowable and controllable

When you do inline a dependency, note the version and license in source comments. Do not import utility packages without considering the dependency implications for consumers.

### 18. The Signals Developers Use to Evaluate a Library

Before writing a line of code, experienced developers evaluate these trust signals in roughly this order:

1. **License clarity** — MIT/Apache 2.0 are frictionless; GPL/AGPL require legal review; no license means no permission
2. **Maintenance activity** — recent commits, closed issues, PR response time
3. **Dependency footprint** — transitive dependency count and bundle size
4. **Type support quality** — not just "has types" but whether generics are useful and errors are typed
5. **Changelog quality** — do maintainers document breaking changes and provide migration guides?
6. **Issue tracker health** — ratio of open/closed issues, whether bug reports get responses
7. **Security posture** — provenance attestations, CVE response time

A technically excellent library with no `LICENSE` file or a silent issue tracker will not be adopted.
