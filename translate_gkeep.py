import os
import json
import re
import base64
import asyncio
import openai
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from datetime import datetime
from pathlib import Path
from aiohttp import ClientSession  # Async HTTP requests
from dotenv import load_dotenv

# Load environment variables (if needed)
load_dotenv()

DEBUG_MODE = False          # When True, process only a few files for debugging
DEBUG_FILE_COUNT = 15       # Number of files to process in debug mode

# Define output folders
OUTPUT_FOLDER = "output_markdown"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs("output_html", exist_ok=True)

# Toggle for enabling/disabling ChatGPT API
USE_CHATGPT = False  # Set to True to enable ChatGPT processing, False for OCR only

# OpenAI API Key (make sure this is set in your environment)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Define OCR cache folder and create if it doesn't exist
OCR_CACHE_FOLDER = "ocr_cache"
os.makedirs(OCR_CACHE_FOLDER, exist_ok=True)

# Define semaphore for limiting OCR concurrency (adjust the limit as needed)
OCR_SEMAPHORE_LIMIT = 4
ocr_semaphore = asyncio.Semaphore(OCR_SEMAPHORE_LIMIT)

def timestamp_to_date(timestamp_usec):
    """Convert microsecond timestamp to a readable date."""
    return datetime.fromtimestamp(timestamp_usec / 1e6).strftime("%Y-%m-%d %H:%M:%S")

def sanitize_filename(filename, replacement="_"):
    """Sanitize a filename to make it safe for use in the file system."""
    sanitized = re.sub(r'[<>:"/\\|?*]', replacement, filename)
    return sanitized.strip().strip(replacement)[:255]

async def ocr_image(image_path):
    """
    Perform OCR on an image file asynchronously.
    Checks for a cached OCR result first; if not available, performs OCR
    (using a semaphore to limit concurrency) and then caches the result.
    """
    # Create a cache filename based on the image's base name
    cache_file = os.path.join(OCR_CACHE_FOLDER, sanitize_filename(os.path.basename(image_path)) + ".txt")
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            cached_text = f.read().strip()
        if cached_text:
            return cached_text

    # If not cached, limit the OCR process with the semaphore
    async with ocr_semaphore:
        try:
            img = Image.open(image_path)
            
            # Preprocess the image
            img = img.convert("L")  # Convert to grayscale
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)  # Increase contrast
            img = img.filter(ImageFilter.SHARPEN)  # Apply sharpening

            # Run OCR in a separate thread to avoid blocking the event loop
            text = await asyncio.to_thread(pytesseract.image_to_string, img, lang="eng")
            text = text.strip()
            
            if not text:
                print(f"Warning: No OCR text extracted from {image_path}")

            # Cache the result for future runs
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(text)

            return text
        except Exception as e:
            print(f"Error during OCR for {image_path}: {e}")
            return ""

async def format_text_with_chatgpt(raw_text, session):
    """
    Send OCR text to OpenAI GPT API for faithful Markdown conversion.
    The API is used only if USE_CHATGPT is enabled.
    """
    try:
        headers = {"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"}
        payload = {
            "model": "gpt-4-turbo",
            "messages": [
                {"role": "system", "content": (
                    "You are an OCR correction assistant. Your job is to fix misrecognized characters, preserve original text structure, "
                    "and correct minor errors (spacing, punctuation, capitalization). DO NOT alter wording, meaning, or sentence structure. "
                    "Make the output as faithful to the original text as possible while cleaning up OCR artifacts. "
                    "Retain all line breaks, bullet points, and structure as closely as possible."
                )},
                {"role": "user", "content": f"Convert the following OCR text to Markdown, preserving all formatting:\n\n'''{raw_text}'''"}
            ]
        }

        async with session.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers) as response:
            result = await response.json()

            if "choices" not in result or not result["choices"]:
                print("⚠️ Warning: No choices returned from API response.")
                return "⚠️ Error: No response from ChatGPT"

            return result["choices"][0]["message"]["content"]
    
    except Exception as e:
        print(f"❌ Error during API call: {e}")
        return "❌ API request failed"

async def create_markdown(note, attachments_folder, ocr_results, formatted_texts):
    """Generate a Markdown string from note data using precomputed OCR & ChatGPT results."""
    title = note.get("title", "Untitled")
    created_date = timestamp_to_date(note.get("createdTimestampUsec", 0))
    edited_date = timestamp_to_date(note.get("userEditedTimestampUsec", 0))
    text_content = note.get("textContent", "").strip()
    labels = ", ".join(label.get("name", "") for label in note.get("labels", []))

    # Handle attachments (OCR processing)
    attachment_text = ""
    
    for ocr_text, formatted_text in zip(ocr_results, formatted_texts):
        attachment_text += f"\n\n## OCR Extracted Text\n"
        attachment_text += f"### Raw OCR Output:\n```\n{ocr_text}\n```\n"
        if USE_CHATGPT:
            attachment_text += f"### ChatGPT Formatted Output:\n{formatted_text}\n"

    # Combine content into Markdown
    markdown_content = f"""
    # {title}

    **Created:** {created_date}  
    **Last Edited:** {edited_date}  
    **Labels:** {labels}  

    ---

    {text_content}

    ---
    {attachment_text}
    """.strip()

    return markdown_content

