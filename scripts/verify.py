#!/usr/bin/env python3
"""Verify the Reading Backlog installation."""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def check(name: str, condition: bool) -> bool:
    """Print check result."""
    status = "OK" if condition else "FAIL"
    print(f"  [{status}] {name}")
    return condition


def main():
    print("\n=== Reading Backlog Verification ===\n")

    all_ok = True

    # Check project structure
    print("Project Structure:")
    all_ok &= check("src/models/article.py", (PROJECT_ROOT / "src/models/article.py").exists())
    all_ok &= check("src/services/storage.py", (PROJECT_ROOT / "src/services/storage.py").exists())
    all_ok &= check("src/services/scraper.py", (PROJECT_ROOT / "src/services/scraper.py").exists())
    all_ok &= check("src/server/app.py", (PROJECT_ROOT / "src/server/app.py").exists())
    all_ok &= check("src/cli/commands.py", (PROJECT_ROOT / "src/cli/commands.py").exists())
    all_ok &= check("extension/manifest.json", (PROJECT_ROOT / "extension/manifest.json").exists())
    all_ok &= check("data/articles.json", (PROJECT_ROOT / "data/articles.json").exists())
    print()

    # Check imports
    print("Python Imports:")
    try:
        from src.models import Article, ArticleCreate, Priority, Status
        all_ok &= check("Models", True)
    except Exception as e:
        all_ok &= check(f"Models: {e}", False)

    try:
        from src.services import storage, scrape_article_sync
        all_ok &= check("Services", True)
    except Exception as e:
        all_ok &= check(f"Services: {e}", False)

    try:
        from src.server.app import app
        all_ok &= check("Server", True)
    except Exception as e:
        all_ok &= check(f"Server: {e}", False)

    try:
        from src.cli.commands import app as cli_app
        all_ok &= check("CLI", True)
    except Exception as e:
        all_ok &= check(f"CLI: {e}", False)
    print()

    # Check CLI command
    print("CLI Commands:")
    try:
        result = subprocess.run(
            ["reading", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        all_ok &= check("reading --help", result.returncode == 0)
    except Exception as e:
        all_ok &= check(f"reading --help: {e}", False)
    print()

    # Summary
    if all_ok:
        print("All checks passed!\n")
        print("Quick Start:")
        print("  1. Start server: python scripts/start_server.py")
        print("  2. Open dashboard: http://127.0.0.1:5123/dashboard")
        print("  3. Use CLI: reading add https://example.com")
        print("  4. Install extension: Load 'extension/' folder in Chrome")
        print()
        return 0
    else:
        print("\nSome checks failed. Please review the errors above.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
