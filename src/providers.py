# providers.py - Complete provider architecture

import google.generativeai as genai
import requests
import time
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import streamlit as st
from tools import tool_registry
from logger import logger
from config import OLLAMA_BASE_URL, OLLAMA_KEEP_ALIVE
from utils import ResponseTimer, estimate_tokens, create_response_object


class BaseProvider(ABC):
    """Base class for all AI providers"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None
        self.initialize_client()
    
    @abstractmethod
    def initialize_client(self):
        """Initialize the provider's client"""
        pass
    
    @abstractmethod
    def generate_response(self, messages: List[Dict], model_config: Dict, search_results: Optional[str] = None) -> Dict[str, Any]:
        """Generate a chat response with metrics"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[Dict]:
        """Get list of available models for this provider"""
        pass
    
    @abstractmethod
    def validate_model_config(self, config: Dict) -> bool:
        """Validate model configuration"""
        pass
    
    @property
    def provider_name(self) -> str:
        """Return the provider name"""
        return self.__class__.__name__.replace("Provider", "").lower()


class GoogleProvider(BaseProvider):
    """Provider for Google AI (Gemini) models"""
    
    def initialize_client(self):
        """Initialize Google AI client"""
        genai.configure(api_key=self.api_key)
        self._client = genai
    
    def generate_response(self, messages: List[Dict], model_config: Dict, search_results: Optional[str] = None) -> Dict[str, Any]:
        """Generate response using Google AI with metrics"""
        with ResponseTimer() as timer:
            try:
                # Calculate input tokens for metrics (current user message only)
                current_user_message = messages[-1].get("content", "") if messages else ""
                input_text = current_user_message
                if search_results:
                    input_text += search_results
                input_tokens = estimate_tokens(input_text)
                
                # ------------------------------------------------------------------
                # Prepare model with tool schemas (if any)
                # ------------------------------------------------------------------
                tool_configs = tool_registry.list_tool_configs()
                model = genai.GenerativeModel(
                    model_name=model_config["name"],
                    tools=tool_configs if tool_configs else None,
                    generation_config={
                        "temperature": model_config.get("temperature", 0.7),
                        "top_p": model_config.get("top_p", 0.9),
                        "max_output_tokens": model_config.get("max_output_tokens", 8192),
                    },
                )

                # Build conversation history for the API
                api_history: List[Dict[str, Any]] = []
                
                # Enhance system prompt with user context
                from prompt_enhancer import enhance_system_prompt
                original_system_prompt = model_config.get("system_prompt", "")
                system_prompt = enhance_system_prompt(original_system_prompt)
                
                if system_prompt:
                    api_history.extend(
                        [
                            {"role": "user", "parts": [f"System Prompt: {system_prompt}"]},
                            {"role": "model", "parts": ["Acknowledged."]},
                        ]
                    )

                for msg in messages:
                    role = "model" if msg["role"] == "assistant" else "user"
                    api_history.append({"role": role, "parts": [msg["content"]]})

                if search_results:
                    api_history.append(
                        {
                            "role": "user",
                            "parts": [f"Here are the search results to help you answer:\n\n{search_results}"],
                        }
                    )

                # ------------------------------------------------------------------
                # Agentic loop: allow the model to call tools up to N times
                # ------------------------------------------------------------------
                final_text = ""
                for _ in range(3):
                    logger.debug("Sending to Gemini:")
                    logger.debug(api_history)
                    response = model.generate_content(api_history)
                    logger.debug("Gemini response raw: %s", response)
                    candidate = response.candidates[0]

                    # Detect tool / function call robustly
                    fc = None
                    try:
                        for part in candidate.content.parts:
                            if hasattr(part, "function_call") and part.function_call:
                                fc = part.function_call
                                break
                    except Exception:
                        pass

                    if not fc:
                        # Normal answer - extract usage data if available
                        final_text = candidate.content.parts[0].text if hasattr(candidate.content.parts[0], "text") else response.text
                        
                        # Use our estimates for simple performance indication
                        actual_input_tokens = input_tokens
                        actual_output_tokens = estimate_tokens(final_text)
                        estimated_fields = ["input_tokens", "output_tokens"]
                        
                        # Create metrics
                        metrics = {
                            "response_time": timer.elapsed_time,
                            "input_tokens": actual_input_tokens,
                            "output_tokens": actual_output_tokens,
                            "estimated": estimated_fields
                        }
                        
                        return create_response_object(final_text, metrics)

                    tool_name = fc.name
                    args_json = fc.args if hasattr(fc, "args") else fc.get("args", "{}")  # type: ignore
                    try:
                        args = json.loads(args_json) if isinstance(args_json, str) else args_json
                    except Exception:
                        args = {}

                    tool_fn = tool_registry.get_callable(tool_name)
                    if not tool_fn:
                        api_history.append({"role": "model", "parts": [f"I tried to call unknown tool {tool_name}"]})
                        continue

                    # Run the tool and append result
                    tool_output = tool_fn(**args)
                    # Format function response according to Gemini's expected schema
                    api_history.append(
                        {
                            "role": "function",
                            "parts": [{
                                "function_response": {
                                    "name": tool_name,
                                    "response": {"name": tool_name, "content": tool_output}
                                }
                            }]
                        }
                    )
                
                # If loop exceeds - create fallback response with metrics
                final_text = "I couldn't complete the request with the available tools."
                metrics = {
                    "response_time": timer.elapsed_time,
                    "input_tokens": input_tokens,
                    "output_tokens": estimate_tokens(final_text),
                    "estimated": ["input_tokens", "output_tokens"]
                }
                return create_response_object(final_text, metrics)

            except Exception as e:
                logger.exception("GoogleProvider failed")
                st.error("Sorry, the AI backend encountered an error. Please check logs.")
                error_text = "Sorry, I encountered an error while generating a response."
                metrics = {
                    "response_time": timer.elapsed_time,
                    "input_tokens": input_tokens,
                    "output_tokens": estimate_tokens(error_text),
                    "estimated": ["input_tokens", "output_tokens"]
                }
                return create_response_object(error_text, metrics)
    
    def get_available_models(self) -> List[Dict]:
        """Get available Google AI models"""
        return [
            {
                "name": "gemini-2.0-flash-exp",
                "provider": "google",
                "display_name": "Gemini 2.0 Flash (Experimental)",
                "capabilities": ["text", "vision", "tools"]
            },
            {
                "name": "gemini-1.5-pro",
                "provider": "google", 
                "display_name": "Gemini 1.5 Pro",
                "capabilities": ["text", "vision", "tools"]
            },
            {
                "name": "gemini-1.5-flash",
                "provider": "google",
                "display_name": "Gemini 1.5 Flash", 
                "capabilities": ["text", "vision", "tools"]
            }
        ]
    
    def validate_model_config(self, config: Dict) -> bool:
        """Validate Google AI model configuration"""
        required_fields = ["name", "provider", "temperature", "top_p"]
        return all(field in config for field in required_fields)


class AnthropicProvider(BaseProvider):
    """Provider for Anthropic (Claude) models using direct HTTP requests"""
    
    def initialize_client(self):
        """Initialize HTTP client"""
        self._client = None
    
    def generate_response(self, messages: List[Dict], model_config: Dict, search_results: Optional[str] = None) -> Dict[str, Any]:
        """Generate response using Anthropic Claude via HTTP with metrics"""
        with ResponseTimer() as timer:
            try:
                # Calculate input tokens for metrics (current user message only)
                current_user_message = messages[-1].get("content", "") if messages else ""
                input_text = current_user_message
                if search_results:
                    input_text += search_results
                input_tokens = estimate_tokens(input_text)
                
                # API endpoint
                url = "https://api.anthropic.com/v1/messages"
                
                # Headers
                headers = {
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                
                # Process messages
                anthropic_messages = []
                for msg in messages:
                    anthropic_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                
                # Add search results if provided
                if search_results:
                    anthropic_messages.append({
                        "role": "user",
                        "content": f"Here are the search results:\n\n{search_results}"
                    })
                
                # Prepare payload
                payload = {
                    "model": model_config["name"],
                    "messages": anthropic_messages,
                    "max_tokens": model_config.get("max_output_tokens", 4096),
                    "temperature": model_config.get("temperature", 0.7)
                }
                
                # Enhance system prompt with user context
                from prompt_enhancer import enhance_system_prompt
                original_system_prompt = model_config.get("system_prompt", "")
                system_prompt = enhance_system_prompt(original_system_prompt)
                
                if system_prompt:
                    payload["system"] = system_prompt.strip()
                
                # Make request
                response = requests.post(url, json=payload, headers=headers, timeout=60)
                response.raise_for_status()
                data = response.json()
                
                # Extract content
                content_parts = []
                for item in data["content"]:
                    if item.get("type") == "text":
                        content_parts.append(item.get("text", ""))
                
                final_text = "\n".join(content_parts)
                
                # Use our estimates for simple performance indication
                actual_input_tokens = input_tokens
                actual_output_tokens = estimate_tokens(final_text)
                estimated_fields = ["input_tokens", "output_tokens"]
                
                # Create metrics
                metrics = {
                    "response_time": timer.elapsed_time,
                    "input_tokens": actual_input_tokens,
                    "output_tokens": actual_output_tokens,
                    "estimated": estimated_fields
                }
                
                return create_response_object(final_text, metrics)
                
            except Exception as e:
                st.error(f"Anthropic Error: {e}")
                error_text = "Sorry, I encountered an error while generating a response."
                metrics = {
                    "response_time": timer.elapsed_time,
                    "input_tokens": input_tokens,
                    "output_tokens": estimate_tokens(error_text),
                    "estimated": ["input_tokens", "output_tokens"]
                }
                return create_response_object(error_text, metrics)
    
    def get_available_models(self) -> List[Dict]:
        """Get available Anthropic models"""
        return [
            {
                "name": "claude-3-5-sonnet-20241022",
                "provider": "anthropic",
                "display_name": "Claude 3.5 Sonnet",
                "capabilities": ["text", "vision"]
            },
            {
                "name": "claude-3-5-haiku-20241022", 
                "provider": "anthropic",
                "display_name": "Claude 3.5 Haiku",
                "capabilities": ["text", "vision"]
            },
            {
                "name": "claude-3-opus-20240229",
                "provider": "anthropic",
                "display_name": "Claude 3 Opus",
                "capabilities": ["text", "vision"]
            }
        ]
    
    def validate_model_config(self, config: Dict) -> bool:
        """Validate Anthropic model configuration"""
        required_fields = ["name", "provider", "temperature"]
        return all(field in config for field in required_fields)


class OllamaProvider(BaseProvider):
    """Provider for Ollama (Local) models using HTTP API"""
    
    def __init__(self, api_key: str = ""):
        # Ollama doesn't require an API key
        super().__init__(api_key)
    
    def initialize_client(self):
        """Initialize HTTP client for Ollama"""
        self._client = None  # Using requests directly
    
    def preload_model(self, model_name: str):
        """Preload a model to keep it in memory"""
        try:
            url = f"{OLLAMA_BASE_URL}/api/generate"
            payload = {
                "model": model_name,
                "prompt": "",
                "stream": False,
                "keep_alive": OLLAMA_KEEP_ALIVE
            }
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                logger.info(f"Preloaded Ollama model: {model_name}")
            else:
                logger.warning(f"Failed to preload Ollama model {model_name}: {response.status_code}")
        except Exception as e:
            logger.warning(f"Could not preload Ollama model {model_name}: {e}")
    
    def generate_response(self, messages: List[Dict], model_config: Dict, search_results: Optional[str] = None) -> Dict[str, Any]:
        """Generate response using Ollama via HTTP with metrics"""
        with ResponseTimer() as timer:
            try:
                # Calculate input tokens for metrics (current user message only)
                current_user_message = messages[-1].get("content", "") if messages else ""
                input_text = current_user_message
                if search_results:
                    input_text += search_results
                input_tokens = estimate_tokens(input_text)
                
                url = f"{OLLAMA_BASE_URL}/api/chat"
                
                # Process messages for Ollama format
                ollama_messages = []
                
                # Enhance system prompt with user context
                from prompt_enhancer import enhance_system_prompt
                original_system_prompt = model_config.get("system_prompt", "")
                system_prompt = enhance_system_prompt(original_system_prompt)
                
                # Add system prompt if provided
                if system_prompt:
                    ollama_messages.append({
                        "role": "system",
                        "content": system_prompt
                    })
                
                # Add conversation history
                for msg in messages:
                    ollama_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                
                # Add search results if provided
                if search_results:
                    ollama_messages.append({
                        "role": "user", 
                        "content": f"Here are the search results to help you answer:\n\n{search_results}"
                    })
                
                # Prepare payload
                payload = {
                    "model": model_config["name"],
                    "messages": ollama_messages,
                    "stream": False,
                    "keep_alive": OLLAMA_KEEP_ALIVE,  # Keep model in memory to avoid reloading
                    "options": {
                        "temperature": model_config.get("temperature", 0.7),
                        "num_predict": model_config.get("max_output_tokens", 8192)
                    }
                }
                
                # Make request
                response = requests.post(url, json=payload, timeout=120)  # Longer timeout for local models
                response.raise_for_status()
                data = response.json()
                
                # Extract response and metrics
                if "message" in data and "content" in data["message"]:
                    final_text = data["message"]["content"]
                else:
                    final_text = "No response received from Ollama"
                
                # Use our estimates for simple performance indication
                actual_input_tokens = input_tokens
                actual_output_tokens = estimate_tokens(final_text)
                estimated_fields = ["input_tokens", "output_tokens"]
                
                # Create metrics
                metrics = {
                    "response_time": timer.elapsed_time,
                    "input_tokens": actual_input_tokens,
                    "output_tokens": actual_output_tokens,
                    "estimated": estimated_fields
                }
                
                return create_response_object(final_text, metrics)
                
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to Ollama. Make sure Ollama is running on localhost:11434")
                error_text = "Error: Could not connect to Ollama server"
                metrics = {
                    "response_time": timer.elapsed_time,
                    "input_tokens": input_tokens,
                    "output_tokens": estimate_tokens(error_text),
                    "estimated": ["input_tokens", "output_tokens"]
                }
                return create_response_object(error_text, metrics)
            except requests.exceptions.Timeout:
                st.error("Ollama request timed out")
                error_text = "Error: Request timed out"
                metrics = {
                    "response_time": timer.elapsed_time,
                    "input_tokens": input_tokens,
                    "output_tokens": estimate_tokens(error_text),
                    "estimated": ["input_tokens", "output_tokens"]
                }
                return create_response_object(error_text, metrics)
            except Exception as e:
                logger.exception("OllamaProvider failed")
                st.error(f"Ollama Error: {e}")
                error_text = "Sorry, I encountered an error while generating a response."
                metrics = {
                    "response_time": timer.elapsed_time,
                    "input_tokens": input_tokens,
                    "output_tokens": estimate_tokens(error_text),
                    "estimated": ["input_tokens", "output_tokens"]
                }
                return create_response_object(error_text, metrics)
    
    def get_available_models(self) -> List[Dict]:
        """Get available Ollama models from the API"""
        try:
            url = f"{OLLAMA_BASE_URL}/api/tags"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            models = []
            for model in data.get("models", []):
                models.append({
                    "name": model["name"],
                    "provider": "ollama",
                    "display_name": f"Ollama {model['name']}",
                    "capabilities": ["text"],
                    "size": model.get("size", 0),
                    "parameter_size": model.get("details", {}).get("parameter_size", "Unknown")
                })
            
            return models
            
        except Exception as e:
            logger.warning(f"Could not fetch Ollama models: {e}")
            return []
    
    def validate_model_config(self, config: Dict) -> bool:
        """Validate Ollama model configuration"""
        required_fields = ["name", "provider"]
        return all(field in config for field in required_fields)


class GrokProvider(BaseProvider):
    """Provider for xAI Grok models using OpenAI-compatible API"""
    
    def initialize_client(self):
        """Initialize HTTP client for xAI API"""
        self._client = None
    
    def generate_response(self, messages: List[Dict], model_config: Dict, search_results: Optional[str] = None) -> Dict[str, Any]:
        """Generate response using xAI Grok via HTTP with metrics"""
        with ResponseTimer() as timer:
            try:
                # Calculate input tokens for metrics (current user message only)
                current_user_message = messages[-1].get("content", "") if messages else ""
                input_text = current_user_message
                if search_results:
                    input_text += search_results
                input_tokens = estimate_tokens(input_text)
                
                # xAI API endpoint (OpenAI-compatible)
                url = "https://api.x.ai/v1/chat/completions"
                
                # Headers
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                # Process messages for OpenAI format
                api_messages = []
                
                # Enhance system prompt with user context
                from prompt_enhancer import enhance_system_prompt
                original_system_prompt = model_config.get("system_prompt", "")
                system_prompt = enhance_system_prompt(original_system_prompt)
                
                # Add system prompt if present
                if system_prompt:
                    api_messages.append({
                        "role": "system",
                        "content": system_prompt
                    })
                
                # Add conversation history
                for msg in messages:
                    api_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                
                # Add search results if provided
                if search_results:
                    api_messages.append({
                        "role": "user",
                        "content": f"Here are the search results to help you answer:\n\n{search_results}"
                    })
                
                # Prepare payload
                payload = {
                    "model": model_config["name"],
                    "messages": api_messages,
                    "max_tokens": model_config.get("max_output_tokens", 4096),
                    "temperature": model_config.get("temperature", 0.7),
                    "top_p": model_config.get("top_p", 0.9),
                    "stream": False
                }
                
                logger.debug(f"Sending request to xAI: {url}")
                logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
                
                # Make the request
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                
                if response.status_code != 200:
                    error_msg = f"xAI API error {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    return create_response_object(f"API Error: {error_msg}", None)
                
                response_data = response.json()
                logger.debug(f"xAI response: {json.dumps(response_data, indent=2)}")
                
                # Extract response text
                if "choices" not in response_data or not response_data["choices"]:
                    return create_response_object("No response from Grok", None)
                
                choice = response_data["choices"][0]
                response_text = choice["message"]["content"]
                
                # Extract usage data (actual tokens from API)
                usage = response_data.get("usage", {})
                actual_input_tokens = usage.get("prompt_tokens", input_tokens)
                actual_output_tokens = usage.get("completion_tokens", estimate_tokens(response_text))
                total_tokens = usage.get("total_tokens", actual_input_tokens + actual_output_tokens)
                
                # Create metrics
                metrics = {
                    "response_time": timer.elapsed_time,
                    "input_tokens": actual_input_tokens,
                    "output_tokens": actual_output_tokens,
                    "total_tokens": total_tokens,
                    "estimated": []  # xAI provides actual token counts
                }
                
                return create_response_object(response_text, metrics)
                
            except requests.exceptions.Timeout:
                return create_response_object("Request timed out. Please try again.", None)
            except requests.exceptions.RequestException as e:
                logger.error(f"Network error with xAI API: {e}")
                return create_response_object(f"Network error: {str(e)}", None)
            except Exception as e:
                logger.error(f"Unexpected error with xAI: {e}")
                return create_response_object(f"Error: {str(e)}", None)
    
    def get_available_models(self) -> List[Dict]:
        """Get available Grok models"""
        # Based on xAI documentation - Grok 3 and Grok 3 mini
        return [
            {
                "name": "grok-3",
                "provider": "grok",
                "description": "xAI's flagship model that excels at complex reasoning, coding, and analysis tasks",
                "context_length": 128000,
                "max_output_tokens": 4096,
                "supports_vision": True,
                "supports_tools": False  # Will add when xAI adds function calling
            },
            {
                "name": "grok-3-mini",
                "provider": "grok",
                "description": "Lightweight Grok model optimized for speed and efficiency",
                "context_length": 128000,
                "max_output_tokens": 4096,
                "supports_vision": False,
                "supports_tools": False
            }
        ]
    
    def validate_model_config(self, config: Dict) -> bool:
        """Validate Grok model configuration"""
        required_fields = ["name", "provider"]
        valid_models = ["grok-3", "grok-3-mini"]
        return (
            all(field in config for field in required_fields) and
            config.get("name") in valid_models and
            config.get("provider") == "grok"
        )


class OpenAIProvider(BaseProvider):
    """Provider for OpenAI GPT models"""
    
    def initialize_client(self):
        """Initialize HTTP client for OpenAI API"""
        self._client = None
    
    def generate_response(self, messages: List[Dict], model_config: Dict, search_results: Optional[str] = None) -> Dict[str, Any]:
        """Generate response using OpenAI GPT via HTTP with metrics"""
        with ResponseTimer() as timer:
            try:
                # Calculate input tokens for metrics (current user message only)
                current_user_message = messages[-1].get("content", "") if messages else ""
                input_text = current_user_message
                if search_results:
                    input_text += search_results
                input_tokens = estimate_tokens(input_text)
                
                # OpenAI API endpoint
                url = "https://api.openai.com/v1/chat/completions"
                
                # Headers
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                # Process messages for OpenAI format
                api_messages = []
                
                # Enhance system prompt with user context
                from prompt_enhancer import enhance_system_prompt
                original_system_prompt = model_config.get("system_prompt", "")
                system_prompt = enhance_system_prompt(original_system_prompt)
                
                # Add system prompt if present
                if system_prompt:
                    api_messages.append({
                        "role": "system",
                        "content": system_prompt
                    })
                
                # Add conversation history
                for msg in messages:
                    api_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                
                # Add search results if provided
                if search_results:
                    api_messages.append({
                        "role": "user",
                        "content": f"Here are the search results to help you answer:\n\n{search_results}"
                    })
                
                # Prepare payload
                payload = {
                    "model": model_config["name"],
                    "messages": api_messages,
                    "max_tokens": model_config.get("max_output_tokens", 16384),
                    "temperature": model_config.get("temperature", 0.7),
                    "top_p": model_config.get("top_p", 0.9),
                    "stream": False
                }
                
                logger.debug(f"Sending request to OpenAI: {url}")
                logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
                
                # Make the request
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                
                if response.status_code != 200:
                    error_msg = f"OpenAI API error {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    return create_response_object(f"API Error: {error_msg}", None)
                
                response_data = response.json()
                logger.debug(f"OpenAI response: {json.dumps(response_data, indent=2)}")
                
                # Extract response text
                if "choices" not in response_data or not response_data["choices"]:
                    return create_response_object("No response from OpenAI", None)
                
                choice = response_data["choices"][0]
                response_text = choice["message"]["content"]
                
                # Extract usage data (actual tokens from API)
                usage = response_data.get("usage", {})
                actual_input_tokens = usage.get("prompt_tokens", input_tokens)
                actual_output_tokens = usage.get("completion_tokens", estimate_tokens(response_text))
                total_tokens = usage.get("total_tokens", actual_input_tokens + actual_output_tokens)
                
                # Create metrics
                metrics = {
                    "response_time": timer.elapsed_time,
                    "input_tokens": actual_input_tokens,
                    "output_tokens": actual_output_tokens,
                    "total_tokens": total_tokens,
                    "estimated": []  # OpenAI provides actual token counts
                }
                
                return create_response_object(response_text, metrics)
                
            except requests.exceptions.Timeout:
                return create_response_object("Request timed out. Please try again.", None)
            except requests.exceptions.RequestException as e:
                logger.error(f"Network error with OpenAI API: {e}")
                return create_response_object(f"Network error: {str(e)}", None)
            except Exception as e:
                logger.error(f"Unexpected error with OpenAI: {e}")
                return create_response_object(f"Error: {str(e)}", None)
    
    def get_available_models(self) -> List[Dict]:
        """Get available OpenAI models"""
        return [
            {
                "name": "gpt-4o",
                "provider": "openai",
                "description": "Most capable OpenAI model with vision and function calling",
                "context_length": 128000,
                "max_output_tokens": 16384,
                "supports_vision": True,
                "supports_tools": True
            },
            {
                "name": "gpt-4o-mini",
                "provider": "openai",
                "description": "Lightweight GPT-4o model optimized for speed and cost",
                "context_length": 128000,
                "max_output_tokens": 16384,
                "supports_vision": True,
                "supports_tools": True
            },
            {
                "name": "gpt-4.1",
                "provider": "openai",
                "description": "Latest GPT-4.1 model with enhanced capabilities",
                "context_length": 1000000,
                "max_output_tokens": 16384,
                "supports_vision": True,
                "supports_tools": True
            },
            {
                "name": "gpt-4.1-mini",
                "provider": "openai",
                "description": "Efficient GPT-4.1 model with large context",
                "context_length": 1000000,
                "max_output_tokens": 16384,
                "supports_vision": True,
                "supports_tools": True
            },
            {
                "name": "gpt-4.1-nano",
                "provider": "openai",
                "description": "Ultra-efficient GPT-4.1 model for simple tasks",
                "context_length": 128000,
                "max_output_tokens": 8192,
                "supports_vision": False,
                "supports_tools": True
            }
        ]
    
    def validate_model_config(self, config: Dict) -> bool:
        """Validate OpenAI model configuration"""
        required_fields = ["name", "provider"]
        valid_models = ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano"]
        return (
            all(field in config for field in required_fields) and
            config.get("name") in valid_models and
            config.get("provider") == "openai"
        )


class ProviderManager:
    """Manages all AI providers"""
    
    def __init__(self):
        self.providers = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all available providers"""
        google_key = st.secrets.get("GEMINI_API_KEY")
        anthropic_key = st.secrets.get("ANTHROPIC_API_KEY")
        grok_key = st.secrets.get("XAI_API_KEY")
        openai_key = st.secrets.get("OPENAI_API_KEY")
        
        if google_key:
            self.providers["google"] = GoogleProvider(google_key)
        
        if anthropic_key:
            self.providers["anthropic"] = AnthropicProvider(anthropic_key)
        
        if grok_key:
            self.providers["grok"] = GrokProvider(grok_key)
            logger.info("Grok provider initialized successfully")
        
        if openai_key:
            self.providers["openai"] = OpenAIProvider(openai_key)
            logger.info("OpenAI provider initialized successfully")
        
        # Initialize Ollama provider (no API key needed)
        try:
            # Test if Ollama is available
            response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            if response.status_code == 200:
                self.providers["ollama"] = OllamaProvider()
                logger.info("Ollama provider initialized successfully")
            else:
                logger.warning("Ollama server not responding correctly")
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
    
    def get_provider(self, provider_name: str) -> BaseProvider:
        """Get a specific provider"""
        if provider_name not in self.providers:
            raise ValueError(f"Provider {provider_name} not available")
        return self.providers[provider_name]
    
    def generate_response(self, provider_name: str, messages: List[Dict], model_config: Dict, search_results: Optional[str] = None) -> Dict[str, Any]:
        """Generate response using specified provider"""
        provider = self.get_provider(provider_name)
        return provider.generate_response(messages, model_config, search_results)


