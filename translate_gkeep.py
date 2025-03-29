import os
import json
import re
import base64
import asyncio
import openai
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from datetime import datetime
from aiohttp import ClientSession  # Async HTTP requests
from dotenv import load_dotenv

# Debugging Controls
DEBUG_MODE = True  # While True, will only process a limited number of files
DEBUG_FILE_COUNT = 15  # Number of files to process in debug mode

# Toggle for enabling/disabling ChatGPT API
USE_CHATGPT = False  # Set to False for OCR-only processing

# Cache Directories
CACHE_OCR_DIR = "cache/ocr"
CACHE_GPT_DIR = "cache/chatgpt"
os.makedirs(CACHE_OCR_DIR, exist_ok=True)
os.makedirs(CACHE_GPT_DIR, exist_ok=True)

# Output Directories
OUTPUT_MD_DIR = "output_markdown"
OUTPUT_HTML_DIR = "output_html"
os.makedirs(OUTPUT_MD_DIR, exist_ok=True)
os.makedirs(OUTPUT_HTML_DIR, exist_ok=True)

# Load API Key
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def timestamp_to_date(timestamp_usec):
    """Convert microsecond timestamp to a readable date."""
    return datetime.fromtimestamp(timestamp_usec / 1e6).strftime("%Y-%m-%d %H:%M:%S")


def get_cache_path(base_dir, filename, ext):
    """Return the full path for a cached file (OCR or GPT)."""
    sanitized_name = sanitize_filename(filename)
    return os.path.join(base_dir, f"{sanitized_name}.{ext}")


def load_cached_text(cache_path):
    """Load text from a cached file if it exists."""
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None


def save_cached_text(cache_path, text):
    """Save text to a cache file."""
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(text)


async def ocr_image(image_path):
    """Perform OCR on an image file asynchronously with caching."""
    filename = os.path.basename(image_path)
    cache_path = get_cache_path(CACHE_OCR_DIR, filename, "txt")

    # Check cache first
    cached_text = load_cached_text(cache_path)
    if cached_text:
        print(f"✅ Using cached OCR for {filename}")
        return cached_text

    print(f"🚀 Running OCR for {filename}")
    try:
        img = Image.open(image_path)

        # Image Preprocessing
        img = img.convert("L")  # Convert to grayscale
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)  # Increase contrast
        img = img.filter(ImageFilter.SHARPEN)  # Sharpen the image

        # Run OCR in a separate thread
        text = await asyncio.to_thread(pytesseract.image_to_string, img, lang="eng")

        # Save OCR result to cache
        save_cached_text(cache_path, text)
        return text.strip()
    except Exception as e:
        print(f"❌ OCR Error: {e}")
        return ""


async def format_text_with_chatgpt(text, filename, session):
    """Send text to ChatGPT and return formatted Markdown, using cache."""
    cache_path = get_cache_path(CACHE_GPT_DIR, filename, "md")

    # Check cache first
    cached_text = load_cached_text(cache_path)
    if cached_text:
        print(f"✅ Using cached ChatGPT output for {filename}")
        return cached_text

    print(f"🚀 Sending text to ChatGPT: {filename}")
    try:
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
        payload = {
            "model": "gpt-4-turbo",
            "messages": [
                {"role": "system", "content": "You are an OCR correction assistant. Your job is to fix misrecognized characters, preserve original text structure, and correct minor errors (spacing, punctuation, capitalization). DO NOT alter wording, meaning, or sentence structure. Make the output as faithful to the original text as possible while cleaning up OCR artifacts. Retain all line breaks, bullet points, and structure as closely as possible."},
                {"role": "user", "content": f"Format this text into Markdown:\n\n'''{text}'''"}
            ]
        }

        async with session.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers) as response:
            result = await response.json()

            if "choices" not in result or not result["choices"]:
                print(f"⚠️ Warning: No choices returned from API.")
                return "⚠️ Error: No response from ChatGPT"

            formatted_text = result["choices"][0]["message"]["content"]

            # Save to cache
            save_cached_text(cache_path, formatted_text)
            return formatted_text

    except Exception as e:
        print(f"❌ Error during API call: {e}")
        return "❌ API request failed"


def sanitize_filename(filename, replacement="_"):
    """Sanitize a filename to make it safe for use in the file system."""
    sanitized = re.sub(r'[<>:"/\\|?*]', replacement, filename)
    return sanitized.strip().strip(replacement)[:255]


async def process_json(json_file, attachments_folder, session):
    """Process a single JSON file and generate Markdown and HTML files asynchronously."""
    with open(json_file, "r", encoding="utf-8") as file:
        note = json.load(file)

    filename = os.path.basename(json_file)
    title = sanitize_filename(note.get("title", "Untitled"))

    labels = [label.get("name", "") for label in note.get("labels", [])]
    label_folder = "_".join(labels) if labels else "Unlabeled"

    # Separate root folders for Markdown and HTML output
    markdown_folder = os.path.join(OUTPUT_MD_DIR, label_folder)
    html_folder = os.path.join(OUTPUT_HTML_DIR, label_folder)
    os.makedirs(markdown_folder, exist_ok=True)
    os.makedirs(html_folder, exist_ok=True)

    # OCR Processing
    ocr_tasks = []
    image_paths = []

    for attachment in note.get("attachments", []):
        file_path = os.path.join(attachments_folder, attachment.get("filePath"))
        if os.path.exists(file_path):
            image_paths.append(file_path)
            ocr_tasks.append(ocr_image(file_path))

    # Run OCR in parallel
    ocr_results = await asyncio.gather(*ocr_tasks)

    # ChatGPT Processing
    formatted_texts = []
    if USE_CHATGPT:
        chatgpt_tasks = [format_text_with_chatgpt(text, filename, session) for text in ocr_results]
        formatted_texts = await asyncio.gather(*chatgpt_tasks)
    else:
        formatted_texts = ocr_results  # Use raw OCR text if ChatGPT is disabled

    # Save outputs
    markdown_file = os.path.join(markdown_folder, f"{title}.md")
    html_file = os.path.join(html_folder, f"{title}.html")

    # Save Markdown
    with open(markdown_file, "w", encoding="utf-8") as md_file:
        md_file.write("\n".join(formatted_texts))
    print(f"✅ Markdown generated: {markdown_file}")

    # Save HTML
    with open(html_file, "w", encoding="utf-8") as html_obj:
        html_obj.write("\n".join(formatted_texts))
    print(f"✅ HTML generated: {html_file}")


async def main():
    input_folder = "Keep"
    attachments_folder = "Keep"

    async with ClientSession() as session:
        tasks = [
            process_json(os.path.join(input_folder, file), attachments_folder, session)
            for file in os.listdir(input_folder)
            if file.endswith(".json")
        ]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
    print("✨ All files processed!")