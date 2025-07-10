# providers.py - Functional provider architecture

import google.generativeai as genai
import requests
import time
import json
from typing import List, Dict, Any, Optional
import streamlit as st
from tools import tool_registry
from logger import logger
from config import OLLAMA_KEEP_ALIVE
from utils import ResponseTimer, estimate_tokens, create_response_object
ss = st.session_state

def generate_google_response(messages: List[Dict], model_config: Dict, search_results: Optional[str] = None) -> Dict[str, Any]:
    """Generate response using Google AI with metrics"""
    genai.configure(api_key=ss.gemini_api_key)
    
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
            
            # Analyze context relevance for the current question
            from context_analyzer import context_analyzer
            current_question = messages[-1].get("content", "") if messages else ""
            context_analysis = context_analyzer.analyze_context_relevance(current_question, messages)
            
            # Debug logging for context analysis
            from main import add_debug_log
            add_debug_log(f"🔍 Context Analysis: {context_analysis['question_type']}")
            add_debug_log(f"📊 Confidence: {context_analysis['confidence']:.2f}")
            add_debug_log(f"💭 Reasoning: {context_analysis['reasoning']}")
            add_debug_log(f"🪟 Context Window: {context_analysis['context_window']} messages")
            
            # Log new chat suggestion if applicable
            if context_analysis.get("suggest_new_chat", False):
                add_debug_log(f"💡 New Chat Suggestion: {context_analysis['new_chat_reasoning']}")
                logger.info(f"New chat suggestion: {context_analysis['new_chat_reasoning']}")
            
            logger.info(f"Context analysis: {context_analysis}")
            
            # Store context analysis in session state for UI use
            ss.last_context_analysis = context_analysis
            
            # Get optimal context window
            optimal_messages = context_analyzer.get_optimal_context_window(context_analysis, messages)
            
            # Log context reduction
            if len(optimal_messages) < len(messages):
                add_debug_log(f"📉 Context Reduced: {len(messages)} → {len(optimal_messages)} messages")
                logger.info(f"Context reduced from {len(messages)} to {len(optimal_messages)} messages")
            
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

            # Use optimal context window instead of full message history
            for msg in optimal_messages:
                role = "model" if msg["role"] == "assistant" else "user"
                api_history.append({"role": role, "parts": [msg["content"]]})

            if search_results:
                api_history.append(
                    {
                        "role": "user",
                        "parts": [f"Here are the search results to help you answer:\\n\\n{search_results}"],
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
                    
                    # Debug logging for final response
                    from main import add_debug_log
                    add_debug_log(f"✅ Final Response: {final_text[:200]}...")
                    logger.info(f"Final model response: {final_text}")
                    
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
                
                # Debug logging for tool execution
                from main import add_debug_log
                add_debug_log(f"🔧 Tool Executed: {tool_name}")
                add_debug_log(f"📝 Tool Args: {args}")
                add_debug_log(f"📊 Tool Output: {tool_output[:200]}...")
                logger.info(f"Tool {tool_name} executed successfully with args: {args}")
                logger.info(f"Tool output: {tool_output}")
                
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
            logger.exception("Google provider failed")
            st.error("Sorry, the AI backend encountered an error. Please check logs.")
            error_text = "Sorry, I encountered an error while generating a response."
            metrics = {
                "response_time": timer.elapsed_time,
                "input_tokens": input_tokens,
                "output_tokens": estimate_tokens(error_text),
                "estimated": ["input_tokens", "output_tokens"]
            }
            return create_response_object(error_text, metrics)

def generate_anthropic_response(messages: List[Dict], model_config: Dict, search_results: Optional[str] = None) -> Dict[str, Any]:
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
            url = ss.api_endpoints['anthropic']
            
            # Headers
            headers = {
                "x-api-key": ss.anthropic_api_key,
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
                    "content": f"Here are the search results:\\n\\n{search_results}"
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
            
            final_text = "\\n".join(content_parts)
            
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

def generate_grok_response(messages: List[Dict], model_config: Dict, search_results: Optional[str] = None) -> Dict[str, Any]:
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
            url = ss.api_endpoints['xai']
            
            # Headers
            headers = {
                "Authorization": f"Bearer {ss.xai_api_key}",
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
                    "content": f"Here are the search results to help you answer:\\n\\n{search_results}"
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

def generate_openai_response(messages: List[Dict], model_config: Dict, search_results: Optional[str] = None) -> Dict[str, Any]:
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
            url = ss.api_endpoints['openai']
            
            # Headers
            headers = {
                "Authorization": f"Bearer {ss.openai_api_key}",
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
                    "content": f"Here are the search results to help you answer:\\n\\n{search_results}"
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

def generate_ollama_response(messages: List[Dict], model_config: Dict, search_results: Optional[str] = None) -> Dict[str, Any]:
    """Generate response using Ollama via HTTP with metrics"""
    with ResponseTimer() as timer:
        try:
            # Calculate input tokens for metrics (current user message only)
            current_user_message = messages[-1].get("content", "") if messages else ""
            input_text = current_user_message
            if search_results:
                input_text += search_results
            input_tokens = estimate_tokens(input_text)
            
            url = f"{ss.api_endpoints['ollama']}/api/chat"
            
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
                    "content": f"Here are the search results to help you answer:\\n\\n{search_results}"
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
            logger.exception("Ollama provider failed")
            st.error(f"Ollama Error: {e}")
            error_text = "Sorry, I encountered an error while generating a response."
            metrics = {
                "response_time": timer.elapsed_time,
                "input_tokens": input_tokens,
                "output_tokens": estimate_tokens(error_text),
                "estimated": ["input_tokens", "output_tokens"]
            }
            return create_response_object(error_text, metrics)