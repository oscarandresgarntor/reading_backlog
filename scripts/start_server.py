#!/usr/bin/env python3
"""Start the Reading Backlog server."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.server.app import run_server

if __name__ == "__main__":
    print("Starting Reading Backlog server...")
    print("Dashboard: http://127.0.0.1:5123/dashboard")
    print("API: http://127.0.0.1:5123/api")
    print("Press Ctrl+C to stop")
    print("-" * 40)
    run_server()
