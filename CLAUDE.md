# Claude Code Rules and Context

## System Information
- **Hardware**: Mac Studio with M2 Max processor
- **OS**: macOS (Apple Silicon)
- **Python**: Use `python3` command (not `python`)
- **Architecture**: ARM64/AArch64

## Project Context
- **Project**: AI Chat MP - Advanced AI chat application with intelligent query routing
- **Main Branch**: `master` (stable version with debug panel)
- **Current Branch**: `add-grok-provider` (recently committed and pushed)
- **Features**: Intelligent routing, dual weather systems, debug panel for internal conversations, Grok provider support

## Development Guidelines
- Always use `python3` for Python execution on this Mac Studio
- This is an Apple Silicon Mac - be aware of architecture-specific considerations
- MongoDB is used for chat storage
- Multiple AI providers: Google Gemini, Anthropic Claude, Ollama

## Key Commands
- **Run app**: `streamlit run src/main.py`
- **Test**: `python3 -m pytest tests/`
- **Install deps**: `pip3 install -r requirements.txt`

## Current Features
- **🧠 Intelligent Query Routing**: Confidence-based routing to tools, search, or model knowledge
- **🌡️ Dual Weather System**: OpenWeatherMap + WeatherFlow Tempest personal weather station
- **🐞 Debug Panel**: Shows internal agent conversations and routing decisions  
- **🔍 Advanced Search**: Brave + Serper with intelligent fallback
- **🤖 Multiple AI Providers**: Google Gemini, Anthropic Claude, Ollama, xAI Grok
- **👤 User Profile**: Personalization and context enhancement
- **⚡ Enhanced Debug Logging**: Question/response tracking with metrics

## File Structure
- `src/main.py` - Application entry point with debug logging
- `src/intelligent_router.py` - Confidence-based query routing
- `src/debug_panel.py` - Debug panel for internal conversations
- `src/providers.py` - AI provider management
- `src/tools.py` - Tool implementations (weather, search)
- `src/ui.py` - Streamlit interface
- `.streamlit/secrets.toml` - API keys configuration