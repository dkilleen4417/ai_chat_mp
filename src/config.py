# config.py

# --- Database Configuration ---
MONGO_LOCAL_URI = "mongodb://localhost:27017/"
MONGO_LOCAL_DB_NAME = "ai_chat_mp"

# --- AI Model Configuration ---
DECISION_MODEL = "gemini-2.5-flash-lite-preview-06-17"
DEFAULT_MODEL = "gemini-2.5-flash-lite-preview-06-17"

# The endpoint for Google's Generative AI services.
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com"

# --- UI Configuration ---
LLM_AVATAR = "🤖"
USER_AVATAR = "😎"

# --- Search Grounding Configuration ---
SEARCH_GROUNDING_SYSTEM_PROMPT = """You are an expert Information Triage Specialist for a large language model. Your primary role is to determine if a user's prompt requires an external web search to provide an accurate, current, and meaningful response. Your decision must be based on whether the model's internal knowledge is likely to be sufficient, outdated, or incomplete.

**Your task is to analyze the user's prompt and respond ONLY with a JSON object in the specified format.**

**CRITERIA FOR REQUIRING A SEARCH (`"needs_search": true`):**
A search is required if the prompt asks for:
1.  **Current or Recent Events:** Information about news, events, or developments that have happened in the last year.
    * *Example: "Who won the F1 race last weekend?"*
2.  **Real-Time Information:** Data that changes rapidly and frequently.
    * *Example: "What's the current stock price of Google?" or "What's the weather in London?"*
3.  **Future Information:** Details about upcoming, scheduled events.
    * *Example: "When is the next solar eclipse?"*
4.  **Specific, Niche, or Time-Sensitive Factual Data:** Information about non-historical figures, specific product details, store hours, or data that has likely changed since my knowledge cutoff (early 2023).
    * *Example: "What are the system requirements for the latest version of Adobe Photoshop?"*
5.  **URL or Website-Specific Queries:** Questions about the content, status, or validity of a specific website.
    * *Example: "Is the website example.com down right now?"*

**CRITERIA FOR NOT REQUIRING A SEARCH (`"needs_search": false`):**
A search is NOT required for:
1.  **General and Established Knowledge:** Facts that are timeless or well-established historical information.
    * *Example: "What is the capital of France?"*
2.  **Creative, Mathematical, or Logic Tasks:** Requests to generate text (poems, code, summaries), solve math problems, or perform reasoning tasks.
    * *Example: "Write a haiku about the moon." or "What is 1024 / 8?"*
3.  **Broad or Philosophical Questions:** Open-ended questions that do not have a single factual answer.
    * *Example: "What is the key to happiness?"*
4.  **General Conversational Prompts:** Greetings, simple questions about the AI, or requests for jokes.
    * *Example: "How are you today?"*

---
**SEARCH PROVIDER SELECTION:**
- Use `"brave"` for general web searches, privacy-focused queries, or when you want diverse results.
- Use `"serper"` for Google-specific results, local searches, or when you need structured data.

**RESPONSE FORMAT:**
Respond with a JSON object containing three keys:
- `"needs_search"` (boolean): Whether a search is needed
- `"search_provider"` (string): Either "brave" or "serper"
- `"reasoning"` (string): A concise explanation for the decision

**EXAMPLE RESPONSES:**
```json
{
  "needs_search": true,
  "search_provider": "brave",
  "reasoning": "Query requires current information about recent events"
}

{
  "needs_search": false,
  "search_provider": "serper",
  "reasoning": "Question can be answered with general knowledge"
}
```

**Example 1:**
User Message: "What were the main announcements from Apple's last keynote event?"
Your Response:
{
    "needs_search": true,
    "reasoning": "The user is asking about a recent event, which requires a search for current information."
}

**Example 2:**
User Message: "Can you explain the concept of photosynthesis?"
Your Response:
{
    "needs_search": false,
    "reasoning": "This is a request for general and established scientific knowledge, which does not require a web search."
}

**Example 3:**
User Message: "What time does the nearest coffee shop close?"
Your Response:
{
    "needs_search": true,
    "reasoning": "This query requires specific, real-time factual data (store hours) that is location-dependent and not in my internal knowledge base."
}
"""

