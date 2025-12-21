# KSHT Chatbot Demo

A proof-of-concept AI chatbot for the [Karya Siddhi Hanuman Temple](https://www.dallashanuman.org/) that can answer visitor questions about temple services, events, timings, and more.

> **Disclaimer**: This is an unofficial demo created to explore AI-assisted visitor support. Not affiliated with or endorsed by Karya Siddhi Hanuman Temple.

## How It Works

The chatbot is powered by content scraped directly from the temple's website:

1. **Crawl** - A script visits every page on the temple website and saves the content
2. **Clean** - An AI reads each page and extracts only the useful information (removing menus, footers, etc.)
3. **Upload** - The cleaned content is uploaded to Tawk.to's Knowledge Base
4. **Chat** - Visitors can ask questions and get instant answers based on the temple's own content

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Pages                             │
│        index.html with Tawk.to chat widget                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Tawk.to                                 │
│   - Live chat widget embedded on the page                    │
│   - AI Assist answers questions from Knowledge Base          │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ manual upload
┌─────────────────────────────────────────────────────────────┐
│                  Python Scripts                              │
│                                                              │
│   crawl.py  ──▶  data/raw/*.md   (raw scraped content)      │
│   clean.py  ──▶  data/cleaned/*.md (AI-cleaned content)     │
│   convert.py ──▶ data/txt/*.txt  (for Tawk.to upload)       │
└─────────────────────────────────────────────────────────────┘
```

### Current Stats

| Metric               | Value  |
| -------------------- | ------ |
| Pages crawled        | 198    |
| Pages cleaned        | 198    |
| Raw content size     | 1.1 MB |
| Cleaned content size | 872 KB |

Content includes temple history, deity information, event schedules, class offerings, puja services, cafeteria menu, and more.

---

## Technical Details

### Prerequisites

- **[uv](https://docs.astral.sh/uv/)** - Fast Python package manager
- **Python 3.13+**
- **LLM Provider** - One of: Ollama (local), Anthropic, or OpenRouter

### Quick Start

#### 1. Clone and install

```bash
git clone https://github.com/spenpal/ksht-chatbot-demo.git
cd ksht-chatbot-demo
uv sync
```

#### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your preferred LLM provider credentials
```

#### 3. Set up an LLM provider

Choose one:

| Provider       | Speed  | Privacy | Cost      | Setup                                                                 |
| -------------- | ------ | ------- | --------- | --------------------------------------------------------------------- |
| **Ollama**     | Fast   | Local   | Free      | `brew install ollama && ollama pull llama3.2:3b`                      |
| **Anthropic**  | Fast   | Cloud   | Paid      | Get API key at [console.anthropic.com](https://console.anthropic.com) |
| **OpenRouter** | Varies | Cloud   | Free tier | Get API key at [openrouter.ai](https://openrouter.ai)                 |

#### 4. Run the pipeline

```bash
# Step 1: Crawl the website (saves to data/raw/)
uv run scripts/crawl.py

# Step 2: Clean content with AI (saves to data/cleaned/)
uv run scripts/clean.py

# Step 3: Convert to TXT for Tawk.to (saves to data/txt/)
uv run scripts/convert.py
```

#### 5. Upload to Tawk.to

1. Log into [Tawk.to dashboard](https://dashboard.tawk.to/)
2. Go to **Administration** → **AI Assist** → **Data Sources**
3. Click **Upload Files** and select files from `data/txt/`

### Scripts

#### `crawl.py` - Web Crawler

Uses [Crawl4AI](https://github.com/unclecode/crawl4ai) to crawl the temple website:

- **BFS Deep Crawl**: Systematically visits all internal links up to configured depth
- **JavaScript Rendering**: Handles the Nuxt.js-based site with browser automation
- **Streaming Mode**: Saves pages incrementally as they're crawled

Configuration (via `.env`):

- `MAX_CRAWL_DEPTH` - How many links deep to crawl (default: 3)
- `MAX_PAGES` - Maximum pages to crawl (default: 100)

#### `clean.py` - AI Content Cleaner

Uses [LiteLLM](https://github.com/BerriAI/litellm) for unified LLM access:

- **Multi-Provider**: Supports Ollama, Anthropic, and OpenRouter
- **Adaptive Rate Limiting**: Automatically detects and handles rate limits from any provider
- **Smart Retry**: Parses error messages to wait exactly as long as needed

The AI is prompted to:

- Remove navigation, menus, footers, sidebars
- Remove ads, widgets, social media buttons
- Keep temple information, schedules, services, contact info
- Preserve markdown formatting

#### `convert.py` - Format Converter

Converts cleaned markdown to TXT for Tawk.to:

- Validates file size limits (5 MB max per file)
- Creates combined knowledge base file if under limit
- Preserves markdown formatting in TXT output

### Configuration

All options are in `.env.example`:

```bash
# LLM Providers (used by clean.py)
OLLAMA_MODEL=llama3.2:3b
OLLAMA_BASE_URL=http://localhost:11434

ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-3-5-haiku-latest

OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=google/gemma-3-27b-it:free

# Crawl Settings (used by crawl.py)
MAX_CRAWL_DEPTH=3
MAX_PAGES=100
```

### Project Structure

```
ksht-chatbot-demo/
├── index.html          # Frontend with Tawk.to widget
├── images/
│   └── ksht-logo.png   # Temple logo
├── scripts/
│   ├── crawl.py        # Web crawler
│   ├── clean.py        # AI content cleaner
│   └── convert.py      # Markdown to TXT converter
├── data/               # Generated content (git-ignored)
│   ├── raw/            # Raw scraped markdown
│   ├── cleaned/        # AI-cleaned markdown
│   └── txt/            # TXT files for upload
├── .env.example        # Configuration template
└── pyproject.toml      # Python dependencies
```

### Dependencies

- `crawl4ai` - Web crawling with browser automation
- `litellm` - Unified LLM API (Ollama, Anthropic, OpenRouter, etc.)
- `questionary` - Interactive CLI prompts
- `python-dotenv` - Environment variable management
