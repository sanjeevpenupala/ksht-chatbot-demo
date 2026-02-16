#!/usr/bin/env python3
"""
LLM Content Cleaner

Processes raw markdown files from data/raw/ using an LLM
to create clean, RAG-ready markdown for Tawk.to.

Usage:
    uv run scripts/clean.py
"""

import argparse
import os
import re
import shutil
import sys
import time
from pathlib import Path

import httpx
import questionary
from dotenv import load_dotenv
from litellm import completion

# Load environment variables
load_dotenv()

# Configuration
DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
CLEANED_DIR = DATA_DIR / "cleaned"

# LLM configuration
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-3-27b-it:free")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")

# Cleaning prompt
CLEANING_PROMPT = """You are preparing temple website content for a knowledge base chatbot.

Clean this scraped markdown by:
1. Removing navigation, menus, footers, sidebars
2. Removing ads, widgets, social media buttons
3. Removing duplicate or boilerplate text
4. Keeping all substantive temple content

Preserve:
- Temple information, history, deity descriptions
- Event schedules, timings, dates
- Service/puja details and procedures
- Contact info, directions, hours
- Educational content about traditions

Output clean, well-formatted markdown. Keep the same heading structure.
Do not add commentary - only output the cleaned content.

Here is the content to clean:

"""


def is_ollama_available() -> bool:
    """Check if Ollama is running and accessible."""
    try:
        response = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


def prompt_llm_selection() -> str:
    """Prompt user to select LLM provider for content cleaning."""
    print("\nSelect LLM provider for content cleaning:")

    choice = questionary.select(
        "Choose an option:",
        choices=[
            "Ollama (local, fast)",
            "Anthropic (cloud, direct API)",
            "OpenRouter (cloud, free tier available)",
        ],
        default="Ollama (local, fast)",
    ).ask()

    if choice is None:
        print("\nCleaning cancelled by user.")
        sys.exit(0)

    if choice.startswith("Ollama"):
        if not OLLAMA_MODEL or OLLAMA_MODEL.strip() == "":
            print("\nError: OLLAMA_MODEL not set in .env file")
            print("Please set OLLAMA_MODEL (e.g., OLLAMA_MODEL=llama3.2:3b)")
            sys.exit(1)
        if not is_ollama_available():
            print(f"\nError: Ollama is not running at {OLLAMA_BASE_URL}")
            print("Please start Ollama: ollama serve")
            sys.exit(1)
        return "ollama"
    elif choice.startswith("Anthropic"):
        if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY.strip() == "":
            print("\nError: ANTHROPIC_API_KEY not set in .env file")
            print("Get an API key at https://console.anthropic.com/")
            sys.exit(1)
        return "anthropic"
    else:
        if not OPENROUTER_API_KEY or OPENROUTER_API_KEY.strip() == "":
            print("\nError: OPENROUTER_API_KEY not set in .env file")
            print("Get a free API key at https://openrouter.ai/")
            sys.exit(1)
        return "openrouter"


def extract_frontmatter(content: str) -> tuple[str, str]:
    """Extract YAML frontmatter from markdown content.

    Returns (frontmatter, body) tuple.
    """
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = f"---{parts[1]}---\n\n"
            body = parts[2].strip()
            return frontmatter, body
    return "", content


