"""
Configuration module for Google Keep to Notion converter.

This module handles all configuration settings including:
- Environment variables
- Default paths
- Debug mode settings
- API settings
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for Google Keep to Notion converter."""
    
    # Debug settings
    DEBUG_MODE = True  # When True, process only a few files for debugging
    DEBUG_FILE_COUNT = 15  # Number of files to process in debug mode
    
    # Paths
    INPUT_FOLDER = "Keep"  # Folder containing JSON files
    ATTACHMENTS_FOLDER = "Keep"  # Folder containing attachments
    OUTPUT_MARKDOWN_FOLDER = "output_markdown"
    OUTPUT_HTML_FOLDER = "output_html"
    
    # API settings
    USE_CHATGPT = True  # Set to True to enable ChatGPT processing, False for OCR only
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Cache settings
    OCR_CACHE_FOLDER = "ocr_cache"
    CHATGPT_CACHE_FOLDER = "chatgpt_cache"
    
    # OCR settings
    OCR_SEMAPHORE_LIMIT = 4  # Adjust based on your system
    OCR_SEMAPHORE = None  # Will be initialized in setup_directories
    
    @classmethod
    def setup_directories(cls):
        """Create necessary directories for output and caching."""
        os.makedirs(cls.OUTPUT_MARKDOWN_FOLDER, exist_ok=True)
        os.makedirs(cls.OUTPUT_HTML_FOLDER, exist_ok=True)
        os.makedirs(cls.OCR_CACHE_FOLDER, exist_ok=True)
        os.makedirs(cls.CHATGPT_CACHE_FOLDER, exist_ok=True)
        
        # Initialize semaphore for OCR concurrency limiting
        cls.OCR_SEMAPHORE = asyncio.Semaphore(cls.OCR_SEMAPHORE_LIMIT)
