# AI Chat MP v2.0

Advanced AI chat application with intelligent LLM-powered query routing, context-aware prompt enhancement, dual weather systems, and comprehensive multi-provider AI support.

## 🌟 Key Features

### 🌍 **Dual Weather System**
- **OpenWeatherMap**: Worldwide weather forecasts for any location
- **WeatherFlow Tempest**: Personal weather station integration for hyper-local data
- **Smart routing**: Automatically detects home vs global weather queries

### 🧠 **LLM-Powered Intelligent Routing**
- **Dual-layer routing**: LLM-based intelligent decisions with rule-based fallbacks
- **Context awareness**: Analyzes query intent, complexity, and optimal response strategy
- **Route types**: Direct tool usage, tool+search, search-only, model knowledge, or combined approaches
- **Real-time optimization**: Dynamic routing decisions based on query characteristics

### 📊 **Response Metrics**
- **Real-time performance**: Response timing, tokens per second, input/output token counts
- **Estimation transparency**: Clear indicators when data is estimated vs actual
- **Clean display**: Ephemeral metrics that don't clutter conversation history

### 🤖 **Comprehensive Multi-Provider Support**
- **Google Gemini**: 2.0/2.5 Flash, Pro models with vision and tool support
- **Anthropic Claude**: 3.5 Haiku, Sonnet, Sonnet 4 with premium reasoning
- **OpenAI**: GPT-4o, GPT-4.1 variants with function calling
- **xAI Grok**: Grok 2, Grok 2 Mini with real-time information access
- **Ollama**: Local models (Llama 3.3, Mistral, etc.) with optimized caching

### 🛠️ **Advanced Tools & Context Enhancement**
- **Web Search**: Brave (privacy-focused) + Serper (Google results) with intelligent fallback
- **Weather Tools**: Global forecasts + WeatherFlow personal weather station integration
- **Query Enhancement**: LLM-powered query optimization with context injection
- **Prompt Architecture**: Context-aware system prompts with user personalization
- **User Profiles**: Location, timezone, preferences, and personal weather station data

## 🚀 Quick Start

### 1. Clone & Setup
```bash
git clone https://github.com/dkilleen4417/ai_chat_mp.git
cd ai_chat_mp
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Secrets
Create `.streamlit/secrets.toml`:
```toml
# AI Provider APIs
GEMINI_API_KEY = "your-google-api-key"
ANTHROPIC_API_KEY = "your-anthropic-key"

# Search APIs
SERPER_API_KEY = "your-serper-key"
BRAVE_API_KEY = "your-brave-key"

# Weather APIs
OPENWEATHER_API_KEY = "your-openweather-key"

# Personal Weather Station (optional)
WEATHERFLOW_ACCESS_TOKEN = "your-weatherflow-token"
WEATHERFLOW_STATION_ID = "your-station-id"
```

### 3. Start MongoDB
```bash
# Local MongoDB required for chat history
mongod --dbpath /path/to/your/db
```

### 4. Run Application
```bash
streamlit run src/main.py
```

## 🏗️ Architecture

### Core Components
- **`main.py`**: Application entry point and session management
- **`providers.py`**: Multi-provider AI abstractions (Google, Anthropic, OpenAI, xAI, Ollama)
- **`llm_intelligent_router.py`**: LLM-powered query routing with rule-based fallbacks
- **`prompt_enhancer.py`**: Context-aware prompt enhancement system
- **`user_profile.py`**: User personalization and context management
- **`tools.py`**: Tool registry and implementations
- **`ui.py`**: Streamlit interface components
- **`utils.py`**: Response metrics and token estimation

### Query Flow
```
User Query → Context Enhancement → LLM Router → Route Decision
├─ tool_direct → Direct Tool Usage
├─ tool_with_search → Tool + Search Verification
├─ search_only → Web Search First
├─ model_knowledge → AI Model Response
└─ combined → Multi-approach Response
```

## 🌡️ Weather Features

### Global Weather
```
"What's the weather in Tokyo?"
"Weather forecast for London, UK"
"How hot is it in Phoenix today?"
```

### Personal Weather Station
```
"What's the current temperature at home?"
"Check my personal weather station"
"PWS current conditions"
```

## 🔧 Development

### Project Structure
```
ai_chat_mp/
├── src/
│   ├── main.py              # Application entry
│   ├── providers.py         # AI provider management
│   ├── intelligent_router.py # Query routing logic
│   ├── tools.py            # Tool implementations
│   ├── ui.py               # User interface
│   ├── utils.py            # Utilities & metrics
│   ├── config.py           # Configuration
│   └── ...
├── .streamlit/
│   └── secrets.toml        # API keys & secrets
├── requirements.txt
└── README.md
```

### Adding New Tools
1. Implement function in `tools.py`
2. Register with `tool_registry.register_tool()`
3. Add patterns to `intelligent_router.py`
4. Test routing decisions

### Adding New Providers
1. Create provider class extending `BaseProvider`
2. Implement required methods
3. Add to `ProviderManager`
4. Update configuration

## 🧪 Testing

The intelligent router can be tested with various query types:
- Weather queries (should route to weather tools)
- Personal weather (should route to PWS tools)  
- Current events (should route to search)
- General knowledge (should use model knowledge)

## 📝 Recent Updates (v2.0)

### 🚀 **Major Architecture Overhaul**
- ✅ **LLM-Powered Routing**: Replaced rule-based routing with intelligent LLM decisions
- ✅ **Context-Aware Prompts**: Comprehensive prompt enhancement with user personalization
- ✅ **Multi-Provider Expansion**: Added OpenAI and xAI Grok support
- ✅ **Advanced User Profiles**: Location, timezone, and personal weather station integration
- ✅ **Enhanced Debug System**: Real-time routing decisions and performance metrics
- ✅ **Query Optimization**: LLM-powered query enhancement for better tool matching
- ✅ **Search Intelligence**: Quality assessment and provider selection optimization
- ✅ **System Prompt V2**: Comprehensive 2000+ character system prompt with versioning

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature-name`
2. Make changes with proper testing
3. Commit with descriptive messages
4. Push and create pull request

## 📄 License

[Add your license information here]

---

🤖 *AI Chat MP v2.0 - Intelligent conversational AI with advanced routing and weather integration*