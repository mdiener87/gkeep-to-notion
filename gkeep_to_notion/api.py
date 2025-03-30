"""
API integration module for Google Keep to Notion converter.

This module handles interactions with external APIs, such as OpenAI's ChatGPT.
"""

import os
from typing import Optional
from aiohttp import ClientSession

from .config import Config


async def format_text_with_chatgpt(raw_text: str, session: ClientSession) -> str:
    """
    Send OCR text to OpenAI GPT API for faithful Markdown conversion.
    
    Args:
        raw_text: The OCR text to format
        session: An aiohttp ClientSession for making requests
        
    Returns:
        Formatted text from ChatGPT
    """
    try:
        headers = {"Authorization": f"Bearer {Config.OPENAI_API_KEY}"}
        payload = {
            "model": "gpt-4-turbo",
            "messages": [
                {"role": "system", "content": (
                    "You are an OCR correction assistant. Your job is to fix misrecognized characters, "
                    "preserve original text structure, and correct minor errors (spacing, punctuation, "
                    "capitalization). DO NOT alter wording, meaning, or sentence structure. "
                    "Make the output as faithful to the original text as possible while cleaning up OCR artifacts. "
                    "Retain all line breaks, bullet points, and structure as closely as possible."
                )},
                {"role": "user", "content": f"Convert the following OCR text to Markdown, preserving all formatting:\n\n'''{raw_text}'''"}
            ]
        }

        async with session.post(
            "https://api.openai.com/v1/chat/completions", 
            json=payload, 
            headers=headers
        ) as response:
            result = await response.json()

            if "choices" not in result or not result["choices"]:
                print("⚠️ Warning: No choices returned from API response.")
                return "⚠️ Error: No response from ChatGPT"

            return result["choices"][0]["message"]["content"]
    
    except Exception as e:
        print(f"❌ Error during API call: {e}")
        return "❌ API request failed"
