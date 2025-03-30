"""
OCR module for Google Keep to Notion converter.

This module handles OCR processing of images using Tesseract OCR.
"""

import os
import asyncio
from typing import Optional
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract

from .config import Config
from .utils import sanitize_filename


async def ocr_image(image_path: str) -> str:
    """
    Perform OCR on an image file asynchronously.
    
    Checks for a cached OCR result first; if not available, performs OCR
    (using a semaphore to limit concurrency) and then caches the result.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        OCR extracted text
    """
    cache_file = os.path.join(
        Config.OCR_CACHE_FOLDER, 
        sanitize_filename(os.path.basename(image_path)) + ".txt"
    )
    
    # Check cache first
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            cached_text = f.read().strip()
        if cached_text:
            return cached_text

    # If not in cache, perform OCR (with concurrency limiting)
    async with Config.OCR_SEMAPHORE:
        try:
            img = Image.open(image_path)
            
            # Preprocess the image for better OCR results
            img = img.convert("L")  # Convert to grayscale
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)  # Increase contrast
            img = img.filter(ImageFilter.SHARPEN)  # Apply sharpening

            # Run OCR in a separate thread to avoid blocking the event loop
            text = await asyncio.to_thread(pytesseract.image_to_string, img, lang="eng")
            text = text.strip()
            
            if not text:
                print(f"Warning: No OCR text extracted from {image_path}")

            # Cache the OCR result
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(text)

            return text
            
        except Exception as e:
            print(f"Error during OCR for {image_path}: {e}")
            return ""
