#!/usr/bin/env python3
"""
KSHT Website Crawler

Crawls the Karya Siddhi Hanuman Temple website (https://www.dallashanuman.org/)
and extracts content as clean Markdown for Tawk.to AI Assist knowledge base.

Usage:
    uv run scripts/crawl.py
"""

import asyncio
import os
import re
from pathlib import Path
from urllib.parse import urlparse

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    DefaultMarkdownGenerator,
    LLMConfig,
)
from crawl4ai.content_filter_strategy import LLMContentFilter, PruningContentFilter
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
TARGET_URL = "https://www.dallashanuman.org/"
DATA_DIR = Path(__file__).parent.parent / "data"
MAX_DEPTH = int(os.getenv("MAX_CRAWL_DEPTH", "3"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "100"))

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-3-27b-it:free")

# Fast mode: skip LLM processing for much faster crawling
FAST_MODE = os.getenv("FAST_MODE", "false").lower() == "true"


def sanitize_filename(url: str) -> str:
    """Convert URL to a safe filename."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    if not path:
        return "index"

    # Replace path separators with underscores
    filename = path.replace("/", "_")
    # Remove or replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
    # Remove any file extensions
    filename = re.sub(r"\.(html?|php|aspx?)$", "", filename, flags=re.IGNORECASE)
    # Limit length
    if len(filename) > 100:
        filename = filename[:100]

    return filename or "page"


def save_result(result, saved_files: set) -> bool:
    """Save a single crawl result to a markdown file. Returns True if saved."""
    if not result.success:
        print(f"  [FAILED] {result.url}: {result.error_message}")
        return False

    # Get markdown content
    markdown_content = ""
    if result.markdown:
        # Prefer filtered markdown if available
        if hasattr(result.markdown, "fit_markdown") and result.markdown.fit_markdown:
            markdown_content = result.markdown.fit_markdown
        elif hasattr(result.markdown, "raw_markdown"):
            markdown_content = result.markdown.raw_markdown
        else:
            markdown_content = str(result.markdown)

    if not markdown_content or len(markdown_content.strip()) < 50:
        print(f"  [SKIPPED] {result.url}: No meaningful content")
        return False

    # Create filename from URL
    filename = sanitize_filename(result.url)
    filepath = DATA_DIR / f"{filename}.md"

    # Handle duplicate filenames
    counter = 1
    while filepath.exists() or str(filepath) in saved_files:
        filepath = DATA_DIR / f"{filename}_{counter}.md"
        counter += 1

    # Add metadata header
    depth = result.metadata.get("depth", 0) if result.metadata else 0
    header = f"""---
source: {result.url}
crawl_depth: {depth}
---

"""

    # Save markdown file immediately
    filepath.write_text(header + markdown_content, encoding="utf-8")
    saved_files.add(str(filepath))
    print(f"  [SAVED] {filepath.name} ({len(markdown_content)} chars)")
    return True


def create_markdown_generator(use_llm: bool = True):
    """Create a markdown generator with optional LLM content filtering."""

    # Skip LLM if fast mode is enabled
    if FAST_MODE:
        print("FAST MODE: Skipping LLM processing for speed")
        use_llm = False

    if use_llm and OPENROUTER_API_KEY:
        print(f"Using LLM-assisted extraction with model: {OPENROUTER_MODEL}")

        llm_config = LLMConfig(
            provider=f"openrouter/{OPENROUTER_MODEL}",
            api_token=OPENROUTER_API_KEY,
        )

        content_filter = LLMContentFilter(
            llm_config=llm_config,
            instruction="""
            Extract the main content from this temple website page.
            Focus on:
            - Temple information (history, deities, significance)
            - Event schedules and timings
            - Puja/service information and procedures
            - Contact information and directions
            - Educational content about Hindu traditions
            - Important announcements

            Exclude:
            - Navigation menus and sidebars
            - Footer content
            - Advertisements
            - Social media widgets

            Format the output as clean, well-structured markdown.
            Preserve any dates, times, and contact details exactly as shown.
            """,
            chunk_token_threshold=4096,
            verbose=True,
        )

        return DefaultMarkdownGenerator(
            content_filter=content_filter, options={"ignore_links": False}
        )
    else:
        print("Using basic content filtering (no LLM)")

        # Fallback to pruning filter if no API key
        content_filter = PruningContentFilter(
            threshold=0.48,
            threshold_type="fixed",
            min_word_threshold=10,
        )

        return DefaultMarkdownGenerator(
            content_filter=content_filter, options={"ignore_links": False}
        )


async def crawl_website():
    """Crawl the KSHT website and save content as Markdown files."""

    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Clear existing markdown files
    for md_file in DATA_DIR.glob("*.md"):
        md_file.unlink()

    print(f"\nCrawling: {TARGET_URL}")
    print(f"Max depth: {MAX_DEPTH}")
    print(f"Max pages: {MAX_PAGES}")
    print(f"Output directory: {DATA_DIR}\n")

    # Browser configuration
    # Use full browser rendering for JavaScript-heavy sites like Nuxt.js
    browser_config = BrowserConfig(
        headless=True,
        verbose=True,
        viewport_width=1280,
        viewport_height=720,
    )

    # Deep crawl strategy
    deep_crawl_strategy = BFSDeepCrawlStrategy(
        max_depth=MAX_DEPTH,
        include_external=False,  # Stay within the domain
        max_pages=MAX_PAGES,
    )

    # Create markdown generator
    markdown_generator = create_markdown_generator(use_llm=True)

    # Crawler run configuration
    # Note: Don't use LXMLWebScrapingStrategy - this site is JavaScript-rendered (Nuxt.js)
    # We need the default browser-based rendering to wait for JS content to load
    crawler_config = CrawlerRunConfig(
        deep_crawl_strategy=deep_crawl_strategy,
        markdown_generator=markdown_generator,
        cache_mode=CacheMode.BYPASS,  # Always fetch fresh content
        word_count_threshold=10,
        excluded_tags=["script", "style", "nav", "footer", "header"],
        exclude_external_links=False,
        verbose=True,
        # Wait for JavaScript to render content
        wait_until="networkidle",  # Wait for network to be idle
        delay_before_return_html=2.0,  # Extra 2 seconds for JS to finish
        page_timeout=60000,  # 60 second timeout for slow pages
        # Enable streaming for incremental results
        stream=True,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        print("Starting crawl (streaming mode - files saved as they're crawled)...")
        saved_count = 0
        crawled_count = 0
        saved_files: set = set()

        # Stream results - each page is yielded as it's crawled
        async for result in await crawler.arun(TARGET_URL, config=crawler_config):
            crawled_count += 1
            if save_result(result, saved_files):
                saved_count += 1

            # Progress update every 10 pages
            if crawled_count % 10 == 0:
                print(f"\n--- Progress: {crawled_count} crawled, {saved_count} saved ---\n")

        print(f"\nCrawl complete! Saved {saved_count}/{crawled_count} pages to {DATA_DIR}")

        return saved_count


def main():
    """Main entry point."""
    if not OPENROUTER_API_KEY:
        print("Warning: OPENROUTER_API_KEY not set. Using basic content filtering.")
        print("Set the API key in .env for LLM-assisted extraction.\n")

    saved_count = asyncio.run(crawl_website())

    if saved_count == 0:
        print("\nNo pages were saved. Check the target URL and try again.")
        exit(1)

    print("\nNext steps:")
    print("1. Review the Markdown files in the 'data/' directory")
    print("2. Run 'uv run scripts/convert.py' to convert to TXT format")
    print("3. Upload the TXT files to Tawk.to Knowledge Base")


if __name__ == "__main__":
    main()