async def create_html(note, attachments_folder, ocr_results, formatted_texts):
    """Generate an HTML string from note data using precomputed OCR & ChatGPT results."""
    title = note.get("title", "Untitled")
    created_date = timestamp_to_date(note.get("createdTimestampUsec", 0))
    edited_date = timestamp_to_date(note.get("userEditedTimestampUsec", 0))
    text_content = note.get("textContent", "").strip()
    labels = ", ".join(label.get("name", "") for label in note.get("labels", []))

    # Handle attachments (Base64-encoded images)
    attachment_images = ""
    attachment_text = ""
    image_count = 0

    for attachment in note.get("attachments", []):
        file_path = os.path.join(attachments_folder, attachment.get("filePath"))
        if os.path.exists(file_path):
            image_count += 1
            with open(file_path, "rb") as img_file:
                base64_data = base64.b64encode(img_file.read()).decode("utf-8")
                mime_type = "image/png" if file_path.endswith(".png") else "image/jpeg"
                attachment_images += f"""
                <p><strong>Image {image_count}:</strong> {os.path.basename(file_path)}</p>
                <img src="data:{mime_type};base64,{base64_data}" alt="Embedded Image {image_count}" style="max-width:100%;"><br>
                """

    # Append collapsible sections for OCR & ChatGPT data
    for idx, (ocr_text, formatted_text) in enumerate(zip(ocr_results, formatted_texts), 1):
        attachment_text += f"""
        <details>
            <summary><strong>OCR Extracted Text {idx}</strong></summary>
            <pre>{ocr_text}</pre>
        </details>
        """
        if USE_CHATGPT:
            attachment_text += f"""
            <details>
                <summary><strong>ChatGPT Formatted Text {idx}</strong></summary>
                <pre>{formatted_text}</pre>
            </details>
            """

    # Combine everything into an HTML structure
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: auto; padding: 20px; }}
            h1 {{ color: #333; }}
            pre {{ background: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; }}
            details {{ margin-bottom: 10px; }}
            summary {{ cursor: pointer; font-size: 1.1em; font-weight: bold; color: #007bff; }}
            summary:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <h1>{title}</h1>
        <p><strong>Created:</strong> {created_date}</p>
        <p><strong>Last Edited:</strong> {edited_date}</p>
        <p><strong>Labels:</strong> {labels}</p>
        <hr>

        <h2>Note Content</h2>
        <p>{text_content}</p>

        <hr>
        <h2>Original Image Data</h2>
        <details>
            <summary><strong>View Embedded Images</strong></summary>
            {attachment_images if image_count > 0 else "<p>No images found.</p>"}
        </details>

        <hr>
        <h2>Extracted OCR & ChatGPT Data</h2>
        {attachment_text}

    </body>
    </html>
    """.strip()

    return html_content

async def process_json(json_file, attachments_folder, session):
    """
    Process a single JSON file:
      - Load note data,
      - Run OCR on all attachments (with caching and semaphore limits),
      - Optionally format the OCR text using ChatGPT,
      - Generate and save Markdown and HTML outputs.
    """
    with open(json_file, "r", encoding="utf-8") as file:
        note = json.load(file)

    labels = [label.get("name", "") for label in note.get("labels", [])]
    label_folder = "_".join(labels) if labels else "Unlabeled"

    # Separate root folders for Markdown and HTML output
    markdown_folder = os.path.join("output_markdown", label_folder)
    html_folder = os.path.join("output_html", label_folder)
    os.makedirs(markdown_folder, exist_ok=True)
    os.makedirs(html_folder, exist_ok=True)

    # Process attachments (OCR)
    ocr_tasks = []
    for attachment in note.get("attachments", []):
        file_path = os.path.join(attachments_folder, attachment.get("filePath"))
        if os.path.exists(file_path):
            ocr_tasks.append(ocr_image(file_path))

    # Run OCR tasks concurrently (with caching and semaphore limiting in ocr_image)
    ocr_results = await asyncio.gather(*ocr_tasks)

    # Format OCR text with ChatGPT if enabled, otherwise reuse raw OCR results
    if USE_CHATGPT:
        chatgpt_tasks = [format_text_with_chatgpt(text, session) for text in ocr_results]
        formatted_texts = await asyncio.gather(*chatgpt_tasks)
    else:
        formatted_texts = ocr_results

    # Generate Markdown and HTML content
    markdown_content = await create_markdown(note, attachments_folder, ocr_results, formatted_texts)
    html_content = await create_html(note, attachments_folder, ocr_results, formatted_texts)

    # Sanitize title for filenames
    title = sanitize_filename(note.get("title", "Untitled"))

    # Save Markdown output
    markdown_file = os.path.join(markdown_folder, f"{title}.md")
    with open(markdown_file, "w", encoding="utf-8") as md_file:
        md_file.write(markdown_content)
    print(f"✅ Markdown generated: {markdown_file}")

    # Save HTML output
    html_file = os.path.join(html_folder, f"{title}.html")
    with open(html_file, "w", encoding="utf-8") as html_file_obj:
        html_file_obj.write(html_content)
    print(f"✅ HTML generated: {html_file}")

async def main():
    input_folder = "Keep"         # Folder containing JSON files
    attachments_folder = "Keep"   # Folder containing attachments

    async with ClientSession() as session:
        if DEBUG_MODE:
            count = 0
            for file in os.listdir(input_folder):
                if file.endswith(".json"):
                    await process_json(os.path.join(input_folder, file), attachments_folder, session)
                    count += 1
                    if count >= DEBUG_FILE_COUNT:
                        break  # Stop after processing DEBUG_FILE_COUNT files
        else:
            tasks = [
                process_json(os.path.join(input_folder, file), attachments_folder, session)
                for file in os.listdir(input_folder) if file.endswith(".json")
            ]
            await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
