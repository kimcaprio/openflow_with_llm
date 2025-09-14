#!/usr/bin/env python3
"""
NiFi MCP Server Runner

Quick script to run the NiFi MCP Server with default settings.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.main import cli

if __name__ == "__main__":
    # Default to running the server
    if len(sys.argv) == 1:
        sys.argv.append("server")
    
    cli()