# Add this to your config.py file

MODEL_TEMPLATES = {
    # Anthropic Models
    "Claude 3.5 Haiku": {
        "name": "claude-3-5-haiku-20241022",
        "provider": "anthropic",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_output_tokens": 8192,
        "max_input_tokens": 200000,
        "input_price": 0.80,
        "output_price": 4.0,
        "text_input": True,
        "image_input": True,
        "text_output": True,
        "image_output": False,
        "tools": True,
        "functions": True,
        "thinking": False,
        "native_grounding": False
    },
    "Claude 3.5 Sonnet": {
        "name": "claude-3-5-sonnet-20241022",
        "provider": "anthropic",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_output_tokens": 8192,
        "max_input_tokens": 200000,
        "input_price": 3.0,
        "output_price": 15.0,
        "text_input": True,
        "image_input": True,
        "text_output": True,
        "image_output": False,
        "tools": True,
        "functions": True,
        "thinking": False,
        "native_grounding": False
    },
    "Claude Sonnet 4": {
        "name": "claude-sonnet-4-20250514",
        "provider": "anthropic",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_output_tokens": 64000,
        "max_input_tokens": 200000,
        "input_price": 3.0,
        "output_price": 15.0,
        "text_input": True,
        "image_input": True,
        "text_output": True,
        "image_output": False,
        "tools": True,
        "functions": True,
        "thinking": False,
        "native_grounding": False
    },
    
    # Google Models
    "Gemini 2.0 Flash": {
        "name": "gemini-2.0-flash-exp",
        "provider": "google",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_output_tokens": 8192,
        "max_input_tokens": 1000000,
        "input_price": 0.0,
        "output_price": 0.0,
        "text_input": True,
        "image_input": True,
        "text_output": True,
        "image_output": True,
        "tools": True,
        "functions": True,
        "thinking": False,
        "native_grounding": True
    },
    "Gemini 2.0 Flash Lite": {
        "name": "gemini-2.0-flash-lite",
        "provider": "google",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_output_tokens": 8192,
        "max_input_tokens": 1000000,
        "input_price": 0.0,
        "output_price": 0.0,
        "text_input": True,
        "image_input": True,
        "text_output": True,
        "image_output": False,
        "tools": True,
        "functions": True,
        "thinking": False,
        "native_grounding": True
    },
    "Gemini 2.5 Flash": {
        "name": "gemini-2.5-flash",
        "provider": "google",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_output_tokens": 8192,
        "max_input_tokens": 1000000,
        "input_price": 0.0,
        "output_price": 0.0,
        "text_input": True,
        "image_input": True,
        "text_output": True,
        "image_output": False,
        "tools": True,
        "functions": True,
        "thinking": True,
        "native_grounding": True
    },
    "Gemini 2.5 Flash Lite Preview": {
        "name": "gemini-2.5-flash-lite-preview-06-17",
        "provider": "google",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_output_tokens": 8192,
        "max_input_tokens": 1000000,
        "input_price": 0.0,
        "output_price": 0.0,
        "text_input": True,
        "image_input": True,
        "text_output": True,
        "image_output": False,
        "tools": True,
        "functions": True,
        "thinking": False,
        "native_grounding": True
    },
    "Gemini 2.5 Pro": {
        "name": "gemini-2.5-pro",
        "provider": "google",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_output_tokens": 8192,
        "max_input_tokens": 1000000,
        "input_price": 1.25,
        "output_price": 5.0,
        "text_input": True,
        "image_input": True,
        "text_output": True,
        "image_output": False,
        "tools": True,
        "functions": True,
        "thinking": True,
        "native_grounding": True
    },
    "Gemini 1.5 Flash": {
        "name": "gemini-1.5-flash",
        "provider": "google",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_output_tokens": 8192,
        "max_input_tokens": 1000000,
        "input_price": 0.0,
        "output_price": 0.0,
        "text_input": True,
        "image_input": True,
        "text_output": True,
        "image_output": False,
        "tools": True,
        "functions": True,
        "thinking": False,
        "native_grounding": True
    },
    "Gemini 1.5 Pro": {
        "name": "gemini-1.5-pro",
        "provider": "google",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_output_tokens": 8192,
        "max_input_tokens": 2000000,
        "input_price": 0.0,
        "output_price": 0.0,
        "text_input": True,
        "image_input": True,
        "text_output": True,
        "image_output": False,
        "tools": True,
        "functions": True,
        "thinking": False,
        "native_grounding": True
    },
    
    # OpenAI Models (requires OpenAI provider)
    "GPT-4o": {
        "name": "gpt-4o",
        "provider": "openai",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_output_tokens": 16384,
        "max_input_tokens": 128000,
        "input_price": 3.0,
        "output_price": 10.0,
        "text_input": True,
        "image_input": True,
        "text_output": True,
        "image_output": False,
        "tools": True,
        "functions": True,
        "thinking": False,
        "native_grounding": False
    },
    "GPT-4o Mini": {
        "name": "gpt-4o-mini",
        "provider": "openai",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_output_tokens": 16384,
        "max_input_tokens": 128000,
        "input_price": 0.15,
        "output_price": 0.60,
        "text_input": True,
        "image_input": True,
        "text_output": True,
        "image_output": False,
        "tools": True,
        "functions": True,
        "thinking": False,
        "native_grounding": False
    },
    "GPT-4.1": {
        "name": "gpt-4.1",
        "provider": "openai",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_output_tokens": 16384,
        "max_input_tokens": 1000000,
        "input_price": 2.25,
        "output_price": 7.50,
        "text_input": True,
        "image_input": True,
        "text_output": True,
        "image_output": False,
        "tools": True,
        "functions": True,
        "thinking": False,
        "native_grounding": False
    },
    "GPT-4.1 Mini": {
        "name": "gpt-4.1-mini",
        "provider": "openai",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_output_tokens": 16384,
        "max_input_tokens": 1000000,
        "input_price": 0.10,
        "output_price": 0.40,
        "text_input": True,
        "image_input": True,
        "text_output": True,
        "image_output": False,
        "tools": True,
        "functions": True,
        "thinking": False,
        "native_grounding": False
    },
    "GPT-4.1 Nano": {
        "name": "gpt-4.1-nano",
        "provider": "openai",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_output_tokens": 8192,
        "max_input_tokens": 128000,
        "input_price": 0.05,
        "output_price": 0.20,
        "text_input": True,
        "image_input": False,
        "text_output": True,
        "image_output": False,
        "tools": True,
        "functions": True,
        "thinking": False,
        "native_grounding": False
    },
    
    # XAI Models (requires XAI provider)
    "Grok 2": {
        "name": "grok-2",
        "provider": "xai",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_output_tokens": 4096,
        "max_input_tokens": 128000,
        "input_price": 2.0,
        "output_price": 10.0,
        "text_input": True,
        "image_input": True,
        "text_output": True,
        "image_output": False,
        "tools": True,
        "functions": True,
        "thinking": False,
        "native_grounding": False
    },
    "Grok 2 Mini": {
        "name": "grok-2-mini",
        "provider": "xai",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_output_tokens": 4096,
        "max_input_tokens": 128000,
        "input_price": 0.20,
        "output_price": 1.0,
        "text_input": True,
        "image_input": False,
        "text_output": True,
        "image_output": False,
        "tools": True,
        "functions": True,
        "thinking": False,
        "native_grounding": False
    }
}