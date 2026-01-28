"""Application configuration."""

from pathlib import Path

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ARTICLES_FILE = DATA_DIR / "articles.json"

# Server settings
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5123

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)
