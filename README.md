# KSHT Chatbot Demo

A demo AI chatbot using [Tawk.to](https://www.tawk.to/) for the [Karya Siddhi Hanuman Temple](https://www.dallashanuman.org/).

This project demonstrates how to:

1. Crawl a website comprehensively using [Crawl4AI](https://github.com/unclecode/crawl4ai)
2. Extract clean content with LLM-assisted filtering (via OpenRouter)
3. Convert content to formats compatible with Tawk.to's Knowledge Base
4. Host a simple static demo page on GitHub Pages

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Pages                             │
│   index.html with centered logo + Tawk.to chat widget       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Tawk.to                                 │
│   - Live chat widget                                         │
│   - AI Assist (uses Knowledge Base to answer queries)        │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ (manual upload)
┌─────────────────────────────────────────────────────────────┐
│                  Python Scripts                              │
│   crawl.py  ──▶  data/*.md  ──▶  data/*.txt                 │
│   (Crawl4AI)     (Markdown)      (for Tawk.to)              │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

- **Python 3.13+**
- **[uv](https://docs.astral.sh/uv/)** - Fast Python package manager
- **OpenRouter API Key** (free) - For LLM-assisted content extraction

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/ksht-chatbot-demo.git
cd ksht-chatbot-demo
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your OpenRouter API key:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

> **Get a free API key:** Sign up at [openrouter.ai](https://openrouter.ai/) and create an API key. Free models like `google/gemma-3-27b-it:free` are available.

### 4. Crawl the website

```bash
uv run scripts/crawl.py
```

This will:

- Crawl the temple website (https://www.dallashanuman.org/)
- Extract content using LLM-assisted filtering
- Save Markdown files to the `data/` directory

### 5. Convert to TXT format

```bash
uv run scripts/convert.py
```

This converts Markdown files to TXT format, which Tawk.to accepts for upload.

### 6. Upload to Tawk.to

Since Tawk.to doesn't have a public API for document uploads, you'll need to upload manually:

1. Log into your [Tawk.to dashboard](https://dashboard.tawk.to/)
2. Navigate to **Administration** → **AI Assist** → **Data Sources**
3. Click **Upload Files**
4. Select the TXT files from the `data/` folder
5. Wait for Tawk.to to process the content

## Project Structure

```
ksht-chatbot-demo/
├── index.html          # Static demo page (for GitHub Pages)
├── images/
│   └── ksht-logo.png   # Temple logo (400x400)
├── scripts/
│   ├── crawl.py        # Website crawler using Crawl4AI
│   └── convert.py      # Markdown to TXT converter
├── data/               # Crawled content (Markdown + TXT files)
├── .env.example        # Environment variables template
├── .gitignore          # Git ignore rules
├── pyproject.toml      # Python project configuration
└── README.md           # This file
```

## Configuration

### Environment Variables

| Variable             | Required | Default                      | Description                           |
| -------------------- | -------- | ---------------------------- | ------------------------------------- |
| `OPENROUTER_API_KEY` | Yes\*    | -                            | OpenRouter API key for LLM extraction |
| `OPENROUTER_MODEL`   | No       | `google/gemma-3-27b-it:free` | OpenRouter model to use               |
| `MAX_CRAWL_DEPTH`    | No       | `3`                          | Maximum crawl depth                   |
| `MAX_PAGES`          | No       | `100`                        | Maximum pages to crawl                |

\*The crawler will work without an API key, but content filtering will be less accurate.

### OpenRouter Free Models

Recommended free models for content extraction:

| Model                                    | Context | Best For                   |
| ---------------------------------------- | ------- | -------------------------- |
| `google/gemma-3-27b-it:free`             | 131K    | General content extraction |
| `meta-llama/llama-3.3-70b-instruct:free` | 131K    | Higher quality extraction  |

## GitHub Pages Deployment

The demo page can be hosted on GitHub Pages:

1. Push the repository to GitHub
2. Go to **Settings** → **Pages**
3. Under "Source", select **Deploy from a branch**
4. Choose the `main` branch and `/ (root)` folder
5. Click **Save**

Your site will be available at: `https://<username>.github.io/ksht-chatbot-demo/`

## How It Works

### 1. Web Crawling (crawl.py)

Uses Crawl4AI with:

- **BFS Deep Crawl Strategy**: Systematically crawls all pages within the domain
- **LLM Content Filter**: Uses OpenRouter to intelligently extract relevant content
- **Markdown Generation**: Outputs clean, structured Markdown

### 2. Format Conversion (convert.py)

Converts Markdown to TXT because:

- Tawk.to only accepts PDF, CSV, or TXT for Knowledge Base uploads
- TXT preserves Markdown readability while being compatible
- Automatically checks file size limits (5 MB max for TXT)

### 3. Tawk.to AI Assist

Once TXT files are uploaded:

- Tawk.to indexes the content in its Knowledge Base
- AI Assist uses this knowledge to answer visitor questions
- The chat widget on your page connects visitors to the AI

## Troubleshooting

### Crawler not finding pages

- Check if the target website uses JavaScript rendering (may need browser mode)
- Verify the website is accessible and not blocking crawlers
- Try increasing `MAX_CRAWL_DEPTH` in `.env`

### LLM extraction not working

- Verify your `OPENROUTER_API_KEY` is correct
- Check if the free model has rate limits
- The crawler will fall back to basic filtering if LLM fails

### Files too large for Tawk.to

- Tawk.to has a 5 MB limit for TXT files
- The converter creates individual files per page
- Upload files individually instead of the combined file
