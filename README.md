# AI Chat MP v2.0

Advanced AI chat application with intelligent query routing, dual weather systems, and multiple AI provider support.

## 🌟 Key Features

### 🌍 **Dual Weather System**
- **OpenWeatherMap**: Worldwide weather forecasts for any location
- **WeatherFlow Tempest**: Personal weather station integration for hyper-local data
- **Smart routing**: Automatically detects home vs global weather queries

### 🧠 **Intelligent Query Routing**
- **Confidence-based routing**: Tools, search, or model knowledge based on query analysis
- **Pattern matching**: Advanced keyword and context recognition
- **Multi-faceted decisions**: Considers tool confidence, search necessity, and model capabilities

### 📊 **Response Metrics**
- **Real-time performance**: Response timing, tokens per second, input/output token counts
- **Estimation transparency**: Clear indicators when data is estimated vs actual
- **Clean display**: Ephemeral metrics that don't clutter conversation history

### 🤖 **Multiple AI Providers**
- **Google Gemini**: Fast, reliable, with vision and tool support
- **Anthropic Claude**: Premium reasoning capabilities
- **Ollama**: Local models with optimized caching (keep-alive support)

### 🛠️ **Advanced Tools**
- **Web Search**: Brave + Serper with intelligent fallback
- **Weather Tools**: Global forecasts + personal weather station
- **Query Enhancement**: Automatic query optimization for better tool matching

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
- **`providers.py`**: AI provider abstractions (Google, Anthropic, Ollama)
- **`intelligent_router.py`**: Confidence-based query routing system
- **`tools.py`**: Tool registry and implementations
- **`ui.py`**: Streamlit interface components
- **`utils.py`**: Response metrics and token estimation

### Query Flow
```
User Query → Intelligent Router → Route Decision
├─ High Tool Confidence → Direct Tool Usage
├─ Medium Confidence → Tool + Search Verification  
├─ Search Needed → Web Search First
└─ General Knowledge → Model Response
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

- ✅ Implemented intelligent confidence-based routing
- ✅ Added WeatherFlow Tempest personal weather station support
- ✅ Enhanced response metrics with real-time performance data
- ✅ Optimized Ollama integration with model caching
- ✅ Fixed token counting to show current message metrics
- ✅ Production-ready codebase organization

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature-name`
2. Make changes with proper testing
3. Commit with descriptive messages
4. Push and create pull request

## 📄 License

[Add your license information here]

---

🤖 *AI Chat MP v2.0 - Intelligent conversational AI with advanced routing and weather integration*