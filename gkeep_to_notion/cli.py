"""
Command-line interface for Google Keep to Notion converter.

This module provides the main entry point for the application.
"""

import os
import sys
import asyncio
import argparse
import aiohttp
from aiohttp import ClientSession

from .config import Config
from .processors import process_note


async def run(args):
    """
    Run the Google Keep to Notion converter.
    
    Args:
        args: Command-line arguments
    """
    # Update configuration based on command-line arguments
    Config.DEBUG_MODE = args.debug
    Config.DEBUG_FILE_COUNT = args.count
    Config.USE_CHATGPT = not args.ocr_only
    Config.INPUT_FOLDER = args.input_folder
    Config.ATTACHMENTS_FOLDER = args.attachments_folder
    
    # Set up necessary directories
    Config.setup_directories()
    
    # Validate OpenAI API key if ChatGPT is enabled
    if Config.USE_CHATGPT and not Config.OPENAI_API_KEY:
        print("❌ Error: OPENAI_API_KEY environment variable is not set, but ChatGPT is enabled.")
        print("Please set the environment variable or use --ocr-only flag.")
        sys.exit(1)
    
    print(f"🔍 Processing Google Keep notes from {Config.INPUT_FOLDER}")
    print(f"{'🐞 DEBUG MODE' if Config.DEBUG_MODE else '🚀 FULL PROCESSING'}")
    print(f"{'🤖 ChatGPT enabled' if Config.USE_CHATGPT else '🔤 OCR only'}")
    
    # Process notes
    # Configure the aiohttp session with a longer timeout
    connector = aiohttp.TCPConnector(limit=5)  # Limit concurrent connections to avoid overloading API
    timeout = aiohttp.ClientTimeout(total=60)  # 60 second timeout
    async with ClientSession(connector=connector, timeout=timeout) as session:
        if Config.DEBUG_MODE:
            print(f"Processing up to {Config.DEBUG_FILE_COUNT} files in debug mode...")
            count = 0
            # Get a list of all JSON files first
            json_files = [f for f in os.listdir(Config.INPUT_FOLDER) if f.endswith(".json")]
            # Process only up to DEBUG_FILE_COUNT files
            for file in json_files[:Config.DEBUG_FILE_COUNT]:
                await process_note(
                    os.path.join(Config.INPUT_FOLDER, file), 
                    Config.ATTACHMENTS_FOLDER, 
                    session
                )
                count += 1
                print(f"Processed {count}/{Config.DEBUG_FILE_COUNT} files")
        else:
            print("Processing all files...")
            print(f"Found {len([f for f in os.listdir(Config.INPUT_FOLDER) if f.endswith('.json')])} JSON files to process")
            
            # Process files in manageable batches to avoid overwhelming the API
            batch_size = 10
            json_files = [f for f in os.listdir(Config.INPUT_FOLDER) if f.endswith(".json")]
            
            for i in range(0, len(json_files), batch_size):
                batch = json_files[i:i+batch_size]
                print(f"Processing batch {i//batch_size + 1}/{(len(json_files) + batch_size - 1)//batch_size}")
                
                tasks = [
                    process_note(
                        os.path.join(Config.INPUT_FOLDER, file), 
                        Config.ATTACHMENTS_FOLDER, 
                        session
                    )
                    for file in batch
                ]
                await asyncio.gather(*tasks)
    
    print("✅ Processing complete!")


def parse_args():
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Convert Google Keep notes to Markdown and HTML with OCR and optional ChatGPT formatting."
    )
    
    parser.add_argument(
        "--debug", 
        action="store_true",
        default=Config.DEBUG_MODE,
        help="Enable debug mode (process limited number of files)"
    )
    parser.add_argument(
        "--count", 
        type=int, 
        default=Config.DEBUG_FILE_COUNT, 
        help="Number of files to process in debug mode"
    )
    parser.add_argument(
        "--ocr-only", 
        action="store_true",
        default=not Config.USE_CHATGPT,
        help="Disable ChatGPT formatting (OCR only)"
    )
    parser.add_argument(
        "--input-folder", 
        type=str, 
        default=Config.INPUT_FOLDER, 
        help="Folder containing Google Keep JSON files"
    )
    parser.add_argument(
        "--attachments-folder", 
        type=str, 
        default=Config.ATTACHMENTS_FOLDER, 
        help="Folder containing Google Keep attachments"
    )
    
    return parser.parse_args()


def main():
    """Main entry point for the application."""
    try:
        args = parse_args()
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