def initialize_provider_manager():
    """Initialize the provider manager in session state"""
    if 'provider_manager' not in st.session_state:
        st.session_state.provider_manager = ProviderManager()

def generate_chat_response_with_providers(search_results: Optional[str] = None):
    """Updated generate_chat_response function using providers with metrics"""
    from utils import format_response_metrics
    
    messages = st.session_state.active_chat.get("messages", [])
    model_config = st.session_state.db.models.find_one({"name": st.session_state.active_chat['model']})
    
    if not messages:
        # Return simple response for empty chat
        return {
            "text": "I'm ready to chat! What can I help you with?",
            "metrics": None
        }
    
    if not model_config:
        # Return error response with no metrics
        return {
            "text": "Error: Model configuration not found.", 
            "metrics": None
        }
    
    try:
        provider_name = model_config.get("provider", "google")
        response_obj = st.session_state.provider_manager.generate_response(
            provider_name=provider_name,
            messages=messages,
            model_config=model_config,
            search_results=search_results
        )
        
        # Store metrics in session state for UI display
        if response_obj.get("metrics"):
            st.session_state.last_response_metrics = response_obj["metrics"]
        
        return response_obj
        
    except Exception as e:
        st.error(f"Error generating response: {e}")
        return {
            "text": "Sorry, I encountered an error while generating a response.",
            "metrics": None
        }