#!/usr/bin/env python3
"""
Markdown to TXT Converter

Converts Markdown files in the data/ directory to TXT format
for uploading to Tawk.to Knowledge Base.

Tawk.to accepts: PDF (max 20 MB), CSV (max 5 MB), TXT (max 5 MB)

Usage:
    uv run scripts/convert.py
"""

from pathlib import Path

# Configuration
DATA_DIR = Path(__file__).parent.parent / "data"
CLEANED_DIR = DATA_DIR / "cleaned"  # Source: cleaned markdown
TXT_DIR = DATA_DIR / "txt"          # Output: text files
COMBINED_FILE = DATA_DIR / "combined_knowledge_base.txt"  # Combined file at root
MAX_FILE_SIZE_MB = 5  # Tawk.to TXT limit
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def convert_markdown_to_txt():
    """Convert all cleaned Markdown files to TXT format in txt/ directory."""

    if not CLEANED_DIR.exists():
        print(f"Error: Cleaned directory not found: {CLEANED_DIR}")
        print("Run 'uv run scripts/crawl.py' first to crawl the website.")
        exit(1)

    md_files = list(CLEANED_DIR.glob("*.md"))

    if not md_files:
        print(f"No Markdown files found in {CLEANED_DIR}")
        print("Run 'uv run scripts/crawl.py' first to crawl the website.")
        exit(1)

    print(f"Found {len(md_files)} Markdown files in {CLEANED_DIR}")
    print("-" * 50)

    # Create txt directory
    TXT_DIR.mkdir(parents=True, exist_ok=True)

    converted_files = []
    total_size = 0

    for md_file in sorted(md_files):
        # Create corresponding TXT file in txt/ directory
        txt_file = TXT_DIR / md_file.with_suffix(".txt").name

        # Read markdown content
        content = md_file.read_text(encoding="utf-8")

        # Write as TXT
        txt_file.write_text(content, encoding="utf-8")

        file_size = txt_file.stat().st_size
        total_size += file_size

        size_kb = file_size / 1024
        print(f"  [CONVERTED] {txt_file.name} ({size_kb:.1f} KB)")

        converted_files.append(txt_file)

    print("-" * 50)
    print(f"Converted {len(converted_files)} files")
    print(f"Total size: {total_size / 1024:.1f} KB")

    # Check if individual files exceed limit
    oversized = [f for f in converted_files if f.stat().st_size > MAX_FILE_SIZE_BYTES]
    if oversized:
        print(
            f"\nWarning: {len(oversized)} file(s) exceed the {MAX_FILE_SIZE_MB} MB limit:"
        )
        for f in oversized:
            print(f"  - {f.name} ({f.stat().st_size / 1024 / 1024:.2f} MB)")
        print("Consider splitting these files before uploading to Tawk.to")

    # Create combined file at root level
    if total_size < MAX_FILE_SIZE_BYTES:
        create_combined_file(converted_files)
    else:
        print(f"\nCombined file would exceed {MAX_FILE_SIZE_MB} MB limit.")
        print("Upload individual TXT files to Tawk.to instead.")

    return converted_files


def create_combined_file(txt_files: list[Path]):
    """Create a single combined TXT file at root level with all content."""

    separator = "\n\n" + "=" * 80 + "\n\n"

    content_parts = []
    for txt_file in sorted(txt_files):
        content = txt_file.read_text(encoding="utf-8")
        # Add a header showing the source file
        header = f"# Source: {txt_file.name}\n\n"
        content_parts.append(header + content)

    combined_content = separator.join(content_parts)
    COMBINED_FILE.write_text(combined_content, encoding="utf-8")

    size_mb = COMBINED_FILE.stat().st_size / 1024 / 1024
    print(f"\nCreated combined file: {COMBINED_FILE.name} ({size_mb:.2f} MB)")
    print(f"Location: {COMBINED_FILE}")

    if size_mb < MAX_FILE_SIZE_MB:
        print("This file can be uploaded directly to Tawk.to")
    else:
        print(f"Warning: Combined file exceeds {MAX_FILE_SIZE_MB} MB limit")
        print("Upload individual TXT files instead")


def main():
    """Main entry point."""
    print("Converting Markdown files to TXT format...")
    print(f"Data directory: {DATA_DIR}\n")

    converted = convert_markdown_to_txt()

    if converted:
        print("\nNext steps:")
        print("1. Log into your Tawk.to dashboard")
        print("2. Navigate to: Administration > AI Assist > Data Sources")
        print(
            "3. Click 'Upload Files' and select the TXT files from the 'data/' folder"
        )
        print("4. Wait for Tawk.to to process the uploaded content")
        print("5. Test the AI Assist chatbot to verify it uses the knowledge base")


if __name__ == "__main__":
    main()
