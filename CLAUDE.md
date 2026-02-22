# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

AI-powered chatbot for Karya Siddhi Hanuman Temple. ETL pipeline that crawls the temple website, cleans content with an LLM, and uploads it to Tawk.to's AI Assist knowledge base. The frontend is a static HTML page with an embedded Tawk.to chat widget.

## Commands

```bash
# Setup
uv sync                        # Install dependencies

# Pipeline (run in order)
uv run scripts/crawl.py         # Crawl temple website → data/raw/
uv run scripts/clean.py         # LLM-clean raw content → data/cleaned/
uv run scripts/convert.py       # Convert to TXT → data/txt/
```

No test suite exists.

## Architecture

**ETL pipeline with decoupled frontend:**

```
dallashanuman.org
  → crawl.py (Crawl4AI + Playwright, BFS)
  → data/raw/*.md
  → clean.py (LiteLLM, interactive provider selection)
  → data/cleaned/*.md
  → convert.py
  → data/txt/*.txt + combined_knowledge_base.txt
  → [manual upload to Tawk.to]
  → index.html (static, Tawk.to widget)
```

- **crawl.py**: BFS web crawler using Crawl4AI with Playwright for JS rendering (Nuxt.js site). Streams pages incrementally, adds YAML frontmatter with source URL and depth.
- **clean.py**: Sends raw markdown to LLM (Ollama/Anthropic/OpenRouter via LiteLLM) with a cleaning prompt. Adaptive rate limiting with exponential backoff. Truncates content to ~12k chars for token safety.
- **convert.py**: Renames .md to .txt, generates a combined knowledge base file. Validates against Tawk.to's 5 MB limit.
- **index.html**: Static landing page, no build step. Temple logo + Tawk.to chat widget.

## Tech Stack

- Python 3.13, managed with `uv`
- crawl4ai (web crawling), litellm (unified LLM API), questionary (CLI prompts)
- Static HTML frontend (no framework, no build)

## Environment

Copy `.env.example` to `.env`. Requires at least one LLM provider configured (Ollama for local, Anthropic or OpenRouter for cloud). Key variables: `MAX_CRAWL_DEPTH`, `MAX_PAGES`, and provider-specific API keys/models.

## Data

`data/` is git-ignored. Pipeline generates: `data/raw/` (scraped markdown), `data/cleaned/` (LLM-processed), `data/txt/` (Tawk.to-ready), and `data/combined_knowledge_base.txt`.
