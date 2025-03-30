"""
Processing module for Google Keep to Notion converter.

This module handles processing of attachments and notes.
"""

import os
import json
import asyncio
from typing import Dict, List, Tuple, Any
from aiohttp import ClientSession

from .config import Config
from .ocr import ocr_image
from .api import format_text_with_chatgpt
from .utils import sanitize_filename
from .output import create_markdown, create_html


async def process_attachment(file_path: str, session: ClientSession) -> Tuple[str, str]:
    """
    Process a single attachment with OCR and optional ChatGPT formatting.
    
    Args:
        file_path: Path to the attachment file
        session: An aiohttp ClientSession for making API requests
        
    Returns:
        Tuple of (ocr_text, formatted_text)
    """
    # Get OCR text from image
    ocr_text = await ocr_image(file_path)
    
    # If ChatGPT formatting is enabled
    if Config.USE_CHATGPT:
        # Check cache for formatted text
        file_basename = sanitize_filename(os.path.basename(file_path))
        chatgpt_cache_file = os.path.join(
            Config.CHATGPT_CACHE_FOLDER, 
            file_basename + ".txt"
        )
        
        # If cache exists and is not empty, use it
        if os.path.exists(chatgpt_cache_file):
            with open(chatgpt_cache_file, "r", encoding="utf-8") as f:
                formatted_text = f.read().strip()
            if formatted_text and not formatted_text.startswith("❌"):
                print(f"✓ Using cached ChatGPT result for {file_basename}")
                return ocr_text, formatted_text
        
        # If we have no ocr_text, don't bother calling the API
        if not ocr_text.strip():
            print(f"⚠️ No OCR text to process for {file_basename}, skipping ChatGPT")
            return ocr_text, ocr_text
            
        # Otherwise, get formatted text from ChatGPT and cache it
        print(f"🤖 Requesting ChatGPT processing for {file_basename}")
        formatted_text = await format_text_with_chatgpt(ocr_text, session)
        
        # Check if the API call was successful
        if formatted_text.startswith("❌"):
            print(f"❌ ChatGPT processing failed for {file_basename}: {formatted_text}")
        
        # Cache the result (even if it failed, to avoid repeated failed calls)
        with open(chatgpt_cache_file, "w", encoding="utf-8") as f:
            f.write(formatted_text)
        
        return ocr_text, formatted_text
    else:
        # If ChatGPT is disabled, use OCR text as formatted text
        return ocr_text, ocr_text


async def process_note(json_file: str, attachments_folder: str, session: ClientSession) -> None:
    """
    Process a single note JSON file and its attachments.
    
    Args:
        json_file: Path to the note JSON file
        attachments_folder: Path to the folder containing attachments
        session: An aiohttp ClientSession for making API requests
    """
    # Load note data from JSON file
    with open(json_file, "r", encoding="utf-8") as file:
        note = json.load(file)

    # Create output folders based on labels
    labels = [label.get("name", "") for label in note.get("labels", [])]
    label_folder = "_".join(labels) if labels else "Unlabeled"

    markdown_folder = os.path.join(Config.OUTPUT_MARKDOWN_FOLDER, label_folder)
    html_folder = os.path.join(Config.OUTPUT_HTML_FOLDER, label_folder)
    os.makedirs(markdown_folder, exist_ok=True)
    os.makedirs(html_folder, exist_ok=True)

    # Get paths to all existing attachments
    attachment_paths = []
    for attachment in note.get("attachments", []):
        file_path = os.path.join(attachments_folder, attachment.get("filePath"))
        if os.path.exists(file_path):
            attachment_paths.append(file_path)

    # Process all attachments
    tasks = [process_attachment(file_path, session) for file_path in attachment_paths]
    results = await asyncio.gather(*tasks)
    ocr_results = [r[0] for r in results]
    formatted_texts = [r[1] for r in results]

    # Generate and save Markdown content
    markdown_content = await create_markdown(note, attachments_folder, ocr_results, formatted_texts)
    title = sanitize_filename(note.get("title", "Untitled"))
    markdown_file = os.path.join(markdown_folder, f"{title}.md")
    with open(markdown_file, "w", encoding="utf-8") as md_file:
        md_file.write(markdown_content)
    print(f"✅ Markdown generated: {markdown_file}")

    # Generate and save HTML content
    html_content = await create_html(note, attachments_folder, ocr_results, formatted_texts, attachment_paths)
    html_file = os.path.join(html_folder, f"{title}.html")
    with open(html_file, "w", encoding="utf-8") as html_file_obj:
        html_file_obj.write(html_content)
    print(f"✅ HTML generated: {html_file}")