def clean_content(content: str, provider: str) -> str:
    """Clean content using LLM.

    Args:
        content: Raw markdown content to clean
        provider: "ollama" or "openrouter"

    Returns:
        Cleaned markdown content
    """
    if provider == "ollama":
        model = f"ollama/{OLLAMA_MODEL}"
        api_base = OLLAMA_BASE_URL
        api_key = None
    elif provider == "anthropic":
        model = ANTHROPIC_MODEL
        api_base = None
        api_key = ANTHROPIC_API_KEY
    else:
        model = f"openrouter/{OPENROUTER_MODEL}"
        api_base = None
        api_key = OPENROUTER_API_KEY

    # Truncate very long content to avoid token limits
    # Rough estimate: 1 token ≈ 4 chars, keep input under ~12k chars
    max_input_chars = 12000
    if len(content) > max_input_chars:
        content = content[:max_input_chars] + "\n\n[Content truncated...]"

    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = completion(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": CLEANING_PROMPT + content,
                    }
                ],
                api_base=api_base,
                api_key=api_key,
                max_tokens=4000,
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            error_str = str(e)
            error_lower = error_str.lower()

            if "rate_limit" in error_lower or "429" in error_lower:
                # Try to extract wait time from error message
                wait_time = _parse_retry_after(error_str)
                if wait_time is None:
                    # Fallback: exponential backoff starting at 10s
                    wait_time = min(10 * (2**attempt), 300)

                print(f"    Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"    LLM error: {e}")
                return ""

    print("    Failed after max retries")
    return ""


def _parse_retry_after(error_str: str) -> int | None:
    """Parse retry-after time from error message."""
    # Look for patterns like "try again in X seconds" or "retry after X"
    patterns = [
        r"try again in (\d+\.?\d*)\s*(?:second|sec|s)",
        r"retry.after[:\s]+(\d+\.?\d*)",
        r"wait (\d+\.?\d*)\s*(?:second|sec|s)",
        r"(\d+\.?\d*)\s*(?:second|sec|s).*(?:limit|wait|retry)",
    ]

    for pattern in patterns:
        match = re.search(pattern, error_str, re.IGNORECASE)
        if match:
            return int(float(match.group(1))) + 1  # Add 1s buffer

    return None


def process_file(filepath: Path, provider: str) -> bool:
    """Process a single file with LLM cleaning.

    Returns True if successful.
    """
    try:
        content = filepath.read_text(encoding="utf-8")

        # Separate frontmatter from body
        frontmatter, body = extract_frontmatter(content)

        if len(body.strip()) < 50:
            print("    Skipped (too short)")
            return False

        # Clean the body content
        cleaned_body = clean_content(body, provider)

        if not cleaned_body or len(cleaned_body.strip()) < 20:
            print("    Failed (empty result)")
            return False

        # Save with frontmatter preserved
        output_path = CLEANED_DIR / filepath.name
        output_path.write_text(frontmatter + cleaned_body, encoding="utf-8")

        print(f"    Saved ({len(cleaned_body)} chars)")
        return True

    except Exception as e:
        print(f"    Error: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Clean raw markdown with LLM")
    parser.add_argument(
        "--provider",
        choices=["ollama", "anthropic", "openrouter"],
        help="LLM provider (skips interactive prompt)",
    )
    args = parser.parse_args()

    # Check raw directory exists
    if not RAW_DIR.exists():
        print(f"Error: Raw directory not found: {RAW_DIR}")
        print("Run 'uv run scripts/crawl.py' first to crawl the website.")
        sys.exit(1)

    # Get all markdown files
    md_files = sorted(RAW_DIR.glob("*.md"))

    if not md_files:
        print(f"No markdown files found in {RAW_DIR}")
        print("Run 'uv run scripts/crawl.py' first to crawl the website.")
        sys.exit(1)

    print(f"Found {len(md_files)} files in {RAW_DIR}")

    # Use CLI arg or prompt for LLM provider
    if args.provider:
        provider = args.provider
    else:
        provider = prompt_llm_selection()

    if provider == "ollama":
        print(f"\nUsing Ollama (model: {OLLAMA_MODEL})")
    elif provider == "anthropic":
        print(f"\nUsing Anthropic (model: {ANTHROPIC_MODEL})")
    else:
        print(f"\nUsing OpenRouter (model: {OPENROUTER_MODEL})")

    # Wipe and recreate cleaned directory
    if CLEANED_DIR.exists():
        shutil.rmtree(CLEANED_DIR)
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Output directory: {CLEANED_DIR}\n")
    print("-" * 50)

    # Process each file
    success_count = 0
    for i, filepath in enumerate(md_files, 1):
        print(f"[{i}/{len(md_files)}] Cleaning {filepath.name}...")
        if process_file(filepath, provider):
            success_count += 1

    print("-" * 50)
    print(f"\nCleaned {success_count}/{len(md_files)} files")

    if success_count == 0:
        print("\nNo files were cleaned. Check LLM configuration and try again.")
        sys.exit(1)

    print("\nNext steps:")
    print("1. Review cleaned files in data/cleaned/")
    print("2. Run 'uv run scripts/convert.py' to convert to TXT format")
    print("3. Upload TXT files to Tawk.to Knowledge Base")


if __name__ == "__main__":
    main()
