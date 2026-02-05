# Reading Backlog

A system to save articles for later reading with automatic metadata extraction.

## Components

- **Chrome Extension**: Save articles with one click from your browser
- **Python Backend**: FastAPI server with web scraping for metadata extraction
- **CLI Tool**: Manage your backlog from the terminal
- **Web Dashboard**: Visual management interface

## Quick Start

### 1. Install Dependencies

```bash
cd /Users/oscarandresgarnicatoro/Documents/GitHub/reading_backlog

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install package in development mode
pip install -e .
```

### 2. Start the Server

```bash
python scripts/start_server.py
```

The server runs at `http://127.0.0.1:5123`:
- Dashboard: `http://127.0.0.1:5123/dashboard`
- API: `http://127.0.0.1:5123/api`

To check if the server is running:
```bash
curl -s http://127.0.0.1:5123/health && echo "" || echo "Server is OFF"
```

To stop the server:
```bash
# If running in foreground, press Ctrl+C

# If running in background
pkill -f start_server.py
```

#### Auto-Start on Login (macOS)

To start the server automatically when you log in:

```bash
# Load the launch agent (one-time setup)
launchctl load ~/Library/LaunchAgents/com.reading-backlog.server.plist

# Stop the service
launchctl unload ~/Library/LaunchAgents/com.reading-backlog.server.plist

# View logs
tail -f ~/Library/Logs/reading-backlog.log
tail -f ~/Library/Logs/reading-backlog.error.log
```

### 3. Install Chrome Extension

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `extension/` folder from this project

### 4. Setup LLM for Smart Extraction (Optional)

For better title/summary extraction and auto-suggested tags, install Ollama:

```bash
# Install Ollama
brew install ollama

# Start the Ollama service (run in a separate terminal)
ollama serve

# Pull the model (one-time download, ~2GB)
ollama pull llama3.2
```

To manage the Ollama service:
```bash
# Stop Ollama
brew services stop ollama

# Start Ollama
brew services start ollama

# Check status
brew services list | grep ollama
```

When Ollama is running, the system will:
- Extract accurate titles from documents
- Generate intelligent summaries
- Suggest relevant tags automatically

If Ollama is not running, the system falls back to basic extraction.

### 5. Use the CLI

```bash
# List all articles
reading list

# Add an article
reading add https://example.com/article

# Add with tags and priority
reading add https://example.com/article --tags "tech,ai" --priority high

# Add a local PDF file
reading add-local ~/Downloads/paper.pdf --tags "research" --priority high

# Mark as read (use first 8 chars of ID)
reading read abc12345

# Show article details
reading show abc12345

# Export to Markdown
reading export
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `reading list` | List all articles (with filters: `--status`, `--priority`, `--tag`) |
| `reading add <url>` | Add article from URL (web page or PDF) |
| `reading add-local <path>` | Add a local PDF file |
| `reading read <id>` | Mark article as read |
| `reading unread <id>` | Mark article as unread |
| `reading show <id>` | Show full article details |
| `reading delete <id>` | Delete an article |
| `reading tag <id> <tags>` | Update article tags |
| `reading priority <id> <level>` | Update article priority |
| `reading export` | Export backlog to Markdown |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/articles` | Add article (scrapes metadata) |
| `GET` | `/api/articles` | List articles (with filters) |
| `GET` | `/api/articles/{id}` | Get single article |
| `PATCH` | `/api/articles/{id}` | Update article |
| `DELETE` | `/api/articles/{id}` | Delete article |
| `POST` | `/api/articles/{id}/read` | Mark as read |
| `POST` | `/api/articles/{id}/unread` | Mark as unread |

## Data Storage

Articles are stored in `data/articles.json`. Each article includes:

- URL, title, summary
- Source domain
- Publication date (if available)
- Tags and priority
- Read/unread status
- Date added

## Project Structure

```
reading_backlog/
├── extension/          # Chrome Extension (Manifest V3)
├── src/
│   ├── models/         # Pydantic data models
│   ├── services/       # Storage and scraper services
│   ├── server/         # FastAPI application
│   ├── cli/            # Typer CLI commands
│   └── dashboard/      # Web dashboard templates
├── data/               # JSON storage
├── scripts/            # Utility scripts
├── requirements.txt
└── setup.py
```

## Testing the Setup

```bash
# Test the API
curl http://127.0.0.1:5123/health

# Add an article via API
curl -X POST http://127.0.0.1:5123/api/articles \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "tags": ["test"], "priority": "medium"}'

# List articles
curl http://127.0.0.1:5123/api/articles
```
