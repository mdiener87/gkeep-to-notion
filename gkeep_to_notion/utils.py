"""
Utility functions for Google Keep to Notion converter.

This module provides common utility functions used throughout the application.
"""

import re
from datetime import datetime
from typing import Optional


def timestamp_to_date(timestamp_usec: int) -> str:
    """
    Convert microsecond timestamp to a readable date.
    
    Args:
        timestamp_usec: Timestamp in microseconds
        
    Returns:
        Formatted date string
    """
    return datetime.fromtimestamp(timestamp_usec / 1e6).strftime("%Y-%m-%d %H:%M:%S")


def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """
    Sanitize a filename to make it safe for use in the file system.
    
    Args:
        filename: The original filename to sanitize
        replacement: Character to use as replacement for invalid characters
        
    Returns:
        Sanitized filename
    """
    sanitized = re.sub(r'[<>:"/\\|?*]', replacement, filename)
    return sanitized.strip().strip(replacement)[:255]
