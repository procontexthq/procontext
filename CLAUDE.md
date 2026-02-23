# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## About the Project

Pro-Context is an open-source MCP (Model Context Protocol) documentation server that provides AI coding agents with accurate, up-to-date library documentation to prevent hallucination of API details. Licensed under GPL-3.0.

## About the Author

This project is authored by Ankur Tewatia, a Senior Lead Consultant with more than a decade of experience in the software industry.

## ⚠️ CRITICAL: Git Operations Policy

**NEVER commit and push changes without explicit user approval.**

You must:

1. Wait for the user to explicitly ask you to commit and push any changes made to the documentation or code.
2. If you believe a commit is necessary, you can say "I think we should commit these changes. Should I commit and push them?" and wait for the user's response.

## Project Motivation

Ankur has recently been working with Generative AI-based applications. Since this is a relatively new technology, all the libraries are relatively new as well and are updated frequently, which makes it difficult for coding agents to produce accurate code leveraging these libraries. Ankur's aim with this repo is to make coding agents more reliable by providing them with correct and up-to-date information.

## Implementation Phases

0. **Specification/Design Phase** — Define the problem, design the system architecture, and create detailed specifications. Complete when all specs in `docs/specs/` are finalized and approved by Ankur.
1. **Foundation** — MCP server skeleton, config, structured logging, error types, stdio transport, health check, registry loader
2. **Core Pipeline** — llms.txt fetcher, SQLite cache, `resolve-library` + `get-library-docs` + `read-page` tools
3. **HTTP Transport** — Streamable HTTP transport (MCP spec 2025-11-25), Origin validation, session management
4. **Polish & Production Readiness** — CI/CD, Docker, E2E tests, performance tuning, packaging (`uvx`-installable)

**Current state**: The project is in the specification/design phase. There is no source code yet. **Do not write any code until the design phase is complete.** The design phase will be considered complete when all documents in `docs/specs/` are finalized and approved by Ankur.

### Active Specifications (`docs/specs/`)

These are the authoritative design documents for the current open-source version.

- `docs/specs/01-functional-spec.md` — Problem statement, 3 MCP tools (`resolve-library`, `get-library-docs`, `read-page`), 1 resource, transport modes, registry, SQLite cache, security model, design decisions
- `docs/specs/02-technical-spec.md` — System architecture, technology stack, data models (Pydantic), in-memory registry indexes, 5-step resolution algorithm, fetcher (httpx + SSRF), SQLite cache schema, heading parser, stdio + Streamable HTTP transport, registry update mechanism, configuration, logging
- `docs/specs/03-implementation-guide.md` — Project structure, pyproject.toml, coding conventions (AppState injection, ProContextError pattern), 6 implementation phases, testing strategy (respx + in-memory SQLite), CI/CD
- `docs/specs/04-api-reference.md` — Formal MCP API: tool definitions (JSON Schema + wire format examples), resource schema, full error code catalogue, stdio and HTTP transport reference, versioning policy

You are allowed to create new documents if the discussion warrants it. Update this section to link to any new documents you create.

## Overview of tech stack, architecture, coding conventions, configurations, commands and testing strategy

This section will be updated in later phases. Make sure these sections are appropriately filled out as soon as these details are finalized.
We must only add information that Claude cannot infer on its own. Use the following as a guide:

| Include in this section                              | Do NOT include                                     |
| ---------------------------------------------------- | -------------------------------------------------- |
| Bash commands Claude can't guess                     | Anything Claude can figure out by reading code     |
| Code style rules that differ from defaults           | Standard language conventions Claude already knows |
| Testing instructions and preferred test runners      | Detailed API documentation (link to docs instead)  |
| Repository etiquette (branch naming, PR conventions) | Information that changes frequently                |
| Architectural decisions specific to this project     | Long explanations or tutorials                     |
| Developer environment quirks (required env vars)     | File-by-file descriptions of the codebase          |
| Common gotchas or non-obvious behaviors              | Self-evident practices like "write clean code"     |

## Instructions for working with this repo

1. Your job is to act as a coding partner, not as an assistant.
2. Your key responsibility is making this repo better and useful for everyone, including Ankur and yourself.
3. Ankur appreciates honest feedback. Do not blindly agree to whatever he asks.
4. When brainstorming, actively participate and add value to the conversation rather than just answering questions.
5. You are a contributor to the project. Take ownership and actively look for ways to improve this repo.
6. Avoid making assumptions. Refer to online sources and cross-verify information. If the requirement is unclear, ask Ankur for clarification.
