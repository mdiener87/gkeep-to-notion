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

DEBUG_MODE = True          # When True, process only a few files for debugging
DEBUG_FILE_COUNT = 15       # Number of files to process in debug mode

# Define output folders
OUTPUT_FOLDER = "output_markdown"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs("output_html", exist_ok=True)

# Toggle for enabling/disabling ChatGPT API
USE_CHATGPT = True  # Set to True to enable ChatGPT processing, False for OCR only

# OpenAI API Key (make sure this is set in your environment)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Define OCR and ChatGPT cache folders (file-based cache)
OCR_CACHE_FOLDER = "ocr_cache"
os.makedirs(OCR_CACHE_FOLDER, exist_ok=True)
CHATGPT_CACHE_FOLDER = "chatgpt_cache"
os.makedirs(CHATGPT_CACHE_FOLDER, exist_ok=True)

# Define semaphore for limiting OCR concurrency (adjust the limit as needed)
OCR_SEMAPHORE_LIMIT = 4  # Adjust based on your system; your 9800x3d might handle 8-12 concurrently
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
    cache_file = os.path.join(OCR_CACHE_FOLDER, sanitize_filename(os.path.basename(image_path)) + ".txt")
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            cached_text = f.read().strip()
        if cached_text:
            return cached_text

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

            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(text)

            return text
        except Exception as e:
            print(f"Error during OCR for {image_path}: {e}")
            return ""

