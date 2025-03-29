# Google Keep to Notion Converter

Convert your exported Google Keep notes (from Google Takeout) into clean, import-ready Markdown and HTML files for use in Notion — complete with OCR image processing and optional ChatGPT formatting.

---

## ✨ Features

- ✅ Parses `.json` notes from Google Keep exports
- 🖼️ Extracts and OCRs embedded images
- 🤖 Optionally formats text using ChatGPT (GPT-4)
- 📁 Outputs clean, structured Markdown and HTML by label
- 🗂️ Local caching for fast repeat runs

---

## 🚀 Quick Start

### 1. Clone the repository

```
git clone https://github.com/yourusername/gkeep-to-notion.git
cd gkeep-to-notion
```

### 2. Create a virtual environment and install dependencies 

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Set your OpenAI API key (optional)
export OPENAI_API_KEY=your-openai-key

### 4.  Export your Google Keep notes
- Go to Google Takeout
- Export only Google Keep
- Extract the .zip file and copy the Keep/ folder into the root of this project

### 5. Run the script
`python translate_gkeep.py`


### Output 
output_markdown/
output_html/

### Configuration Options
DEBUG_MODE = True        # Limit processing to a few files
DEBUG_FILE_COUNT = 15    # Number of notes to process in debug mode
USE_CHATGPT = False      # Enable ChatGPT Markdown formatting

### Requirements
Python 3.10+

Tesseract OCR installed and available in your system PATH

OpenAI API key (if USE_CHATGPT = True)

### Dependencies
Installable via pip install -r requirements.txt:
- aiohttp
- openai
- pytesseract
- pillow
- python-dotenv

### Caching
To avoid repeated OCR and API calls, the script saves intermediate results to:

cache/ocr/ – Raw OCR output
cache/chatgpt/ – ChatGPT-formatted Markdown

To clear the cache, simply delete those folders before re-running.

## License

[MIT](LICENSE)

Copyright (c) 2025 Michael Diener
