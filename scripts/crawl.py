#!/usr/bin/env python3
"""
KSHT Website Crawler

Crawls the Karya Siddhi Hanuman Temple website (https://www.dallashanuman.org/)
and extracts content as raw Markdown for further processing.

Usage:
    uv run scripts/crawl.py
"""

import asyncio
import os
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    DefaultMarkdownGenerator,
)
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
TARGET_URL = "https://www.dallashanuman.org/"
DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
MAX_DEPTH = int(os.getenv("MAX_CRAWL_DEPTH", "3"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "100"))


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
    """Save raw crawl result. Returns True if saved."""
    if not result.success:
        print(f"  [FAILED] {result.url}: {result.error_message}")
        return False

    # Get raw markdown content
    raw_markdown = ""

    if result.markdown:
        raw_md = getattr(result.markdown, "raw_markdown", None)
        if raw_md:
            raw_markdown = raw_md

    # Skip if no content
    if not raw_markdown or len(raw_markdown.strip()) < 50:
        print(f"  [SKIPPED] {result.url}: No content or too short")
        return False

    # Create filename from URL
    filename = sanitize_filename(result.url)

    # Create metadata header
    depth = result.metadata.get("depth", 0) if result.metadata else 0
    header = f"""---
source: {result.url}
crawl_depth: {depth}
---

"""

    # Save raw markdown
    filepath = RAW_DIR / f"{filename}.md"

    # Handle duplicates
    counter = 1
    base_filename = filename
    while filepath.exists() or str(filepath) in saved_files:
        filepath = RAW_DIR / f"{base_filename}_{counter}.md"
        counter += 1

    filepath.write_text(header + raw_markdown, encoding="utf-8")
    saved_files.add(str(filepath))
    print(f"  [SAVED] {filepath.name} ({len(raw_markdown)} chars)")

    return True


async def crawl_website():
    """Crawl the KSHT website and save content as raw Markdown files."""

    # Wipe and recreate raw directory
    if RAW_DIR.exists():
        shutil.rmtree(RAW_DIR)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\nCrawling: {TARGET_URL}")
    print(f"Max depth: {MAX_DEPTH}")
    print(f"Max pages: {MAX_PAGES}")
    print(f"Output directory: {RAW_DIR}\n")

    # Browser configuration for JS-rendered sites (Nuxt.js)
    browser_config = BrowserConfig(
        headless=True,
        verbose=True,
        viewport_width=1280,
        viewport_height=720,
    )

    # Deep crawl strategy
    deep_crawl_strategy = BFSDeepCrawlStrategy(
        max_depth=MAX_DEPTH,
        include_external=False,
        max_pages=MAX_PAGES,
    )

    # Basic content filtering (no LLM)
    content_filter = PruningContentFilter(
        threshold=0.48,
        threshold_type="fixed",
        min_word_threshold=10,
    )

    markdown_generator = DefaultMarkdownGenerator(
        content_filter=content_filter, options={"ignore_links": False}
    )

    # Crawler configuration
    crawler_config = CrawlerRunConfig(
        deep_crawl_strategy=deep_crawl_strategy,
        markdown_generator=markdown_generator,
        cache_mode=CacheMode.BYPASS,
        word_count_threshold=10,
        excluded_tags=["script", "style", "nav", "footer", "header"],
        exclude_external_links=False,
        verbose=True,
        # Wait for JavaScript to render content
        wait_until="networkidle",
        delay_before_return_html=5.0,
        page_timeout=90000,
        # Wait for loading placeholder to disappear
        wait_for="js:() => !document.body.innerText.includes('Retrieving Page')",
        wait_for_timeout=15000,
        stream=True,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        print("Starting crawl (streaming mode)...")
        saved_count = 0
        crawled_count = 0
        saved_files: set = set()

        async for result in await crawler.arun(TARGET_URL, config=crawler_config):
            crawled_count += 1
            if save_result(result, saved_files):
                saved_count += 1

            if crawled_count % 10 == 0:
                print(
                    f"\n--- Progress: {crawled_count} crawled, {saved_count} saved ---\n"
                )

        print(
            f"\nCrawl complete! Saved {saved_count}/{crawled_count} pages to {RAW_DIR}"
        )

        return saved_count


def main():
    """Main entry point."""
    saved_count = asyncio.run(crawl_website())

    if saved_count == 0:
        print("\nNo pages were saved. Check the target URL and try again.")
        exit(1)

    print("\nNext steps:")
    print("1. Review raw files in data/raw/")
    print("2. Run 'uv run scripts/clean.py' to clean content with LLM")
    print("3. Run 'uv run scripts/convert.py' to convert to TXT format")


if __name__ == "__main__":
    main()
