"""
API integration module for Google Keep to Notion converter.

This module handles interactions with external APIs, such as OpenAI's ChatGPT.
"""

import os
import asyncio
from typing import Optional
from aiohttp import ClientSession

from .config import Config


async def format_text_with_chatgpt(raw_text: str, session: ClientSession) -> str:
    """
    Send OCR text to OpenAI GPT API for faithful Markdown conversion.
    Includes retry logic for better reliability.
    
    Args:
        raw_text: The OCR text to format
        session: An aiohttp ClientSession for making requests
        
    Returns:
        Formatted text from ChatGPT
    """
    # Skip empty or nearly empty text
    if not raw_text or len(raw_text.strip()) < 10:
        return "❌ Text too short for processing"
    
    # Set up retry parameters
    retry_attempts = Config.API_RETRY_ATTEMPTS
    retry_delay = Config.API_RETRY_DELAY
    
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
        ],
        "temperature": 0.3  # Lower temperature for more consistent outputs
    }

    timeout_seconds = 30  # Set timeout to avoid hanging requests
    
    # Try multiple times with exponential backoff
    for attempt in range(retry_attempts):
        try:
            async with session.post(
                "https://api.openai.com/v1/chat/completions", 
                json=payload, 
                headers=headers,
                timeout=timeout_seconds
            ) as response:
                # Check response status
                if response.status != 200:
                    error_text = await response.text()
                    error_msg = f"API returned status {response.status}: {error_text[:100]}"
                    print(f"⚠️ Attempt {attempt+1}/{retry_attempts}: {error_msg}")
                    
                    # If we have retries left, wait and try again
                    if attempt < retry_attempts - 1:
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                        print(f"Retrying in {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        return f"❌ {error_msg}"
                
                result = await response.json()

                if "choices" not in result or not result["choices"]:
                    error_msg = "No choices in API response"
                    print(f"⚠️ Attempt {attempt+1}/{retry_attempts}: {error_msg}")
                    
                    if attempt < retry_attempts - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        print(f"Retrying in {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        return f"❌ {error_msg}"
                
                if "error" in result:
                    error_msg = f"API error: {result['error']['message']}"
                    print(f"⚠️ Attempt {attempt+1}/{retry_attempts}: {error_msg}")
                    
                    if attempt < retry_attempts - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        print(f"Retrying in {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        return f"❌ {error_msg}"

                # Success!
                return result["choices"][0]["message"]["content"]
        
        except asyncio.TimeoutError:
            error_msg = f"API request timed out after {timeout_seconds} seconds"
            print(f"⚠️ Attempt {attempt+1}/{retry_attempts}: {error_msg}")
            
            if attempt < retry_attempts - 1:
                wait_time = retry_delay * (2 ** attempt)
                print(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                continue
            else:
                return f"❌ {error_msg}"
                
        except Exception as e:
            error_msg = f"API error: {str(e)}"
            print(f"⚠️ Attempt {attempt+1}/{retry_attempts}: {error_msg}")
            
            if attempt < retry_attempts - 1:
                wait_time = retry_delay * (2 ** attempt)
                print(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                continue
            else:
                return f"❌ {error_msg}"
    
    # If we somehow get here (shouldn't happen), return a generic error
    return "❌ Failed to get response after multiple attempts"
