"""
Anthropic Framework Module
Supports Claude 3 (Sonnet, Opus, Haiku) via Anthropic v1/messages API.
"""

import time
import streamlit as st
import requests
from typing import Dict, List, Optional

# Import API key utilities
from utils.api_keys import get_api_key, validate_api_key

def process_chat(
    messages: List[Dict[str, str]],
    model: str,
    temperature: float = 0.7,
    top_p: float = 0.9,
    framework_config: Optional[Dict[str, str]] = None
) -> Optional[dict]:
    """
    Process a chat using the Anthropic Claude API (Claude 3 Sonnet, Opus, Haiku).

    Args:
        messages: List of message dicts with 'role' and 'content' (roles: 'user', 'assistant', 'system')
        model: Model name (e.g., 'claude-3-sonnet-20240229')
        temperature: Sampling temperature
        top_p: Nucleus sampling parameter
        framework_config: Dictionary containing Anthropic framework configuration

    Returns:
        Dictionary with standard response format:
        {
            "content": str,  # The generated text response
            "prompt_tokens": int,  # Number of input tokens
            "completion_tokens": int,  # Number of output tokens
            "elapsed_time": float  # Time taken for the request in seconds
        }
    """
    start_time = time.time()
    
    if not framework_config:
        return {
            "error": "Anthropic framework configuration not provided.",
            "content": "Error: Configuration not provided.",
            "prompt_tokens": 0, 
            "completion_tokens": 0, 
            "elapsed_time": 0
        }

    try:
        api_key_ref = framework_config.get("api_key_ref")
        api_base_url = framework_config.get("api_base_url")

        if not api_key_ref:
            return {
                "error": "API key reference (api_key_ref) not found in Anthropic framework configuration.",
                "content": "Error: Missing API key reference.",
                "prompt_tokens": 0, 
                "completion_tokens": 0, 
                "elapsed_time": 0
            }
            
        if not api_base_url:
            return {
                "error": "API base URL (api_base_url) not found in Anthropic framework configuration.",
                "content": "Error: Missing API base URL.",
                "prompt_tokens": 0, 
                "completion_tokens": 0, 
                "elapsed_time": 0
            }

        # Safely get and validate the API key
        api_key = get_api_key(api_key_ref)
        
        if not api_key:
            return {
                "error": f"API key for reference '{api_key_ref}' not found in st.secrets.",
                "content": "Error: API key not found.",
                "prompt_tokens": 0, 
                "completion_tokens": 0, 
                "elapsed_time": 0
            }
            
        is_valid, error_msg = validate_api_key(api_key, "Anthropic API key")
        if not is_valid:
            return {
                "error": f"API key validation failed: {error_msg}",
                "content": f"Error: {error_msg}",
                "prompt_tokens": 0, 
                "completion_tokens": 0, 
                "elapsed_time": 0
            }
            


        # Construct the full URL - ensure we don't double-append /v1/messages
        base_url = api_base_url.rstrip('/')
        if not base_url.endswith('/v1/messages'):
            if base_url.endswith('/v1'):
                base_url = f"{base_url}/messages"
            else:
                base_url = f"{base_url}/v1/messages"
        url = base_url
        

        # Updated headers for Anthropic API
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        # Process messages for Anthropic API
        system_prompt = None
        filtered_messages = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                # Combine all system messages into one
                if system_prompt:
                    system_prompt += "\n" + content
                else:
                    system_prompt = content
            elif role in ("user", "assistant"):
                # Ensure role is valid for Anthropic (either 'user' or 'assistant')
                filtered_messages.append({
                    "role": role,
                    "content": content
                })

        # Prepare the request payload according to Anthropic's API
        payload = {
            "model": model,
            "messages": filtered_messages,
            "max_tokens": 1024,  # Required by Anthropic API
            "temperature": max(0, min(temperature, 1.0)),  # Ensure temperature is between 0 and 1
            "top_p": max(0, min(top_p, 1.0)),  # Ensure top_p is between 0 and 1
            "stream": False
        }
        
        # Add system prompt if available
        if system_prompt:
            payload["system"] = system_prompt.strip()
            


        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        start_time = time.time()
        # Make the API request with better error handling
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=60
            )
            elapsed_time = time.time() - start_time
            
            # Check for HTTP errors
            response.raise_for_status()
            data = response.json()
            
            # Response handling
            
        except requests.exceptions.HTTPError as http_err:
            elapsed_time = time.time() - start_time
            error_msg = f"HTTP error occurred: {http_err}"
            if hasattr(http_err, 'response') and http_err.response is not None:
                try:
                    error_data = http_err.response.json()
                    error_msg += f" - {error_data.get('error', {}).get('message', 'No error details')}"

                except ValueError:
                    error_msg += f" - {http_err.response.text}"
            return {
                "error": error_msg,
                "content": f"Error: {error_msg}",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "elapsed_time": elapsed_time
            }

        # Extract response content safely
        try:
            if not data.get("content") or not isinstance(data["content"], list):
                raise ValueError("Invalid or missing content in API response")
                
            # Extract text content from the response
            content_parts = []
            for content_item in data["content"]:
                if content_item.get("type") == "text":
                    content_parts.append(content_item.get("text", ""))
            
            content = "\n".join(part for part in content_parts if part)
            
            # Extract token usage
            usage = data.get("usage", {})
            prompt_tokens = usage.get("input_tokens", 0)
            completion_tokens = usage.get("output_tokens", 0)
            
        except (KeyError, IndexError, AttributeError) as e:
            error_msg = f"Error parsing API response: {str(e)}"
            return {
                "error": error_msg,
                "content": f"Error: {error_msg}",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "elapsed_time": elapsed_time
            }

        return {
            "content": content,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "elapsed_time": elapsed_time
        }
    except Exception as e:
        import traceback
        error_msg = f"Unexpected error in Anthropic API call: {str(e)}"
        print(f"[Anthropic] {error_msg}")
        print(f"[Anthropic] Traceback: {traceback.format_exc()}")
        return {
            "error": error_msg,
            "content": f"Error: {error_msg}",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "elapsed_time": time.time() - start_time if 'start_time' in locals() else 0
        }
