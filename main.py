#!/usr/bin/env python3
"""
Main entry point for the Google Keep to Notion converter.

This script simply imports and runs the CLI module.
"""

import sys
from gkeep_to_notion.cli import main

if __name__ == "__main__":
    sys.exit(main())
