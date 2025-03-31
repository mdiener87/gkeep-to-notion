"""
Output generation module for Google Keep to Notion converter.

This module handles the generation of Markdown and HTML output from processed notes.
"""

import os
import base64
from typing import Dict, List, Any

from .config import Config
from .utils import timestamp_to_date


async def create_markdown(note: Dict[str, Any], attachments_folder: str, 
                         ocr_results: List[str], formatted_texts: List[str]) -> str:
    """
    Generate a Markdown string from note data using precomputed OCR & ChatGPT results.
    
    Args:
        note: The note data dictionary
        attachments_folder: Path to the folder containing attachments
        ocr_results: List of OCR results for attachments
        formatted_texts: List of formatted texts for attachments
        
    Returns:
        Markdown content as a string
    """
    # Extract note metadata
    title = note.get("title", "Untitled")
    created_date = timestamp_to_date(note.get("createdTimestampUsec", 0))
    edited_date = timestamp_to_date(note.get("userEditedTimestampUsec", 0))
    text_content = note.get("textContent", "").strip()
    html_content = note.get("textContentHtml", "").strip()
    labels = ", ".join(label.get("name", "") for label in note.get("labels", []))

    # Generate content section
    content_section = ""
    
    # If we have HTML content, include a note about it
    if html_content:
        content_section += f"## Note Content (HTML)\n\n{text_content}\n\n"
        content_section += f"*Note: This note contains formatted HTML content that can be viewed in the HTML version.*\n\n"
    elif text_content:
        content_section += f"## Note Content\n\n{text_content}\n\n"
    
    # Generate attachment section
    attachment_section = ""
    if ocr_results and ocr_results[0]:  # Only add the header if we have attachments
        attachment_section += "## Attachments\n\n"
        
        for idx, (ocr_text, formatted_text) in enumerate(zip(ocr_results, formatted_texts), start=1):
            attachment_section += f"### Attachment {idx}\n\n"
            attachment_section += f"#### Raw OCR Output:\n```\n{ocr_text}\n```\n\n"
            if formatted_text != ocr_text and Config.USE_CHATGPT:  # Only add ChatGPT text if enabled and different
                attachment_section += f"#### ChatGPT Output:\n{formatted_text}\n\n"

    # Combine all sections into a Markdown document
    markdown_content = f"""
    # {title}

    **Created:** {created_date}  
    **Last Edited:** {edited_date}  
    **Labels:** {labels}  

    ---

    {content_section}
    {attachment_section}
    """.strip()

    return markdown_content