async def format_text_with_chatgpt(raw_text, session):
    """
    Send OCR text to OpenAI GPT API for faithful Markdown conversion.
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
                {"role": "user", "content": f"Convert the following OCR text to Markdown, preserving all formatting:\n\n'''{raw_text}'''"}  # Triple quotes for clarity
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

async def process_attachment(file_path, session):
    """
    Process a single attachment:
      - Get OCR text using Tesseract (with caching and semaphore limits)
      - If ChatGPT is enabled, check the cache for formatted text; if not present, call the API and cache the result.
    Returns a tuple: (ocr_text, formatted_text)
    """
    ocr_text = await ocr_image(file_path)
    if USE_CHATGPT:
        chatgpt_cache_file = os.path.join(CHATGPT_CACHE_FOLDER, sanitize_filename(os.path.basename(file_path)) + ".txt")
        if os.path.exists(chatgpt_cache_file):
            with open(chatgpt_cache_file, "r", encoding="utf-8") as f:
                formatted_text = f.read().strip()
            if formatted_text:
                return ocr_text, formatted_text
        formatted_text = await format_text_with_chatgpt(ocr_text, session)
        with open(chatgpt_cache_file, "w", encoding="utf-8") as f:
            f.write(formatted_text)
        return ocr_text, formatted_text
    else:
        return ocr_text, ocr_text

async def create_markdown(note, attachments_folder, ocr_results, formatted_texts):
    """Generate a Markdown string from note data using precomputed OCR & ChatGPT results."""
    title = note.get("title", "Untitled")
    created_date = timestamp_to_date(note.get("createdTimestampUsec", 0))
    edited_date = timestamp_to_date(note.get("userEditedTimestampUsec", 0))
    text_content = note.get("textContent", "").strip()
    labels = ", ".join(label.get("name", "") for label in note.get("labels", []))

    attachment_text = ""
    for ocr_text, formatted_text in zip(ocr_results, formatted_texts):
        attachment_text += f"\n\n## OCR Extracted Text\n"
        attachment_text += f"### Raw OCR Output:\n```\n{ocr_text}\n```\n"
        if USE_CHATGPT:
            attachment_text += f"### ChatGPT Formatted Output:\n{formatted_text}\n"

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
    """
    Generate an HTML string from note data in a panel view.
    For each valid attachment, display a row with:
      - Column 1: Original image
      - Column 2: Raw OCR output
      - Column 3: ChatGPT-formatted output (if enabled)
    Each bit of content is collapsible (starting open).
    """
    title = note.get("title", "Untitled")
    created_date = timestamp_to_date(note.get("createdTimestampUsec", 0))
    edited_date = timestamp_to_date(note.get("userEditedTimestampUsec", 0))
    labels = ", ".join(label.get("name", "") for label in note.get("labels", []))
    
    # Prepare a list of valid attachment file paths
    attachment_files = []
    for attachment in note.get("attachments", []):
        file_path = os.path.join(attachments_folder, attachment.get("filePath"))
        if os.path.exists(file_path):
            attachment_files.append(file_path)

    # Build rows for each attachment, aligning image, OCR, and ChatGPT data by index
    rows_html = ""
    for idx, file_path in enumerate(attachment_files, start=1):
        # Build image column
        with open(file_path, "rb") as img_file:
            base64_data = base64.b64encode(img_file.read()).decode("utf-8")
        mime_type = "image/png" if file_path.endswith(".png") else "image/jpeg"
        image_html = f'<img src="data:{mime_type};base64,{base64_data}" alt="Embedded Image {idx}" style="max-width:100%;">'
        
        # Retrieve corresponding OCR and ChatGPT texts (if available)
        ocr_text = ocr_results[idx-1] if idx-1 < len(ocr_results) else ""
        formatted_text = formatted_texts[idx-1] if idx-1 < len(formatted_texts) else ""
        
        # Wrap each piece of content in a collapsible <details> element that starts open
        image_details = f'''
        <details open>
            <summary>Image {idx}</summary>
            {image_html}
        </details>
        '''
        ocr_details = f'''
        <details open>
            <summary>OCR Output {idx}</summary>
            <pre>{ocr_text}</pre>
        </details>
        '''
        chatgpt_details = ""
        if USE_CHATGPT:
            chatgpt_details = f'''
            <details open>
                <summary>ChatGPT Output {idx}</summary>
                <pre>{formatted_text}</pre>
            </details>
            '''
        
        # Create a row that displays the three columns side by side.
        if USE_CHATGPT:
            row = f'''
            <div class="attachment-row">
                <div class="attachment-column">{image_details}</div>
                <div class="attachment-column">{ocr_details}</div>
                <div class="attachment-column">{chatgpt_details}</div>
            </div>
            '''
        else:
            row = f'''
            <div class="attachment-row">
                <div class="attachment-column">{image_details}</div>
                <div class="attachment-column">{ocr_details}</div>
            </div>
            '''
        rows_html += row

    html_content = f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                max-width: 1200px;
                margin: auto;
                padding: 20px;
            }}
            h1 {{
                color: #333;
            }}
            .meta-info {{
                margin-bottom: 20px;
            }}
            .attachment-row {{
                display: flex;
                gap: 20px;
                margin-bottom: 20px;
            }}
            .attachment-column {{
                flex: 1;
            }}
            details {{
                margin-bottom: 10px;
            }}
            summary {{
                cursor: pointer;
                font-size: 1.1em;
                font-weight: bold;
                color: #007bff;
            }}
            summary:hover {{
                text-decoration: underline;
            }}
            pre {{
                background: #f4f4f4;
                padding: 10px;
                border-radius: 5px;
                overflow-x: auto;
                white-space: pre-wrap;
                word-wrap: break-word;
            }}
        </style>
    </head>
    <body>
        <h1>{title}</h1>
        <div class="meta-info">
            <p><strong>Created:</strong> {created_date}</p>
            <p><strong>Last Edited:</strong> {edited_date}</p>
            <p><strong>Labels:</strong> {labels}</p>
        </div>
        {rows_html}
    </body>
    </html>
    '''
    return html_content.strip()

async def process_json(json_file, attachments_folder, session):
    """
    Process a single JSON file:
      - Load note data,
      - For each attachment, perform OCR and (if enabled) ChatGPT formatting using independent caches,
      - Generate and save Markdown and HTML outputs.
    """
    with open(json_file, "r", encoding="utf-8") as file:
        note = json.load(file)

    labels = [label.get("name", "") for label in note.get("labels", [])]
    label_folder = "_".join(labels) if labels else "Unlabeled"

    markdown_folder = os.path.join("output_markdown", label_folder)
    html_folder = os.path.join("output_html", label_folder)
    os.makedirs(markdown_folder, exist_ok=True)
    os.makedirs(html_folder, exist_ok=True)

    attachment_paths = []
    for attachment in note.get("attachments", []):
        file_path = os.path.join(attachments_folder, attachment.get("filePath"))
        if os.path.exists(file_path):
            attachment_paths.append(file_path)

    if USE_CHATGPT:
        tasks = [process_attachment(file_path, session) for file_path in attachment_paths]
        results = await asyncio.gather(*tasks)
        ocr_results = [r[0] for r in results]
        formatted_texts = [r[1] for r in results]
    else:
        tasks = [ocr_image(file_path) for file_path in attachment_paths]
        ocr_results = await asyncio.gather(*tasks)
        formatted_texts = ocr_results

    markdown_content = await create_markdown(note, attachments_folder, ocr_results, formatted_texts)
    html_content = await create_html(note, attachments_folder, ocr_results, formatted_texts)

    title = sanitize_filename(note.get("title", "Untitled"))

    markdown_file = os.path.join(markdown_folder, f"{title}.md")
    with open(markdown_file, "w", encoding="utf-8") as md_file:
        md_file.write(markdown_content)
    print(f"✅ Markdown generated: {markdown_file}")

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
