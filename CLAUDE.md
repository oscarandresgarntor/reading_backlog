# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Reading Backlog is a system to save articles for later reading with automatic metadata extraction. It combines a Python backend (FastAPI), CLI tool (Typer), Chrome extension, and web dashboard.

## Common Commands

```bash
# Setup
source venv/bin/activate
pip install -e .

# Start the server (runs at http://127.0.0.1:5123)
python scripts/start_server.py

# CLI usage
reading list                          # List all articles
reading add <url>                     # Add article from URL
reading add-local ~/path/to/file.pdf  # Add local PDF
reading read <id>                     # Mark as read (first 8 chars of ID)
reading show <id>                     # Show details

# Health check
curl http://127.0.0.1:5123/health

# Stop server
pkill -f start_server.py

# Auto-start service (macOS)
launchctl load ~/Library/LaunchAgents/com.reading-backlog.server.plist    # Start
launchctl unload ~/Library/LaunchAgents/com.reading-backlog.server.plist  # Stop
tail -f ~/Library/Logs/reading-backlog.log                                 # Logs
```

## Architecture

### Data Flow
1. **Chrome Extension** (`extension/`) → sends URL to API
2. **FastAPI Server** (`src/server/`) → receives request, calls scraper
3. **Scraper** (`src/services/scraper.py`) → fetches URL, detects HTML/PDF, extracts content
4. **LLM Service** (`src/services/llm.py`) → if Ollama is running, enhances extraction with llama3.2
5. **Storage** (`src/services/storage.py`) → persists to `data/articles.json`

### Key Design Patterns
- **Sync/Async duality**: `scrape_article()` is async for API, `scrape_article_sync()` wraps it for CLI
- **LLM fallback**: All LLM features gracefully fall back to basic extraction if Ollama isn't running
- **Partial ID matching**: CLI commands accept first 8 characters of article UUID

### Module Responsibilities
- `src/models/article.py`: Pydantic models (Article, ArticleCreate, ArticleUpdate, Priority, Status enums)
- `src/services/scraper.py`: URL fetching, HTML/PDF detection and parsing, trafilatura for HTML, pymupdf for PDF
- `src/services/llm.py`: Ollama integration for title/summary/tag extraction
- `src/services/storage.py`: JSON file persistence with filtering and export
- `src/server/routes.py`: REST API endpoints under `/api`
- `src/cli/commands.py`: Typer CLI with Rich formatting

### Configuration
Server config in `src/config.py`: host `127.0.0.1`, port `5123`, data stored in `data/articles.json`.

## Optional LLM Setup

For enhanced metadata extraction:
```bash
brew install ollama
ollama serve            # Run in separate terminal
ollama pull llama3.2    # One-time download
```