async def create_html(note: Dict[str, Any], attachments_folder: str, 
                     ocr_results: List[str], formatted_texts: List[str],
                     attachment_paths: List[str]) -> str:
    """
    Generate an HTML string from note data in a panel view.
    
    For each valid attachment, display a row with:
      - Column 1: Original image
      - Column 2: Raw OCR output
      - Column 3: ChatGPT-formatted output (if enabled)
    Each content section is collapsible (starting open).
    
    Args:
        note: The note data dictionary
        attachments_folder: Path to the folder containing attachments
        ocr_results: List of OCR results for attachments
        formatted_texts: List of formatted texts for attachments
        attachment_paths: List of file paths to attachments
        
    Returns:
        HTML content as a string
    """
    # Extract note metadata
    title = note.get("title", "Untitled")
    created_date = timestamp_to_date(note.get("createdTimestampUsec", 0))
    edited_date = timestamp_to_date(note.get("userEditedTimestampUsec", 0))
    text_content = note.get("textContent", "").strip()
    html_content = note.get("textContentHtml", "").strip()
    labels = ", ".join(label.get("name", "") for label in note.get("labels", []))
    
    # Use the attachment paths provided
    attachment_files = attachment_paths

    # Generate content section
    content_html = ""
    if html_content:
        # If we have HTML content, use it
        content_html = f'''
        <div class="note-content-html">
            {html_content}
        </div>
        '''
    elif text_content:
        # If we only have plain text, format it as pre-formatted text
        content_html = f'''
        <div class="note-content-text">
            <pre>{text_content}</pre>
        </div>
        '''
    
    # Note content details
    note_content_details = ""
    if content_html:
        note_content_details = f'''
        <div class="content-section">
            <h2>Note Content</h2>
            {content_html}
        </div>
        <hr>
        '''

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
        if formatted_text != ocr_text and Config.USE_CHATGPT:  # Only show ChatGPT output if enabled and different
            # Render Markdown as HTML instead of showing raw Markdown
            chatgpt_details = f'''
            <details open>
                <summary>ChatGPT Output {idx}</summary>
                <div class="markdown-content">
                    {formatted_text}
                </div>
            </details>
            '''
        
        # Create a row that displays the three columns side by side
        cols = 3 if chatgpt_details else 2
        row = f'''
        <div class="attachment-row">
            <div class="attachment-column">{image_details}</div>
            <div class="attachment-column">{ocr_details}</div>
            {chatgpt_details and f'<div class="attachment-column">{chatgpt_details}</div>' or ''}
        </div>
        '''
        rows_html += row

    # Create complete HTML document
    html_content = f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <!-- Add a basic Markdown CSS library -->
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.2.0/github-markdown.min.css">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                line-height: 1.6;
                max-width: 1200px;
                margin: auto;
                padding: 20px;
                color: #333;
            }}
            h1, h2 {{
                color: #333;
            }}
            .meta-info {{
                margin-bottom: 20px;
                background-color: #f9f9f9;
                padding: 15px;
                border-radius: 5px;
                border-left: 4px solid #007bff;
            }}
            .content-section {{
                margin: 20px 0;
                padding: 15px;
                background-color: #f9f9f9;
                border-radius: 5px;
            }}
            .note-content-html {{
                padding: 15px;
                background: white;
                border-radius: 5px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .note-content-text pre {{
                white-space: pre-wrap;
                background: white;
                padding: 15px;
                border-radius: 5px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .attachment-row {{
                display: flex;
                gap: 20px;
                margin-bottom: 20px;
                flex-wrap: wrap; /* Allow wrapping on smaller screens */
            }}
            .attachment-column {{
                flex: 1;
                min-width: 300px; /* Ensure minimum width on small screens */
                background-color: #f9f9f9;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 15px;
            }}
            details {{
                margin-bottom: 15px;
            }}
            summary {{
                cursor: pointer;
                font-size: 1.1em;
                font-weight: bold;
                color: #007bff;
                padding: 8px 0;
            }}
            summary:hover {{
                text-decoration: underline;
            }}
            pre {{
                background: white;
                padding: 10px;
                border-radius: 5px;
                overflow-x: auto;
                white-space: pre-wrap;
                word-wrap: break-word;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            hr {{
                border: 0;
                height: 1px;
                background-color: #ddd;
                margin: 30px 0;
            }}
            /* Style the markdown content */
            .markdown-content {{
                padding: 15px;
                background: white;
                border-radius: 5px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            /* Apply GitHub Markdown styles but restrict to our container */
            .markdown-content {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            }}
            .markdown-content h1, 
            .markdown-content h2,
            .markdown-content h3,
            .markdown-content h4,
            .markdown-content h5,
            .markdown-content h6 {{
                margin-top: 24px;
                margin-bottom: 16px;
                font-weight: 600;
                line-height: 1.25;
            }}
            .markdown-content h1 {{
                font-size: 2em;
                border-bottom: 1px solid #eaecef;
                padding-bottom: .3em;
            }}
            .markdown-content h2 {{
                font-size: 1.5em;
                border-bottom: 1px solid #eaecef;
                padding-bottom: .3em;
            }}
            .markdown-content p {{
                margin-top: 0;
                margin-bottom: 16px;
            }}
            .markdown-content ul, 
            .markdown-content ol {{
                padding-left: 2em;
                margin-top: 0;
                margin-bottom: 16px;
            }}
            .markdown-content code {{
                padding: .2em .4em;
                margin: 0;
                font-size: 85%;
                background-color: rgba(27,31,35,.05);
                border-radius: 3px;
                font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
            }}
            .markdown-content pre {{
                word-wrap: normal;
                padding: 16px;
                overflow: auto;
                font-size: 85%;
                line-height: 1.45;
                background-color: #f6f8fa;
                border-radius: 3px;
            }}
            .markdown-content pre > code {{
                padding: 0;
                margin: 0;
                font-size: 100%;
                word-break: normal;
                white-space: pre;
                background: transparent;
                border: 0;
            }}
            .markdown-content a {{
                color: #0366d6;
                text-decoration: none;
            }}
            .markdown-content a:hover {{
                text-decoration: underline;
            }}
            .markdown-content blockquote {{
                padding: 0 1em;
                color: #6a737d;
                border-left: .25em solid #dfe2e5;
                margin: 0 0 16px 0;
            }}
            .markdown-content table {{
                display: block;
                width: 100%;
                overflow: auto;
                margin-top: 0;
                margin-bottom: 16px;
                border-spacing: 0;
                border-collapse: collapse;
            }}
            .markdown-content table th,
            .markdown-content table td {{
                padding: 6px 13px;
                border: 1px solid #dfe2e5;
            }}
            .markdown-content table tr {{
                background-color: #fff;
                border-top: 1px solid #c6cbd1;
            }}
            .markdown-content table tr:nth-child(2n) {{
                background-color: #f6f8fa;
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
        
        {note_content_details}
        
        <h2>Attachments</h2>
        {rows_html}
    </body>
    </html>
    '''
    
    return html_content.strip()
